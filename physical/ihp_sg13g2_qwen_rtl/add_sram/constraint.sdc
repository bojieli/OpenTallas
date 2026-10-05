set clk_period 20.0
set core_clock_name core_clock
set io_clock_name io_clock

create_clock -name $core_clock_name -period $clk_period [get_ports clk]
create_clock -name $io_clock_name -period $clk_period
set_clock_uncertainty 0.20 [get_clocks $core_clock_name]
set_clock_transition 0.10 [get_clocks $core_clock_name]

set data_inputs [get_ports {cmd_valid abi_major* abi_minor* expected_command_index* command_record* sram_read_ready sram_response_valid sram_response_data* sram_write_ready done_ready}]
set_input_delay 1.0 -clock $io_clock_name $data_inputs
set_input_transition 0.10 $data_inputs
set_input_delay 0.0 -clock $io_clock_name [get_ports rst_n]
set_input_transition 0.10 [get_ports rst_n]
set_output_delay 1.0 -clock $io_clock_name [all_outputs]
set_load 0.02 [all_outputs]
set_false_path -from [get_ports rst_n]
