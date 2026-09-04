import os
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Locate AIGamePyLibrary automatically.
#
# Supported layouts:
#   parent/
#     AIA-Tennis/
#     AIGamePyLibrary/
#
# or:
#   AIA-Tennis/
#     AIGamePyLibrary/
# -----------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent
LIBRARY_CANDIDATES = (
    ROOT.parent / "AIGamePyLibrary",
    ROOT / "AIGamePyLibrary",
)

for candidate in LIBRARY_CANDIDATES:
    package_init = candidate / "AIGamePyLibrary" / "__init__.py"
    if package_init.is_file():
        sys.path.insert(0, str(candidate))
        break

try:
    from AIGamePyLibrary import *
except ModuleNotFoundError as exc:
    if exc.name == "AIGamePyLibrary":
        raise SystemExit(
            "AIGamePyLibrary was not found.\n"
            "Run build_deepcourt.bat on Windows, or clone\n"
            "https://github.com/theaia/AIGamePyLibrary next to this repository."
        ) from exc
    raise

# -----------------------------------------------------------------------------
# DeepCourt: reactive tennis bot for AIA Tennis v0.11
# -----------------------------------------------------------------------------

BOT_NAME = "DeepCourt"

InitializeTennis(BOT_NAME, "United States of America", "Tan", 0, "Brown", 0)

self_tf = TennisGetTransform("Self")
opp_tf = TennisGetTransform("Opponent")
racket_tf = TennisGetTransform("Self Racket Center")

self_pos = RelativePosition(self_tf, "Self")
opp_pos = RelativePosition(opp_tf, "Self")
racket_pos = RelativePosition(racket_tf, "Self")

ball_pos = TennisGetVector3("Ball Position")
predicted_bounce = TennisGetVector3("Predicted Bounce")
center_half = TennisGetVector3("Center Of Half")
center_back = TennisGetVector3("Center Of Back")
serve_stance = TennisGetVector3("Serve Stance")
receive_stance = TennisGetVector3("Receive Stance")
legal_serve_target = TennisGetVector3("Legal Serve Target")
random_aim = TennisGetVector3("Random Aim Target")
self_scoring_location = TennisGetVector3("Self Average Scoring Location")
estimated_opp_shot = TennisGetVector3("Estimated Opponent Shot Location")

is_playing = TennisGetBool("Is Playing")
is_self_server = TennisGetBool("Is Self Server")
is_self_serving = TennisGetBool("Is Self Serving")
is_second_serve = TennisGetBool("Is Second Serve")
ball_incoming = TennisGetBool("Ball Incoming")
ball_playable = TennisGetBool("Is Ball Playable")
ball_charged = TennisGetBool("Ball Has Charged Effect")

self_stamina = TennisGetFloat("Self Stamina Pct")
court_width = TennisGetFloat("Court Width")
time_to_destination = TennisGetFloat("Time To Destination")

shot_topspin = TennisGetFloat("Shot: Topspin")
shot_flat = TennisGetFloat("Shot: Flat")

# Move the BODY so the logical racket center reaches the ball. Contact quality in
# the game is graded from Self Racket Center, not simply the player transform.
racket_offset = racket_pos - self_pos

# Predicted Bounce is not trustworthy during a serve toss, so keep a safe fallback.
safe_bounce = ConditionalSetVector3(
    IsNull(predicted_bounce),
    center_back,
    predicted_bounce,
)

body_for_bounce = safe_bounce - racket_offset
body_for_live_ball = ball_pos - racket_offset

# Pre-position at the bounce, then track the live ball once it becomes playable.
incoming_target = ConditionalSetVector3(
    ball_playable,
    body_for_live_ball,
    body_for_bounce,
)

# Shade the stock receive position toward center to cover wide serves better.
receive_ready = receive_stance * 0.60 + center_half * 0.40
base_recovery = center_back * 0.72 + center_half * 0.28

# Bias recovery toward the opponent's estimated target without overcommitting.
safe_opp_estimate = ConditionalSetVector3(
    IsNull(estimated_opp_shot),
    base_recovery,
    estimated_opp_shot,
)
estimate_body = safe_opp_estimate - racket_offset
recovery_target = base_recovery * 0.65 + estimate_body * 0.35

rally_move = ConditionalSetVector3(
    ball_incoming,
    incoming_target,
    recovery_target,
)

setup_move = ConditionalSetVector3(
    is_self_server,
    serve_stance,
    receive_ready,
)

move_target = ConditionalSetVector3(
    is_playing,
    rally_move,
    setup_move,
)

# Sprint only when walking is unlikely to arrive in time or the target is far away.
move_distance = Distance(self_pos, move_target)
walk_cannot_make_it = (time_to_destination * 7.6) < move_distance
very_far = move_distance > 5.0
urgent = walk_cannot_make_it | very_far

normal_stamina_ok = self_stamina > 0.24
fire_stamina_ok = self_stamina > 0.16
stamina_ok = ConditionalSetBool(
    ball_charged,
    fire_stamina_ok,
    normal_stamina_ok,
)

sprint = is_playing & ball_incoming & urgent & stamina_ok

# Prefer a learned scoring location for depth; fall back to a legal random target.
base_aim = ConditionalSetVector3(
    IsNull(self_scoring_location),
    random_aim,
    self_scoring_location,
)

# Aim wide, away from the opponent, while leaving margin inside the sideline.
safe_wide = court_width * 0.415
opp_right = opp_pos.z > 0.70
opp_left = opp_pos.z < -0.70

wide_z_if_not_right = ConditionalSetFloat(
    opp_left,
    safe_wide,
    base_aim.z,
)
away_z = ConditionalSetFloat(
    opp_right,
    safe_wide * -1.0,
    wide_z_if_not_right,
)

rally_aim_raw = Vector3(base_aim.x, base_aim.y, away_z)
rally_aim = TennisAutoAim(rally_aim_raw)

# Aggressive wide Flat first serve; conservative legal Topspin second serve.
serve_side = Sign(legal_serve_target.z)
aggressive_serve_z = serve_side * court_width * 0.38
aggressive_serve = Vector3(
    legal_serve_target.x,
    legal_serve_target.y,
    aggressive_serve_z,
)
serve_aim = ConditionalSetVector3(
    is_second_serve,
    legal_serve_target,
    aggressive_serve,
)

aim_target = ConditionalSetVector3(
    is_self_serving,
    serve_aim,
    rally_aim,
)

# AutoSwitch allows independent movement and shot placement.
move_and_aim = TennisAutoSwitch(move_target, aim_target)

# Flat is the default attacking ball. Topspin gives more margin when stretched or
# when handling a charged incoming shot.
stretched = (move_distance > 5.5) | walk_cannot_make_it
use_topspin_rally = stretched | ball_charged
rally_shot = ConditionalSetFloat(
    use_topspin_rally,
    shot_topspin,
    shot_flat,
)

serve_shot = ConditionalSetFloat(
    is_second_serve,
    shot_topspin,
    shot_flat,
)
shot_type = ConditionalSetFloat(
    is_self_serving,
    serve_shot,
    rally_shot,
)

auto_swing = TennisAutoSwing(shot_type, "Prefer Charge")

TennisController(
    move_and_aim,
    auto_swing.swing,
    shot_type,
    sprint,
)

# Compile the static graph directly into the save directory used by AIA Tennis.
save_path = GetTennisSavePath(BOT_NAME)
os.makedirs(os.path.dirname(save_path), exist_ok=True)
SaveData(save_path, "auto")
print(f"Saved DeepCourt graph to: {save_path}")
