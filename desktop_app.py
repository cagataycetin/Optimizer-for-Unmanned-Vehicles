"""İHA tasarım asistanı: yalnızca standart Python/Tkinter kullanan masaüstü taslak."""

import csv
import json
import sqlite3
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app_service import NUMERIC_FIELDS, ProjectStore, aircraft_from_fields, load_project, sample_aircraft, save_project
from uav import DEFAULT_DB, ROOT, flight_conditions

BG = "#F4F6FA"
WHITE = "#FFFFFF"
NAVY = "#141D32"
INK = "#202B40"
MUTED = "#758096"
LINE = "#E5E9F1"
PURPLE = "#6654D9"
PALE = "#F0EDFF"
TEAL = "#159B8E"
AMBER = "#B87916"
FONT = "Segoe UI"


def label(parent, text="", size=11, color=INK, bold=False, bg=None, **kwargs):
    return tk.Label(parent, text=text, font=(FONT, size, "bold" if bold else "normal"),
                    fg=color, bg=bg or parent.cget("bg"), anchor="w", justify="left", **kwargs)


def button(parent, text, command, primary=False, **kwargs):
    return tk.Button(parent, text=text, command=command, font=(FONT, 10, "bold"),
                     bg=PURPLE if primary else WHITE, fg=WHITE if primary else INK,
                     activebackground="#5543C4" if primary else PALE,
                     activeforeground=WHITE if primary else PURPLE,
                     relief="flat", bd=0, highlightthickness=0, padx=16, pady=10, cursor="hand2", **kwargs)


def panel(parent, **kwargs):
    return tk.Frame(parent, bg=WHITE, highlightbackground=LINE, highlightthickness=1, **kwargs)


class ProfileChart(tk.Canvas):
    def __init__(self, parent, height=240):
        super().__init__(parent, bg=WHITE, height=height, highlightthickness=0)
        self.series = []
        self.bind("<Configure>", lambda event: self.draw())

    def set_series(self, series):
        self.series = [(name, points, color) for name, points, color in series if points]
        self.draw()

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 100 or h < 80:
            return
        if not self.series:
            self.create_text(w / 2, h / 2 - 10, text="Bu seçim için koordinat verisi henüz yok.",
                             fill=MUTED, font=(FONT, 11))
            self.create_text(w / 2, h / 2 + 18, text="Kütüphaneden bir DAT dosyası ekleyebilirsiniz.",
                             fill=MUTED, font=(FONT, 10))
            return
        left, right = 44, w - 28
        top, bottom = 48, h - 40
        min_y = min(y for _, points, _ in self.series for _, y in points) - 0.035
        max_y = max(y for _, points, _ in self.series for _, y in points) + 0.035
        # İki eksende aynı ölçek: profil şekli görüntüde bozulmaz.
        scale = min((right - left) / 1.04, (bottom - top) / (max_y - min_y))
        x0 = left + ((right - left) - scale) / 2
        y0 = (top + bottom) / 2 + scale * (max_y + min_y) / 2
        for tick in (0, 0.25, 0.5, 0.75, 1):
            x = x0 + tick * scale
            self.create_line(x, top, x, bottom, fill="#EDF0F5", dash=(3, 4))
            self.create_text(x, h - 20, text=f"{tick:g}", fill=MUTED, font=(FONT, 9))
        self.create_line(left, y0, right, y0, fill=LINE, dash=(4, 3))
        self.create_text(w - 20, h - 20, text="x/c", fill=MUTED, font=(FONT, 9))
        self.create_text(22, 48, text="y/c", fill=MUTED, font=(FONT, 9))
        legend_x = 24
        for name, points, color in self.series:
            self.create_line(legend_x, 22, legend_x + 20, 22, fill=color, width=3)
            self.create_text(legend_x + 27, 22, text=name, fill=INK, font=(FONT, 10), anchor="w")
            legend_x += 155
            coords = [v for x, y in points for v in (x0 + x * scale, y0 - y * scale)]
            if len(coords) >= 4:
                self.create_line(*coords, fill=color, width=2.5, smooth=False)


class UAVApp(tk.Tk):
    def __init__(self, db_path=DEFAULT_DB):
        global FONT
        super().__init__()
        self.title("İHA Optimizasyon | Tasarım Asistanı")
        self.configure(bg=BG)
        self.geometry(f"{min(1370, self.winfo_screenwidth() - 50)}x{min(920, self.winfo_screenheight() - 70)}")
        self.minsize(1040, 710)
        self.option_add("*Font", (FONT, 10))
        families = {name.casefold() for name in tkfont.families()}
        FONT = next((name for name in ("Segoe UI", "DejaVu Sans", "Helvetica")
                     if name.casefold() in families), tkfont.nametofont("TkDefaultFont").actual("family"))
        for font_name in ("TkDefaultFont", "TkTextFont", "TkMenuFont"):
            tkfont.nametofont(font_name).configure(family=FONT, size=10)
        self.store = ProjectStore(db_path)
        self.records = self.store.airfoils()
        self.lookup = {row["id"]: row for row in self.records}
        self.names = {row["name"]: row["id"] for row in self.records}
        self.results = None
        self.current_page = "home"
        self.project_path = None
        self.result_labels = {}
        sample = sample_aircraft()
        sample["name"] = "İlk İHA Tasarımım"
        self.fields = {key: tk.StringVar(self, str(value)) for key, value in sample.items()}
        self.fields["current_airfoil"].set(self.lookup["naca2412"]["name"])
        self.form_message = tk.StringVar(self, "Örnek değerler yüklü. Kendi tasarımınız için düzenleyin.")
        self.status_message = tk.StringVar(self, "Hazır  •  Yerel çalışma alanı")
        self.search_var = tk.StringVar(self)
        self.family_var = tk.StringVar(self, "Tüm aileler")
        self.library_selection = "naca2412"
        self.baseline_var = tk.StringVar(self, "NACA 2412")
        self.candidate_var = tk.StringVar(self, "S1223")
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        for var in self.fields.values():
            var.trace_add("write", self.invalidate_results)
        self._style()
        self._shell()
        self.show_page("home")

    def _style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground=WHITE, background=WHITE, foreground=INK,
                        bordercolor=LINE, arrowcolor=MUTED, padding=8)
        style.map("TCombobox", fieldbackground=[("readonly", WHITE)], selectbackground=[("readonly", WHITE)],
                  selectforeground=[("readonly", INK)])
        style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=INK,
                        rowheight=38, borderwidth=0, font=(FONT, 10))
        style.configure("Treeview.Heading", background="#F8F9FC", foreground=MUTED,
                        relief="flat", padding=10, font=(FONT, 9, "bold"))
        style.map("Treeview", background=[("selected", PALE)], foreground=[("selected", PURPLE)])
        style.configure("Vertical.TScrollbar", background=LINE, troughcolor=BG, borderwidth=0, arrowsize=12)

    def _shell(self):
        sidebar = tk.Frame(self, bg=NAVY, width=224)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        brand = tk.Frame(sidebar, bg=NAVY)
        brand.pack(fill="x", padx=24, pady=(32, 0))
        logo = tk.Canvas(brand, width=42, height=42, bg=NAVY, highlightthickness=0)
        logo.pack(side="left", padx=(0, 10))
        logo.create_polygon(4, 25, 34, 9, 26, 37, 20, 25, fill="#9C91F7", outline="")
        logo.create_line(20, 25, 34, 9, fill=NAVY, width=2)
        label(brand, "AERO\nDESIGN LAB", 12, WHITE, True, bg=NAVY).pack(side="left")
        label(sidebar, "İHA TASARIM ASİSTANI", 8, "#7F8BA5", True, bg=NAVY).pack(anchor="w", padx=26, pady=(14, 32))
        self.nav_buttons = {}
        for key, text in (("home", "01   Genel Bakış"), ("design", "02   İHA Tasarımı"),
                          ("library", "03   Airfoil Kütüphanesi"), ("compare", "04   Karşılaştırma"),
                          ("roadmap", "05   Yol Haritası")):
            nav = tk.Button(sidebar, text=text, anchor="w", command=lambda k=key: self.show_page(k),
                            bg=NAVY, fg="#AEB8CC", activebackground="#27324B", activeforeground=WHITE,
                            bd=0, highlightthickness=0, relief="flat", padx=16, pady=15, font=(FONT, 10), cursor="hand2")
            nav.pack(fill="x", padx=12, pady=3)
            self.nav_buttons[key] = nav
        foot = tk.Frame(sidebar, bg="#1E2941")
        foot.pack(side="bottom", fill="x", padx=18, pady=22)
        label(foot, "Geliştirme sürümü  0.2", 10, WHITE, True).pack(anchor="w", padx=14, pady=(15, 5))
        label(foot, "Veriyle başla.\nTasarımını adım adım geliştir.", 9, "#ACB7CB").pack(anchor="w", padx=14, pady=(0, 15))
        right = tk.Frame(self, bg=BG)
        right.pack(side="left", fill="both", expand=True)
        topbar = tk.Frame(right, bg=WHITE, height=67, highlightthickness=1, highlightbackground=LINE)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)
        self.breadcrumb = label(topbar, "Çalışma Alanı  /  Genel Bakış", 10, MUTED)
        self.breadcrumb.pack(side="left", padx=28)
        label(topbar, "●  ÇEVRİMDIŞI HAZIR", 9, TEAL, True).pack(side="right", padx=28)
        statusbar = tk.Frame(right, bg=WHITE)
        statusbar.pack(side="bottom", fill="x")
        label(statusbar, textvariable=self.status_message, size=9, color=MUTED).pack(anchor="w", padx=28, pady=9)
        self.scroll = tk.Canvas(right, bg=BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(right, orient="vertical", command=self.scroll.yview)
        scrollbar.pack(side="right", fill="y")
        self.scroll.pack(side="left", fill="both", expand=True)
        self.scroll.configure(yscrollcommand=scrollbar.set)
        self.content = tk.Frame(self.scroll, bg=BG)
        self.content_window = self.scroll.create_window((0, 0), window=self.content, anchor="nw")
        self.content.bind("<Configure>", lambda e: self.scroll.configure(scrollregion=self.scroll.bbox("all")))
        self.scroll.bind("<Configure>", lambda e: self.scroll.itemconfigure(self.content_window, width=e.width))
        self.bind_all("<MouseWheel>", self._wheel)
        self.bind_all("<Button-4>", lambda e: self.scroll.yview_scroll(-3, "units"))
        self.bind_all("<Button-5>", lambda e: self.scroll.yview_scroll(3, "units"))
        self.bind("<Control-s>", lambda e: self.save_design())
        self.bind("<Control-o>", lambda e: self.open_design())

    def _wheel(self, event):
        if event.widget.winfo_class() not in ("Treeview", "TCombobox"):
            self.scroll.yview_scroll(-int(event.delta / 120) if abs(event.delta) >= 120 else -event.delta, "units")

    def show_page(self, page):
        self.current_page = page
        self.result_labels = {}
        for widget in self.content.winfo_children():
            widget.destroy()
        for key, nav in self.nav_buttons.items():
            nav.configure(bg="#2C3053" if key == page else NAVY, fg=WHITE if key == page else "#AEB8CC")
        names = {"home": "Genel Bakış", "design": "İHA Tasarımı", "library": "Airfoil Kütüphanesi",
                 "compare": "Karşılaştırma", "roadmap": "Yol Haritası"}
        self.breadcrumb.configure(text="Çalışma Alanı  /  " + names[page])
        self.body = tk.Frame(self.content, bg=BG)
        self.body.pack(fill="both", expand=True, padx=28, pady=28)
        getattr(self, "page_" + page)()
        self.scroll.yview_moveto(0)

    def heading(self, title, description):
        label(self.body, title, 25, bold=True).pack(anchor="w")
        label(self.body, description, 10, MUTED, wraplength=850).pack(anchor="w", pady=(7, 24))

    def metric_row(self, parent, specs):
        row = tk.Frame(parent, bg=parent.cget("bg"))
        row.pack(fill="x", pady=(0, 22))
        for i, (title, value, note, color) in enumerate(specs):
            row.columnconfigure(i, weight=1, uniform="metric")
            card = panel(row)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 7, 0 if i == len(specs) - 1 else 7))
            label(card, title, 9, MUTED, True).pack(anchor="w", padx=18, pady=(17, 8))
            number = label(card, value, 25, color, True)
            number.pack(anchor="w", padx=18)
            label(card, note, 9, MUTED).pack(anchor="w", padx=18, pady=(4, 17))
        return row

    def page_home(self):
        self.heading("Tasarım yolculuğun burada başlıyor.", "İHA bilgilerini tanımla, profilleri keşfet ve bir sonraki analizine hazırlan.")
        summary = self.store.summary()
        self.metric_row(self.body, [
            ("ADAY AIRFOIL", str(summary["candidate_airfoils"]), "Kaynaklı profil kataloğu", PURPLE),
            ("KOORDİNAT HAZIR", str(summary["airfoils_with_geometry"]), "İncelenebilir profil geometrisi", TEAL),
            ("AERODİNAMİK ANALİZ", str(summary["polar_runs"]), "Bir sonraki geliştirme adımı", AMBER),
        ])
        hero = tk.Frame(self.body, bg="#EDEAFB", highlightbackground="#E0DBFA", highlightthickness=1)
        hero.pack(fill="x", pady=(0, 22))
        text = tk.Frame(hero, bg="#EDEAFB")
        text.pack(side="left", fill="both", expand=True, padx=26, pady=25)
        label(text, "İLK ADIM  /  TASARIM GİRDİLERİ", 9, PURPLE, True).pack(anchor="w")
        label(text, "Fikrini bir tasarıma dönüştür.", 21, INK, True).pack(anchor="w", pady=(10, 8))
        label(text, "Kütle, kanat geometrisi ve seyir hızını gir.\nUçuş koşullarını hesaplayarak analize başla.",
              11, MUTED).pack(anchor="w")
        actions = tk.Frame(text, bg="#EDEAFB")
        actions.pack(anchor="w", pady=(18, 0))
        button(actions, "Tasarımı Oluştur  →", lambda: self.show_page("design"), True).pack(side="left", padx=(0, 10))
        button(actions, "Kayıtlı Tasarımı Aç", self.open_design).pack(side="left")
        plane = tk.Canvas(hero, width=220, height=190, bg="#EDEAFB", highlightthickness=0)
        plane.pack(side="right", padx=22)
        plane.create_oval(22, 13, 202, 185, outline="#DBD5F5", width=1)
        plane.create_oval(42, 33, 182, 165, outline="#DBD5F5", width=1)
        plane.create_polygon(110, 24, 119, 92, 193, 125, 193, 139, 120, 121, 116, 157,
                             143, 169, 143, 179, 110, 171, 77, 179, 77, 169, 104, 157,
                             100, 121, 27, 139, 27, 125, 101, 92, fill="#7768CD", outline="")
        def fit_hero(event):
            if event.width < 940:
                plane.pack_forget()
            elif not plane.winfo_manager():
                plane.pack(side="right", padx=22)
        hero.bind("<Configure>", fit_hero)
        lower = tk.Frame(self.body, bg=BG)
        lower.pack(fill="x")
        lower.columnconfigure(0, weight=3)
        lower.columnconfigure(1, weight=2)
        profile = panel(lower)
        profile.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        label(profile, "Profil geometrisine yakından bak", 13, bold=True).pack(anchor="w", padx=20, pady=(19, 4))
        label(profile, "İki gerçek profil, ortak kord ölçeğinde.", 9, MUTED).pack(anchor="w", padx=20)
        chart = ProfileChart(profile, 220)
        chart.pack(fill="x", padx=12, pady=(4, 10))
        chart.set_series([("NACA 2412", self.store.geometry("naca2412"), PURPLE),
                          ("S1223", self.store.geometry("s1223"), TEAL)])
        next_step = panel(lower)
        next_step.grid(row=0, column=1, sticky="nsew")
        label(next_step, "Çalışma alanın hazır", 13, bold=True).pack(anchor="w", padx=20, pady=(19, 15))
        for number, title, subtitle in [("01", "Tasarımını tanımla", "İHA ve uçuş koşullarını gir."),
                                         ("02", "Profilleri incele", "Geometrileri üst üste karşılaştır."),
                                         ("03", "Analiz verisini tamamla", "Polarlar için bir sonraki aşamaya geç.")]:
            row = tk.Frame(next_step, bg=WHITE)
            row.pack(fill="x", padx=20, pady=(0, 16))
            label(row, number, 13, PURPLE, True).pack(side="left", padx=(0, 14))
            detail = tk.Frame(row, bg=WHITE)
            detail.pack(side="left")
            label(detail, title, 10, bold=True).pack(anchor="w")
            label(detail, subtitle, 9, MUTED).pack(anchor="w", pady=(3, 0))
        button(next_step, "Kütüphaneyi Aç  →", lambda: self.show_page("library")).pack(anchor="w", padx=20, pady=(0, 15))

    def field(self, parent, row, column, key, title, unit=""):
        block = tk.Frame(parent, bg=WHITE)
        block.grid(row=row, column=column, sticky="ew", padx=(0, 18), pady=(0, 16))
        label(block, title + (f"  ·  {unit}" if unit else ""), 9, MUTED, True).pack(anchor="w", pady=(0, 7))
        if key == "current_airfoil":
            entry = ttk.Combobox(block, textvariable=self.fields[key], values=list(self.names), state="readonly")
        else:
            entry = tk.Entry(block, textvariable=self.fields[key], font=(FONT, 11),
                             bg="#FCFCFE", fg=INK, insertbackground=PURPLE, relief="flat",
                             highlightthickness=1, highlightbackground=LINE, highlightcolor=PURPLE)
        entry.pack(fill="x", ipady=7 if key != "current_airfoil" else 0)
        self.form_entries[key] = entry

    def page_design(self):
        self.heading("İHA Tasarımı", "Tasarımını tanımla. Uçuş koşullarını hesapla, kaydet ve kaldığın yerden devam et.")
        actions = tk.Frame(self.body, bg=BG)
        actions.pack(fill="x", pady=(0, 18))
        button(actions, "Örnek Değerleri Yükle", self.load_sample).pack(side="left", padx=(0, 10))
        button(actions, "Tasarım Aç", self.open_design).pack(side="left", padx=(0, 10))
        button(actions, "Tasarımı Kaydet", self.save_design).pack(side="right")
        form = panel(self.body)
        form.pack(fill="x", pady=(0, 18))
        label(form, "Tasarım ve uçuş bilgileri", 14, bold=True).pack(anchor="w", padx=22, pady=(20, 5))
        label(form, "İlk model: klasik sabit kanat · düz, yatay ve ivmesiz uçuş", 9, MUTED).pack(anchor="w", padx=22, pady=(0, 20))
        grid = tk.Frame(form, bg=WHITE)
        grid.pack(fill="x", padx=(22, 4))
        grid.columnconfigure(0, weight=1, uniform="fields")
        grid.columnconfigure(1, weight=1, uniform="fields")
        self.form_entries = {}
        self.field(grid, 0, 0, "name", "Tasarım adı")
        self.field(grid, 0, 1, "current_airfoil", "Mevcut airfoil")
        for i, (key, title, unit) in enumerate(NUMERIC_FIELDS):
            self.field(grid, 1 + i // 2, i % 2, key, title, unit)
        strip = tk.Frame(form, bg="#F8F9FC")
        strip.pack(fill="x", padx=22, pady=(0, 20))
        label(strip, "Ondalık ayırıcı olarak virgül veya nokta kullanabilirsin. Hız, hava hızıdır.",
              9, MUTED, wraplength=780).pack(anchor="w", padx=12, pady=10)
        bottom = tk.Frame(form, bg=WHITE)
        bottom.pack(fill="x", padx=22, pady=(0, 20))
        self.feedback_label = label(bottom, textvariable=self.form_message, size=9, color=MUTED, wraplength=520)
        self.feedback_label.pack(side="left", fill="x", expand=True)
        button(bottom, "Uçuş Koşullarını Hesapla  →", self.calculate, True).pack(side="right")
        results_card = panel(self.body)
        results_card.pack(fill="x", pady=(0, 18))
        label(results_card, "Hesaplama sonuçları", 14, bold=True).pack(anchor="w", padx=22, pady=(19, 5))
        label(results_card, "Bu değerler profil taramasının uçuş koşullarını belirler.", 9, MUTED).pack(anchor="w", padx=22, pady=(0, 18))
        metrics = tk.Frame(results_card, bg=WHITE)
        metrics.pack(fill="x", padx=22, pady=(0, 15))
        for i, (key, title) in enumerate((("required_wing_CL", "Gerekli kanat CL"), ("reference_reynolds", "Referans Reynolds"),
                                         ("mach", "Mach sayısı"), ("aspect_ratio", "Açıklık oranı"))):
            metrics.columnconfigure(i, weight=1, uniform="results")
            box = tk.Frame(metrics, bg="#F8F9FC")
            box.grid(row=0, column=i, sticky="nsew", padx=(0, 9))
            label(box, title, 9, MUTED).pack(anchor="w", padx=12, pady=(14, 8))
            value = label(box, "—", 22, PURPLE, True)
            value.pack(anchor="w", padx=12, pady=(0, 14))
            self.result_labels[key] = value
        actions = tk.Frame(results_card, bg=WHITE)
        actions.pack(fill="x", padx=22, pady=(0, 18))
        button(actions, "Sonuçları CSV Olarak Al", self.export_results).pack(side="left", padx=(0, 10))
        button(actions, "Profil Karşılaştırmaya Geç", self.open_comparison).pack(side="left")
        note = "Kanat CL ile 2B profil cl aynı değildir. Referans Reynolds ilk tarama içindir; yerel kanat yükünü çözmez."
        label(results_card, note, 9, MUTED, wraplength=820).pack(anchor="w", padx=22, pady=(0, 18))
        self.update_result_labels()

    def invalidate_results(self, *args):
        if self.results is not None:
            self.results = None
            self.form_message.set("Girdiler değişti. Sonuçlar için yeniden hesapla.")
            self.update_result_labels()

    def update_result_labels(self):
        for key, widget in self.result_labels.items():
            if widget.winfo_exists():
                value = "—"
                if self.results is not None:
                    value = f"{self.results[key]:,.0f}".replace(",", ".") if key == "reference_reynolds" else f"{self.results[key]:.3f}"
                widget.configure(text=value)

    def get_aircraft(self):
        fields = {key: var.get() for key, var in self.fields.items()}
        fields["current_airfoil"] = self.names.get(fields["current_airfoil"], "")
        if not fields["current_airfoil"]:
            raise ValueError("Mevcut airfoil için kütüphaneden bir profil seç.")
        return aircraft_from_fields(fields)

    def notify(self, text, error=False):
        self.status_message.set(text)
        self.form_message.set(text)
        if self.current_page == "design" and hasattr(self, "feedback_label"):
            self.feedback_label.configure(fg="#BC4545" if error else TEAL)

    def calculate(self):
        try:
            aircraft = self.get_aircraft()
            self.results = flight_conditions(aircraft)
            self.update_result_labels()
            self.notify("Uçuş koşulları hesaplandı. Sonuçlar aşağıda.")
            if self.current_page == "design":
                self.update_idletasks()
                self.scroll.yview_moveto(1)
            return True
        except ValueError as error:
            self.results = None
            self.update_result_labels()
            self.notify(str(error), True)
            return False

    def set_aircraft(self, aircraft):
        for key, value in aircraft.items():
            if key in self.fields:
                self.fields[key].set(self.lookup.get(value, {}).get("name", value) if key == "current_airfoil" else str(value))
        self.results = None
        self.update_result_labels()

    def load_sample(self):
        aircraft = sample_aircraft()
        aircraft["name"] = "Örnek İHA Tasarımı"
        self.set_aircraft(aircraft)
        self.project_path = None
        self.notify("Örnek değerler yüklendi. Bunlar gerçek bir İHA ölçümü değildir.")

    def save_design(self):
        try:
            aircraft = self.get_aircraft()
            path = filedialog.asksaveasfilename(parent=self, title="İHA tasarımını kaydet", defaultextension=".json",
                                               filetypes=[("İHA proje dosyası", "*.json")], initialfile="iha-tasarim.json")
            if not path:
                return
            save_project(path, aircraft)
            self.project_path = path
            self.notify("Tasarım kaydedildi: " + Path(path).name)
        except (OSError, ValueError) as error:
            self.notify(str(error), True)
            messagebox.showerror("Tasarım kaydedilemedi", str(error), parent=self)

    def open_design(self):
        path = filedialog.askopenfilename(parent=self, title="İHA tasarımı aç", filetypes=[("İHA proje dosyası", "*.json")])
        if not path:
            return
        try:
            aircraft = load_project(path)
            if aircraft["current_airfoil"] not in self.lookup:
                raise ValueError("Projedeki mevcut airfoil bu kütüphanede bulunamadı.")
            self.set_aircraft(aircraft)
            self.project_path = path
            self.show_page("design")
            self.notify("Tasarım açıldı: " + Path(path).name + ". Hesapla butonuyla sonuçları yenile.")
        except (OSError, ValueError) as error:
            messagebox.showerror("Tasarım açılamadı", str(error), parent=self)

    def export_results(self):
        if not self.calculate():
            return
        path = filedialog.asksaveasfilename(parent=self, title="Hesaplama raporu", defaultextension=".csv",
                                           filetypes=[("CSV raporu", "*.csv")], initialfile="ucus-hesabi.csv")
        if not path:
            return
        try:
            aircraft = self.get_aircraft()
            with Path(path).open("w", encoding="utf-8-sig", newline="") as handle:
                writer = csv.writer(handle, delimiter=";")
                writer.writerow(["Bölüm", "Alan", "Değer"])
                writer.writerows(("Girdi", key, value) for key, value in aircraft.items())
                writer.writerows(("Sonuç", key, value) for key, value in self.results.items())
            self.notify("Hesaplama raporu kaydedildi: " + Path(path).name)
        except OSError as error:
            messagebox.showerror("Rapor kaydedilemedi", str(error), parent=self)

    def page_library(self):
        self.heading("Airfoil Kütüphanesi", "80 aday profili keşfet. Koordinat verilerini incele ve kendi DAT dosyalarını ekle.")
        filters = tk.Frame(self.body, bg=BG)
        filters.pack(fill="x", pady=(0, 16))
        search = tk.Entry(filters, textvariable=self.search_var, bg=WHITE, fg=INK, relief="flat",
                          highlightbackground=LINE, highlightthickness=1, font=(FONT, 11))
        search.pack(side="left", fill="x", expand=True, ipady=11, padx=(0, 12))
        search.bind("<KeyRelease>", lambda e: self.filter_library())
        search.bind("<Escape>", lambda e: (self.search_var.set(""), self.filter_library()))
        families = ttk.Combobox(filters, textvariable=self.family_var, state="readonly", width=22,
                                values=["Tüm aileler"] + sorted({row["family"] for row in self.records}))
        families.pack(side="left")
        families.bind("<<ComboboxSelected>>", lambda e: self.filter_library())
        label(self.body, "Profil adı veya aile ile ara. Kaynak kaydı olan profillere koordinat ekleyebilirsin.", 9, MUTED).pack(anchor="w", pady=(0, 10))
        table_card = panel(self.body)
        table_card.pack(fill="x", pady=(0, 16))
        self.tree = ttk.Treeview(table_card, columns=("name", "family", "status", "points"), show="headings", height=7, selectmode="browse")
        for key, title, width in (("name", "PROFİL", 150), ("family", "AİLE", 200),
                                  ("status", "VERİ DURUMU", 170), ("points", "NOKTA", 70)):
            self.tree.heading(key, text=title, anchor="w")
            self.tree.column(key, width=width, minwidth=65, anchor="w")
        scrollbar = ttk.Scrollbar(table_card, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.select_library)
        self.library_count = label(self.body, "", 9, MUTED)
        self.library_count.pack(anchor="w", pady=(0, 14))
        detail = panel(self.body)
        detail.pack(fill="x")
        header = tk.Frame(detail, bg=WHITE)
        header.pack(fill="x", padx=20, pady=(18, 6))
        self.library_title = label(header, "Profil seç", 16, bold=True)
        self.library_title.pack(side="left")
        button(header, "DAT Dosyası Ekle", self.import_selected).pack(side="right")
        self.library_note = label(detail, "", 10, MUTED, wraplength=820)
        self.library_note.pack(anchor="w", padx=20)
        self.library_chart = ProfileChart(detail, 230)
        self.library_chart.pack(fill="x", padx=12)
        actions = tk.Frame(detail, bg=WHITE)
        actions.pack(fill="x", padx=20, pady=(0, 17))
        button(actions, "Mevcut Profil Olarak Seç", self.use_selected).pack(side="left", padx=(0, 10))
        button(actions, "Kaynağı Tarayıcıda Aç", self.open_source).pack(side="left")
        self.filter_library()

    def filter_library(self):
        selected = self.library_selection
        self.tree.delete(*self.tree.get_children())
        term = self.search_var.get().strip().casefold()
        family = self.family_var.get()
        for row in self.records:
            if term and term not in (row["name"] + " " + row["id"] + " " + row["family"]).casefold():
                continue
            if family != "Tüm aileler" and row["family"] != family:
                continue
            self.tree.insert("", "end", iid=row["id"], values=(row["name"], row["family"],
                             "Koordinat hazır" if row["point_count"] else "Kaynak kaydı", row["point_count"] or "—"))
        children = self.tree.get_children()
        self.library_count.configure(text=f"{len(children)} / {len(self.records)} profil gösteriliyor")
        if children:
            self.tree.selection_set(selected if selected in children else children[0])
            self.select_library()
        else:
            self.library_selection = None
            self.library_title.configure(text="Eşleşen profil bulunamadı")
            self.library_note.configure(text="Arama terimini değiştir veya aile filtresini temizle.")
            self.library_chart.set_series([])

    def select_library(self, event=None):
        selected = self.tree.selection()
        if not selected:
            return
        self.library_selection = selected[0]
        row = self.lookup[self.library_selection]
        self.library_title.configure(text=row["name"])
        self.library_note.configure(text=f"{row['family']}  ·  " +
                                    (f"{row['point_count']} koordinat noktası hazır. Aerodinamik polar henüz yok." if row["point_count"]
                                     else "Koordinat dosyası bekleniyor. Kaynaktan indirip DAT Dosyası Ekle ile içeri al."))
        self.library_chart.set_series([(row["name"], self.store.geometry(row["id"]), PURPLE)])

    def import_selected(self):
        if not self.library_selection:
            self.notify("Önce listeden bir profil seç.", True)
            return
        path = filedialog.askopenfilename(parent=self, title=self.lookup[self.library_selection]["name"] + " için koordinat seç",
                                         filetypes=[("Airfoil koordinat dosyası", "*.dat"), ("Tüm dosyalar", "*.*")])
        if not path:
            return
        try:
            count = self.store.import_dat(self.library_selection, path)
            self.records = self.store.airfoils()
            self.lookup = {row["id"]: row for row in self.records}
            self.filter_library()
            self.notify(f"{self.lookup[self.library_selection]['name']}: {count} koordinat noktası eklendi.")
        except (OSError, ValueError, sqlite3.Error) as error:
            messagebox.showerror("Koordinatlar eklenemedi", str(error), parent=self)

    def use_selected(self):
        if self.library_selection:
            self.fields["current_airfoil"].set(self.lookup[self.library_selection]["name"])
            self.show_page("design")
            self.notify("Mevcut profil seçildi. İHA bilgilerini düzenleyerek devam et.")

    def open_source(self):
        if self.library_selection:
            webbrowser.open(self.lookup[self.library_selection]["source_url"])

    def open_comparison(self):
        self.baseline_var.set(self.fields["current_airfoil"].get())
        self.show_page("compare")

    def page_compare(self):
        self.heading("Profil Karşılaştırma", "İki profilin geometrisini aynı ölçek üzerinde incele.")
        card = panel(self.body)
        card.pack(fill="x", pady=(0, 18))
        selectors = tk.Frame(card, bg=WHITE)
        selectors.pack(fill="x", padx=22, pady=22)
        for i, (title, variable) in enumerate((("Mevcut profil", self.baseline_var), ("Aday profil", self.candidate_var))):
            selectors.columnconfigure(i, weight=1, uniform="select")
            block = tk.Frame(selectors, bg=WHITE)
            block.grid(row=0, column=i, sticky="ew", padx=(0, 14))
            label(block, title, 9, MUTED, True).pack(anchor="w", pady=(0, 8))
            combo = ttk.Combobox(block, textvariable=variable, values=list(self.names), state="readonly")
            combo.pack(fill="x")
            combo.bind("<<ComboboxSelected>>", lambda e: self.refresh_comparison())
        button(card, "Profilleri Karşılaştır", self.refresh_comparison, True).pack(anchor="w", padx=22, pady=(0, 14))
        self.compare_chart = ProfileChart(card, 300)
        self.compare_chart.pack(fill="x", padx=12)
        self.compare_note = label(card, "", 10, MUTED, wraplength=820)
        self.compare_note.pack(anchor="w", padx=22, pady=(0, 20))
        self.compare_table = ttk.Treeview(card, columns=("metric", "base", "candidate"), show="headings", height=3, selectmode="none")
        for key, title in (("metric", "GEOMETRİ VERİSİ"), ("base", "MEVCUT PROFİL"), ("candidate", "ADAY PROFİL")):
            self.compare_table.heading(key, text=title, anchor="w")
            self.compare_table.column(key, width=190, anchor="w")
        self.compare_table.pack(fill="x", padx=22, pady=(0, 20))
        next_card = tk.Frame(self.body, bg="#FFF8EB", highlightbackground="#F0E2C5", highlightthickness=1)
        next_card.pack(fill="x")
        label(next_card, "Performans önerisi için sıradaki adım: polar verileri", 12, AMBER, True).pack(anchor="w", padx=22, pady=(20, 8))
        label(next_card, "Kaldırma, sürükleme ve moment verileri eklendiğinde bu ekran aynı uçuş koşullarında\n"
              "performans karşılaştırması da sunacak. Bu sürümde daha iyi uçan profil sıralaması yapılmıyor.",
              10, MUTED, wraplength=820).pack(anchor="w", padx=22, pady=(0, 20))
        self.refresh_comparison()

    def refresh_comparison(self):
        ids = [self.names.get(self.baseline_var.get()), self.names.get(self.candidate_var.get())]
        points = [self.store.geometry(profile) if profile else [] for profile in ids]
        self.compare_chart.set_series([(self.baseline_var.get(), points[0], PURPLE),
                                       (self.candidate_var.get(), points[1], TEAL)])
        missing = [name for name, data in zip((self.baseline_var.get(), self.candidate_var.get()), points) if not data]
        note = "Koordinatı eksik: " + ", ".join(missing) + ". Kütüphaneden DAT dosyası ekle." if missing else "Geometriler ortak kord ölçeğinde gösteriliyor. Şekil farkı, performans üstünlüğünü tek başına belirlemez."
        self.compare_note.configure(text=note)
        self.compare_table.delete(*self.compare_table.get_children())
        for title, values in [("Koordinat noktası", [str(len(data)) if data else "Veri yok" for data in points]),
                               ("Geometri durumu", ["Hazır" if data else "Bekleniyor" for data in points]),
                               ("Aerodinamik polar", ["Henüz eklenmedi", "Henüz eklenmedi"])]:
            self.compare_table.insert("", "end", values=(title, *values))

    def page_roadmap(self):
        self.heading("Birlikte geliştireceğimiz yol haritası", "Çalışan bir temelden, doğrulanmış ve açıklanabilir tasarım önerilerine.")
        steps = [
            ("01", "Masaüstü taslak", "TAMAMLANDI", TEAL, "Tasarım girdileri, uçuş hesabı, 80 aday profil ve geometri karşılaştırma."),
            ("02", "Veri setini genişletme", "SIRADAKİ", PURPLE, "Koordinat kapsamı, geometri kalite kontrolü ve ilk beş profil için ortak analiz koşulları."),
            ("03", "Aerodinamik analiz", "PLANLANDI", MUTED, "XFOIL polarları; Reynolds, Mach, geçiş ve yakınsama bilgileriyle kayıt."),
            ("04", "Gerekçeli profil önerileri", "PLANLANDI", MUTED, "Mevcut tasarımla aynı uçuş noktasında karşılaştırma; kısıtlarla ilk üç aday."),
            ("05", "3B kanat ve doğrulama", "PLANLANDI", MUTED, "Kanat yük dağılımı, trim ve deneysel verilerle modelin geçerli aralığını belirleme."),
        ]
        for number, title, state, color, description in steps:
            card = panel(self.body)
            card.pack(fill="x", pady=(0, 13))
            row = tk.Frame(card, bg=WHITE)
            row.pack(fill="x", padx=22, pady=20)
            label(row, number, 24, color, True).pack(side="left", padx=(0, 22))
            info = tk.Frame(row, bg=WHITE)
            info.pack(side="left", fill="x", expand=True)
            label(info, title, 13, bold=True).pack(anchor="w")
            label(info, description, 10, MUTED, wraplength=650).pack(anchor="w", pady=(7, 0))
            label(row, state, 8, color, True).pack(side="right", padx=(15, 0))
        button(self.body, "Ayrıntılı Yol Haritasını Aç", self.open_roadmap).pack(anchor="w", pady=(8, 0))

    def open_roadmap(self):
        import os
        import subprocess
        import sys
        path = ROOT / "YOL_HARITASI.md"
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as error:
            messagebox.showerror("Dosya açılamadı", str(error), parent=self)

    def destroy(self):
        if hasattr(self, "store"):
            self.store.close()
            del self.store
        super().destroy()


def launch():
    if __import__("sys").platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            pass
    app = UAVApp()
    app.mainloop()
