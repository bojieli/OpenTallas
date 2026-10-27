# HBM-CORE-LAT-R5 argmax_sw_vm_r2 (ot_hbm_argmax_static_sw_vm_r2) -- LEC root cause (COORD RULING HBM-CORE-LAT-R4 (2))

R4 synth LEC (results/hbm_core_lat_r4_root/argmax_static_sw_vm_r2/lec_synth_r4.json): NOT EQUIVALENT 13249/13313, 64 points
(13 differ = cq_d wdat bits 18..31, 51 unproven = engine out_idx/out_value/out_range_fault) with "RTL registers removed by synthesis
although not constant: res_id[18..31]" and FSM `st` cube hypotheses in the unmatched cones.

## Root cause (CHECKED from RTL)
`res_id <= {14'd0, o_idx} - {29'd0, ab_q[2:0]}` (or `- 0`): the value lies in [-7, 2^18-1], so res_id[31:18] are 14 copies of the
borrow. res_id is a NO-RESET register; before its first load the 14 flops are independent X, so Yosys merging them is a legal
X-refinement but the LEC (free initial state) cannot match the 14 gold flops to 1 gate flop. The unmatched res_id bits then broke the
inductive FSM-cube / engine-output hypotheses that share the cq_d / wdat cones.

## Fix (RTL, not an LEC allowance)  rtl/hbm_accel/generic/ot_hbm_argmax_static_sw_vm_r2.sv
`reg [18:0] res_id_r` loaded with the 19-bit difference; `wire [31:0] res_id = {{13{res_id_r[18]}}, res_id_r}`. Same value on every
load, same enable; the redundant 13 flops are gone from the RTL itself.

## Proofs (proof/, yosys 0.68 in openroad/orfs:asap7lock, 8 GB docker)
- P3 (combinational, all inputs free): old 32-bit expression == sign-extended 19-bit expression, and old[31:18] == {14{old[18]}}:
  `sat -prove` SUCCESS (prove3.log). CHECKED.
- P1 (FSM range): st[3] == 0 always (only the 8 declared codes E_IDLE..E_END are reachable; the `default` arm is dead).
- P2 (observability): st in {E_W0, E_W1, E_END} => res_id_r has been loaded since reset (proof-only observer `ld`, set exactly at the
  RTL load condition st==E_WAIT && cnt==0). So res_id is never observed (wdat at E_W1, cq_d at E_W0/E_W1) in its X state.
  P1+P2: `sat -tempinduct -prove-asserts -set-init-zero` on the core with the engine u_e cut to free inputs (over-approximation):
  base + induction step length 1 SUCCESS (prove.log). CHECKED.
  Mutant (proof_mutant/: observer set at E_RD instead of the load): induction FAILS to max steps -> proof not vacuous. CHECKED.
- Lockstep bench rtl/test/hbm_netlist_v16/run_argmax_r2_busy_export.sh (patched r2 vs the closed e4dc0b651 RTL, every output every
  edge, 8000 cycles): seeds 1/2/3 mismatches 0/0/0 (seed 2 prints FAIL only on the coverage floor resets 3 <= 3, not on a mismatch);
  OT_ARGMAX_BUSY_EXPORT_MUT mutant 1356 mismatches (caught). CHECKED. Coverage note: dones 0 in all seeds (commands end in fault), but
  falls_end 76-80 per seed, i.e. the W0/W1 cq writes with res_id are compared.

## R5a LEC (res_id fix only): UNPROVEN 13104/13345, 241 differ (lec_r5a/lec.json, 1890.8 s) CHECKED
With res_id fixed, every remaining unproven cone runs through the recoded FSM (`st` 669 / `st#t` 314 cone references): lec.py could
map only codes 0..3 to one-hot gate flops ("encoding search too large" for the full 4-gold/8-gate search), so the E_W0..E_END cubes
are never hypothesised and the write/ack/engine-capture cones (cq_d, res_val, res_id_r, le, i_sec, i_left, dp, rq_v, cnt, done,
fault, engine out_*) stay unproven. Root cause = the synthesis one-hot recode, not a design difference (P1: only 8 codes reachable).
## Fix 2 (RTL): `(* fsm_encoding = "none" *) reg [3:0] st;` -- Yosys keeps the RTL binary code (gate st[0..2] $_DFFE_PN0P_, st[3] const 0,
CHECKED in 1_2_yosys.v). P1/P2/P3 re-proved on the final RTL (SUCCESS). Lockstep sim unaffected (attribute only).
