# dsfd_vm_bgl28_mc5_h1pcs OWN measured root insertions (claude s81-grpA r3, 2026-10-14), replacing the stale UNBOUND W5
# nominal references (dsfd_vm_bgl28_mc5_nominal.tcl) for this kit only.  Source: this kit's own --cts gate
# (ot-epyc1tb ref_gate/dsfd_vm_bgl28_mc5_h1pcs-20261014-053302, BGL_MC_RAW, TT = arrival_max mean over each root's
# owning registers).  Mismatch of the W5 values it replaces: core +9.8, req +4.8, ret -94.9, fwd0 -3.2, fwd1 +100.7 ps:
# the delivered phase put ret sinks ~95 ps early and fwd1 sinks ~101 ps late -> 13,305 inter-root hold endpoints,
# 20,547 hold buffers, DPL-0033.  The die delivers each clock entry at phi - R (die clock delivery rule 10-13) with
# exactly these R; ONE fixed phase per root at every corner (no per-corner alignment).
set ::ot_bgl_mc_nominal_refs [dict create core_clk 402.804328 req_clk 258.9882988786308 ret_clk 170.79300641185526 fwd0_clk 164.53627991031811 fwd1_clk 318.32582030472514]
