# hgi-takeover 2026-10-10 / hgi-1010/d4 (coordinator: port SECDED clock plan, option 1 as hbm-forks did for the svc face
# taps).  ckf / ckt are face clock taps of ot_hcoll_port (FACE_CK bit 0 / bit 1): die clock leaves at the RX face
# (bottom, ckf: rxf_p / rxv_p) and the TX face (right, ckt: ph_tx_flit / ph_tx_v).  Same clock as clk (one core_clk with
# several source ports); each tap's SOURCE latency stands for the die tree's delivery of that leaf so its pin flops
# align with the interior registers.
# THIS file is the CALIBRATE (CTS-only) constraint: a provisional source latency of 640 ps (route e21dc1395 routed
# interior TT 692 ps less a ~50 ps face tree).  The route uses face_ck_latency.py's per-corner MEASURED values
# (interior mean insertion less each tap's own tree, on the calibrate CTS db).
# hgi-1010/d4 fix: the 3b90d75fa version wrote "-source 0.640" (ns) into a ps-unit flow (period 833): 0.64 ps.  The
# latency is now scaled by the loaded time unit.
set ot_fc_per [get_property [get_clocks core_clk] period]
set ot_fc_ps [expr {$ot_fc_per > 10.0 ? 1.0 : 0.001}]
set ot_fc_taps {}
foreach ot_fc_p {ckf ckt} { if {[llength [get_ports -quiet $ot_fc_p]]} { lappend ot_fc_taps $ot_fc_p } }
create_clock -name core_clk -period $ot_fc_per [get_ports [concat clk $ot_fc_taps]]
foreach ot_fc_p $ot_fc_taps { set_clock_latency -source [expr {640.0 * $ot_fc_ps}] [get_ports $ot_fc_p] }
