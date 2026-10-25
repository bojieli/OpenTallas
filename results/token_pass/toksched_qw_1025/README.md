# TOK-SCHED qwen_rom: QC su_c SRAM-IF MIF=1 and KV lane L663 (2026-10-25 12:33 PDT)

Base: origin/main eeb8e96b6. Token model: results/arch/token_path_20261009/qwen_rom.json (249,431 cycles, 4,810.95 tok/s at 1.2 GHz).

## (a) QC sl_W5_su_c binds btab/prog/vmr (+ crh rp1) with MIF=1 -- proposed ledger row QC.SU_SRAMIF

- Cost per SU op is +2: the PROG issue word comes +1 later, because the slice su_go delay D goes from 2 to 3. The SU operand reads then come +1 later. These are VM A/B/C, CROM and the BTAB SU port, read in parallel.
- Writes land +1, but the read/write order is unchanged, so they cost 0. See qc_sramif.json.
- The static plan was re-run with SU_LAT 24..27: `tools/qwen_layerbench/ctlm_image.py` via su_lat_sweep.py, output su_lat_sweep.json. Every seal PASSES. The plan's priced constant PROG_CONSTANTS SU_LAT = 24 becomes 26 when the parent binds .MIF(1).
- 14 of the 20 SU ops in a layer are serial on the critical path. Their delays at SU_LAT 26:

  | SU ops | count | delays | by |
  |---|---|---|---|
  | qknorm_rope | 8 | native attention start | +16 |
  | attn_tail + rmsnorm2 | 2 | gate_up | +4 |
  | SwiGLU pc18/19 | 2 | down | +4 |
  | residual | 2 | layer END | +4 |

  rmsnorm1, pc2 and pc17 are hidden under ME ops.
- Total: 28 cycles a layer, 1,008 a token. Throughput goes from 4,810.95 to 4,791.59 tok/s, **-0.402 %**. This is a modelled upper bound.
- Sensitivity: operand-only +1 gives 504 cycles a token, 0.202 %.

## (b) KV lane L663 = hub_Wi.o_host_fdi -> io_W3.i_host_fdi (host SerDes TX, 1,044 b)

Which value the schedule must carry:

| plan | value | where it stands |
|---|---|---|
| main | 42 | die_plan.json latency.lanes, set by the obst merge 183f0b03b9. lat_v39pd still said 34: the only lane of 2,416 that differed. This branch regenerates lat_v39pd with gen.py latency --fold-r8 on main's plan. The diff is L663 34 -> 42 only, and the R8 landing is byte-identical. |
| v3.9r | 35 | claude/path-kv-rebase-1025@3832299dfb, lat_v39r. Consistent with its plan: 0 mismatches. |
| committed bind dirs | 26 | bound_r8, bound_pv and binder2 are v3.6 binds and carry L663 = 26. The TOK vehicle takes this value from bind_latency.json of whatever plan it is rebound from. |

Token cost:

- L663 is not on the token path: **0 cycles/token, 0 tok/s** on both plans, and no ledger row. Die-to-host TX delivers tokens and responses to the host. The AR loop and the attention input/output cross the UCIe link (sys_c), not the host SerDes.
- If the host paced every token, the upper bound would be +8 (main), 0.0032 %, or +1 (v3.9r).

v3.9r pv-unblock lanes (56 lanes, +1..+3 vs f7ch):

- Only 16 can touch the token: 14 y_valid lanes (max 48 -> 49) and 2 ctl_req_valid lanes (17 -> 18). The others are fault or dcfg lanes.
- Upper bound: +2 a layer, 72 a token, 0.029 %.

Not priced here: v3.9r vs main as a whole. 839 lanes move, including attention-step lanes up to +16. That needs the KV static calendar re-run on lat_v39r (KV-TOK rebind). See kv_l663.json.
