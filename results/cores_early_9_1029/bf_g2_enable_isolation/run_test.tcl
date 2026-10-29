read_db $::env(ODB)
source /hook/bf_enable_isolation.tcl
write_verilog /out/post_isolation.v
