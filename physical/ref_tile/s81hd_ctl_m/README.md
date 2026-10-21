# s81hd_ctl_m (HD-CTLGATE, S81-HEAD 10-21) -- MAIN

Head-die controller `ot_s81hd_ctl` (rtl/dsrom_sys/s81_head, HD-CTL b4f571642) as a FLAT leaf: x store 80 kb in 4 x
ot_sram_1r1w_64x512_m1_r2c2 (macros), bus B stream issue, N/S final, rank merge, host / draft endpoints, XB forward,
MU replay, and `dsfd_mtp_seq` synthesised in.  Flat because the only CLOSED dsfd_mtp_seq views (dsfd_mtp_seq_b/_c,
10-08) are legacy MAXL M7 views that an M5-cap cluster cannot bind (child_lint layer rule) and the M5 reroute
dsfd_mtp_seq_m5 is NEEDS_RTL; the RTL hierarchy is unchanged.
Outline 1036.8 x 1036.8 (MAIN).  19,016 signal pins -> pin-bound: N = sn_o/sn_i + mesh TX (4,454), S = ss_o/ss_i + mesh
RX + mflt (4,478), E = 5 draft lanes (5,560, 5.4/um), W = lep ring (ri/ro/mu_*/lw/faults) + 2 host lanes + ck/rst_n
(4,522).  SRAMs: one centre column x 432.0, y 302.4 / 432.0 / 561.6 / 691.2 (129.6 pitch), R0.

Benches (Verilator 5.050): tb_s81hd_ctl (HD-CTL): 2 positions (strict win + all-equal tie), every slice m = 0..8247 at
G+5+m on both spines, merge + tie, token via dsfd_mtp_seq, host RESULT: PASS; mutants SLICE / TIE FAIL (witnesses
rtl/dsrom_sys/s81_head/test/witness/).  Kit job runs run_hd_ctl_bench.sh sim base|SLICE|TIE.

SAFE review (8 points):
1 pins: PASS. Every input lands in a pin flop, every output leaves a flop (HD-CTL); reset rst_n -> ot_rst_relay_tree3
  (2-stage landing, 24 leaves <= 32 pins); reset_landing 2.  Faces <= 5.4 pins/um (rule <= 6).
2 reach: RISK, measured by the gate. Pin flops sit in the face bands (io_flop_at_pins cols 4); per-lane frame logic
  is local to its lane's pin span; the long hops are the narrow ones (BEST record 97 b to the centre merge, SRAM read
  -> bus B pin flops ~518 um at most).  No relay without an RTL change (+cycles, HD-CTL/HD-CHAIN call); the gate's
  wire_reach (textbook_lint) and trial GRT decide.  
3 fanout: PASS. HD-CTL census max 32 (glue, 40,764 roots, 0 violations); flat census incl. dsfd_mtp_seq: see below.
4 depth: PASS. One compare or one 4:1 mux level group per stage; merge = 2-level registered tree (HD-CTL).
5 storage: PASS. x store in 4 SRAM macros (80 kb); flop holds each < 2 kb (lane buffers 1,659 b, HFWD hold 512 b).
6 floorplan: macros on the 43.2 lattice, >= 44-um channels on the W/E data-pin faces, >= 51-um N/S gaps, full std-cell
  rows; fill ~5 % waived (pin-bound, fill_reason); square.
7 clock: one region, k-means regional roots K=16; spread <= 80 ps TT+FF measured by the --cts gate; io_hold_margin
  0.03.  ctl <-> lep / lane / spine crossings are land-plan rows (HD-CHAIN).
8 schedule: static; flow control only in the lane adapters (off-die credits) and at the dsfd_mtp_seq grant pairs fed by
  the static schedule; overflow = sticky fault.  Added cycles (HD-CTL README): ri -> x write 2, start -> go 3, forward
  ri -> ro 7, N/S fire -> BEST frame 5, merge fire -> RESULT 6.

Census (pre-gate, flat incl. dsfd_mtp_seq, hd_census.sh HD_HARD=""): PENDING (fleet run cenflat_ctl, recorded by the pickup)
