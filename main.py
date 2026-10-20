"""PyCharm'da Run 'main' veya Windows'ta BASLAT.bat ile arayüzü açın."""

import sys


def main():
    try:
        from desktop_app import launch
        launch()
    except ImportError as error:
        print(f"Arayüz açılamadı: {error}", file=sys.stderr)
        print("Tkinter içeren bir Python 3.10+ kurulumu gerekiyor.", file=sys.stderr)
        return 1
    except Exception as error:
        import traceback
        traceback.print_exc()
        try:
            from tkinter import messagebox
            messagebox.showerror("Uygulama başlatılamadı", str(error))
        except Exception:
            pass
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
