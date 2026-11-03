create_clock -name ck -period 833 [get_ports ck]
set_input_delay 0 -clock ck [delete_from_list [all_inputs] [get_ports ck]]
set_output_delay 0 -clock ck [all_outputs]
