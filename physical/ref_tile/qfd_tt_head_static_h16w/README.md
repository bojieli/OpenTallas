# qfd_tt_head_static_h16w -- PARALLEL FALLBACK of h16v (default ABC script, net_def, depth 26); same RTL (QW-H16V 10-20), TOK.QW.LAYER.3.SEG head leaf: RTL depth round

h16u = h16t geometry, ONE clock region (SRAMs on ck_head).  The remaining blocker measured on the h16t CTS ODB
(ck_head->ck_head, TT placement RC) was LOGIC depth: dts r_q -345 (16 yosys array dividers), fixed_issue sched_q -344 /
cycle (cycle+1 folded into a 30-AND ripple by the gate mapping), u_store cfg_fault -300 / sealed / loading (serial
copies count + if-chain seal_bad), dpre/dtilk -242, rom_cmd_q -140 ((stage-1)*816 product + rippled 24-bit add),
program_obs -92 (observer 16-slot priority scan).  Table: ../qfd_tt_head_static_h16u/h16t_reg_violators_by_rtl.txt.

RTL (rtl/qwen_sys/static_schedule_20261014/safe32, head-only files; shared originals untouched), all exact, 0 edges:
- ot_hdc_dyn_ttiles_tab.sv: one quotient (pos>>WT)/3 as a mod-3 Kogge-Stone suffix scan, registered WITH pos_r
  (same edge, same next value); the 16 DYN_TTILES entries are constant shifts + kept KS increments
  (floor(floor(x/3)>>s) = floor((x>>s)/3)).  Unit test vs ot_hdc_dyn_ttiles: exhaustive pos, 7 parameter sets.
- hr_safe32: relocation stage terms (valid/head/code_base/scale_base) registered with loaded_stage from the same next
  value (reset base(0)); ot_qwen_tp8_rom_relocate_pb with kept KS 24-bit adds.
- ot_qwen_fixed_issue_ld.sv (copies of fixed_issue_pw / seg_pw / fixed_issue for the head): cycle+1 and the two cycle
  magnitude compares as kept KS; seal_bad = flat term vector OR tree; copies>=1..4 from prefix popcount trees selected
  by one-hot min(count,DEPTH).  yosys sequential equivalence vs the as-built modules (SREG1 SLATE1): PROVEN.
- rk_safe32: candidate / prog_a adds kept KS; program write observer in closed form (structurally one macro x one slot,
  full mask) with the original observer as a simulation reference.
RTL parent bench (qfd_tt_ctlm_dv + safe32 head RTL with the reference $fatal checks) V5.050: img0 PASS 123/123, imgh PASS 131/131.

Netlist: results/rtl/qw_head_safe32_1020/h16v/run_gen.sh (prepare_generic h16v sources -> synth -noabc -> ABC ->
bound_head_netlist load-cap 16 -> param header + single region).  h16v = ABC '&if -g; &synch2; &if -g; dch; map -D 1'
(net_ifg2): bounded max depth 20 levels, 0 flops over 20 (h16u: 40).  Fallback h16w = default ABC (net_def): 26.
Cells 31.5k generic (h16u 30.4k).

## SAFE-DESIGN checklist
1 Pins: pin registers ON (ck_head); reset landed by the kit (2 stages) -- PASS (as h16u)
2 Reach: 345.6 x 302.4 leaf, no planned wire > 405 um -- gate
3 Fanout: bounded netlist load-cap 16 (same bounding as h16t, whose gate census PASSed max 32) -- PASS by construction; gate census
4 Depth: bounded max 20 levels (h16u 40); every RTL violator group of the h16t table restructured -- FIXED
5 Storage: FIFO 6x 32x128 SRAM + 2x 64x512 programme store; new regs: pq_r 18 b, rb_* 50 b, pw_s2 3 b -- PASS
6 Floorplan: h16u geometry (8 macros on the 43.2 lattice), E face pin-bound -- WARN (unchanged)
7 Clock: single CTS root ck_head (flops + 8 SRAM clock pins), no crossing -- gate
8 Schedule: 0 added edges (all restructures exact; new registers load on existing edges) -- PASS
Parent: qfd_tt_ctlm_dv u_hr must drop .ck_pm0/.ck_pm1 (1r port list), as prepare_bench.py does.
