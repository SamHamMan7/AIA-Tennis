import os

from AIGamePyLibrary import *

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

racket_offset = racket_pos - self_pos

safe_bounce = ConditionalSetVector3(
    IsNull(predicted_bounce),
    center_back,
    predicted_bounce,
)

body_for_bounce = safe_bounce - racket_offset
body_for_live_ball = ball_pos - racket_offset

incoming_target = ConditionalSetVector3(
    ball_playable,
    body_for_live_ball,
    body_for_bounce,
)

receive_ready = receive_stance * 0.60 + center_half * 0.40
base_recovery = center_back * 0.72 + center_half * 0.28

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

base_aim = ConditionalSetVector3(
    IsNull(self_scoring_location),
    random_aim,
    self_scoring_location,
)

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

move_and_aim = TennisAutoSwitch(move_target, aim_target)

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

save_path = GetTennisSavePath(BOT_NAME)
os.makedirs(os.path.dirname(save_path), exist_ok=True)
SaveData(save_path, "auto")
print(f"Saved DeepCourt graph to: {save_path}")
