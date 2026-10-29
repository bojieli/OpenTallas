# DIE-QC-35 PROG QC-020 ffh10r: SIGNED OFF (physical sign-off; routed LEC still to run)

Same hooks / config / run script as `../ffh10e` (FF-only post-route hold ECO, margin 10, FF vclk 381.14, clk_freeze),
started from the ROUTED ffh10 `5_2_route.odb` (sha256 ebe156c63c00bb28..) + its 6_final.spef (KV mk_eco default
OT_ECO_FROM=route form), so the ffh10 clock detailed wires stay FIXED. Kit intel2
`/srv/opentallas-scratch2/claude/die-qc-34-kits/prog/kit_ffh10r`; unit **oth-ubuntu-1139601-1793300807** exit 0
(12:03-12:18 PDT); client log intel2 `~/dqc35k/prog_ffh10r.otrun.log`.

CHECKED (kit run_route.log + signoff/signoff.json, copy here):
- ECO: routed-SPEF FF hold before -4.115 ps (= ffh10 sign-off); 196 hold buffers (data paths); OT_CLK_FREEZE ON 333
  clock nets with wire, 333 re-encoded FIXED; assert OK "all 333 clock nets carry their pre-ECO FIXED wire" (17 nets
  touched by GRT updateDirtyNets were restored by the freeze); post (GRT RC) +6.32; DRT 0 violations (no DRT-1231).
- **signoff.py verdict SIGNED**: TT setup **+232.16** | FF hold **+6.67** (measured pin-flop FF vclk reference) |
  related-pair skew TT/FF **79.2 / 71.5** (<= 80; 0.8 ps headroom) | pin-flop spread info 62.51/62.57 | DRV slew/cap 0 |
  fanout PASS | DRC 0, antenna 0 | PG PASS | timing_modes PASS | sdc_lint, face_guard, unconstrained, clock PASS.
- No clock ECO, no pads/trims, no skew targets, no new check; hold cells are ordinary repair_timing data-path buffers
  (12.4a a1) at the 12.19 10-ps margin on measured arrivals.

Not yet done (blocks CLOSED): **routed LEC** (kit RTL vs 6_final.v). The kit has no rtl/ dir (deleted with the s8b kit;
config.mk VERILOG_FILES /work/rtl/qfd_dv_s5_vm8x.sv + 3 SRAM _bb.v, spec 86288faea:physical/ref_tile/qfd_dv_s5_prog);
stage those exact sources into the kit, then main `tools/die_plan/lec.py KIT --netlist .../6_final.v --out
KIT/lec_routed` with OT_LEC_SUPERSET_VEC=1 (autopilot signoff_chain form); also the PG census on 6_final.
Caveat: the related pair has 0.8 ps headroom and moved 78.4-85.6 across three routes of the same tree (ffh10e); any
re-route of this DB must keep the clock wires FIXED, and the tree re-balance of the pcap/p_q and u_hi_wd -> u_hi leaf
groups stays the structural item for the next plan event.
