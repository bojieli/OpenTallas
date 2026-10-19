yosys read_verilog -sv /data/param_probe.sv
set raw {V \"foo\"}
dict for {k v} $raw {puts "PARAM_VALUE=<$v>"; yosys chparam -set $k $v top}
yosys hierarchy -top top
puts "QUOTED_STRING_PARAM_CANONICALIZE PASS"
