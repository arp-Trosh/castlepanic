"""Game sounds, all synthesized here with numpy (no sound files, no audio libraries).

Each sound is made once and written to a .wav in the cache folder, then played without blocking: on Windows by
the standard library's winsound (one sound at a time), elsewhere by the system's own player (pw-play, paplay,
aplay or afplay) in a child process, so several can overlap. Without a player the game is silent.
"""
import os
import shutil
import subprocess
import sys
import threading
import time
import wave

import numpy as np
from numba import njit

RATE = 22050
VERSION = 4  # (bump when a sound changes: they are made once and cached)


def _t(dur):
    return np.arange(int(dur * RATE)) / RATE


def _env(n, attack=0.005, release=0.1, dur=None):
    t = np.arange(n) / RATE
    dur = dur or n / RATE
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    r = np.clip((dur - t) / max(release, 1e-4), 0, 1)
    return a * r


def _noise(rng, dur):
    return rng.uniform(-1, 1, int(dur * RATE))


def _lowpass(x, cutoff):
    """One-pole low-pass; cutoff in Hz, or an array of Hz per sample."""
    cutoff = np.ascontiguousarray(np.broadcast_to(np.asarray(cutoff, float), x.shape))
    return _onepole(np.ascontiguousarray(x, float), 1 - np.exp(-2 * np.pi * cutoff / RATE))


@njit(cache=True)
def _onepole(x, a):
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


@njit(cache=True)
def _twopole(x, r, c):
    y = np.zeros_like(x)
    y1 = 0.0
    y2 = 0.0
    for i in range(len(x)):
        v = (1 - r[i]) * x[i] + c[i] * y1 - r[i] * r[i] * y2
        y2 = y1
        y1 = v
        y[i] = v
    return y


def _bandpass(x, f, q=5.0):
    """A resonator (two-pole), for formants and pitched noise."""
    f = np.ascontiguousarray(np.broadcast_to(np.asarray(f, float), x.shape))
    r = np.exp(-np.pi * (f / q) / RATE)
    return _twopole(np.ascontiguousarray(x, float), r, 2 * r * np.cos(2 * np.pi * f / RATE))


def _saw(freq, dur):
    f = np.broadcast_to(np.asarray(freq, float), (int(dur * RATE),))
    ph = np.cumsum(f) / RATE
    return 2 * (ph % 1.0) - 1


def _sine(freq, dur):
    f = np.broadcast_to(np.asarray(freq, float), (int(dur * RATE),))
    return np.sin(2 * np.pi * np.cumsum(f) / RATE)


VOWELS = {"a": (800, 1150, 2900), "o": (450, 800, 2830), "u": (325, 700, 2530), "e": (400, 1600, 2700),
          "aw": (570, 840, 2410), "uh": (640, 1190, 2390)}


def _voice(pitch, vowel, dur, rasp=0.2, rng=None, q=6):
    """A voice: a buzz (pitch: Hz or per-sample array) through the vowel's formants, with breath noise."""
    rng = rng or np.random.default_rng(0)
    src = _saw(pitch, dur) + rasp * _noise(rng, dur)[: int(dur * RATE)]
    out = np.zeros_like(src)
    for k, f in enumerate(VOWELS[vowel]):
        out += _bandpass(src, f, q) * (1.0, 0.6, 0.25)[k]
    return out


def _pluck(freq, dur, rng, damp=0.996):
    """Karplus-Strong string: a bowstring's twang."""
    return _ks(rng.uniform(-1, 1, int(RATE / freq)), int(dur * RATE), damp)


@njit(cache=True)
def _ks(buf, n, damp):
    period = len(buf)
    out = np.empty(n)
    for i in range(n):
        out[i] = buf[i % period]
        buf[i % period] = damp * 0.5 * (buf[i % period] + buf[(i + 1) % period])
    return out


def _mix(*parts):
    n = max(len(p) for p, _ in parts)
    out = np.zeros(n)
    for p, at in parts:
        k = int(at * RATE)
        m = min(len(p), n - k) if k < n else 0
        if k + len(p) > len(out):
            out = np.concatenate([out, np.zeros(k + len(p) - len(out))])
        out[k:k + len(p)] += p
    return out


def _norm(x, peak=0.8):
    m = np.max(np.abs(x)) or 1.0
    return x / m * peak


# ------------------------------------------------------------------------------------------------ the sounds

def make_sounds():
    rng = np.random.default_rng(7)
    S = {}

    # a war horn: two notes, brassy (saw through a low-pass that opens), vibrato
    def horn(notes, dur):
        parts = []
        at = 0.0
        for f, d in notes:
            t = _t(d)
            vib = f * (1 + 0.006 * np.sin(2 * np.pi * 5.5 * t))
            x = _saw(vib, d) + 0.5 * _saw(vib * 1.003, d)
            x = _lowpass(x, 400 + 1600 * np.clip(t / 0.15, 0, 1)) * _env(len(t), 0.06, 0.15)
            parts.append((x, at))
            at += d * 0.9
        return _norm(_mix(*parts), 0.6)
    S["turn"] = horn([(147, 0.35), (196, 0.7)], 1.0)
    S["victory"] = horn([(196, 0.25), (247, 0.25), (294, 0.25), (392, 1.2)], 2)
    t = _t(2.5)
    S["defeat"] = _norm(_lowpass(_saw(110 * (1 - 0.08 * t), 2.5) + _saw(131 * (1 - 0.08 * t), 2.5) +
                                 _saw(165 * (1 - 0.08 * t), 2.5), 500) * _env(len(t), 0.2, 1.2), 0.6)

    # bow: a low twang and a whoosh; the arrow's thunk
    tw = _pluck(110, 0.4, rng) * _env(int(0.4 * RATE), 0.001, 0.3)
    wh = _bandpass(_noise(rng, 0.3), np.linspace(2500, 900, int(0.3 * RATE)), 3) * _env(int(0.3 * RATE), 0.05, 0.2)
    S["bow"] = _norm(_mix((tw, 0), (wh * 3, 0.05)), 0.7)
    S["arrow_hit"] = _norm(_lowpass(_noise(rng, 0.12), 900) * _env(int(0.12 * RATE), 0.001, 0.1) +
                           0.5 * _sine(90, 0.12) * _env(int(0.12 * RATE), 0.001, 0.1), 0.8)
    # swing: a fast whoosh
    n = int(0.35 * RATE)
    S["swing"] = _norm(_bandpass(_noise(rng, 0.35), np.linspace(600, 3000, n), 2.5) *
                       np.sin(np.linspace(0, np.pi, n)) ** 2, 0.7)
    # a man's yell: "Hyah!" (rising then falling pitch, vowel a)
    t = _t(0.45)
    pitch = 170 + 60 * np.sin(np.pi * np.clip(t / 0.45, 0, 1))
    yell = _voice(pitch, "a", 0.45, 0.3, rng) * _env(len(t), 0.03, 0.15)
    S["charge"] = _norm(_mix((_bandpass(_noise(rng, 0.08), 3000, 2) * 0.5, 0), (yell, 0.04)), 0.75)
    S["drive_back"] = _norm(_mix((S["charge"], 0), (S["swing"], 0.2)), 0.75)

    # monster voices by size: goblins shriek, orcs bark, trolls rumble
    def growl(base, vowel, dur, rasp, fall=0.3):
        t = _t(dur)
        p = base * (1 + 0.15 * np.sin(2 * np.pi * 7 * t)) * (1 - fall * t / dur)
        return _voice(p, vowel, dur, rasp, rng, q=4) * _env(len(t), 0.03, dur * 0.4)
    S["growl_goblin"] = _norm(growl(320, "e", 0.5, 0.6, -0.2), 0.6)
    S["growl_orc"] = _norm(growl(120, "aw", 0.6, 0.8), 0.7)
    S["growl_troll"] = _norm(growl(65, "uh", 0.9, 1.0), 0.8)
    S["hurt_goblin"] = _norm(growl(420, "a", 0.22, 0.5, 0.3), 0.6)
    S["hurt_orc"] = _norm(growl(150, "uh", 0.28, 0.7, 0.4), 0.7)
    S["hurt_troll"] = _norm(growl(80, "o", 0.4, 0.9, 0.4), 0.8)
    S["die_goblin"] = _norm(growl(380, "e", 0.8, 0.5, 0.6), 0.6)
    S["die_orc"] = _norm(growl(140, "aw", 1.0, 0.8, 0.6), 0.7)
    S["die_troll"] = _norm(growl(75, "o", 1.4, 1.0, 0.5), 0.8)
    S["monster_attack"] = _norm(growl(100, "a", 0.6, 1.2, -0.1), 0.8)

    # crashes: a thump, a burst of rubble, a rumble, then pebbles
    def crash(dur, size):
        n = int(dur * RATE)
        body = _lowpass(_noise(rng, dur), 300 + 400 / size) * np.exp(-np.arange(n) / RATE * 3 / size)
        thump = _sine(55 / size + 20, dur) * np.exp(-np.arange(n) / RATE * 6)
        clicks = np.zeros(n)
        for _ in range(int(40 * size)):
            k = int(rng.uniform(0.05, dur * 0.9) * RATE)
            m = min(n - k, 300)
            clicks[k:k + m] += _bandpass(rng.uniform(-1, 1, m), rng.uniform(1500, 4000), 6) * rng.uniform(0.2, 1)
        return _norm(body * 1.5 + thump + clicks * 0.6, 0.85)
    S["wall_crash"] = crash(1.4, 1.0)
    S["tower_fall"] = crash(2.6, 2.0)
    S["crush"] = _norm(_mix((crash(0.5, 0.6), 0), (S["hurt_orc"] * 0.6, 0.02)), 0.85)
    # the boulder: rumbling, bumping low noise
    n = int(2.5 * RATE)
    t = np.arange(n) / RATE
    bumps = 0.6 + 0.4 * np.sin(2 * np.pi * 3.1 * t) ** 8
    S["boulder_roll"] = _norm(_lowpass(_noise(rng, 2.5), 160) * bumps * _env(n, 0.3, 0.6) +
                              0.3 * _sine(38 + 6 * np.sin(2 * np.pi * 0.7 * t), 2.5) * _env(n, 0.3, 0.6), 0.85)
    # hammer knocks for building
    knock = _bandpass(_noise(rng, 0.08), 700, 8) * _env(int(0.08 * RATE), 0.001, 0.07)
    S["build"] = _norm(_mix((knock, 0), (knock, 0.22), (knock, 0.44)), 0.8)
    # tar: bubbling glorps
    gl = []
    for k in range(4):
        d = 0.12
        gl.append((_sine(np.linspace(140, 420, int(d * RATE)), d) * _env(int(d * RATE), 0.01, 0.05), k * 0.13))
    S["tar"] = _norm(_mix(*gl), 0.6)
    # heal: a shimmer of rising bells
    notes = [523, 659, 784, 1047]
    S["heal"] = _norm(_mix(*[(_sine(f, 0.6) * np.exp(-_t(0.6) * 5), k * 0.08) for k, f in enumerate(notes)]), 0.5)
    # a war drum: the Monsters march / a token is drawn
    def drum(d=0.35, f=70):
        n = int(d * RATE)
        return _sine(f * np.exp(-np.arange(n) / RATE * 4), d) * np.exp(-np.arange(n) / RATE * 9) + \
            0.3 * _lowpass(_noise(rng, d), 800) * np.exp(-np.arange(n) / RATE * 25)
    S["token"] = _norm(drum(0.4, 80), 0.8)
    S["march"] = _norm(_mix((drum(), 0), (drum(), 0.32), (drum(0.35, 62), 0.64), (drum(0.5, 55), 0.96)), 0.8)
    S["monsters_move"] = S["march"]
    S["card"] = _norm(_bandpass(_noise(rng, 0.07), 5000, 1.5) * _env(int(0.07 * RATE), 0.002, 0.06), 0.4)
    # Missing, the relief: a breathy "phew" (a puff, then a falling, sighing "ew"), and a soft horn chord that
    # resolves, suspended fourth to major (the war horn's answer)
    puff = _bandpass(_noise(rng, 0.09), 1300, 1.5) * _env(int(0.09 * RATE), 0.005, 0.06)
    t = _t(0.75)
    sigh = _voice(230 - 90 * t / 0.75, "u", 0.75, 1.6, rng, q=3) * _env(len(t), 0.04, 0.45)

    def chord(freqs, d, attack):
        t = _t(d)
        x = sum(_saw(f * (1 + 0.004 * np.sin(2 * np.pi * 5 * t)), d) for f in freqs)
        return _lowpass(x, 700) * _env(len(t), attack, d * 0.5)
    resolve = _mix((chord([196, 262, 294], 0.55, 0.15), 0), (chord([196, 247, 294], 1.4, 0.05), 0.5))
    S["missing"] = _norm(_mix((puff * 0.8, 0), (sigh, 0.06), (_norm(resolve, 0.35), 0.75)), 0.7)
    # the siege begins: a long horn call over a rolling war drum
    call = horn([(147, 0.3), (147, 0.18), (196, 0.3), (220, 0.3), (294, 1.4)], 2.4)
    roll = [(drum(0.4, 60 if k % 4 else 50), 0.25 * k) for k in range(12)]
    S["start"] = _norm(_mix((call, 0.1), *roll, (drum(0.9, 45) * 1.4, 3.0)), 0.8)
    S["spawn"] = S["growl_orc"]
    S["hit"] = S["arrow_hit"]
    return S


# ------------------------------------------------------------------------------------------------ playing

def _cache_dir():
    if os.name == "nt":
        base = os.environ.get("LOCALAPPDATA", os.path.expanduser("~"))
    else:
        base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    d = os.path.join(base, "castlepanic", f"sounds-v{VERSION}")
    os.makedirs(d, exist_ok=True)
    return d


def _write_wav(path, x):
    data = (np.clip(x, -1, 1) * 32000).astype("<i2").tobytes()
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(data)


def _player():
    if os.name == "nt":
        return "winsound"
    for cmd in (["pw-play"], ["paplay"], ["aplay", "-q"], ["afplay"]):
        if shutil.which(cmd[0]):
            return cmd
    return None


KIND_VOICE = {"goblin": "goblin", "goblin_king": "goblin", "healer": "goblin", "orc": "orc", "orc_warlord": "orc",
              "troll": "troll", "troll_mage": "troll"}


class Sound:
    """sound.play(name, kind=...) from anywhere; it never blocks or raises."""

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.paths = {}
        self.player = _player() if enabled else None
        self._procs = []
        self._last = {}
        self._ready = threading.Event()
        if self.player:
            threading.Thread(target=self._prepare, daemon=True).start()

    def _prepare(self):
        try:
            d = _cache_dir()
            marker = os.path.join(d, "turn.wav")
            if not os.path.exists(marker):
                for name, x in make_sounds().items():
                    _write_wav(os.path.join(d, name + ".wav"), x)
            for f in os.listdir(d):
                if f.endswith(".wav"):
                    self.paths[f[:-4]] = os.path.join(d, f)
            self._ready.set()
        except Exception:
            self.player = None

    def toggle(self):
        self.enabled = not self.enabled
        return self.enabled

    def play(self, name, kind=None, **_):
        if not self.enabled or not self.player or not self._ready.is_set():
            return
        if name in ("monster_hurt", "monster_die", "spawn") and kind:
            voice = KIND_VOICE.get(kind, "orc")
            name = {"monster_hurt": "hurt_", "monster_die": "die_", "spawn": "growl_"}[name] + voice
        path = self.paths.get(name)
        if not path:
            return
        now = time.monotonic()
        if now - self._last.get(name, 0) < 0.08:
            return  # the same sound twice at once just gets louder and muddier
        self._last[name] = now
        try:
            if self.player == "winsound":
                import winsound
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
                return
            self._procs = [p for p in self._procs if p.poll() is None]
            if len(self._procs) >= 6:
                return
            self._procs.append(subprocess.Popen(self.player + [path], stdin=subprocess.DEVNULL,
                                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        except Exception:
            pass

    def close(self):
        for p in self._procs:
            try:
                p.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    # python -m castlepanic.sound [name ...]: hear them
    s = Sound()
    s._ready.wait(30)
    for n in sys.argv[1:] or sorted(s.paths):
        print(n)
        s.play(n)
        time.sleep(1.2)
