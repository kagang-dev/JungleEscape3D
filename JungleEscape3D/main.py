"""
JUNGLE ESCAPE 3D - main.py
Run with:   python main.py

Game states
    loading -> menu <-> settings
    menu -> playing <-> paused
    playing -> dying -> gameover -> (restart -> playing) or (menu)

Main loop idea (polymorphism): every obstacle and coin is a GameObject, so the
loop just calls update() / touches() / on_hit() on each one.  Each class
reacts in its own way.
"""
import sys

from panda3d.core import (AmbientLight, ClockObject, DirectionalLight, Filename,
                          Fog, WindowProperties, loadPrcFileData)

# These settings must be loaded BEFORE ShowBase is created.
loadPrcFileData("", """
window-title JUNGLE ESCAPE 3D
win-size 1280 720
sync-video 1
framebuffer-multisample 0
show-frame-rate-meter 0
""")

from direct.showbase.ShowBase import ShowBase

import difficulty
from camera import ChaseCamera
from coins import CoinManager
from environment import Environment
from obstacles import ObstacleManager
from player import Player
from settings import (COIN_SCORE, FOG_COLOR, QUALITY, QUALITY_LEVELS, SOUND_DIR,
                      START_SPEED, MAX_SPEED, SaveData)
from sky import build_sky
from sounds import ensure_sounds
from ui import GameUI

CLOCK = ClockObject.getGlobalClock()


class JungleEscape(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()
        self.setBackgroundColor(*FOG_COLOR)
        self.save = SaveData()
        self.camLens.setNearFar(1.0, 700)
        self.camLens.setFov(60)

        self.speed = START_SPEED
        self.play_time = 0.0
        self.distance = 0.0
        self.coin_count = 0
        self.score = 0
        self.stage = 0
        self.dying_timer = 0.0
        self.gameover_age = 0.0
        self.fps_timer = 0.0
        self.state = "loading"

        self.ui = GameUI(self, {
            "play": self.start_game, "settings": self.open_settings, "exit": self.userExit,
            "back": self.go_menu, "toggle_sound": self.toggle_sound,
            "toggle_fps": self.toggle_fps, "toggle_fullscreen": self.toggle_fullscreen,
            "toggle_quality": self.cycle_quality,
            "pause": self.pause_game, "resume": self.resume_game,
            "restart": self.start_game, "menu": self.go_menu,
            "click": lambda: self.play("click"),
        })
        self.ui.set_loading("Growing the jungle...")
        self.graphicsEngine.renderFrame()
        self.graphicsEngine.renderFrame()

        self._setup_lights_and_fog()
        build_sky(self.camera)
        self._load_sounds()

        self.world = self.render.attachNewNode("world")
        self.env = Environment(self.world, self.save.quality)
        self.player = Player(self.world)
        self.coins = CoinManager(self.world)
        self.obstacles = ObstacleManager(self.world, self.env, self.coins)
        self.coins.obstacles = self.obstacles
        self.cam_ctrl = ChaseCamera(self, self.player)
        self.ui.set_loading("")

        self._bind_keys()
        self.go_menu()
        if self.save.fullscreen:
            self._apply_fullscreen()
        self.taskMgr.add(self.update, "update")

    # ------------------------------------------------------------ setup
    def _setup_lights_and_fog(self):
        ambient = AmbientLight("ambient")
        ambient.setColor((0.55, 0.60, 0.55, 1))
        self.render.setLight(self.render.attachNewNode(ambient))

        sun = DirectionalLight("sun")
        sun.setColor((1.0, 0.94, 0.78, 1))
        sun_np = self.render.attachNewNode(sun)
        sun_np.setHpr(-35, -55, 0)
        self.render.setLight(sun_np)

        fill = DirectionalLight("fill")
        fill.setColor((0.14, 0.2, 0.3, 1))
        fill_np = self.render.attachNewNode(fill)
        fill_np.setHpr(150, -30, 0)
        self.render.setLight(fill_np)

        self.fog = Fog("jungle_fog")
        self.fog.setColor(*FOG_COLOR)
        self._apply_fog()
        self.render.setFog(self.fog)

    def _apply_fog(self):
        self.fog.setLinearRange(*QUALITY[self.save.quality]["fog"])

    def _load_sounds(self):
        self.sfx = {}
        try:
            paths = ensure_sounds(SOUND_DIR)
            for name, path in paths.items():
                self.sfx[name] = self.loader.loadSfx(Filename.fromOsSpecific(path))
        except Exception as err:                       # sound must never crash the game
            print("Sound disabled:", err)
        amb = self.sfx.get("ambience")
        if amb:
            amb.setLoop(True)
            amb.setVolume(0.35)
            if self.save.sound:
                amb.play()

    def play(self, name):
        snd = self.sfx.get(name)
        if snd and self.save.sound:
            snd.play()

    def _bind_keys(self):
        for key in ("a", "arrow_left"):
            self.accept(key, self.on_left)
        for key in ("d", "arrow_right"):
            self.accept(key, self.on_right)
        for key in ("space", "w", "arrow_up"):
            self.accept(key, self.on_jump)
        for key in ("s", "arrow_down"):
            self.accept(key, self.on_slide)
        self.accept("escape", self.on_escape)
        self.accept("enter", self.on_enter)

    # ------------------------------------------------------------ input
    def on_left(self):
        if self.state == "playing":
            self.player.move_left()

    def on_right(self):
        if self.state == "playing":
            self.player.move_right()

    def on_jump(self):
        if self.state == "playing":
            if self.player.jump():
                self.play("jump")
        elif self.state == "menu" or (self.state == "gameover" and self.gameover_age > 0.7):
            self.start_game()

    def on_slide(self):
        if self.state == "playing" and self.player.slide():
            self.play("slide")

    def on_escape(self):
        if self.state == "playing":
            self.pause_game()
        elif self.state == "paused":
            self.resume_game()
        elif self.state == "settings":
            self.go_menu()

    def on_enter(self):
        if self.state == "menu" or (self.state == "gameover" and self.gameover_age > 0.7):
            self.start_game()

    # ------------------------------------------------------------ state changes
    def reset_world(self):
        self.speed = START_SPEED
        self.play_time = 0.0
        self.distance = 0.0
        self.coin_count = 0
        self.score = 0
        self.stage = 0
        self.player.reset()
        self.env.reset()
        self.obstacles.reset()
        self.coins.reset()

    def go_menu(self):
        first_time = self.state == "loading"
        came_from_game = self.state in ("paused", "gameover", "dying", "playing")
        self.reset_world()
        self.state = "menu"
        self.cam_ctrl.set_mode("menu")
        self.cam_ctrl.set_speed(START_SPEED)
        if came_from_game or first_time:
            self.cam_ctrl.snap()
        self.ui.show_menu(self.save.high_score)

    def open_settings(self):
        self.state = "settings"
        self.ui.show_settings(self.save)

    def start_game(self):
        from_menu = self.state == "menu"
        self.reset_world()
        self.state = "playing"
        self.player.start_run()
        self.cam_ctrl.set_mode("follow")
        self.cam_ctrl.set_speed(self.speed)
        if not from_menu:
            self.cam_ctrl.snap()
        self.ui.show_hud()
        self._update_hud()

    def pause_game(self):
        if self.state == "playing":
            self.state = "paused"
            self.ui.show_pause()

    def resume_game(self):
        if self.state == "paused":
            self.state = "playing"
            self.ui.hide_pause()

    def game_over(self):
        new_best = self.score > self.save.high_score
        if new_best:
            self.save.high_score = self.score
            self.save.save()
        self.state = "gameover"
        self.gameover_age = 0.0
        self.ui.show_gameover(self.score, self.coin_count, self.save.high_score, new_best,
                              int(self.distance), int(self.play_time))

    # ------------------------------------------------------------ settings
    def toggle_sound(self):
        self.save.sound = not self.save.sound
        amb = self.sfx.get("ambience")
        if amb:
            amb.play() if self.save.sound else amb.stop()
        self.save.save()
        self.ui.refresh_settings(self.save)

    def toggle_fps(self):
        self.save.show_fps = not self.save.show_fps
        if not self.save.show_fps:
            self.ui.set_fps("")
        self.save.save()
        self.ui.refresh_settings(self.save)

    def toggle_fullscreen(self):
        self.save.fullscreen = not self.save.fullscreen
        self._apply_fullscreen()
        self.save.save()
        self.ui.refresh_settings(self.save)

    def cycle_quality(self):
        """low -> medium -> high -> low. Rebuilds the jungle with the new detail level."""
        idx = (QUALITY_LEVELS.index(self.save.quality) + 1) % len(QUALITY_LEVELS)
        self.save.quality = QUALITY_LEVELS[idx]
        self.save.save()
        self.ui.refresh_settings(self.save)
        self.ui.set_loading("Applying %s graphics..." % self.save.quality)
        self.graphicsEngine.renderFrame()
        self.graphicsEngine.renderFrame()
        self.env.set_quality(self.save.quality)
        self._apply_fog()
        self.ui.set_loading("")

    def _apply_fullscreen(self):
        props = WindowProperties()
        if self.save.fullscreen:
            props.setFullscreen(True)
            props.setSize(self.pipe.getDisplayWidth(), self.pipe.getDisplayHeight())
        else:
            props.setFullscreen(False)
            props.setSize(1280, 720)
        self.win.requestProperties(props)

    # ------------------------------------------------------------ main loop
    def update(self, task):
        dt = min(CLOCK.getDt(), 0.05)
        st = self.state

        if st == "playing":
            self._update_playing(dt)
        elif st in ("menu", "settings"):
            self.player.update_idle(dt)
        elif st in ("dying", "gameover"):
            self.player.update_crashed(dt)
            self.gameover_age += dt
            if st == "dying":
                self.dying_timer -= dt
                if self.dying_timer <= 0:
                    self.game_over()

        if st != "paused":
            self.cam_ctrl.update(dt)
        self.ui.update(dt)

        if self.save.show_fps:
            self.fps_timer -= dt
            if self.fps_timer <= 0:
                self.fps_timer = 0.5
                self.ui.set_fps("FPS: %d" % round(CLOCK.getAverageFrameRate()))
        return task.cont

    def _update_playing(self, dt):
        # difficulty: speed and challenge grow smoothly with survival time
        self.play_time += dt
        self.speed = difficulty.speed_at(self.play_time)
        level = difficulty.level_at(self.play_time)
        self.player.update(dt, self.speed)
        self.distance = self.player.y
        self.cam_ctrl.set_speed(self.speed)

        self.env.update(self.player.y)
        self.obstacles.update(dt, self.player, self.speed, level)
        self.coins.update(dt, self.player, self.speed, level)

        # polymorphism: obstacles and coins are all GameObjects
        objects = self.obstacles.items + self.coins.coins
        for obj in objects:
            obj.update(dt, self.player)
        for obj in objects:
            if obj.touches(self.player):
                event = obj.on_hit(self.player)
                if event == "coin":
                    self.coin_count += 1
                    self.coins.collected(obj)
                    self.play("coin")
                    self.ui.pulse_coins()
                elif event in ("crash", "gap") and self.player.invincible <= 0:
                    self._hurt(obj, event)
                    break

        self.score = int(self.distance) + self.coin_count * COIN_SCORE
        idx = difficulty.stage_index(self.play_time)
        if idx != self.stage:
            self.stage = idx
            self.ui.show_banner("SPEED UP!")
        self._update_hud()

    def _hurt(self, obj, event):
        """The player hit something: lose a life, or die if no lives are left."""
        self.player.lives -= 1
        self.play("crash")
        self.cam_ctrl.kick(0.35)
        if self.player.lives > 0:
            target = obj.y + obj.respawn_offset() if obj.respawn_offset() > 0 else self.player.y
            obj.shatter()
            self.player.recover(max(0.0, target - self.player.y))
            self.ui.show_banner("OUCH!")
        else:
            self.player.crash(event)
            self.state = "dying"
            self.dying_timer = 1.2

    def _update_hud(self):
        frac = (self.speed - START_SPEED) / (MAX_SPEED - START_SPEED)
        self.ui.set_hud(self.score, self.coin_count, max(self.save.high_score, self.score),
                        int(self.distance), int(self.play_time), frac,
                        difficulty.stage_name(self.play_time), max(0, self.player.lives))


def main():
    try:
        game = JungleEscape()
        game.run()
    except Exception:
        import traceback
        traceback.print_exc()
        input("The game crashed. Press Enter to close...")
        sys.exit(1)


if __name__ == "__main__":
    main()
