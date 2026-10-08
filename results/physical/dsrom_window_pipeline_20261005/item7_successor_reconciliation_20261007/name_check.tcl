set checks 0
foreach escaped {0 1} {
for {set bank 0} {$bank<4} {incr bank} {
for {set col 0} {$col<17} {incr col} {
set raw [format {g_bank[%d].g_col[%d].g_split.g_payload.u_column} $bank $col]
if {$escaped} {set raw [string map {[ \[ ] \]} $raw]}
set iname [string map {\\ {}} $raw]
if {![regexp {g_bank\[([0-3])\].*g_col\[([0-9]+)\]} $iname unused b k]} { error "name failed $raw" }
if {$b != $bank || $k != $col} {error "index mismatch"}
incr checks
}}}
puts "PASS escaped_and_plain_columns=$checks"
