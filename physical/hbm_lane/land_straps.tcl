# HBM-LANDING 10-18: landing K strap (LANDING-CONTRACT L7) of the hbfd_land*_<W>_<DIR> kits.  k0..k2 are identity STRAPS
# tied by the die binder per lane (one hardened view per width; K does not create variants): constant in operation, so
# the tile times no path from them (the die STA case-analyses the tied value).  Without this the default die-context IO
# budget put a fake input arrival on k -> rc compare -> o (gate 10-18: in->reg -490 ps, 6 levels from k1).
if {[llength [get_ports -quiet {k0 k1 k2}]]} {
  set_false_path -from [get_ports {k0 k1 k2}]
  puts "OT_HBM_LAND: k0..k2 = die straps (false path; die STA case analysis)"
}
