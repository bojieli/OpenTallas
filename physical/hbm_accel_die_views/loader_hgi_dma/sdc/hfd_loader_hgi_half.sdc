# hfd_loader (HGI, loader_hgi_dma view, [svc] 2026-10-10): the half-rate core ot_hfd_loader_half37 (SHARED 1) sits at
# u_ld.u_ld inside ot_hfd_loader_hgi; its core u_core runs on ck gated every other cycle, so core -> core paths get two
# ck periods (multicycle setup 2 / hold 1), exactly as loader/sdc/hfd_loader_half.sdc for the legacy wrapper (u_ld.u_core).
# Everything else (CP window, kport, DMA unit, VM client, face stages) is single cycle.
set ot_core [get_cells -quiet {u_ld.u_ld.u_core.*}]
if {[llength $ot_core] > 0} {
  set_multicycle_path -setup 2 -from $ot_core -to $ot_core
  set_multicycle_path -hold 1 -from $ot_core -to $ot_core
  puts "OT_LOADER_HALF multicycle on [llength $ot_core] core cells"
} else {
  puts "OT_LOADER_HALF WARNING no core cells matched u_ld.u_ld.u_core.* (expected only before synthesis)"
}
