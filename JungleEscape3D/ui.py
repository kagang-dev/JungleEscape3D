"""
ui.py - Menus and the in-game HUD (Panda3D DirectGUI), jungle adventure theme.

Screens: main menu, settings, HUD, pause menu, game over.
main.py passes in a dictionary of callback functions; the UI only displays
things and calls those callbacks when buttons are pressed.
"""
from direct.gui.DirectGui import DGG, DirectButton, DirectFrame
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TextNode, TransparencyAttrib

GOLD = (1.0, 0.85, 0.25, 1)
WHITE = (1, 1, 1, 1)
PANEL = (0.05, 0.11, 0.05, 0.86)
PANEL_DARK = (0.03, 0.07, 0.03, 0.70)
RED = (0.9, 0.18, 0.18, 1)


class GameUI:
    def __init__(self, base, cb):
        self.base = base
        self.cb = cb
        self.coin_pulse = 0.0
        self.banner_time = 0.0
        self.lives_shown = -1
        self._build_menu()
        self._build_settings()
        self._build_hud()
        self._build_pause()
        self._build_gameover()
        self.fps_text = OnscreenText(text="", parent=base.a2dBottomRight, pos=(-0.05, 0.05),
                                     scale=0.045, fg=(1, 1, 1, 0.9), align=TextNode.ARight,
                                     shadow=(0, 0, 0, 0.8))
        self.loading = OnscreenText(text="", pos=(0, 0), scale=0.09, fg=WHITE,
                                    shadow=(0, 0, 0, 1), mayChange=True)
        self.hide_all()

    # ------------------------------------------------------------ helpers
    def _button(self, parent, text, pos, command, w=0.40, color=(0.14, 0.46, 0.18), size=0.07):
        h = 0.082
        DirectFrame(parent=parent, pos=pos, frameColor=(1.0, 0.85, 0.3, 1),
                    frameSize=(-w - 0.008, w + 0.008, -h - 0.008, h + 0.008))
        lighter = tuple(min(1.0, c + 0.14) for c in color)
        darker = tuple(c * 0.7 for c in color)
        btn = DirectButton(
            parent=parent, pos=pos, text=text, text_scale=size, text_fg=WHITE,
            text_shadow=(0, 0, 0, 0.8), text_pos=(0, -size * 0.3),
            frameSize=(-w, w, -h, h), relief=DGG.FLAT,
            frameColor=(color + (1,), darker + (1,), lighter + (1,), (0.3, 0.3, 0.3, 1)),
            command=self._click, extraArgs=[command], pressEffect=1)
        shine = DirectFrame(parent=parent, pos=pos, frameColor=(1, 1, 1, 0.10),
                            frameSize=(-w, w, 0.0, h))
        shine.setTransparency(TransparencyAttrib.MAlpha)
        return btn

    def _click(self, command):
        self.cb["click"]()
        command()

    def _text(self, parent, text, pos, scale, fg=WHITE, align=TextNode.ACenter):
        return OnscreenText(text=text, parent=parent, pos=pos, scale=scale, fg=fg,
                            align=align, shadow=(0, 0, 0, 0.9), mayChange=True)

    def _overlay(self, color):
        f = DirectFrame(parent=self.base.aspect2d, frameColor=color, frameSize=(-4, 4, -2, 2))
        f.setTransparency(TransparencyAttrib.MAlpha)
        return f

    def _panel(self, parent, w, h):
        f = DirectFrame(parent=parent, frameColor=PANEL, frameSize=(-w, w, -h, h))
        f.setTransparency(TransparencyAttrib.MAlpha)
        for z0, z1 in ((h - 0.012, h), (-h, -h + 0.012)):
            DirectFrame(parent=parent, frameColor=GOLD, frameSize=(-w, w, z0, z1))
        for x0, x1 in ((-w, -w + 0.012), (w - 0.012, w)):
            DirectFrame(parent=parent, frameColor=GOLD, frameSize=(x0, x1, -h, h))
        return f

    # ------------------------------------------------------------ menu
    def _build_menu(self):
        self.menu = DirectFrame(parent=self.base.aspect2d, frameColor=(0, 0, 0, 0))
        x = -0.78
        self._text(self.menu, "JUNGLE", (x, 0.58), 0.22, GOLD)
        self._text(self.menu, "ESCAPE 3D", (x, 0.40), 0.13, WHITE)
        self._text(self.menu, "Run. Jump. Slide. Survive.", (x, 0.30), 0.05, (0.9, 1, 0.8, 1))
        self._button(self.menu, "PLAY", (x, 0, 0.12), self.cb["play"])
        self._button(self.menu, "SETTINGS", (x, 0, -0.08), self.cb["settings"], color=(0.2, 0.36, 0.5))
        self._button(self.menu, "EXIT", (x, 0, -0.28), self.cb["exit"], color=(0.5, 0.2, 0.16))
        self.menu_best = self._text(self.menu, "", (x, -0.46), 0.055, GOLD)
        self._text(self.menu, "A / D or Arrows: move    SPACE: jump    S / Down: slide    ESC: pause",
                   (0, -0.93), 0.045, (1, 1, 1, 0.85))

    # ------------------------------------------------------------ settings
    def _build_settings(self):
        self.settings = self._overlay((0, 0, 0, 0.35))
        panel = DirectFrame(parent=self.settings, frameColor=(0, 0, 0, 0))
        self._panel(panel, 0.72, 0.74)
        self._text(panel, "SETTINGS", (0, 0.52), 0.11, GOLD)
        self.btn_quality = self._button(panel, "", (0, 0, 0.28), self.cb["toggle_quality"], w=0.55)
        self.btn_sound = self._button(panel, "", (0, 0, 0.08), self.cb["toggle_sound"], w=0.55)
        self.btn_fps = self._button(panel, "", (0, 0, -0.12), self.cb["toggle_fps"], w=0.55)
        self.btn_full = self._button(panel, "", (0, 0, -0.32), self.cb["toggle_fullscreen"], w=0.55)
        self._button(panel, "BACK", (0, 0, -0.55), self.cb["back"], w=0.3, color=(0.5, 0.2, 0.16))

    def refresh_settings(self, save):
        self.btn_quality["text"] = "GRAPHICS: " + save.quality.upper()
        self.btn_sound["text"] = "SOUND: " + ("ON" if save.sound else "OFF")
        self.btn_fps["text"] = "SHOW FPS: " + ("ON" if save.show_fps else "OFF")
        self.btn_full["text"] = "FULLSCREEN: " + ("ON" if save.fullscreen else "OFF")

    # ------------------------------------------------------------ HUD
    def _build_hud(self):
        b = self.base
        self.hud_items = []

        def add(item):
            self.hud_items.append(item)
            return item

        # left: score panel
        add(DirectFrame(parent=b.a2dTopLeft, frameColor=PANEL_DARK, pos=(0.04, 0, -0.03),
                        frameSize=(0, 0.72, -0.30, 0))).setTransparency(TransparencyAttrib.MAlpha)
        add(DirectFrame(parent=b.a2dTopLeft, frameColor=GOLD, pos=(0.04, 0, -0.03),
                        frameSize=(0, 0.008, -0.30, 0)))
        add(OnscreenText(text="SCORE", parent=b.a2dTopLeft, pos=(0.08, -0.085), scale=0.04,
                         fg=(0.8, 1, 0.8, 1), align=TextNode.ALeft))
        self.score_text = add(OnscreenText(text="0", parent=b.a2dTopLeft, pos=(0.08, -0.17), scale=0.11,
                                           fg=WHITE, align=TextNode.ALeft, shadow=(0, 0, 0, 0.9),
                                           mayChange=True))
        self.info_text = add(OnscreenText(text="", parent=b.a2dTopLeft, pos=(0.08, -0.23), scale=0.042,
                                          fg=(1, 1, 1, 0.9), align=TextNode.ALeft, mayChange=True))
        self.best_text = add(OnscreenText(text="", parent=b.a2dTopLeft, pos=(0.08, -0.275), scale=0.036,
                                          fg=GOLD, align=TextNode.ALeft, mayChange=True))
        # right: coins + speed
        add(DirectFrame(parent=b.a2dTopRight, frameColor=PANEL_DARK, pos=(-0.04, 0, -0.03),
                        frameSize=(-0.55, 0, -0.30, 0))).setTransparency(TransparencyAttrib.MAlpha)
        self.coin_icon = add(DirectFrame(parent=b.a2dTopRight, frameColor=GOLD, pos=(-0.47, 0, -0.095),
                                         frameSize=(-0.04, 0.04, -0.04, 0.04)))
        self.coin_icon.setR(45)
        self.coin_text = add(OnscreenText(text="0", parent=b.a2dTopRight, pos=(-0.40, -0.12), scale=0.085,
                                          fg=GOLD, align=TextNode.ALeft, shadow=(0, 0, 0, 0.9),
                                          mayChange=True))
        self.stage_text = add(OnscreenText(text="", parent=b.a2dTopRight, pos=(-0.3, -0.20), scale=0.04,
                                           fg=(0.8, 1, 0.8, 1), align=TextNode.ACenter, mayChange=True))
        add(DirectFrame(parent=b.a2dTopRight, frameColor=(0, 0, 0, 0.6), pos=(-0.52, 0, -0.26),
                        frameSize=(0, 0.46, -0.02, 0.02))).setTransparency(TransparencyAttrib.MAlpha)
        self.speed_bar = add(DirectFrame(parent=b.a2dTopRight, frameColor=(0.4, 0.9, 0.3, 1),
                                         pos=(-0.52, 0, -0.26), frameSize=(0, 0.1, -0.02, 0.02)))
        add(OnscreenText(text="SPEED", parent=b.a2dTopRight, pos=(-0.53, -0.275), scale=0.03,
                         fg=(1, 1, 1, 0.8), align=TextNode.ARight))
        # top centre: lives (red gems)
        self.lives_gems = []
        for i in range(3):
            g = add(DirectFrame(parent=b.a2dTopCenter, frameColor=RED, pos=(-0.15 + i * 0.15, 0, -0.1),
                                frameSize=(-0.035, 0.035, -0.035, 0.035)))
            g.setR(45)
            self.lives_gems.append(g)
        # pause button
        self.pause_btn = add(DirectButton(
            parent=b.a2dTopRight, pos=(-0.15, 0, -0.42), text="II", text_scale=0.06,
            text_fg=WHITE, text_pos=(0, -0.02), frameSize=(-0.07, 0.07, -0.07, 0.07),
            relief=DGG.FLAT,
            frameColor=((0, 0, 0, 0.45), (0, 0, 0, 0.7), (0.1, 0.4, 0.15, 0.8), (0, 0, 0, 0.3)),
            command=self.cb["pause"]))
        # banner ("SPEED UP!")
        self.banner = OnscreenText(text="", pos=(0, 0.62), scale=0.13, fg=GOLD,
                                   shadow=(0, 0, 0, 1), mayChange=True)
        self.banner.setTransparency(TransparencyAttrib.MAlpha)

    def set_hud(self, score, coins, best, distance, seconds, speed_frac, stage, lives):
        self.score_text.setText(str(score))
        self.coin_text.setText(str(coins))
        self.best_text.setText("BEST " + str(best))
        self.info_text.setText("%d m    %d:%02d" % (distance, seconds // 60, seconds % 60))
        self.stage_text.setText(stage)
        self.speed_bar["frameSize"] = (0, 0.46 * max(0.03, min(1.0, speed_frac)), -0.02, 0.02)
        self.speed_bar["frameColor"] = (0.4 + 0.6 * speed_frac, 0.9 - 0.55 * speed_frac, 0.3, 1)
        if lives != self.lives_shown:
            self.lives_shown = lives
            for i, g in enumerate(self.lives_gems):
                g["frameColor"] = RED if i < lives else (0.25, 0.25, 0.25, 0.7)

    def show_banner(self, text):
        self.banner.setText(text)
        self.banner_time = 1.8

    def pulse_coins(self):
        self.coin_pulse = 1.0

    def update(self, dt):
        if self.coin_pulse > 0:
            self.coin_pulse = max(0.0, self.coin_pulse - dt * 4.0)
            self.coin_text.setScale(0.085 + 0.03 * self.coin_pulse)
            self.coin_icon.setScale(1.0 + 0.35 * self.coin_pulse)
        if self.banner_time > 0:
            self.banner_time = max(0.0, self.banner_time - dt)
            k = min(1.0, self.banner_time / 0.6)
            self.banner.setColorScale(1, 1, 1, k)
            self.banner.setScale(1.0 + (1.8 - self.banner_time) * 0.06)
            if self.banner_time == 0:
                self.banner.setText("")

    # ------------------------------------------------------------ pause
    def _build_pause(self):
        self.pause = self._overlay((0, 0, 0, 0.55))
        panel = DirectFrame(parent=self.pause, frameColor=(0, 0, 0, 0))
        self._panel(panel, 0.6, 0.62)
        self._text(panel, "PAUSED", (0, 0.40), 0.12, GOLD)
        self._button(panel, "RESUME", (0, 0, 0.18), self.cb["resume"])
        self._button(panel, "RESTART", (0, 0, -0.02), self.cb["restart"], color=(0.2, 0.36, 0.5))
        self._button(panel, "MAIN MENU", (0, 0, -0.22), self.cb["menu"], color=(0.5, 0.2, 0.16))

    # ------------------------------------------------------------ game over
    def _build_gameover(self):
        self.over = self._overlay((0.25, 0.02, 0.02, 0.5))
        panel = DirectFrame(parent=self.over, frameColor=(0, 0, 0, 0))
        self._panel(panel, 0.66, 0.78)
        self._text(panel, "GAME OVER", (0, 0.52), 0.13, (1, 0.35, 0.25, 1))
        self.over_score = self._text(panel, "", (0, 0.35), 0.08)
        self.over_coins = self._text(panel, "", (0, 0.25), 0.06, GOLD)
        self.over_dist = self._text(panel, "", (0, 0.16), 0.05, (0.9, 1, 0.9, 1))
        self.over_best = self._text(panel, "", (0, 0.07), 0.06, (0.8, 1, 0.8, 1))
        self.over_new = self._text(panel, "", (0, -0.02), 0.05, (1, 0.9, 0.3, 1))
        self._button(panel, "RESTART", (0, 0, -0.24), self.cb["restart"])
        self._button(panel, "MAIN MENU", (0, 0, -0.46), self.cb["menu"], color=(0.5, 0.2, 0.16))

    def show_gameover(self, score, coins, best, new_best, distance, seconds):
        self.over_score.setText("SCORE: %d" % score)
        self.over_coins.setText("COINS: %d" % coins)
        self.over_dist.setText("DISTANCE: %d m    TIME: %d:%02d" % (distance, seconds // 60, seconds % 60))
        self.over_best.setText("BEST: %d" % best)
        self.over_new.setText("NEW HIGH SCORE!" if new_best else "")
        self.over.show()

    # ------------------------------------------------------------ visibility
    def hide_all(self):
        for f in (self.menu, self.settings, self.pause, self.over):
            f.hide()
        self.set_hud_visible(False)
        self.banner.hide()

    def set_hud_visible(self, visible):
        for item in self.hud_items:
            item.show() if visible else item.hide()
        if visible:
            self.banner.show()
            self.lives_shown = -1

    def show_menu(self, best):
        self.hide_all()
        self.menu_best.setText("BEST SCORE: %d" % best)
        self.menu.show()

    def show_settings(self, save):
        self.hide_all()
        self.refresh_settings(save)
        self.settings.show()

    def show_hud(self):
        self.hide_all()
        self.set_hud_visible(True)

    def show_pause(self):
        self.pause.show()

    def hide_pause(self):
        self.pause.hide()

    def set_fps(self, text):
        self.fps_text.setText(text)

    def set_loading(self, text):
        self.loading.setText(text)
