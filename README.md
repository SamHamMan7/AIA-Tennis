# DeepCourt Tennis AI

DeepCourt is a reactive AI bot for AIA Tennis v0.11, built with `AIGamePyLibrary`.

## What it does

- Prepositions using `Predicted Bounce`.
- Corrects movement so `Self Racket Center`, not just the body center, meets the ball.
- Tracks the live ball once it becomes playable.
- Recovers toward deep center with a small opponent-tendency bias.
- Aims wide away from the opponent.
- Uses charged Flat attacks normally and safer Topspin when stretched or on second serve.
- Uses an aggressive wide first serve and a conservative legal second serve.
- Sprints only for time-critical interceptions while preserving stamina.

## Easiest Windows setup

1. Download or clone this repository.
2. Double-click:

```text
build_deepcourt.bat
```

The builder will automatically:

- look for `AIGamePyLibrary` next to this repository;
- clone it from `theaia/AIGamePyLibrary` if it is missing;
- update it when possible;
- detect `py` or `python`;
- compile DeepCourt;
- save `DeepCourt.txt` into the game's Tennis save directory;
- open that save directory when the build succeeds.

The expected result is:

```text
%USERPROFILE%\AppData\LocalLow\Unicorn One\AIComp\Saves\Tennis\DeepCourt.txt
```

Then launch `Aialanders.exe`, open Tennis, and select/load **DeepCourt**.

## Requirements

- Windows
- Python 3
- Git for Windows if `AIGamePyLibrary` has not already been cloned
- AIA Tennis v0.11

## Manual setup

If you prefer to run the Python file directly, keep the two repositories as siblings:

```text
some-folder/
├── AIA-Tennis/
│   ├── CookedTennisAI.py
│   └── build_deepcourt.bat
└── AIGamePyLibrary/
    └── AIGamePyLibrary/
        ├── __init__.py
        ├── nodes.py
        └── ...
```

Then run from `AIA-Tennis`:

```bash
py CookedTennisAI.py
```

or:

```bash
python CookedTennisAI.py
```

`CookedTennisAI.py` now detects the sibling library automatically, so no `PYTHONPATH` setup is required.

## How the bot is executed

The Python script does **not** stay running during a match. It compiles a static node graph into `DeepCourt.txt`. The Unity game then reevaluates that graph every simulation tick.

That means you only need to rebuild after changing the Python bot or updating its graph logic.

## Updating

To update DeepCourt later:

```bash
git pull
```

Then run `build_deepcourt.bat` again.

## Repository

This bot is maintained separately from the game library. `AIGamePyLibrary` remains an external dependency from:

```text
https://github.com/theaia/AIGamePyLibrary
```
