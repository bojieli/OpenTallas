# DIE-HBM-97 cpfire 11-10: u_cp one-edge-early fire compare (RTL event, COORD yes on dma-vpose3 B)

**Problem.** In `ot_hgi_dma_back_static_vp4_banks_cp`, TT setup fails on `u_fcore.u_cp.u_core fire_at -> head_pl/cmd`
in every routed or CTS form (-22 to -35 ps, 95 endpoints). It is not a placement effect. `fire = head_v && cyc == fire_at`
is a 32-bit compare that then enables the CW = 308-bit head load and the cmd capture.

**Change (define-gated, 0 cycles).** Under `OT_CMD_FIRE_EARLY`, `fire` is a flop computed one edge early from the next
state (see `cmd_fire_early_patch.py` header). It applies to `rtl/hbm_accel/host_static_20261015/ot_static_cmd_target.sv`
(canonical core) and to the dma kits' local copy `cp_rstrep_core` (`kit_rtl/candidate.sv`; original in
`kit_rtl/candidate.orig.sv`, patched by the same script, identical anchors). There is no schedule, pin or latency change.

**Scope.** Only the dma type kit sets `-DOT_CMD_FIRE_EARLY` (config.mk VERILOG_DEFINES). Every other user is unchanged.

Users of the core found by grepping main dd9e1ac9 rtl/:
| user | params | kits |
|---|---|---|
| ot_hgi_dma_back_cp_collar (repo) / cp_rstrep_core (dma kit copy) | MODE 1 CW 308 RELF 2 TGT_PIN 1 | dma_back_static_vp4_banks_cp (define ON in vPose3F only) |
| ot_hbm_svc_sm_xcal_t | MODE 0 AWA 10 AWB 7 RBW 7 RCW 8 (MUT 0/2) | svc xcal |
| ot_hbm_sm_vm_wr_q_t, _lanes, _faces, _faces4 | MODE 1 CW 26 (MUT 0/1) | vm wr_q |
| ot_hbm_sm_vm_wr_q_t_lanes4 | MODE 1 CW 27 | vm wr_q lanes4 |
| ot_hgi_sm_xload_static_cl2, _cl2p | MODE 1 CW 108 (MUT 0/1) | xload |
| benches: tb_static_cmd_target, tb_hbm_target_participation, tb_dma_vp4_banks_cp(lw) | - | - |

`eq/identity.tsv`: with the define off, the core elaborated under every user parameter set (yosys proc + write_verilog)
has the same sha before and after: 9/9 SAME. The users' own files are not touched.

**EQ step A (yosys sat, `eq/run_eq.sh`).**
- inv: `sat -tempinduct` of the three FORMAL invariants (fire_q == head_v && cyc == fire_at; fe_cyc1 == cyc+1-M;
  nxt_v -> fe_rel == cyc+1-nxt_lb-M). Result: PROVEN at induction length 1, for the repo core (MUT 0 and MUT 1) and for the
  kit copy cp_rstrep_core (DATA_RESET_REPLICAS 1). With the invariant, every other line of the core sees the same fire,
  so the define-on core is cycle-equivalent to the define-off core (0-latency retiming; substitution argument).
- negative control (OT_CMD_FIRE_EARLY_NEG, fires one edge late): FAILS, with a real base-case counterexample (model found
  for base case) for both repo and kit cores (logs/*_neg30).
- bmc: miter old vs new, all outputs, 48 cycles from reset, plus NEG miter (expected FAIL). Results are added when they finish.

**EQ step B.** lec.py runs in the kit flow (async LEC, VERILOG_DEFINES honoured) on the define-on netlist against the
define-on RTL. A + B together: netlist == define-off RTL.
