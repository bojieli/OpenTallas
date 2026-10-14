# dsfd_vm_bgl28_mc5_h1pcs OWN measured root insertions (claude s81-grpA r3, 2026-10-14), replacing the stale UNBOUND W5
# nominal references (dsfd_vm_bgl28_mc5_nominal.tcl) for this kit only.  Source: this kit's own --cts gate
# (ot-epyc1tb ref_gate/dsfd_vm_bgl28_mc5_h1pcs-20261014-053302, BGL_MC_RAW, TT = arrival_max mean over each root's
# owning registers).  Mismatch of the W5 values it replaces: core +9.8, req +4.8, ret -94.9, fwd0 -3.2, fwd1 +100.7 ps:
# the delivered phase put ret sinks ~95 ps early and fwd1 sinks ~101 ps late -> 13,305 inter-root hold endpoints,
# 20,547 hold buffers, DPL-0033.  The die delivers each clock entry at phi - R (die clock delivery rule 10-13) with
# exactly these R; ONE fixed phase per root at every corner (no per-corner alignment).
# r4 (2026-10-14 12:09): RAW boundary means from the --raw-source gate (main 56937833c ck_insertion; the die delivers phi - R
# with R = insertion.json boundary mean): core 390.3 / req 255.4 / ret 172.1 / fwd0 166.5 / fwd1 317.8 (was all-register
# means 402.8 / 259.0 / 170.8 / 164.5 / 318.3).  OPEN tile defect: core leaf spread 153.4 ps (369.3..522.7) > 80.
set ::ot_bgl_mc_nominal_refs [dict create core_clk 390.3 req_clk 255.4 ret_clk 172.1 fwd0_clk 166.5 fwd1_clk 317.8]
