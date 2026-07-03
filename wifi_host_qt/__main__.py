"""Entry point for wifi-host-qt."""

from .main_window import run_app


def main() -> int:
    return run_app()


if __name__ == "__main__":
    raise SystemExit(main())
