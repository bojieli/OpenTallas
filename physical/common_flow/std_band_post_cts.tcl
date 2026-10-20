# HBM-MC3G 10-20 (spec post_cts_extra): CTS-stage births (hold / timing repair buffers) join the std-cell band and are
# legalized there; clock-net drivers and port-net cells stay outside (clock / pin roles).  Then the band check and the
# exact role list for tools/ref_tile/band_exception_harvest.py.
source /src/physical/common_flow/std_band_fence.tcl
if {[ot_band_fence_adopt post_cts] > 0} {
  detailed_placement
  check_placement -verbose
}
ot_band_fence_check post_cts
ot_band_fence_roles post_cts
