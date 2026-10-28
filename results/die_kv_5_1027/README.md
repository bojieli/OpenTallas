# DIE-KV-5 (2026-10-27 23:44 - 10-28 PDT): KV strap manifest in partition frame, KV-TOK reprice, HB4 kit inputs

Base: claude/die-kv-4-1027@53fe162cfb + claude/meso-reconcile-1027@32e8cbb16 (count_align_bind v2 + --parts relay,
die_sta_related --clock-cal spice). Runs: intel1:/srv/opentallas-scratch2/claude/die-kv-5-1027. Plan hm_r26q9c (b7761d84).
Clock = DIE-KV-3 H200B; CA rows = DIE-KV-4 proto/H200B_{spice,s100}_xing_lpo.json (spice = x1.0485 TT / x1.0552 FF).

## 1. Strap kits (METHODOLOGY 1.8 + 12.15a)
DIE-KV-4's open point (UNCHECKED region-frame K; start-relay offsets of the 32 multi-partition regions) is resolved:
`count_align_bind.py --from-ocv --parts ocv` (v2 + ca-origin relay) on the spice rows gives K in the PARTITION frame.
Bind: 0 identity/loop errors over 3,468 fundamental loops, 2,000 chips 0 window violations, worst 106.3 / 110.5 ps,
sched_lat total 9,487, D4/D8 3393/202, 32 relays, 112 non-tree K shifted by the relay (CHECKED-own run, rc 0).
`strap_list_v2.py` -> `strap/strap_kits_parts_spice.json`:

| | value |
|---|---|
| strap kits (receiving types) | 51 |
| landed partitions | 160 (1 root, 127 child origins, 32 relays) |
| CA buses summed over types / D8 type-buses (DEPTH = type max) | 1,865 / 165 |
| LEC variants (master x used strap tuple) | **117** (DIE-KV-4 region frame: 112, superseded) |
| K span | -26..32 -> 6 bits mod 64 |
| extra straps | role on 4 types (hgi_v7 root/child, pc_v1, pc_v3, phy_v1 origin/relay); tree-bus select on 14 types; PAD/EDGE_FALL on 4 types (hg_v1, hroot, pc_v1, pc_v3) |
| tied strap bits | 21,854 (= TIEHI/TIELO cells at max_fanout 1, straps.py rule 3) |

Largest: kv3_pc_v1 24 inst / 29 buses all D8 / 12 variants; kv3_phy_v1 28 / 1 / 11.
NOT BUILT / NOT ENQUEUED: main has no strap form (ot_dp_clk_landing_ca/origin/relay take K/PAD/EDGE_FALL as
parameters, clock_landings raises TYPE_SPLIT, parent_id_straps schema is ID-only). Same blocker as HEAD (DIE-HEAD-4b
23:37 ASK, default: MESO-RECONCILE-2 successor builds the shared form). KIT_PREFLIGHT runs on kits, so it waits too.
KV-KITS-4/COLLECT-2315 builds core_tx + releases 7 KV rows; it has no strap kits -> no duplicate work.

## 2. KV-TOK reprice (12.15c: accepted, recorded)
MESO-INTEG-1 `kv_ca_price.py` on the LAND-KV-1 v39r lane-class record (kv_v39r_price_land_q5c39 + lane_delta_land_q5c39;
lane/crossing count check passes on all priced lanes).

| bind | added cycles | per request | embed | tok/s |
|---|---|---|---|---|
| old +3 ring | 2,499 | 66 | 123 | 4763.2 |
| DIE-KV-3 H200B x1.00 (MESO-INTEG-1 planner) | 2,195 | 58 | 107 | 4769.0 |
| H200B x1.00, reconcile planner + relay | 2,231 | 59 | 107 | 4768.3 |
| **H200B spice, reconcile planner + relay (gate)** | **2,194** | 58 | 106 | **4769.0** |

Lane deltas KV-3 x1.00 -> spice: +236 cycles on 216 lanes (max +2), -126 on 116 lanes, net +110 (reproduces DIE-KV-4;
CHECKED-own). TOK change KV-3 -> spice: -1 added cycle/token, **+0.0 tok/s** (4769.0 -> 4769.0): the raised lanes are
not on the priced critical classes. vs old ring +5.8 tok/s. UNCHECKED: lane-class model; interior families
(vport/pv/ahub/seq/acal) unpriced, as in the source record.

## 3. HB4 prep (ASK1 form, COORD 22:43: HB4 placed+routed in the kits)
`hb4_dump.py` wraps MAIN die_sta_related (no fork; same args as DIE-KV-4 sta_reccal: --clock-cal spice --cppr-lca
--clock-ocv table --clock-droop shared --hold-buffers HB4 --core-latency-ff 202.5) and records the per-pair kit-contract
damage it already computes. Reproduces DIE-KV-4 exactly: intra -11.02 (24 pairs), seam -74.35 (339) (CHECKED-own).
`hb4_list.py` -> `hb4/hb4_kit_inputs.json.gz` (per pair + per TYPE kit input = max over the type's instances):

| | kit-contract (nominal, gate form of ASK1) | + clock OCV (R18 additive, INFO) |
|---|---|---|
| intra pairs | 24, all kv3_pc_v1 (taps t2/t5 -> t6/t7/t9/t10), worst 11.02 ps, k=1 | 6,873 pairs / 45 types, worst 79.25, k 1-2 |
| intra kit entries | 8 (kv3_pc_v1 tap pairs) | 3,852 |
| seam pairs | 339, all phy -> pc inside the 32 phy+pc regions (phy_v1->pc_v1 260, phy->pc 42, phy_v1->pc_v3 37) | 384 |
| seam pairs carrying bits (nearest-tap) | 85 (254 tap pairs have no pin register under them -> 0 cells) | |
| seam bits / HB4 cells | 31,198 / 31,487 on 32 pc instances (3,215 um2) | 38,208 / 87,692 |
| seam kit entries | 6 buses i_phy_Q__sN_{fhN,piN,piN_d1..d3,rhN} per pc type, deficit 30.5-74.4, k 1-2 | k 3-4 |

Kit use: intra = per (launch tap, capture tap) extra early window beyond the plan tap_window 80 ps; seam = per receiving
input bus extra hold (set_input_delay -min lowered by the deficit), so the receiving pc kit places HB4 at its input-face
registers. Structural note: the seam pairs are phy taps 70-150 ps early vs pc (DIE-KV-3 finding); plan-computed per-tap
sizing (12.8) of the phy region tree would remove them without HB4 -- not done here.
