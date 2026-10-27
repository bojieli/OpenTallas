# QC-CORES-1 item 3: qfd_qc_su_lane reset bridge (2026-10-27)

Verdict: the bridge is NOT open. No RTL change is needed, and none was made.
The "open bridge" line comes from PATH-QC 10-26 03:11. Codex closed the bridge 10 min later, on codex/qc-su-wrapper-1026:
- 5a2f34968 bound_groups.reset_members projects the planned per-lane tap onto the five leaves;
- ba0ef724a adds the bound_group contracts;
- 81b06dfad keeps the original identities.

This code is integrated in ONEQC codex/qc-1026 but **not on main**.

## Evidence (CHECKED)
1. **Plan level (plan_d43 f2c91d03 + codex/qc-1026 cores/su_exact pins), `plan_group_depth_check.py` -> `plan_d43_group_depth.txt`.**
   - 44 of 44 lane groups in 11 SU types are OK.
   - Leaf tap and lane tap have the same published depth (su_l0 4, su_l1 5).
   - Both taps have START role mission.
2. **Bind level (intel2 claude-qc-bindprice-1026/final; plan landing_phase_r8, commit 009bc96f5).**
   - errors 0, tied_by_port 0, 11 bound_groups.
   - All 16 qfd_qc_su_lane_{e,w}_l0..7.sv are byte-identical (sha256) to rtl/physical on codex/qc-1026.
   - Every u_laneN gets its own tap rst_n_t9..t14. Each tap is an equal-depth relay: `ot_dp_rrelay` stages, then `ot_dp_rgate` (reset AND run).
   - The relay sits beside the core's rst_n pin. There are no ties.
3. **Formal check, `rst_eq.py` -> `rst_eq.json`.**
   - Method: yosys `sat -tempinduct -seq 5` on the extracted relay tree, proving leaf tap == every lane tap from an arbitrary state.
   - Result: PASS on 11 of 11 types and 44 of 44 lane taps.
   - Mutant (one lane tap one relay short) is rejected on 11 of 11.
   - So reset assert and release are cycle-identical to the five ungrouped leaves.
   - Inside the core, all five leaves share the pin, as in qfd_dv_s5_lp (all lpr_c_u_* N=0 off one lpr_r_su).

## What actually blocks the kit
- **Face preflight FAIL (not reset).**
  - Last kit: intel1 codex-qc-su-trial-1026/kits_keep2/qfd_qc_su_lane_w_l0__414.72x267.84, 10-26 04:31.
  - Checks: port_gate 1064/1064 PASS, lint PASS, dont_use PASS.
  - Failure: face_guard shared 24 (5 named: c_o[68] = lrly kv_wdata[19], c_o[297..300] = lrly wrom_addr[20..23]). All are driven from one TIELO net with 19263 loads.
  - Cause: output-register bits whose D is constant after reset synthesize to a constant.
  - Fix belongs to the SU core owner: keep the private port FFs (dont_touch), or declare them constant outputs in the pin contract per the COORD dead-input ruling.
- **Plan event.**
  - The r18/d43 candidate branch has no physical/die_plan/qwen_compute/cores/su_exact, but plan_d43 points its SU hard_cores at cores/su_exact/*_pins.json. Without that directory, reset_tree cannot resolve the pin tables.
  - QC.BIND (kit-rtl from strict bind) also waits for plan adoption.
