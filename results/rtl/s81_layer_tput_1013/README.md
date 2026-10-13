# S81 per-layer throughput run, 2026-10-13

Owner decision 10-13: DeepSeek S81 ROM throughput is qualified per layer. This is the first per-layer run on current
main RTL (source `bd6e8228`, Verilator 5.050, ot-epyc4). Regenerate: `run_die_layer.sh` then
`python3 tools/s81_ctrl/die_layer_tput.py results/rtl/s81_layer_tput_1013/run --out .../record.json`.

## Result

| Run | Verdict | Bench layer cycles |
|---|---|---:|
| base L0 (1M token, pinned cases 8c18c065) | PASS: y 640/640, NORM rows 480/480, H_STORE 640/640 | 11,168 |
| base L2 | PASS, same counts | 20,360 |
| mut_hc L0 (hc_post does not write h back) | FAIL as required: H_STORE 0/640 | |
| mut_coll L0 (output slice pops early) | FAIL as required: 227 collective errors | |

Per class (price = token-path node, never changed):

| Class | Measured | Price | Ratio | Path | Reading |
|---|---:|---:|---:|---|---|
| HC fused NORM (`hc_pre` + quant [+ norm.scale]) | 449 (all 4 jobs) | 327.0-333.9 | 1.35-1.37 | critical, 80 a token | clean; proposed in the ledger: 1.178 % AR, 0.995 % MTP |
| all-reduce + HC POST pair (POST streams on the all-reduce, ends 23 cycles after it) | 660-1,208 | 939.9 | 0.70-1.29 | critical | NOT a nominal number: the bench injects link errors (EPER 97, go-back-N) and has no PHY / board leg; no row |
| all-gathers, topk_merge | 30-115 | 422-1,033 | 0.07-0.11 | critical | not comparable: price includes PHY, FEC and board latency the bench link lacks |
| HC jobs with no token-path node (H_LOAD 333, H_STORE 81, COEF 14 x 2 a layer; GAIN 173 x 2 at boot) | 442 a layer | none | - | open | if serial with the layer this is about 17,700 cycles a token (about 2 % AR); needs a price decision, not proposed |
| field (8-10 phases a layer) | - | - | - | critical | real gather / capture but synthetic phase shapes: not measured |
| su, svc, sel, col, hcx | - | - | - | mixed | behavioural at program duration: not measured |

s81 ledger after this run: accepted 1.812 % + proposed 1.178 % = 2.99 % of 15 %.

## What had to be repaired

The bench did not build on main: `run_die_layer.sh` lacked `rtl/dsrom_sys/s81_suhc/hier/*.sv`, and the testbench
still connected the removed `fcode` pin and probed the flat engine outside `g_flat`. Both are fixed here; the bench
also prints one `OPT` line per op.

## Coverage of the UNMEASURED S81 units (147 budget entries with QUALIFIED and no ratio)

- Exercised bit-exact in this run, HC ratio measured (over 1.10): the HC slab function, flat engine only
  (`ot_s81_hc_*` 12 entries, `ot_dsrom_su_hcpost_lane_pr`). The hierarchical slab (HIER 1) was not run.
- Exercised bit-exact, throughput not qualifiable from this bench: collective (`dsfd_coll_*`, 15 entries).
- Not covered (131 with the collective): field 55, SU tiles 22, hbm / svc 18, head 9, select 8, ctl 4, wave 2,
  `dsfd_colt_lane`.
- Critical-path units that still need their own production-shape bench: the field phases (q_elem, BF, PQC, relays,
  VM; 50 % of the token), the 26 critical SU nodes a layer, the collective at nominal link latency without injected
  errors, svc / window load, select, head.
- The Engram layers (L1, L14) are not in the vehicle: the pinned cases hold L0, L2 and head only.
