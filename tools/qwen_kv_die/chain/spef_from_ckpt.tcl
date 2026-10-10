# ds-1010 2026-10-10: GRT-parasitic SPEF from a retained full-die GRT checkpoint (no re-route).
# write_db after global_route keeps the global routes in this OpenROAD build (26Q3-1510): after read_db,
# grt::have_routes = 1 and estimate_parasitics -global_routing gives the same wire RC as the routing session
# (verified net by net on a small block; read_guides is NOT needed and is what raises GRT-0008).
# Env: OT_THREADS.  Inputs /work/ckpt_grt.odb; output /work/die_grt.spef.  Fails loudly without routes.
proc mem {tag} { set f [open /proc/self/status]; set s [read $f]; close $f
  regexp {VmRSS:\s+(\d+)} $s -> r; regexp {VmHWM:\s+(\d+)} $s -> h
  puts "OTMEM $tag rss_mb=[expr {$r/1024}] hwm_mb=[expr {$h/1024}] t=[clock seconds]"; flush stdout }
proc step {name body} { set t0 [clock milliseconds]
  if {[catch {uplevel 1 $body} err]} { puts "OT_STEP_FAIL $name $err"; flush stdout; exit 1 }
  puts "OT_TIME step=$name s=[format %.1f [expr {([clock milliseconds]-$t0)/1000.0}]]"; mem $name }
set_thread_count $::env(OT_THREADS)
step load { read_db /work/ckpt_grt.odb }
step routes { if {![grt::have_routes]} { error "checkpoint carries no global routes" }; puts "OT_HAVE_ROUTES 1" }
read_liberty /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
step spef { estimate_parasitics -global_routing -spef_file /work/die_grt.spef }
puts OT_SPEF_DONE
