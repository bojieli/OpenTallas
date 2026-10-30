# DIE-HBM-29-T (2026-10-29 21:40 PDT): token price of d28c latency increases L6 +1, L181 +3, row-1 feed +30 together

Model: same ds S2 schedule model as DIE-HBM-28-C tok_hbm28c.py (accepted_cost g25 rank0, NativeCost, T.schedule).
Base 576,702.4 cyc = 1906 (guarded); TOK-HBM-11 A+B reproduced 5.163 % = 1812.4 tok/s (CHECKED).

## Unit mapping (from the d28c strict bind out/rtl + plan d28c lane latencies, CHECKED by reading)
- **L6/L6m word (hub->b100, 7->8)**: bus u_bout_L6_o in q_hub_nw carries hb_idx_q ql_codes/ql_head/ql_sc/ql_v/ql_w,
  hb_idx_qctl key_index/key_slot/nq and mu_keybuf key_out -> index scorer row 0. Unit **IDX**, serial +1 per IDX record.
- **L181/L181m (su31->hub, 2->5)**: bind leaves hc_NW3.c_rr[512], c_w_done[2], su_NW3 bank_read_data[4x128],
  g_tap_r8b near_rq[34] / near_wq[48]. Hub sinks:
  - HC gather (ot_hbm_hc_q_static lg_rr/lg_w_done): round trip q3 = L174 2 + L181 5 = 7, vs q0 = L36 14 + L55 8 = 22,
    q2 = L38 9 + L59 8 = 17 -> **masked** (+0).
  - cxport inject inj_q3 (SAFE_GATHER): q3 = L3/L113 2 + su30->su31 + L181 5 ~ 9, vs q0 = L36 14 (or L102 7) + L24 2 -> **masked** (+0).
  - hub VM banks Q6/Q7 rq0/wq0 (SU tap near_rq/wq): the other quadrant taps ride 2-cycle lanes (L180/L57) or direct
    wires, so L181 is the slowest tap lane: **not masked**. Priced as a BOUND (+3 on every SU record) and a wide bound
    (+3 on SU, COLL, HC, FUSED). Masking assumes the static gathers wait for all quadrants (UNCHECKED semantics).

## Cases (model runs CHECKED; lane cycle counts from the plan)
| case | cost vs 1906 | tok/s | delta vs 1812.4 |
|---|---|---|---|
| (a) alone: IDX +1 | 5.171 % | 1812.3 | -0.008 % |
| (c) alone: IDX +30 | 5.412 % | 1808.1 | -0.237 % |
| (b) alone, masked (+0) | 5.163 % | 1812.4 | 0 |
| (b) alone, bound SU +3 | 5.643 % | 1804.2 | -0.455 % |
| (b) alone, wide bound SU/COLL/HC/FUSED +3 | 6.026 % | 1797.7 | -0.814 % |
| **(a)+(b)+(c) plausible: IDX +31** | 5.421 % | **1808.0** | **-0.245 %** |
| **(a)+(b)+(c) bound: IDX +31, SU +3** | 5.901 % | **1799.8** | **-0.698 %** |
| (a)+(b)+(c) wide bound | 6.284 % | 1793.3 | -1.055 % |

Every case is far below the 5 % OWNER escalation threshold, so no OWNER escalation is needed.
Run: repo root, PYTHONPATH=src python3 tok_hbm29t.py OUT.json (~3 min, intel1).
