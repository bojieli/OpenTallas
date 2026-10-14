# Qwen TP8 ectl multicast candidates, 2026-10-13

Candidate branch from die lead `e0e968a94`. Neither candidate is adopted or closed. No live g9 job was cancelled, restarted, or modified. Existing bounding-box and per-pair timing gates remain unchanged.

The same-table baseline has152 failing e/score-return pairs; the pin candidate reduces that to64 exponent pairs and zero score-return pairs.

The baseline has 256 three-end A-row/B-row/control/Q nets. All A and control nets fit the 500 um bounding-box limit; 64 B-row and 64 Q nets fail. These are actual source-to-far-head failures: maximum B-row 544.452 um and Q 722.943 um. Splitting the report into pair distances would not repair the wiring.

## Pin assignment for the unclosed head parent

`OT_TP8_ECTL_PIN_REPLAN_CANDIDATE=1` enables an isolated experimental assignment in `tp8b_v5.py`. It preserves the electrical source-plus-two-heads net and the exact 1559-bit head word. It adds zero registers and zero clock edges. The closed A/B/C views and all source clocks stay unchanged. The head parent must physically implement this assignment with input registers at these pins and close its own clock tree/timing.

The measured local head pin windows, all on S/M5, within the existing 712.8 x 453.6 grant are:

| Logical field | Bits | Local x range, um | Exact native ti mapping |
|---|---:|---:|---|
| A row | 512 | 214.908–314.700 | ti[515:4] |
| B row | 512 | 329.772–429.564 | ti[1027:516] |
| B control | 16 | 324.300–328.044 | cl[3:0] -> ti[3:0], cl[15:4] -> ti[1039:1028] |
| C Q | 519 | 579.132–638.508 | ti[1558:1040] |
| C exponent control | 16 | about 642.1–644.5 | head e[15:0] |
| C score return | 34 | about 650.6–655.5 | head s[33:0] |
| Reset | 1 | 4.332 | rst_n |

The legacy reset location at x217 would intersect the moved A-row pins and is moved in this candidate. Exponent and score pin positions minimize the mismatch among the four real C ports and are snapped to the M5 0.012 + n*0.048 lattice. Each ti bit retains its exact field position, including the noncontiguous control bits. A uniform 1559-bit pin-range assignment is insufficient: the head kit must consume the per-bit rectangles/field map in the probe output, or introduce an exact field-port wrapper.

The head clock is unchanged. The emitted baseline clock rectangle is N/M5 x356.400–356.424, y453.408–453.600 (center x356.412). The source view clock positions are A127.404, B127.404, C86.508, N/M5. Local M5 pin-lattice violations: zero. The existing measured A/B boundary clock spreads are135.0/131.4 ps (C34.8 ps), so the source clock-spread obligation also remains open; this candidate does not change or certify their trees. All four orientations occur on the actual head instances: 32 each R0, MX, MY and R180. `pin_candidate_report.json` records the absolute source clock coordinates and the actual oriented data endpoints; final real-case origin legalization remains required.

Geometric result: all 256 multicast bounding boxes pass, worst 466.752 um; source-to-head pair maximum 466.752 um; zero signal rectangle collisions. This closes the geometric issue only.

Using the current measured 74-master timing table, every far-head multicast still fails against the unclosed head's placeholder setup share:

| Field | Smallest measured-source/placeholder-head reach, um | Maximum candidate pair, um | Failing pairs |
|---|---:|---:|---:|
| A row | 387.9 | 466.752 | 64 |
| B row | 359.8 | 466.752 | 64 |
| B control | 363.4 | 466.752 | 64 |
| C Q | 381.8 | 466.752 | 64 |

For a same-level head, source B's worst residual is O-R = 516.7-258.5 = 258.2 ps. At 466.752 um the wire costs 354.732 ps. The actual head input setup residual S+R must therefore be at most 70.401 ps under the unchanged 683.333 ps budget. A deep head incurs the 150 ps skew budget and reduces that requirement to 10.401 ps. Neither bound is proved by any closed head view. Other required same-level input residual bounds are A91.701, control73.101 and Q87.101 ps. Thus this pin assignment alone is not a timing fix.

The exponent controls still have 64 far-head pair failures (minimum reach426.4 um, maximum length about468.3 um). The score returns all pass this table (minimum reach481.0 um, maximum length about469.8 um). In particular ts_WN_3_3 shrinks to about469.73 um from the old lateral detour; its actual endpoints are recorded. The g9 terminal planner's separate interim-relay endpoint limits remain authoritative and may still require a relay.

## Registered fork implementation candidate

`rtl/physical/ot_qwen_ectl_word_fork_candidate.sv` provides an RTL candidate with inputs row_a512, row_b512, cl16, q519, e0/e1 each16, ck and rst_n. Its two independent 1575-bit output banks capture on one edge and emit t0/t1 each1559 plus eo0/eo1 each16. The word is exactly `{q, cl[15:4], row_b, row_a, cl[3:0]}`. Each input is one electrical source connection. Output register copies are marked keep/dont_touch; synthesis must independently prove 3150 Q roots survive, since attributes alone are insufficient evidence.

The two output banks preserve exponent-control and word alignment. All six incoming components must have equal added transport depth before the capture; all word and exponent components must retain equal depth to each head afterward. A/B/control/Q arrival balancing remains mandatory. No assumed LEF, Liberty or CLOSED verdict is supplied.

A prospective pin-capacity envelope is 285.12 x172.8 um: W/M4 carries 1591 input bits at two-track pitch (152.736 um); N/M5 and S/M5 each carry one1575-bit output bundle (151.200 um), with clock/reset outside those windows. This is a capacity proposal, not a floorplan or placement proof. It does not fit in the existing129.6-um ectl band, whose648-um width is already entirely occupied by A/B/C. The common fork must be placed within a replanned unclosed head parent or given a real reservation while preserving the reticle and the current contract revision policy. The geometry/cut/clock/fanout/hold/setup proofs are outstanding. A route should not be launched for this speculative outline.

Cost before any pads: 3150 output flops per pair, 64 pairs ->201600 flops. At the prospective outline:49,268.736 um2 per pair ->3.153199 mm2 total. These are arithmetic bounds, not synthesized area. Added latency is at least one capture edge, plus the measured maximum balanced input and output transport depths. Balanced pad flops add1591*D_in +3150*D_out per pair. A root has3150 clock sinks, below15000; measured insertion <=300 ps and spread <=80 ps remain required and unproven.

Changing head transport also changes the score/tag/node-beat latency expected by the fixed closed ectl C implementation. Its KDEPTH/SCD/HXK/HXN/LANE_D behavior and the full native attention bench must be updated and proved before adoption. There is no measured unit-throughput loss or accepted-cost ledger row. No claim of <=5% unit or <=15% design loss is made.

## Validation and next decision

- `bash tools/qwen_tp8/ectl_fork_candidate_bench.sh OUT`: positive exact packing/two copies/reset passes257 edges; a row-swap mutant fails at edge0. This is RTL functional evidence only.
- `python tools/qwen_tp8/ectl_multicast_candidate_probe.py OUT --candidate --timing TABLE`: 256 boxes pass, zero signal collisions and local pin-lattice failures; it explicitly records all256 remaining multicast pair failures and64 exponent pair failures.
- Existing real-leaf binding regression remains four tests passing.
- R0/MX/MY/R180 source/local projection round-trip check passes.

Recommendation: give the head stream the disconnected field pin plan and measure its actual boundary residuals first, while preserving g9. The score-return pin fix removes a known geometric search dead end. If the actual head residual does not meet the explicit70.4/10.4-ps bound, reserve and physically prove registered fanout/transport with equal component depths and retime the control path. Do not accept either geometry-only candidate as die closure.
