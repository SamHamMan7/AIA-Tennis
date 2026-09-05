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
#
# The game's rally accuracy is determined by horizontal distance from the ball to
# Self Racket Center. Good/Perfect contact keeps the chosen landing exactly; an
# Early/Late hit can add a very large lateral miss. This version therefore gives
# contact quality priority over extreme angle hunting.
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
legal_serve_target = TennisGetVector3("Center Of Legal Serve Area")
random_aim = TennisGetVector3("Random Aim Target")
self_scoring_location = TennisGetVector3("Self Average Scoring Location")
estimated_opp_shot = TennisGetVector3("Estimated Opponent Shot Location")

is_playing = TennisGetBool("Is Playing")
is_self_server = TennisGetBool("Is Self Server For Set")
is_self_serving = TennisGetBool("Is Self Actively Serving")
is_second_serve = TennisGetBool("Is Second Serve")
ball_incoming = TennisGetBool("Ball Incoming")
ball_playable = TennisGetBool("Is Ball Playable")
ball_in_swing_range = TennisGetBool("Ball In Swing Range")
ball_has_bounced = TennisGetBool("Ball Has Bounced")
ball_charged = TennisGetBool("Ball Has Charged Effect")

self_stamina = TennisGetFloat("Self Stamina Pct")
court_width = TennisGetFloat("Court Width")
time_to_destination = TennisGetFloat("Self Time To Destination")

shot_topspin = TennisGetFloat("Shot: Topspin")
shot_flat = TennisGetFloat("Shot: Flat")

# -----------------------------------------------------------------------------
# Contact geometry
# -----------------------------------------------------------------------------
# The logical racket sweet spot is offset from the body. Move the body by the
# inverse of that offset so the racket, rather than the player's feet, reaches the
# ball. This is the exact transform the game uses to grade rally contact.
racket_offset = racket_pos - self_pos

safe_bounce = ConditionalSetVector3(
    IsNull(predicted_bounce),
    center_back,
    predicted_bounce,
)

body_for_bounce = safe_bounce - racket_offset
body_for_live_ball = ball_pos - racket_offset

# While an unbounced rally ball is approaching, lead the current ball slightly
# toward its predicted bounce. This reduces the last-second chase that was causing
# the old bot to arrive with the racket off-center. After a bounce, track live.
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

# Measure the horizontal sweet-spot error directly. Height is intentionally
# ignored because Tennis v0.11's contact grade also ignores height once the strike
# volume is satisfied.
contact_dx = ball_pos.x - racket_pos.x
contact_dz = ball_pos.z - racket_pos.z
contact_dist_sq = contact_dx * contact_dx + contact_dz * contact_dz

# Good contact extends to 1.85 m. Use a small buffer inside that ring so normal
# runtime jitter still leaves us in the no-accuracy-penalty zone.
good_contact = contact_dist_sq <= (1.70 * 1.70)
perfect_contact = contact_dist_sq <= (1.02 * 1.02)

# -----------------------------------------------------------------------------
# Footwork / recovery
# -----------------------------------------------------------------------------
# The stock receive stance is too vulnerable to wide fire serves. Start even more
# centrally than v1 so there is less emergency lateral travel.
receive_ready = receive_stance * 0.45 + center_half * 0.55

# Recover a little less deep than v1. Getting to the ball early improves contact
# far more than camping on the baseline helps defense.
base_recovery = center_back * 0.58 + center_half * 0.42

# Opponent-shot estimates are useful, but the old 35% commitment could pull us
# away from a sudden change of direction. Keep it as only a small bias.
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

# Sprint sooner than v1. Arriving early is valuable because Good/Perfect contact
# completely avoids the game's large Early/Late aim displacement.
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
# Scoring history is useful for depth, but pull it toward a neutral center target
# so an old winner near a line does not become our permanent high-risk aim.
base_aim = ConditionalSetVector3(
    IsNull(self_scoring_location),
    random_aim,
    self_scoring_location,
)

center_aim = TennisAutoAim(Vector3(0.0, 0.0, 0.0))
safe_base_aim = base_aim * 0.62 + center_aim * 0.38

# v1 aimed at 41.5% of court width: only ~0.9 m inside a singles sideline.
# That was far too aggressive once an imperfect contact added lateral drift.
# v2 uses ~2.3 m of sideline margin but still attacks the side away from opponent.
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

# Keep the first serve aggressive enough to move the receiver, but no longer hug
# the service-box line. Second serve remains the center of the legal area.
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
# Topspin is the consistency ball. Only switch to the faster Flat when the racket
# is already centered and we are not scrambling. This means bad contact is not
# combined with the game's fastest, hardest-to-control trajectory.
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

# AutoSwing normally releases once it reaches the strike volume. If the ball is
# reachable but the racket sweet spot is still outside our buffered Good ring,
# keep holding charge briefly. As soon as alignment becomes Good, the extra hold
# disappears and AutoSwing's release reaches the controller. We do NOT alter serve
# toss timing with this gate.
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
