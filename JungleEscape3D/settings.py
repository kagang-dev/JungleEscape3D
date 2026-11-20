"""
settings.py - Global constants and save data for JUNGLE ESCAPE 3D.

Everything you may want to tweak (speed, gravity, graphics quality...) lives here.
"""
import json
import os

GAME_TITLE = "JUNGLE ESCAPE 3D"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FILE = os.path.join(BASE_DIR, "savedata.json")
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")
TEXTURE_DIR = os.path.join(BASE_DIR, "assets", "textures")
CACHE_DIR = os.path.join(BASE_DIR, "assets", "cache")
# Bump this number if you change the world generation code: it forces the
# pre-built jungle pieces in assets/cache to be rebuilt.
CACHE_VERSION = 1

# ---------------------------------------------------------------- lanes
LANE_WIDTH = 3.0
LANES = (-LANE_WIDTH, 0.0, LANE_WIDTH)
LANE_SWITCH_SPEED = 26.0

# ---------------------------------------------------------------- speed (see difficulty.py)
START_SPEED = 15.0
MAX_SPEED = 44.0

# ---------------------------------------------------------------- physics
GRAVITY = 60.0
JUMP_VELOCITY = 18.0                     # peak jump height = v^2 / (2g) = 2.7
FAST_FALL_VELOCITY = -28.0
SLIDE_TIME = 0.75

# ---------------------------------------------------------------- player hitbox
PLAYER_HALF_WIDTH = 0.40
PLAYER_HALF_DEPTH = 0.40
PLAYER_HEIGHT = 1.85
PLAYER_SLIDE_HEIGHT = 0.85

# ---------------------------------------------------------------- world streaming
SEGMENT_LENGTH = 30.0
SPAWN_AHEAD = 150.0
DESPAWN_BEHIND = 25.0

# ---------------------------------------------------------------- gameplay
COIN_SCORE = 10

# ---------------------------------------------------------------- look
FOG_COLOR = (0.66, 0.80, 0.70)

# Graphics quality presets.  Pick one in the Settings menu.
#   segments : how many 30-unit world pieces exist at once (view distance)
#   trees / shrubs / ferns / grass / litter : decoration amount per world piece
#   cards    : use leaf "cards" (fronds, ferns, grass blades) - nicer but heavier
#   rings, segs, blobs : detail of the foliage clumps
#   sides    : sides of tree trunks
#   fog      : (start, end) distance of the jungle fog
#   variants : how many (jungle, river, ruins) piece variants are generated
QUALITY_LEVELS = ("low", "medium", "high")
QUALITY = {
    "low": dict(segments=8, trees=3, shrubs=4, ferns=5, grass=16, litter=14, cards=False,
                rings=4, segs=6, blobs=4, sides=5, fog=(32.0, 105.0), variants=(3, 1, 1)),
    "medium": dict(segments=9, trees=5, shrubs=6, ferns=8, grass=30, litter=26, cards=True,
                   rings=5, segs=8, blobs=5, sides=6, fog=(40.0, 125.0), variants=(4, 2, 2)),
    "high": dict(segments=10, trees=7, shrubs=9, ferns=12, grass=48, litter=40, cards=True,
                 rings=6, segs=9, blobs=7, sides=7, fog=(46.0, 140.0), variants=(5, 2, 2)),
}


class SaveData:
    """Stores the high score and the user settings in savedata.json."""

    def __init__(self):
        self.high_score = 0
        self.sound = True
        self.show_fps = False
        self.fullscreen = False
        self.quality = "medium"
        self.load()

    def load(self):
        try:
            with open(SAVE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.high_score = int(data.get("high_score", 0))
            self.sound = bool(data.get("sound", True))
            self.show_fps = bool(data.get("show_fps", False))
            self.fullscreen = bool(data.get("fullscreen", False))
            q = data.get("quality", "medium")
            self.quality = q if q in QUALITY else "medium"
        except (OSError, ValueError, TypeError):
            pass

    def save(self):
        data = {
            "high_score": self.high_score,
            "sound": self.sound,
            "show_fps": self.show_fps,
            "fullscreen": self.fullscreen,
            "quality": self.quality,
        }
        try:
            with open(SAVE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except OSError:
            print("Warning: could not write", SAVE_FILE)
