import os
import sys
from pathlib import Path

# -----------------------------------------------------------------------------
# Locate AIGamePyLibrary automatically.
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
# DeepCourt v2 -- accuracy-first reactive tennis bot for AIA Tennis v0.11.
# -----------------------------------------------------------------------------

BOT_NAME = "DeepCourt"
InitializeTennis(BOT_NAME, "United States of America", "Tan", 0, "Brown", 0)

# -----------------------------------------------------------------------------
# World state
# -----------------------------------------------------------------------------
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
ball_in_swing_range = TennisGetBool("Ball In Swing Range")
ball_has_bounced = TennisGetBool("Ball Has Bounced")
ball_charged = TennisGetBool("Ball Has Charged Effect")

self_stamina = TennisGetFloat("Self Stamina Pct")
court_width = TennisGetFloat("Court Width")
time_to_destination = TennisGetFloat("Time To Destination")

shot_topspin = TennisGetFloat("Shot: Topspin")
shot_flat = TennisGetFloat("Shot: Flat")

# -----------------------------------------------------------------------------
# Contact geometry
# -----------------------------------------------------------------------------
racket_offset = racket_pos - self_pos

safe_bounce = ConditionalSetVector3(
    IsNull(predicted_bounce),
    center_back,
    predicted_bounce,
)

body_for_bounce = safe_bounce - racket_offset
body_for_live_ball = ball_pos - racket_offset

lead_target = body_for_live_ball * 0.72 + body_for_bounce * 0.28
playable_target = ConditionalSetVector3(
    ball_has_bounced,
    body_for_live_ball,
    lead_target,
)

incoming_target = ConditionalSetVector3(
    ball_playable,
    playable_target,
    body_for_bounce,
)

# Rally contact quality is graded from the horizontal ball-to-racket-center error.
contact_dx = ball_pos.x - racket_pos.x
contact_dz = ball_pos.z - racket_pos.z
contact_dist_sq = contact_dx * contact_dx + contact_dz * contact_dz

good_contact = contact_dist_sq <= (1.70 * 1.70)

# -----------------------------------------------------------------------------
# Footwork / recovery
# -----------------------------------------------------------------------------
receive_ready = receive_stance * 0.45 + center_half * 0.55
base_recovery = center_back * 0.58 + center_half * 0.42

safe_opp_estimate = ConditionalSetVector3(
    IsNull(estimated_opp_shot),
    base_recovery,
    estimated_opp_shot,
)
estimate_body = safe_opp_estimate - racket_offset
recovery_target = base_recovery * 0.80 + estimate_body * 0.20

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

move_distance = Distance(self_pos, move_target)
walk_cannot_make_it = (time_to_destination * 6.9) < move_distance
very_far = move_distance > 4.0
urgent = walk_cannot_make_it | very_far

normal_stamina_ok = self_stamina > 0.18
fire_stamina_ok = self_stamina > 0.10
stamina_ok = ConditionalSetBool(
    ball_charged,
    fire_stamina_ok,
    normal_stamina_ok,
)

sprint = is_playing & ball_incoming & urgent & stamina_ok

# -----------------------------------------------------------------------------
# Safer shot placement
# -----------------------------------------------------------------------------
base_aim = ConditionalSetVector3(
    IsNull(self_scoring_location),
    random_aim,
    self_scoring_location,
)

center_aim = TennisAutoAim(Vector3(0.0, 0.0, 0.0))
safe_base_aim = base_aim * 0.62 + center_aim * 0.38

safe_wide = court_width * 0.28
centered_z = safe_base_aim.z * 0.45
opp_right = opp_pos.z > 0.90
opp_left = opp_pos.z < -0.90

wide_z_if_not_right = ConditionalSetFloat(
    opp_left,
    safe_wide,
    centered_z,
)
away_z = ConditionalSetFloat(
    opp_right,
    safe_wide * -1.0,
    wide_z_if_not_right,
)

rally_aim_raw = Vector3(safe_base_aim.x, safe_base_aim.y, away_z)
rally_aim = TennisAutoAim(rally_aim_raw)

serve_side = Sign(legal_serve_target.z)
aggressive_serve_z = serve_side * court_width * 0.25
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

move_and_aim = TennisAutoSwitch(move_target, aim_target)

# -----------------------------------------------------------------------------
# Shot type + swing timing
# -----------------------------------------------------------------------------
stretched = (move_distance > 4.8) | walk_cannot_make_it
clean_attack = good_contact & ~stretched & ~ball_charged
rally_shot = ConditionalSetFloat(
    clean_attack,
    shot_flat,
    shot_topspin,
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

# If AutoSwing wants to release while the racket is still outside the buffered
# Good-contact ring, keep charge held for a moment so footwork can finish lining
# up. Serve timing is left entirely to AutoSwing.
hold_for_alignment = (
    is_playing
    & ball_playable
    & ball_in_swing_range
    & ~good_contact
)
rally_swing = auto_swing.swing | hold_for_alignment
swing_control = ConditionalSetBool(
    is_self_serving,
    auto_swing.swing,
    rally_swing,
)

TennisController(
    move_and_aim,
    swing_control,
    shot_type,
    sprint,
)

# -----------------------------------------------------------------------------
# Export
# -----------------------------------------------------------------------------
save_path = GetTennisSavePath(BOT_NAME)
os.makedirs(os.path.dirname(save_path), exist_ok=True)
SaveData(save_path, "auto")
print(f"Saved DeepCourt graph to: {save_path}")
