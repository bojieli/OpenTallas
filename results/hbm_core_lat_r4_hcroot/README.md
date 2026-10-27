# HBM-CORE-LAT-R4 hcroot (2026-10-27)
Kit: intel2:/srv/opentallas-scratch2/claude/hbm-core-lat-r4-hcroot/kits_cts/hcp_sys1 (copy of R3 kits_fp/hcp_sys1_eeab1883a31b, 3_place.odb).
GEOM-REVIEW-16 01:11 PASS-COND pin snap applied in the kit: clk 77.76 -> 77.784 (pre_cts_r4.tcl place_pin; OT_R4_CLKPIN M5 77.768-77.800 CHECKED in cts_r4.log); io.tcl + pins.json updated.
CTS (cts_r4.sh, unit oth-ubuntu-3021013-1793089044, exit 0): plan-built tree = R3 hcp_sys1.tree_spec.tcl (port ck->clk only), QC cf/mscts_core.tcl + mscts_h.tcl (sha in inputs.sha256), TritonCTS off, ITERS 0, POST_CTS report-only (kit F4 chain-move + tap_balance disabled = no clock edits).
  OT_R4_MEMBERSHIP sinks 9034 leaves 256 load 35..36; 360 nodes, depth 7; post-CTS hold gate (placement RC) PASS FF reg2reg wns -15.69 ps / 326 endpoints (CHECKED, hold_gate.log). No insertion measured yet.
STOPPED (COORD order 01:2x): the synth LEC of this netlist is NOT EQUIVALENT (R3 kit lec/lec.json: 7724 proved / 1070 differ / 1772 gold-only regs) = FAIL_PREFLOOR.
  route_r4.sh unit oth-ubuntu-3061825-1793089197 stopped during GRT; partial 5_* deleted; 4_cts.odb kept (valid only if the netlist stays unchanged).

## LEC diagnosis (first failing cones; read from RTL + netlist, CHECKED unless marked)
- u_core.d0[6..14] = F_NV field = `last_r ? nlast_r[8:0] : WNV` with WNV = W = 256. nlast_r is a NO-RESET register loaded on accept_cmd
  from the wrapper-tied cmd_nchunk = 16'h0A00, so nlast_r = ((2559 & 255) + 1) = 256 = WNV. d0[NV] is the constant 256 once nlast_r is
  loaded; before the first command nlast_r is X. Yosys opt_dff folds the undefined-init constant-D register (a legal X refinement), so the
  d0[NV] flops become constants in the gate netlist.
- lec.py treats gold no-reset registers as a free initial state and finds no constant (gold_constant_flops 0, paired_flops 0), so it reports
  "RTL registers removed by synthesis although not constant".
- Likely the same class: d0[25] (xpos[0] + r[0]; xpos is no-reset, loaded from the tied cmd_xbase). UNCHECKED.
- st[3] (async reset, all FSM states < 8) and u_div r_rem/r_mb are also unmatched (gold r_rem[1][250] vs gate r_rem#t[26][21] array layout).
  This is a correspondence/naming problem; no functional difference has been shown. UNCHECKED.
- Conclusion: no RTL or synth bug has been shown. Fix options:
  (a) RTL owner: pass the static wrapper's tied command fields to the core as parameters/constants, or reset the cmd registers (LEC then
      proves the constants from reset).
  (b) LEC owner: add an X-refinement rule for uninitialised registers whose D under enable is constant.
  Then rerun LEC. If the netlist changes, re-plan the tree; if it does not, 4_cts.odb can be reused.
