# CDC_PC plan delta (DIE-KV-32, 2026-10-29; COORD RULINGS [DIE-KV-31] 11:12: plan FIX on frozen event26a allowed)

Problem (CHECKED, intel2 die-kv-31-1029/hr_kits2/qkd_hr_cdc_pc face_guard.json): FAIL shared 18 = u_tx__o_d[528..545],
all driven through BUFx2 from ONE TIELOx1 net _077740_ (53 loads). u_tx is the 528->546 side of the HR CDC (u_tx__i_d is
[527:0]); its top 18 data bits are constant 0 (the extractor already absorbed the parent constant on u_tx i_d[545:528]),
so the 18 output pins are reserved constants. In hub_Wi they feed host__qkd_hr_phy_adp_* c_d (core_conns.json).

Delta (form = remove, COORD option 1):
1. cores/qkd_hr_cdc_pc_pins.json: remove u_tx__o_d[528..545] (18 M5 pins, face y=0, x 311.640..316.536); face count
   1099 -> 1081 (this commit). 2166 -> 2148 pins.
2. core RTL (kv_core_rtl --hr-elab / hr_face_ports): u_tx__o_d output [527:0]; the 18 bits stay internal (dead after
   synthesis). Proof obligation: the removed bits are constant 0 in the pre-transform netlist (sat/induction), plus the
   usual equiv on the remaining ports. NOT DONE (next step).
3. hub_Wi parent glue: the consuming phy_adp c_d bits tie 1'b0 at the parent as DECLARED constants (ID-strap rule form:
   TIELO in the partition, set_case_analysis/false_path, LEC hub_Wi bound vs source). phy_adp kits unchanged (pins kept).
   NOT DONE (next step, bind owner = KV per COORD 11:12).
Estimate: -18 die-internal crossings, 0 cycles, no non-constant path removed; cdc_pc y=0 face demand -18 of 1099.

G0/G0C (check.py --completeness --core-conns, main 88b244ad3 die_plan.json v3.9e): base 20 ERROR (13 cuts, 7 core_pin_form
kv3_head_eighth_* strap pins, pre-existing) / 1428 WARN; delta 20 ERROR / 1428 WARN; finding diff = 1 WARN text only
(cdc_pc face S edge-form count 1099 -> 1081). The delta adds 0 errors [CHECKED, logs g0_base.log / g0_cdcpc_delta.log].
