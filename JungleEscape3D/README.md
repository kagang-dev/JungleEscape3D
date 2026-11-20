# JUNGLE ESCAPE 3D  (v2)

A 3D endless runner made with Python + Panda3D. No external assets needed:
all models are generated in code and all sounds are synthesised on first run.

## Install (Windows)
1. Install Python 3.9 - 3.12 from https://www.python.org (tick "Add Python to PATH").
2. Open a terminal in this folder and run:  `pip install panda3d`
   (if `pip` is not found, use `py -m pip install panda3d`)
3. Start the game:  `python main.py`  (or `py main.py`, or double-click `run_game.bat`)

The first start takes a few seconds ("Growing the jungle...") while the forest is generated.

## Controls
| Key                | Action                         |
|--------------------|--------------------------------|
| A / Left Arrow     | Move left                      |
| D / Right Arrow    | Move right                     |
| SPACE (or W / Up)  | Jump                           |
| S / Down Arrow     | Slide (in the air: slam down)  |
| ESC                | Pause / resume                 |
| ENTER / SPACE      | Start / restart from menus     |

## Rules
* You have 3 lives (red gems at the top). Hitting an obstacle costs one life, then
  you blink for 2 seconds and cannot be hurt. At 0 lives the game is over.
* Score = distance + 10 per coin. The high score is saved.
* The longer you survive, the faster it gets and the more obstacles appear
  (see `difficulty.py`). Stages: Explorer, Trailblazer, Adventurer, Daredevil, Legend.
* Settings: graphics quality (Low / Medium / High), sound, FPS counter, fullscreen.

## Files and classes
| File             | Purpose / main classes |
|------------------|------------------------|
| main.py          | `JungleEscape(ShowBase)`: window, game states, input, main loop |
| gameobjects.py   | OOP core: `GameObject` -> `Coin`, `Obstacle` -> `Log`, `Barrier`, `Rock`, `Ruin`, `Branch`, `Gap` |
| player.py        | `Player`: explorer model, animation, movement, lives |
| obstacles.py     | `ObstacleManager`: obstacle models and spawning |
| coins.py         | `CoinManager`: coin model, patterns, sparkle effects |
| environment.py   | `Environment`: endless jungle (trees, plants, trail, river, ruins) |
| sky.py           | Sky dome, clouds, sun |
| camera.py        | `ChaseCamera`: smooth chase camera + menu orbit |
| ui.py            | `GameUI`: menus, HUD, pause, game over |
| difficulty.py    | Speed and difficulty curves |
| shapes.py        | `MeshBuilder`: procedural modelling (smooth shading, limbs, rough blobs) |
| settings.py      | Constants, quality presets, `SaveData` |
| sounds.py        | Generates the .wav sound effects |

Save data is stored in `savedata.json` next to main.py.

## Performance tips (low-end PCs)
* Settings -> GRAPHICS: choose LOW (fewest objects, shortest view distance).
* Settings -> SHOW FPS to check your frame rate.
* Presets can be edited in `QUALITY` inside settings.py.
