"""Castle Panic in the terminal, in 3D: python -m castlepanic [--name NAME]"""
import argparse
import getpass

from unicode3d.terminal import add_display_args, display_options, run

from .session import MAX_NAME
from .ui import App


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    try:
        default_name = getpass.getuser().capitalize()
    except Exception:
        default_name = "Player"
    parser.add_argument("--name", default=default_name, help="your name")
    parser.add_argument("--fps", type=int, default=None, help="target frame rate (default: as saved in Settings, or 30)")
    parser.add_argument("--no-sound", action="store_true", help="play silently")
    parser.add_argument("--seed", type=int, default=None, help="a fixed shuffle, for testing")
    add_display_args(parser)
    args = parser.parse_args()
    display = display_options(args)
    fixed = {k for k, v in dict(display, fps=args.fps).items() if v is not None}
    app = App(args.name[:MAX_NAME], sound=not args.no_sound, seed=args.seed, fixed=fixed)
    try:
        run(app.frame, args.fps or 30, mouse=True, title="Castle Panic", **display)
    except KeyboardInterrupt:
        pass
    finally:
        app.close()


if __name__ == "__main__":
    main()
