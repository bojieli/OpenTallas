A0 rc7 / rc7b read-only pickup, 2026-10-20 00:36-00:39 PT
VERDICT: BLOCKED / binding mapped-fanout FAIL; original gates still LIVE.
Source claude/qw-cluster3-a0-1019 pinned shipping commit666a22494.
All files are point-in-time snapshots, NOT terminal gate verdicts.
Original jobs: NK rc7/rc7b ep6 230117/230116; NL rc7 agidock128 230000; NL rc7b ep5 230024.
Clients 210927/210930/210931/210932 preserved; no duplicate gate/review/submission.
Actual gate layout dumps copied from remote routes/gate/work/orfs, rendered with existing layout_png.py and all four floorplan PNGs personally inspected.
NK: 19 hard blocks, total fill44.3%; NL:18 hard blocks fill41.4%. Outline820.8x907.2 aspect1.11. Symmetric ROM stacks and LSL columns, free channels visible; NK has tall narrow central node. Clock pins on W/E faces.
Checklist (strictly separate proven observations from missing qualification):
1 PINS: textbook in->out0, in->reg0/reg->out0; rst_n lands on1 flop before copies. Pin geometry PASS2622NK/1076NL. All functional ties and exact two-stage internal reset topology NOT independently audited.
2 REACH: UNPROVEN. textbook reach0 is not a physical full-net census. Requires placed native census with landed-hop classification.
3 FANOUT: FAIL. textbook.json high_fanout_top NK _34574_/Y NOR2 262 loads; NL _33514_/Y AND3 291 loads. findings/refuse empty reflects obsolete thresholds. Diagnostic buffer-transparent mapped Verilog walk independently reproduces262/291; driver excerpts and endpoints preserved. This is a logical fanout count through buffers, not number of immediate buffer pins.
4 DEPTH: measured525.1ps/15levels NK,471.8ps/13levels NL; timing analysis/GRT incomplete. No full timing PASS claimed.
5 STORAGE: UNPROVEN >2kb storage census. ROM/SRAM hard children present; cannot infer every soft indexed array compliance from total flops17819NK/16788NL.
6 FLOORPLAN: outline/fill/pin geometry above. PNGs show continuous free channels; no independent lattice/row-band-density clearance claimed.
7 CLOCK: boundary max spreads NK10.2/9.9(rc7),10.7/10.4(b); NL10.2/10.0(rc7),8.2/8.0(b). Root ck has one boundary flop; internal all-flop spreads NK257/230,298/267; NL175/156,171/153. Boundary small spread does not clear internal linked-child timing. Native source/boundary classification owed.
8 SCHEDULE: no new RTL/edges in this pickup. Static scheduling proof inherited, not requalified.
Structural recommendation (must complete full native census before new gate): localize and keep go/reset/enable producers by destination group; preserve same-edge capture. ot_qwen_w12_matvec.sv g_rr6 ld_go at410-416 feeds copies g_sp and other go-latched fields. NK seed _15037_ reaches g_rr6.g_sp[0..23].q[2] in3 logic hops; NL _14014_ includes rst_n__ot_rlc[4] and reaches ts_r/ots_r and g_issue_fast.u_a1.b capture gates. Partition enables/reset qualification per<=32 destination loads with kept registers and independent next-state cones; avoid a single shared combinational enable before all replicated copies. Also re-census g_sp output shift-amount copies (historical33 register violations max48); rc7 inherited REGROOT7, no clearance shown.
No proposed RTL change or new gate until complete mapped all-driver/reset, physical reach, storage, pins/ties census is clean. Original progressing jobs remain evidence to collect, not eligible release passers merely if gate WARN/PASS.
