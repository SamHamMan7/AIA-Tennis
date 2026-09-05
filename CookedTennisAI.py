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
# DeepCourt v4 -- v0.13-aware tactical tennis bot.
# Reliable racket-center contact remains the base. Drop, lob, and curve shots are
# situational weapons rather than replacements for the consistent rally game.
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
rally_fatigue = TennisGetFloat("Rally Fatigue")

shot_topspin = TennisGetFloat("Shot: Topspin")
shot_flat = TennisGetFloat("Shot: Flat")
shot_drop = TennisGetFloat("Shot: Drop")
shot_lob = TennisGetFloat("Shot: Lob")
shot_curve_left = TennisGetFloat("Shot: Curve Left")
shot_curve_right = TennisGetFloat("Shot: Curve Right")

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

# Prediction is more accurate in v0.12+, but live tracking after the bounce still
# gives the best final sweet-spot alignment.
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

# Rally accuracy is determined by horizontal distance from the logical racket
# center. Keep a buffer inside the Good-contact radius.
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
# Base rally placement
# -----------------------------------------------------------------------------
base_aim = ConditionalSetVector3(
    IsNull(self_scoring_location),
    random_aim,
    self_scoring_location,
)

# Near-zero AutoAim resolves to a legal opponent-half center landing.
center_aim = TennisAutoAim(Vector3(0.0, 0.0, 0.0))
safe_base_aim = base_aim * 0.62 + center_aim * 0.38

safe_wide = court_width * 0.28
centered_z = safe_base_aim.z * 0.45

opp_right = opp_pos.z > 1.35
opp_left = opp_pos.z < -1.35
opp_wide = opp_right | opp_left

open_z_if_not_right = ConditionalSetFloat(
    opp_left,
    safe_wide,
    centered_z,
)
open_court_z = ConditionalSetFloat(
    opp_right,
    safe_wide * -1.0,
    open_z_if_not_right,
)

random_right = random_aim.z >= 0.0
mixed_side_z = ConditionalSetFloat(
    random_right,
    safe_wide * 0.82,
    safe_wide * -0.82,
)

normal_rally_z = ConditionalSetFloat(
    opp_wide,
    open_court_z,
    mixed_side_z,
)

normal_rally_aim = TennisAutoAim(
    Vector3(safe_base_aim.x, safe_base_aim.y, normal_rally_z)
)

# -----------------------------------------------------------------------------
# Tactical trick shots -- v0.12 / v0.13
# -----------------------------------------------------------------------------
# With the court centered around the net, abs(opponent X) is a useful estimate of
# how deep the opponent is. Only try tricks on clean contact while not scrambling.
opp_depth = Abs(opp_pos.x)
stretched = (move_distance > 4.8) | walk_cannot_make_it
stable_for_trick = good_contact & ~stretched & ~ball_charged & (rally_fatigue < 0.55)

opp_near_net = opp_depth < 4.1
opp_very_deep = opp_depth > 8.2

# Random Aim Target changes over play. Use its lateral magnitude as a lightweight
# gate so drop/curve attempts are occasional instead of happening on every chance.
trick_roll = Abs(random_aim.z) > (court_width * 0.20)

lob_opportunity = stable_for_trick & opp_near_net
drop_opportunity = stable_for_trick & opp_very_deep & trick_roll
curve_opportunity = stable_for_trick & opp_wide & ~opp_near_net & ~opp_very_deep & trick_roll

# In v0.12+ aim is the actual intended landing location. Give each trick its own
# depth instead of trying to control depth with charge.
# Lob: deep and mostly away from the sideline.
lob_aim = TennisAutoAim(
    Vector3(center_aim.x * 1.68, center_aim.y, normal_rally_z * 0.70)
)

# Drop: short, with enough lateral angle to make a deep defender run forward.
drop_aim = TennisAutoAim(
    Vector3(center_aim.x * 0.36, center_aim.y, normal_rally_z * 0.58)
)

# Curve: deep-ish but start nearer the middle so the stronger v0.12 curve can do
# the sideways work without aiming dangerously close to a line.
curve_aim = TennisAutoAim(
    Vector3(center_aim.x * 1.35, center_aim.y, open_court_z * 0.30)
)

# Try both curve directions depending on which side the opponent occupies. This
# can be reversed later if testing shows Unity's left/right convention is opposite
# to the apparent world-space direction.
curve_shot = ConditionalSetFloat(
    opp_right,
    shot_curve_left,
    shot_curve_right,
)

# Priority: lob the net-rusher, drop-shot the deep camper, curve a wide opponent.
clean_attack = good_contact & ~stretched & ~ball_charged
normal_rally_shot = ConditionalSetFloat(
    clean_attack,
    shot_flat,
    shot_topspin,
)

shot_after_curve = ConditionalSetFloat(
    curve_opportunity,
    curve_shot,
    normal_rally_shot,
)
shot_after_drop = ConditionalSetFloat(
    drop_opportunity,
    shot_drop,
    shot_after_curve,
)
rally_shot = ConditionalSetFloat(
    lob_opportunity,
    shot_lob,
    shot_after_drop,
)

aim_after_curve = ConditionalSetVector3(
    curve_opportunity,
    curve_aim,
    normal_rally_aim,
)
aim_after_drop = ConditionalSetVector3(
    drop_opportunity,
    drop_aim,
    aim_after_curve,
)
rally_aim = ConditionalSetVector3(
    lob_opportunity,
    lob_aim,
    aim_after_drop,
)

# -----------------------------------------------------------------------------
# Serve placement
# -----------------------------------------------------------------------------
# v0.12+ clamps serve aim into the legal service area. Keep the first serve safely
# inward anyway; the second serve uses the known center-of-valid-serve target.
serve_side = Sign(legal_serve_target.z)
safe_first_serve_z = serve_side * court_width * 0.14
safe_first_serve = Vector3(
    legal_serve_target.x,
    legal_serve_target.y,
    safe_first_serve_z,
)

serve_aim = ConditionalSetVector3(
    is_second_serve,
    legal_serve_target,
    safe_first_serve,
)

aim_target = ConditionalSetVector3(
    is_self_serving,
    serve_aim,
    rally_aim,
)

move_and_aim = TennisAutoSwitch(move_target, aim_target)

# -----------------------------------------------------------------------------
# Swing timing
# -----------------------------------------------------------------------------
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

# PreferCharge lets the v0.12+ trick types carry their own charge/power behavior.
# Serving stays on the simple Normal Only sequence for reliability.
rally_auto_swing = TennisAutoSwing(rally_shot, "Prefer Charge")
serve_auto_swing = TennisAutoSwing(serve_shot, "Normal Only")

hold_for_alignment = (
    is_playing
    & ball_playable
    & ball_in_swing_range
    & ~good_contact
)
rally_swing = rally_auto_swing.swing | hold_for_alignment

swing_control = ConditionalSetBool(
    is_self_serving,
    serve_auto_swing.swing,
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
