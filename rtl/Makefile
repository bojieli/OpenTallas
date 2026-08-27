.PHONY: sim unit-sim integration-sim lint formal synth synth-reference verify clean

SOURCES = expert_mask_controller.sv via_mask_rom.sv rom_mac_tile.sv opentallas_tile.sv
LIB_SOURCES = lib/ot_skid_buffer.sv lib/ot_async_fifo.sv lib/ot_crc_pkg.sv \
	lib/ot_crc16_ccitt.sv lib/ot_crc32c.sv
REFERENCE_SOURCES = $(LIB_SOURCES) via_mask_rom.sv ot_route_mask.sv ot_rom_wrapper.sv \
	ot_format_decode.sv ot_numeric_dot.sv ot_reduction_tree.sv \
	ot_schedule_controller.sv ot_credit_manager.sv ot_session_table.sv \
	ot_cmd_frontend.sv ot_hbm_frontend.sv ot_stage_link_tx.sv \
	ot_stage_link_rx.sv ot_stage_link_endpoint.sv ot_ras_controller.sv \
	ot_power_reset_controller.sv ot_csr_block.sv ot_stage_controller.sv \
	ot_bist_controller.sv ot_dft_controller.sv ot_stage_top.sv ot_tile.sv \
	lib/ot_sync_bits.sv
LINT_REFERENCE_SOURCES = $(filter-out via_mask_rom.sv,$(REFERENCE_SOURCES))

build:
	mkdir -p build

sim: build
	iverilog -g2012 -Wall -s tb_opentallas_tile -o build/tb_tile $(SOURCES) test/tb_opentallas_tile.sv
	vvp build/tb_tile

unit-sim: build
	iverilog -g2012 -Wall -s tb_reference_units -o build/tb_units $(REFERENCE_SOURCES) test/tb_reference_units.sv
	vvp build/tb_units

integration-sim: build
	iverilog -g2012 -Wall -s tb_stage_top -o build/tb_stage_top $(REFERENCE_SOURCES) test/tb_stage_top.sv
	vvp build/tb_stage_top

lint:
	verilator --lint-only -Wall -Wno-fatal -Wno-DECLFILENAME -Wno-WIDTH -Wno-MULTITOP \
		--top-module ot_tile $(SOURCES) static_timeslot_switch.sv $(LINT_REFERENCE_SOURCES)

formal:
	python3 ../tools/rtl_campaign.py --formal

synth: build
	yosys -q -l build/synth.log synth.ys
	grep -A24 '=== opentallas_tile ===' build/synth.log

synth-reference: build
	yosys -q -l build/synth_reference.log synth_reference.ys
	grep -A24 '=== ot_stage_top ===' build/synth_reference.log

verify: sim unit-sim integration-sim lint formal synth synth-reference

clean:
	rm -rf build
