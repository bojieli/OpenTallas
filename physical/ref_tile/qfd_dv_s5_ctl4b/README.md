# qfd_dv_s5_ctl4b -- slice2 glue leaf ctl, repair4 bounded netlist (QW-SLICE7-CTL, Q.STA.SLICE.2)

Successor of qfd_dv_s5_ctl / qfd_dv_s5_ctlb (claude/qw-slice6-ctl-1019 1f858dec1), whose gate2 WARN did not qualify:
ASAP7 mapped census 136 drivers > 32 (49 flop, max 1956 = reset). Same ports, outline and faces as the predecessor
(fallback 432 x 216 (2:1), both chain words on the long S face).
Main kit qfd_dv_s5_ctl4, parallel fallback qfd_dv_s5_ctl4b.

RTL: top `qfd_dv_s5_ctl_repair4_leaf` (HARD 1, MU_NU 4, MUT 0; unsupported shapes fail elaboration) =
`rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4.sv` (bounded constructor netlist built from 1f858dec1 HARD 1 by
tools/qwen_dv/bound_math_netlist.py --load-cap 16 --transparent-inverters --retain-mux --shared-helpers --retain-all-comb --fuse-ao,
Codex codex/qw-slice6-headsctl-1020 656ea2912) + helpers + scalar-name leaf wrapper. Source SHA256 in
results/arch/qw_slice6_1019/ctlrepair4_1020/model/schedule_and_source.json.

## Pre-gate native census (ASAP7 mapped, native4, ep5 unit oth-ubuntu-2637279-1792486441)
max loads 32, 0 non-clock roots > 32 (raw inputs + reset included), raw reset 2 loads, 7207 FF, Liberty area 4354.81 um2,
TT stage estimate 551.8 ps / 19 levels, pin boundary levels in->reg 0 / reg->out 0 / in->out 0.
Mapped SHA256 33ab1b540c113b3242760cc100e43c01cde6ee7fe6ffba46c4bebb120f0852b9 (results/arch/qw_slice6_1019/ctlrepair4_1020/native4/).
The gate re-runs the mapped census with main's true-Liberty-role hook before floorplan (handback HOLD item 1).

## Benches (Verilator 5.050)
ctl4_eq: repair4 vs ctl_gate2 behavioural snapshot, 151,677 values / 8,000 edges, 2 mid-run resets: PASS.
ctl4_mut11: real MUT11 netlist (collective-command bit defect, rebuilt by the same constructor): FAIL 5 cc_o mismatches;
committed witness results/arch/qw_slice6_1019/ctlrepair4_1020/bench4/mut11.log. Runner rtl/test/qwen_dv/s5/ctlrepair1/kit4/bench.sh.

## SAFE-DESIGN checklist
1 Pins: PASS -- every input in one pin register (HARD 1), every output from a flop, no in->out path (boundary levels 0); rst_n 2-stage landing.
2 Reach: PASS -- tile side <= 432 um; slice distances are lp landings in the parent.
3 Fanout: FIXED -- recursive structural duplication of every FF/comb root to <= 32 (census above); kept helper boundaries stop ABC re-sharing.
4 Depth: FIXED -- 1313 AO21/OA21 fusions, 551.8 ps / 19 levels TT (repair3 688.5 ps / 22 HOLD superseded); gate path classes confirm.
5 Storage: PASS -- no runtime-indexed flop array; NU4 argmax semantic state 2016 b <= 2 kb whole (no chunk exemption).
6 Floorplan: pin-bound (4,898 port bits at <= 6 pins/um per face), no macros, one full-width std-cell band, aspect 2.0.
7 Clock: one centre-fed root (7207 sinks, 0.35 mm tile); gate judges pin-flop spread <= 80 ps TT+FF; io_hold_margin 0.03.
8 Schedule: static; 0 steady data edges vs the HARD 1 reference (which already prices +2 through ctl); reset assertion +1 and release +1 (boot only), NOTICE in lanes/QW-SLICE7.md.
Area/FF delta vs 1f858dec1 (handback HOLD): source model 6930 -> 7207 FF (+277 reset/replica FF); apples-to-apples mapped area is read from this gate's synthesis.
