# The actual engine's generated clock and ping-pong contracts are unchanged.
source /src/physical/dsrom_qx10_parent_context/boundary.sdc
set cfg_clock [get_pins -quiet g_cfg_provider.u_provider.g_hard_cfg.u_cfg/clk]
if {[llength $cfg_clock]!=1} {error "actual configuration macro clock missing"}
# cfg macro is on core_clk, one read per free edge; its own SS/FF Liberty
# clkQ/address/CE/CLK caps drive the real loader's48 payload capture pins.
# No multicycle/false path or fake clock is added for this ROM.
# The unchanged q-only wrapper selects BF16=0/go_bf_pin=0. In the actual
# joined netlist the BF16-only base[41:29] and unused[47:43] capture bits are
# pruned. Assert every consumed descriptor bit, not a standalone48-port count.
set block [ord::get_db_block]
set macro [$block findInst g_cfg_provider.u_provider.g_hard_cfg.u_cfg]
if {$macro eq "NULL"} {error "actual cfg macro instance absent"}
set clock_net [[$macro findITerm clk] getNet]
set expected {}
for {set bit 0} {$bit<29} {incr bit} {lappend expected $bit}
lappend expected 42
set actual {}
foreach inst [$block getInsts] {
    set name [string map {\\ {}} [$inst getName]]
    if {[regexp {^g_cfg_provider\.u_provider\.u_ld\.c_d\[([0-9]+)\]\$} $name -> bit]} {
        if {![string match DFF* [[$inst getMaster] getName]] ||
            [[$inst findITerm CLK] getNet] ne $clock_net ||
            [[$inst findITerm D] getNet] eq "NULL"} {error "cfg consumed bit$bit lost real root-clock capture"}
        lappend actual $bit
    }
}
if {[lsort -integer $actual] ne $expected} {error "actual source-consumed cfg capture bitset changed: $actual"}
puts "OT_QX10_CFG_CLOCK_CAPTURE root=core_clk macro=[get_full_name $cfg_clock] logical_payload=48 consumed_capture_bits=$actual physical_ROM_bits=72 missing_full_field_input_clocks=1"
