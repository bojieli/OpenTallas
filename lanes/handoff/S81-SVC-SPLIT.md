# S81-SVC-SPLIT handoff (Sonnet worker of FABLE-FIX-S81-SVC2, 11-17 ~13:30 PST)
Goal: svc lo7 flat shell (5.69M mapped) under the 400k cell cap by hard cores. Status: MEASURED sizes only; no core kit generated, no build launched, nothing signed.

## Measurement (epyc8 /srv/opentallas-scratch3/claude/s81-svc-split/size0; count.txt count2.txt deep.txt h.json)
Method: yosys hierarchical generic synth (begin:fine, fine:check, no flatten) of the lo7 kit canonical 1_1_yosys_canonicalize.rtlil (565 modules), write_json, counted in Python (no yosys stat). The first attempt from VERILOG_FILES failed ($error unsupported by the plain yosys frontend); RTLIL is the right input.
Total 6,350,726 generic vs 5,688,798 mapped (x0.896). Per child of u_bound (generic cells):
- ot_s81_su_sms 2,415,131 (38%): dsfd_su_t_smh -> 4 x dsfd_su_t_smhq 576,971 each; each smhq = 4 x dsfd_su_t_sml 106,819 (ot_hdc_v41x_exp 89.6k inside) + 2 x dsfd_su_t_smd 74,279; plus SRL=2 95,630 (smc 57,533, smr 36,924).
- dsdv_idx_rg3_nq_fit 2,051,597 (32%): 4 x PR=1 500,579 each; each = 8 x ot_hdc_v41x_idx_hslice 62,409 (32 hslice total, 2.0M).
- 4 x ot_hdc_v41x_attn_merge_x 318,150 each (1,272,600; 80 qaddf 3.6k each).
- 118 x ot_bind_native 163,925; 14 x ot_dp_clk_landing_cas 129,277 (9k each); 4 x attn_tr_x 64,792; 13 x ot_dp_dly 47,348; 2 x dsfd_ctrl_rg3 25,680; dsdv_eng_tap(+_entry39) 29,440; land/pmem/pvq capture 27k; rest <60k.
- ot_s81c_attn_hcore x64 and dsdv_svc_sx_hrow are already hard macros (excluded in the flow).
NOTE the sum of dominant modules means ~4.7M generic sits in three families, all repeated.

## Candidate hard cores (PICK LIST, ESTIMATE, owner Fable to decide)
1. ot_hdc_v41x_idx_hslice: 62k generic (~56k mapped) x32 -> removes 2.0M. Core, 8 per PR group placed as 32 replicas (or 1 core = 1 PR group of 8 hslice, 500k generic, too big: use the hslice).
2. dsfd_su_t_sml 107k x16 (1.71M) and dsfd_su_t_smd 74k x8 (0.59M) -> core pair; smc 57k and smr 37k stay core candidates (small, 1 each).
3. ot_hdc_v41x_attn_merge_x 318k x4 -> core x4 (under cap).
4. Rings: 14 landing_cas 129k -> hard ring cores per KV pattern (CLAND-MACRO-1 mkmacro) if the shell still sits over cap.
Shell after 1-3: ~0.52M generic (~0.47M mapped) = bind_native 164k + rings 129k + tr_x 65k + dly 47k + rest. Still > 400k, so rings (4) and probably tr_x/bind_native must follow. Not yet checked: what the 118 ot_bind_native modules are, and port counts of each core (pin budget).

## Worst path / reset (read only)
- lap_ok path: ot_dp_clk_landing_ca.sv r_lap_c: ctl_w/st_w -> w_c / tag compare -> r_lap_q, a tclk->rclk crossing read. The cas instance has STATUS_REG=0 (default); STATUS_REG=1 (+GUARD_REG) is the existing per-slot rclk capture, 0 added data cycles but ARM_E shifts one count. The -2.57 ns was taken at GPL overflow 0.41 on unplaced wires, so not a real path measure until the shell is placed. Not decided.
- Reset: kit has bound_reset.json tree (depth 12 relays u_rrl_k, from face_flops via reset_tree.tcl); the 15,395 fanout is the pre-placement net. After the split each core needs its own reset entry; the shell tree reaches the cores' rst pins only.

## Open / next (needs Fable direction)
pick final list; check core pin counts; generate core kits with the normal generator (mkmacro / gen.py), run via ot-run on epyc8/intel1/epyc2; no plan rows written yet for S81-DIE-R3.
