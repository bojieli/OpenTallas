# HBM-CORE-LAT-R5 hub-type placements (R4 GOAL=place kits, collected 2026-10-27 02:37 PDT)
Kits: <host>:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-hub/kits/<module>_<pinsha12>-_r4 (trial centre-entry slices, B2o=planU2 pin hash, no CTS).
Renders: render_core_placed.py on each kit's placed.csv (viewed by author). Numbers from the render json / lec.json = CHECKED (read from files).

| type | host | synth LEC | placement | outline um | fill of free | notes |
|---|---|---|---|---|---|---|
| qcore_r13@ebe3df4b204d | intel2 | EQUIVALENT 38891 pts (1 RTL/6 gate unobservable) | PLACED | 224.64x207.36 | 0.577 | 2 SRAMs NE, pins W/S/E, entry centre; uniform, max bin 0.72, pin->reg p90 8.0 |
| sfustore_hw@e7982b24ac22 | intel1 | EQUIVALENT 13827 pts | PLACED | 336.96x328.32 | 0.076 | 16 SRAMs NOT on a regular grid; all 1829 pins on S face; std logic = S-face band + scatter; outline oversized (R3 proposal 293.76x285.12) |
| programme_store_r10@b0729904377c | epyc2 | EQUIVALENT 58963 pts (1070 RTL-X dont-care) | FAIL GPL-0305 (RePlAce diverged; routability inflation +182%) | 574.56x738.72 | movable 43373 um2 / white 84343 um2 | outline = B2o; R3 proposal 535.68x682.56; divergence = local pin-face congestion (inflation), not density |
| gq_land@4e84c42519cf | intel2 | NOT EQUIVALENT 24/11019 | not placed (FAIL_PREFLOOR) | - | - | see diagnosis below |
| pc_ctrl_leaf_cfg_h9b p00@f667644f356a | intel2 | RUNNING (correspondence round ~30+) | pending | - | - | collect kits/ot_hbm_svc_pc_ctrl_leaf_cfg_h9b_f667644f356a-_r4/{lec/lec.json,placed.csv,run_place.log} |

## gq_land LEC NOT EQUIVALENT: diagnosis (CHECKED from RTL + gate netlist names)
- Failing points = g_face_clone_vm_kq[281k+277..279], k=0..7 = kq_n word bits [279:277] = ln_s[m][15:13].
- ln_s[m][15:13] = base_q[sq][15:13] = g_dst[15:13] for every q (sec_add keeps [15:13]); base_q and ln_s have NO reset.
- Gate netlist: base_q[0..3][13..15] merged to ONE copy per bit (base_q[3][13], base_q[3][14], base_q[0][15] only) and
  ln_s pairs merged (only ln_s[1,2,5,7][15:13] exist): Yosys merged no-reset flops with identical D (legal X refinement).
- lec.py gives gold no-reset registers a free initial state, so the gold sq mux can select unequal initial copies -> 'differs'.
  Same class as hcp_sys1 (R4 diagnosis). No functional bug shown.
- Fix per COORD RULING R4 (1) pattern (RTL, not an LEC allowance): reset base_q and ln_s (or keep [15:13] once:
  base_q 13 bits + one g_dst[15:13] register); RTL owner = gq (ot_hgi_coll_gq.sv); then re-synth + LEC.
