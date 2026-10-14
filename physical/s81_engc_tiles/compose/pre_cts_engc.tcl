# dsfd_engram_c PRE_CTS (el1013-s81-engram 2026-10-13).  The all-tile cluster has no top-level register, so the view
# flow's IO reference (vclk_latency.tcl: vclk = midpoint of core_clk's reported latency) lands on the children's clock
# PINS (CTS-stop run c8: 626 ps, the mid of 443..763) and misses each child's internal insertion + face arcs.  Here
# vclk stays at the fixed ENGC_VCLK_PS of the route SDC (io_vclk_m_<V>.sdc; V = the cluster's effective clock
# insertion, chosen from the measured per-child IO slacks and reported to the die lead); no re-measure.
source /src/physical/abi3/v41x_karb_repair_buffer_cap.tcl
