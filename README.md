# DeepCourt Tennis AI

DeepCourt is a reactive AI bot for AIA Tennis v0.11, built with `AIGamePyLibrary`.

## What it does

- Prepositions using `Predicted Bounce`.
- Corrects body position so `Self Racket Center`, not the body center, meets the ball.
- Tracks the live ball once it becomes playable.
- Recovers toward deep center with a small opponent-tendency bias.
- Aims wide away from the opponent.
- Uses charged Flat attacks normally and safer Topspin when stretched or on second serve.
- Uses an aggressive wide first serve and a conservative legal second serve.
- Sprints only for time-critical interceptions with a stamina reserve.

## Setup

1. Clone/update `https://github.com/theaia/AIGamePyLibrary` so you have the current Tennis nodes.
2. Put `CookedTennisAI.py` next to the `AIGamePyLibrary` package directory.
3. Run:

```bash
py CookedTennisAI.py
```

or:

```bash
python CookedTennisAI.py
```

4. The script writes `DeepCourt.txt` directly to:

```text
%USERPROFILE%\AppData\LocalLow\Unicorn One\AIComp\Saves\Tennis\DeepCourt.txt
```

5. Launch Tennis v0.11 and select/load DeepCourt as the AI graph.

## Notes

The Python file compiles a static node graph. Python itself does not run once the match starts; Unity reevaluates the generated graph every simulation tick.
