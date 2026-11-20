"""
gameobjects.py - The OOP heart of the game.

Class family tree
-----------------
    GameObject                 (parent: anything placed in the jungle)
    |-- Coin                   (child: spins, floats, gives points)
    `-- Obstacle               (child: has a hitbox, hurts the player)
        |-- Log                (grandchildren: each one overrides some methods)
        |-- Barrier
        |-- Rock
        |-- Ruin
        |-- Branch
        `-- Gap

Polymorphism: main.py keeps one list of GameObjects and simply calls
    obj.update(dt, player)   obj.touches(player)   obj.on_hit(player)
on every item.  Each class answers in its own way (a Coin gives points, a Rock
crashes the player, a Gap makes the player fall).
"""
import math


class GameObject:
    """Parent class of every object placed in the world."""

    kind = "object"

    def __init__(self, node, x, y):
        self.node = node          # the Panda3D NodePath that is drawn
        self.x = x
        self.y = y
        self.alive = True         # False = cannot hurt / be collected any more
        self.removed = False      # True = node was deleted from the scene

    # -- methods that child classes override --------------------------------
    def update(self, dt, player):
        """Called every frame. The parent does nothing."""

    def box(self):
        """Hitbox as (xmin, xmax, ymin, ymax, zmin, zmax)."""
        return (self.x - 0.5, self.x + 0.5, self.y - 0.5, self.y + 0.5, 0.0, 1.0)

    def on_hit(self, player):
        """Called when the player touches this object. Returns an event name."""
        return None

    # -- shared behaviour (code reuse) --------------------------------------
    def touches(self, player):
        """True if this object's hitbox overlaps the player's hitbox."""
        if not self.alive:
            return False
        ox0, ox1, oy0, oy1, oz0, oz1 = self.box()
        px0, px1, py0, py1, pz0, pz1 = player.hitbox()
        return not (ox0 > px1 or ox1 < px0 or oy0 > py1 or oy1 < py0
                    or oz0 > pz1 or oz1 < pz0)

    def is_behind(self, y):
        return self.y < y

    def remove(self):
        if not self.removed:
            self.removed = True
            self.alive = False
            self.node.removeNode()


# ---------------------------------------------------------------- coin
class Coin(GameObject):
    """A collectible gold coin. Child of GameObject."""

    kind = "coin"

    def __init__(self, node, disc, x, y, z):
        super().__init__(node, x, y)
        self.disc = disc          # the part that spins
        self.z = z
        self.spin = (x * 37 + y * 11) % 360
        self.age = (y * 0.37) % 6.28

    def update(self, dt, player):                      # overrides GameObject.update
        self.spin += 200.0 * dt
        self.age += dt * 3.0
        self.disc.setH(self.spin)
        self.node.setZ(self.z + math.sin(self.age) * 0.12)   # floating

    def box(self):                                     # overrides GameObject.box
        return (self.x - 1.3, self.x + 1.3, self.y - 1.3, self.y + 1.3,
                self.z - 0.5, self.z + 0.5)

    def on_hit(self, player):                          # overrides GameObject.on_hit
        return "coin"


# ---------------------------------------------------------------- obstacles
class Obstacle(GameObject):
    """Parent of all obstacles. Children set the size of the hitbox."""

    kind = "obstacle"
    HW, HD, ZMIN, ZMAX = 1.2, 0.5, 0.0, 1.0      # half width, half depth, z range
    NEEDS = "jump"                                  # how the player should beat it

    def __init__(self, node, x, y):
        super().__init__(node, x, y)

    def box(self):
        return (self.x - self.HW, self.x + self.HW, self.y - self.HD,
                self.y + self.HD, self.ZMIN, self.ZMAX)

    def on_hit(self, player):
        return "crash"

    def shatter(self):
        """What happens to the obstacle after it hurt the player."""
        self.remove()

    def respawn_offset(self):
        """How far forward the player is moved after being hurt."""
        return 0.0


class Log(Obstacle):
    kind = "log"
    HW, HD, ZMIN, ZMAX = 1.30, 0.50, 0.0, 0.90
    NEEDS = "jump"


class Barrier(Obstacle):
    kind = "barrier"
    HW, HD, ZMIN, ZMAX = 1.30, 0.28, 0.0, 1.25
    NEEDS = "jump"

    def shatter(self):                                 # overrides: it gets smashed flat
        self.node.setSz(0.15)
        self.alive = False


class Rock(Obstacle):
    kind = "rock"
    HW, HD, ZMIN, ZMAX = 1.25, 1.20, 0.0, 3.20
    NEEDS = "dodge"


class Ruin(Obstacle):
    kind = "ruin"
    HW, HD, ZMIN, ZMAX = 1.25, 1.10, 0.0, 3.30
    NEEDS = "dodge"


class Branch(Obstacle):
    kind = "branch"
    HW, HD, ZMIN, ZMAX = 1.45, 0.40, 1.45, 8.0
    NEEDS = "slide"

    def __init__(self, node, x, y):
        super().__init__(node, x, y)
        self.t = (x + y) % 6.28

    def update(self, dt, player):                      # overrides: leaves sway
        self.t += dt * 1.6
        self.node.setR(math.sin(self.t) * 1.2)


class Gap(Obstacle):
    kind = "gap"
    HW, HD, ZMIN, ZMAX = 1.25, 2.00, -20.0, 0.30
    NEEDS = "jump"

    def on_hit(self, player):                          # overrides: the player falls
        return "gap"

    def shatter(self):                                 # the hole stays in the ground
        self.alive = False

    def respawn_offset(self):                          # move the player past the hole
        return self.HD + 1.8


OBSTACLE_CLASSES = {"log": Log, "barrier": Barrier, "rock": Rock,
                    "ruin": Ruin, "branch": Branch, "gap": Gap}
