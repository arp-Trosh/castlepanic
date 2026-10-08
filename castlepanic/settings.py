"""The display settings (glyphs, colours, frame rate, shadows, reflections, detail, quality), kept between runs in a
small JSON
file: ~/.config/castlepanic/settings.json (on Windows, %APPDATA%\\castlepanic\\settings.json)."""
import json
import os

KEYS = ("glyphs", "color", "fps", "shadows", "reflections", "detail", "quality")
# Values saved by older versions, under their names now: unicode3d's lowest quality preset was "fast" before
# 0.17, and is "low".
RENAMED = {("quality", "fast"): "low"}


def _path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    if os.name == "nt":
        base = os.environ.get("APPDATA", base)
    return os.path.join(base, "castlepanic", "settings.json")


def load():
    """The saved settings: {key: value} for those saved, {} if none (or the file can't be read). Values saved under
    an old name (RENAMED) come back under the new one."""
    try:
        with open(_path()) as f:
            data = json.load(f)
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {k: RENAMED.get((k, v), v) if isinstance(v, str) else v for k, v in data.items() if k in KEYS}


def save(values):
    """Keep these settings for next time; quietly gives up if the file can't be written."""
    path = _path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump({k: v for k, v in values.items() if k in KEYS}, f, indent=1)
    except OSError:
        pass
