"""
sounds.py - Creates the game's sound effects procedurally.

No downloads needed: on the first run the .wav files are generated with
Python's built-in `wave` module and saved in assets/sounds/.
"""
import math
import os
import random
import struct
import wave

RATE = 22050


def _write(path, samples):
    frames = b"".join(
        struct.pack("<h", int(max(-1.0, min(1.0, s)) * 32767)) for s in samples)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)


def _tone(f0, f1, dur, vol=0.5):
    """Sine tone sliding from f0 to f1 Hz with a soft envelope."""
    n = int(RATE * dur)
    out, phase = [], 0.0
    for i in range(n):
        t = i / n
        phase += 2 * math.pi * (f0 + (f1 - f0) * t) / RATE
        env = min(1.0, t * 12) * (1.0 - t) ** 1.5
        out.append(math.sin(phase) * vol * env)
    return out


def _noise(dur, vol=0.5, smooth=0.5, decay=2.0, rng=None):
    """Low-pass filtered noise (wind / whoosh / crash)."""
    rng = rng or random.Random(1)
    n = int(RATE * dur)
    out, last = [], 0.0
    for i in range(n):
        t = i / n
        last = last * smooth + rng.uniform(-1, 1) * (1 - smooth)
        out.append(last * vol * min(1.0, t * 20) * (1.0 - t) ** decay)
    return out


def _mix(a, b):
    n = max(len(a), len(b))
    a = a + [0.0] * (n - len(a))
    b = b + [0.0] * (n - len(b))
    return [x + y for x, y in zip(a, b)]


def _ambience():
    """8 seconds of jungle: soft wind + a few bird chirps (loops)."""
    rng = random.Random(5)
    dur = 8.0
    n = int(RATE * dur)
    wind = _noise(dur, vol=0.9, smooth=0.97, decay=0.0, rng=rng)
    wind = [w * 0.5 * (0.7 + 0.3 * math.sin(i / RATE * 0.8)) for i, w in enumerate(wind)]
    out = wind[:n]
    for start in (0.8, 1.0, 3.4, 3.6, 3.8, 5.9, 7.0):
        f0 = rng.uniform(2200, 3000)
        chirp = _tone(f0, f0 + rng.uniform(500, 1200), 0.12, 0.10)
        s = int(start * RATE)
        for i, v in enumerate(chirp):
            if s + i < n:
                out[s + i] += v
    fade = int(RATE * 0.05)
    for i in range(fade):          # fade edges so the loop has no click
        k = i / fade
        out[i] *= k
        out[n - 1 - i] *= k
    return out


def ensure_sounds(folder):
    """Generate any missing sound files and return {name: path}."""
    os.makedirs(folder, exist_ok=True)
    makers = {
        "coin": lambda: _tone(988, 988, 0.06, 0.4) + _tone(1319, 1319, 0.12, 0.4),
        "jump": lambda: _tone(260, 620, 0.18, 0.4),
        "slide": lambda: _noise(0.3, 0.6, smooth=0.8, decay=1.2),
        "crash": lambda: _mix(_noise(0.6, 0.9, smooth=0.7, decay=2.0), _tone(110, 40, 0.5, 0.6)),
        "click": lambda: _tone(700, 500, 0.05, 0.4),
        "ambience": _ambience,
    }
    paths = {}
    for name, make in makers.items():
        path = os.path.join(folder, name + ".wav")
        if not os.path.exists(path):
            try:
                _write(path, make())
            except OSError:
                continue
        paths[name] = path
    return paths
