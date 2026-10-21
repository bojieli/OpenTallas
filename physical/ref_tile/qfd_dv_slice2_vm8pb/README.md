# qfd_dv_slice2_vm8pb (QW-SLICE2W 10-20, Q.STA.SLICE.2; CRITICAL prefix qfd_dv_slice2: gate only, no submit)
P2 successor of the P1 landed parents qfd_dv_slice2_vm8l / vm8lh (gates FAIL 10-20: ck_r_io 31k ring sinks TT/FF spread 339/300 ps,
leaf regions 129-289 ps, in->reg -544 ps, reset-run cross_clock -71 ps; vm8l placement setup -963 / hold -433 ps).
RTL rtl/qwen_dv/s5/p2/qfd_dv_s5_vm8p.sv: the 7 CLOSED leaves (vmr x3, crh lo/hi, btab, prog) in ONE clock region, no rings;
tier 1 VM replicas at the S face (d=0), tier 2 btab/prog (d=1) + cl (d=2 pad), tier 3 ch (d=2); static relays, no reset on data.
PARALLEL FALLBACK: S band 172.8 um (tier y 172.8 / 475.2 / 864.0) + S-face pin_ranges aligned to leaf columns.
Bench (Verilator 5.050, ot-epyc5): lockstep vs flat vm8fh, answers +2d: MUT0 PASS 71,544 compares; MUT1 (prog p_idx relay bypass) FAIL;
MUT2 (cl table data one relay short) FAIL -- results/arch/qw_slice2w_1020/bench.
## SAFE-DESIGN checklist (owner 10-19) + PRE-GATE NATIVE CENSUS
1 Pins: PASS (owner 10-20 09:05): same region -> inputs captured by the leaves' own pin registers (tier 1) or relays; outputs are the
  S-face capture registers (flop-last); reset: leaves' own 2-stage landing, relayed by d.
2 Reach: tiers 2/3 relayed (<= ~430 um per hop planned); tier-1 broadcast VM writes reach up to ~600 um single-cycle (guidance under the
  09:35 freeze; the gate STA decides).
3 Fanout: census PASS, 11,217 roots, max dynamic loads 4, 0 > 32 (results/arch/qw_slice2w_1020/native).
4 Depth: wires + relay registers only, no logic. PASS.
5 Storage: 6,280 relay/capture flops, none runtime-indexed; storage lives in the leaves' SRAM macros. PASS.
6 Floorplan: leaves on the 43.2 lattice, channels >= 25.9 um, aspect 1.05, macro-bound fill ~43 %, one full-width S std-cell band.
7 Clock: one root ck (S centre), balanced clock spine with child-insertion leaf targets (cluster default); pin-flop spread measured by the gate.
8 Schedule: static; price vs vm8fh: VM reads +0, BTAB/PROG reads +2 / table writes +1, CROM reads +4 / table writes +2,
  write->read distance unchanged per leaf (P1 was +6 on every read).
