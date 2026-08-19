"""Allow ``python -m osf`` to run the CLI."""

from osf.cli import main


if __name__ == "__main__":
    raise SystemExit(main())