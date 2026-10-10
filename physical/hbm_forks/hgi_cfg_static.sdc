# hbm-forks 2026-10-09: HGI-1 quasi-static mode registers (docs/HBM_GENERIC_INTERFACE.md 1.2).  The active words of every
# ot_hgi_cfg_rx (cfg_act_q) change only on cfg_commit, which the config master issues only while the die is idle
# (E_BUSY refusal) and follows with a SETTLE-cycle doorbell hold-off (>= deepest bus latency + 16).  They are therefore
# constants for timing: no path from them is a timed 1.2 GHz launch.  The config bus itself (stations, rx pin flops,
# shadow words) stays fully timed.  Source this after the block SDC in every forked block's route.
set ot_hgi_act [get_cells -quiet -hierarchical -filter {NAME =~ *cfg_act_q*}]
if {[llength $ot_hgi_act] > 0} {
  set_false_path -from $ot_hgi_act
}
