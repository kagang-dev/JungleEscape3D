"""
difficulty.py - How the game gets faster and harder the longer you survive.

Everything depends on the survival time t (seconds):
    speed_at(t)  - running speed, a smooth S-shaped curve (slow start, no jumps)
    level_at(t)  - difficulty 0.0 .. 1.0 (controls obstacle density and variety)

Approximate speed:  0s=15   30s=19   60s=24   120s=33   240s=42   (max 44)
Approximate level:  0s=0.0  30s=0.12 60s=0.26 120s=0.53  240s=0.84
"""
import math

from settings import MAX_SPEED, START_SPEED


def speed_at(t):
    f = 1.0 - math.exp(-((t / 120.0) ** 1.4))
    return START_SPEED + (MAX_SPEED - START_SPEED) * f


def level_at(t):
    return 1.0 - math.exp(-((t / 150.0) ** 1.3))


def lerp(a, b, t):
    return a + (b - a) * t


def row_gap_seconds(level):
    """(min, max) seconds of running between two obstacle rows."""
    return lerp(1.35, 0.80, level), lerp(1.95, 1.10, level)


STAGES = ((0, "EXPLORER"), (30, "TRAILBLAZER"), (70, "ADVENTURER"),
          (120, "DAREDEVIL"), (190, "LEGEND"))


def stage_index(t):
    idx = 0
    for i, (start, _) in enumerate(STAGES):
        if t >= start:
            idx = i
    return idx


def stage_name(t):
    return STAGES[stage_index(t)][1]
