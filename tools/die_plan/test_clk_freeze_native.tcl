# Native regression: run with INPUT_ODB, CLK_FREEZE_OLD, CLK_FREEZE_NEW,
# and CODEC_OUT environment variables. Original input is read only.
read_db $::env(INPUT_ODB)
set block [ord::get_db_block]
proc property_fixture {name} {
 global block
 set n [odb::dbNet_create $block $name]
 $n setSigType CLOCK
 set w [odb::dbWire_create $n]
 set enc [odb::dbWireEncoder];$enc begin $w
 $enc newPath [[ord::get_db_tech] findLayer M3] ROUTED
 $enc addPoint 1000 1000
 set normal [$enc addPoint 2000 1000]
 set extended [$enc addPoint 2000 2000 80]
 $enc end
 if {![$w setProperty $normal 4242] || ![$w setProperty $extended 8383]} {error "fixture property insertion failed"}
 return $n
}
source $::env(CLK_FREEZE_OLD)
set old [property_fixture property_old_control]
if {![catch {ot_clk_fix_wire $old} message]} {error "negative control: old codec unexpectedly preserved nonzero properties"}
puts "CODEC_NEGATIVE_PASS $message"
odb::dbNet_destroy $old
source $::env(CLK_FREEZE_NEW)
set new [property_fixture property_new_fixture]
set wire [$new getWire]
set pn 0;set pe 0
for {set i 0} {$i<[$wire length]} {incr i} {
 if {([$wire getOpcode $i]&31)==12} {
  if {[$wire getData $i]==4242} {incr pn}
  if {[$wire getData $i]==8383} {incr pe}
 }
}
if {$pn!=1 || $pe!=1} {error "fixture lacks nonzero POINT/POINT_EXT properties: $pn/$pe"}
set ::env(RESULTS_DIR) $::env(CODEC_OUT)
file mkdir $::env(RESULTS_DIR)
ot_clk_freeze
foreach n [ot_clk_dbnets] {
 if {[ot_clk_wire_tokens $n] ne $::ot_clk_tok([$n getName])} {error "strict property token mismatch"}
}
ot_clk_dump $::env(CODEC_OUT)/clock_encoded.tsv encoded
write_db $::env(CODEC_OUT)/encoded.odb
puts "CODEC_PROPERTY_PASS normal=$pn extended=$pe nets=[llength [ot_clk_dbnets]]"
