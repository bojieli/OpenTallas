# drive-0849: the hand-made sys kit (4842b33d5) lacked io_plain.sdc, which post_plain.tcl reads after CTS / GRT / DRT / fill
# (STA-0340 at 4_1_cts in both icut a2cf5ee1c routes).  Plain boundary = die_p770.sdc's IO form: 0.2 x 833.333 each side.
unset_input_delay [all_inputs]
unset_output_delay [all_outputs]
set_input_delay 166.667 -clock core_clk [all_inputs -no_clocks]
set_output_delay 166.667 -clock core_clk [all_outputs]
set_false_path -to [get_ports -quiet {po_me_clk}]
