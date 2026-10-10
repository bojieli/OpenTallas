# CLAUDE mtp-rom 2026-10-08: the closed WFC's two fixed one-edge synchronous-read ports (prompt port -> dsfd_wfc_tok
# f_pr, VM read address -> dsfd_wfc_vmx f_vr) are launched from WFC flops and ABUT these blocks (intra-region): their
# arrival is the WFC's clk->q + an abutted wire, not the generic die-link 0.2 T + 150 ps.  Budget: 150 ps after the
# virtual clock (vs 316.7 generic); the WFC side must then meet output delay T - 150 - setup on pr_* / vm_raddr
# (a re-derived link budget, to be confirmed by rebudget on the routed WFC + this view; REVIEW_QUEUE MTP-ROM R3).
set ot_abut [get_ports -quiet {f_pr[*] f_vr[*]}]
if {[llength $ot_abut]} {
  set_input_delay 150 -clock vclk $ot_abut
  set_input_delay -min 0 -clock vclk $ot_abut
}
