# Preserve all four source-pinned Z18 macro locations/orientations.
source /src/physical/dsrom_qx10_parent_context/macros.tcl
set cfg_inst [ot_find $block g_cfg_provider.u_provider.g_hard_cfg.u_cfg]
if {[[$cfg_inst getMaster] getName] ne "ot_rom_4096x72_m8"} {error "real cfg ROM master missing"}
set cfg_x [ot_snap_joint 4.32 $xgrid0 $xpitch 0.0 0.054]
set cfg_y [ot_snap_joint 4.32 $ygrid0 $ypitch 0.0 0.048]
place_inst -name [$cfg_inst getName] -location [format "%.3f %.3f" $cfg_x $cfg_y] -orientation R0 -status FIRM
puts "OT_QX10_CFG_MACRO master=ot_rom_4096x72_m8 x=$cfg_x y=$cfg_y orientation=R0 original_weight_macros=4"
