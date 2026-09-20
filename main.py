from app.views.main_window import main as gui_main


def main() -> int:
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
