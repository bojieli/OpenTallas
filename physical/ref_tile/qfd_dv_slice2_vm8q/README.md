# qfd_dv_slice2_vm8q (QW-SLICE2W3 10-21, Q.STA.SLICE.2; CRITICAL prefix qfd_dv_slice2: gate only, no submit)
P3 structural successor of the P2 gates qfd_dv_slice2_vm8p / vm8pb (FAIL 10-21, records 8e4a190af): clock_rule pin-flop spread
TT/FF 202/246 (vm8pb 384/455) ps because tier-1 pins landed directly on hard-child pin registers; wire_reach 966/1050 stages
> 500 um (VM broadcast writes pin -> u_vc 819 um single-cycle; ONE shared table-write trunk per tier feeding leaves ~950 um
apart); rst_n 4 sinks unlanded; GRT-0183 boxed-in net in repair_timing (setup -280 ps); S-face 10.5 pins/um cluster.
RTL rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q.sv (spec generator tools/qwen_dv/s5_vm8q_spec.py). Geometry: MAIN 1425.6 x 993.6 (aspect 1.43): row 1 y 129.6 = va/vb/vc (x 86.4/432/777.6) + pg (x 1080), row 2 y 561.6 = cl/ch/bt (x 86.4/432/777.6); read-port W/E faces on 86.4 channels, inter-row relay channel 155 um.
Bench (Verilator 5.050, fleet): rtl/qwen_dv/s5/p3/qfd_dv_s5_vm8q_bench.sh = lockstep vs flat vm8fh, VM answers +1, BTAB/PROG +2,
CROM +4; MUT1 (prog p_idx relay bypass) / MUT2 (cl top data word one relay short) must FAIL -- results/arch/qw_slice2w_1020/bench_p3.
## SAFE-DESIGN checklist (owner 10-19) + pre-gate native census
1 Pins: every leaf input lands on its own parent relay flop (spine-balanced, not a hard-child pin register); outputs = S-face
  capture registers (vm8out, flop-last); rst_n lands at the face in 2 stages (kit reset_landing), then per-leaf reset relays. FIXED.
2 Reach: per-leaf kept relay copies (qfd_dv_s5_vm8q_vwr/vrd/twb/twp/twc/rst, route.synth_keep_modules) sit beside their leaf;
  pins in per-column disjoint ranges under the leaf column they feed; row 2 reached through the inter-row channel. FIXED.
3 Fanout: relays only (max ~4 loads in P2 census); broadcast copies are kept modules so Yosys cannot merge them back. Census in gate.
4 Depth: wires + relay registers only, no logic. PASS.
5 Storage: relay/capture flops only, none runtime-indexed; storage lives in the leaves' SRAM macros. PASS.
6 Floorplan: 7 CLOSED leaves on the 43.2 lattice, channels >= 43.2 (pin faces 86.4), S pins <= 4.4/um (P2 10.5), aspect <= 1.43,
  full-width S std-cell band. FIXED (outline grows vs the P2 sub-slot: slice2 W parent slot must follow).
7 Clock: one region, root ck at S centre (col C), balanced spine; every pin-flop is a parent flop -> pin-flop spread measured by
  the gate (<= 80 TT/FF). io_hold_margin 0.03. FIXED.
8 Schedule: static. Price vs P2: VM reads +1 and VM writes +1 (write->read distance unchanged), reset release +2 (landing);
  BTAB/PROG/CROM and p_q (SU8 si) timing unchanged.  NOTICE to QW-TOKSCHED.
