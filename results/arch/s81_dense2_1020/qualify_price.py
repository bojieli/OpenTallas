"""DENSE2 10-20: static qualification of an exact-merged split map + inter-die traffic / cycle pricing.
usage: qualify_price.py MERGED_MAP.json FRAMES  -> static_capacity_receipt_<tag>.json (next to the map)

Qualification (qualify_static_n.py rules, split form): every stage exact PASS with identical expert layouts; every dense
layer exactly once as A and once as B, B on the stage right after A; every (layer, expert) exactly once; causality
(experts of L-1 end on or before A(L), experts of L start on or after B(L)).
Pricing (MODEL on the 139-stage composed calendar, dv_mu_calendar_phys @3fe699d4d, s112_139 records):
  stage hop HOP = 1006 + 2 cycles a stage (cal2 STAGE_HOP law); h message 40,976 B = H_MSG 652 cycles on the stage link
  (dv_mu_calendar.H_MSG / ROM-MULTIUSER) -> 62.85 B / cycle.
  A -> B message per rank die, per token per layer: R a_proj outputs as BF16 (the a_proj op output: the fixture value
  each row's FP32 accumulator rounds to; lower_xs gen/check) + one 16-B header (user / tok / pos tag). FP32 bound shown.
  It rides the existing A -> B stage link right after x (no new link class, no flow control: fixed slot).
  Latency: B's own a_proj rows start on x arrival (one hop after A's), A's rows start on x at A; A's outputs leave A at
  max(A a_proj done, x serialisation done) -> they reach B at most ser_out cycles after x + B's own phase would need
  them (the one-phase a_proj is x-stream bound, same length on A and B).  Priced as +ser_out a split layer on the token
  critical path (upper bound), x6 positions per MTP step; plus (N - 139) x HOP for the added stages.
"""
import collections, hashlib, json, math, sys
from pathlib import Path
p = Path(sys.argv[1]); F = int(sys.argv[2]); b = p.read_bytes(); m = json.loads(b)
N = m['stages_count']; st = m['stages']; assert len(st) == N and m.get('dense_split2')
assert m['verdict']['all_pass'] and not m['verdict']['missing'], m['verdict']
cov = collections.Counter(); where = {}; es = {}
for i, s in enumerate(st):
    c = s['capacity']; assert c['pass'] and c['layout_identical_all'], (s['stage'], c)
    assert c['dense_layer'] == s['dense_layer'] and c['experts'] == s['n_experts'] and c.get('dense_split2') == s['dense_split2'], s['stage']
    for L, a, z in s['experts']:
        for e in range(a, z + 1):
            cov[(L, e)] += 1; es[(L, e)] = i
    if s['dense_layer'] is not None:
        k = (s['dense_layer'], s['dense_split2']); assert k not in where, k; where[k] = i
assert set(cov) == {(L, e) for L in range(40) for e in range(384)} and set(cov.values()) == {1}
for L in range(40):
    a, z = where[(L, 'A')], where[(L, 'B')]; assert z == a + 1, (L, a, z)
    assert all(es[(L, e)] >= z for e in range(384)) and (L == 0 or all(es[(L - 1, e)] <= a for e in range(384)))
R = m['costs']['dense_split2_rows']
HOP, H_MSG, H_BYTES, HDR = 1008, 652, 40976, 16
bpc = H_BYTES / H_MSG
msg_bf16, msg_fp32 = 2 * R + HDR, 4 * R + HDR
ser, ser32 = math.ceil(msg_bf16 / bpc), math.ceil(msg_fp32 / bpc)
T_AR, T_MTP, N0, R_AR, R_MTP = 1186042.6, 1668506.8, 139, 1011.8, 2991.2
FCLK = R_AR * T_AR; TAU = R_MTP * T_MTP / FCLK
dt_ar = HOP * (N - N0) + 40 * ser; dt_mtp = HOP * (N - N0) + 40 * 6 * ser
ar = FCLK / (T_AR + dt_ar); mtp = TAU * FCLK / (T_MTP + dt_mtp)
r = dict(verdict='PASS', scope='actual allocator capacity + identical expert slot layouts + split causality on the '
         f'{F}-frame column-reduced inventory; MU calendar / behavioural token chain owed', map=p.name,
         map_sha256=hashlib.sha256(b).hexdigest(), frames=F, dense_split2_rows=R, stages=N, rank_dies_per_stage=4,
         layer_dies=4 * N, nominal_total_dies=4 * N + 32 + 52, experts_exactly_once=len(cov), dense_halves_exactly_once=len(where),
         worst_q_fill=max(s['capacity']['q_max_fill'] for s in st), worst_q_fill_pct=max(s['capacity']['q_fill_pct'] for s in st),
         worst_cfg7_phases=max(s['capacity']['cfg7_phases'] for s in st),
         inter_die=dict(per_rank_die_per_token_layer_bytes_bf16=msg_bf16, per_rank_die_bytes_fp32_bound=msg_fp32,
                        per_stage_per_token_layer_bytes_bf16=4 * msg_bf16, per_token_all_layers_stage_bytes_bf16=40 * 4 * msg_bf16,
                        link_bytes_per_cycle=round(bpc, 2), ser_cycles_bf16=ser, ser_cycles_fp32=ser32,
                        link_busy_add_per_position_cycles=ser, link_busy_add_per_mtp_step_cycles=6 * ser,
                        x_msg_cycles=H_MSG, link='existing A->B stage link, fixed slot after x, no new link class'),
         cycles=dict(added_stage_hops=HOP * (N - N0), split_layer_adds_ar=40 * ser, split_layer_adds_mtp=40 * 6 * ser,
                     T_ar=round(T_AR + dt_ar, 1), T_mtp=round(T_MTP + dt_mtp, 1)),
         rate_model=dict(ar_per_user_G16=round(ar, 1), mtp_per_user_G16=round(mtp, 1),
                         ar_per_user_G4=round(ar * (1 - 0.033), 1), mtp_per_user_G4=round(mtp * (1 - 0.0138), 1),
                         base='139-stage composed calendar (1,011.8 / 2,991.2), MODEL; MU users not re-run'))
out = p.with_name(f'static_capacity_receipt_{p.stem}.json'); out.write_text(json.dumps(r, indent=1) + '\n'); print(json.dumps(r))
