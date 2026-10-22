yosys read_verilog -sv -DSYNTHESIS qkd_ahub_grouped_transport_private.sv
yosys chparam -set ENABLE 1 qkd_ahub_grouped_zh_transport_private
yosys hierarchy -check -top qkd_ahub_grouped_zh_transport_private
source /out/ot_keep_regs.tcl
yosys synth -top qkd_ahub_grouped_zh_transport_private -flatten 
yosys check -assert
yosys write_json /out/grouped.generic.json
yosys dfflibmap -liberty /tmp/lib/seq.lib
yosys abc -liberty /tmp/lib/all.lib
yosys opt_clean
yosys read_liberty -lib /tmp/lib/all.lib
yosys write_json /out/grouped.mapped.json
yosys write_verilog -noattr /out/grouped.mapped.v
yosys tee -o /out/grouped.stat stat -liberty /tmp/lib/all.lib
