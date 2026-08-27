.PHONY: sim lint synth verify clean

SOURCES = expert_mask_controller.sv via_mask_rom.sv rom_mac_tile.sv opentallas_tile.sv

build:
	mkdir -p build

sim: build
	iverilog -g2012 -Wall -s tb_opentallas_tile -o build/tb_tile $(SOURCES) test/tb_opentallas_tile.sv
	vvp build/tb_tile

lint:
	verilator --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-WIDTH -Wno-MULTITOP $(SOURCES) static_timeslot_switch.sv

synth: build
	yosys -q -l build/synth.log synth.ys
	grep -A24 '=== opentallas_tile ===' build/synth.log

verify: sim lint synth

clean:
	rm -rf build
