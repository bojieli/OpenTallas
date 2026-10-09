###############################################################################
# Created by write_sdc
###############################################################################
current_design ot_hbm_production_clock_digital_body
###############################################################################
# Timing Constraints
###############################################################################
create_clock -name aon -period 3000.0000 [get_ports {aon_clk}]
set_clock_uncertainty -setup 60.0000 aon
set_clock_uncertainty -hold 25.0000 aon
set_propagated_clock [get_clocks {aon}]
create_clock -name stream -period 833.3334 [get_ports {clk_stream}]
set_clock_uncertainty -setup 60.0000 stream
set_clock_uncertainty -hold 25.0000 stream
set_propagated_clock [get_clocks {stream}]
create_clock -name serial -period 1111.1111 [get_ports {clk_serial}]
set_clock_uncertainty -setup 60.0000 serial
set_clock_uncertainty -hold 25.0000 serial
set_propagated_clock [get_clocks {serial}]
create_clock -name hbm -period 1024.0000 [get_ports {clk_hbm}]
set_clock_uncertainty -setup 60.0000 hbm
set_clock_uncertainty -hold 25.0000 hbm
set_propagated_clock [get_clocks {hbm}]
create_clock -name link -period 833.3334 [get_ports {clk_link}]
set_clock_uncertainty -setup 60.0000 link
set_clock_uncertainty -hold 25.0000 link
set_propagated_clock [get_clocks {link}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {bist_done}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {bist_done}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {bist_pass}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {bist_pass}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {fatal_error}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {fatal_error}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[0]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[0]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[1]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[1]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[2]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[2]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[3]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[3]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[4]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[4]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[5]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[5]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[6]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[6]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[7]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[7]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {links_ready[8]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {links_ready[8]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {phy_ready[0]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {phy_ready[0]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {phy_ready[1]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {phy_ready[1]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {phy_ready[2]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {phy_ready[2]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {phy_ready[3]}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {phy_ready[3]}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {pll_lock}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {pll_lock}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {por_n}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {por_n}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {power_good}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {power_good}]
set_input_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {requalify}]
set_input_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {requalify}]
set_output_delay 25.0000 -clock [get_clocks {serial}] -min -add_delay [get_ports {cmd_reset_serial_n}]
set_output_delay 100.0000 -clock [get_clocks {serial}] -max -add_delay [get_ports {cmd_reset_serial_n}]
set_output_delay 25.0000 -clock [get_clocks {stream}] -min -add_delay [get_ports {cmd_reset_stream_n}]
set_output_delay 100.0000 -clock [get_clocks {stream}] -max -add_delay [get_ports {cmd_reset_stream_n}]
set_output_delay 25.0000 -clock [get_clocks {serial}] -min -add_delay [get_ports {coll_reset_serial_n}]
set_output_delay 100.0000 -clock [get_clocks {serial}] -max -add_delay [get_ports {coll_reset_serial_n}]
set_output_delay 25.0000 -clock [get_clocks {stream}] -min -add_delay [get_ports {coll_reset_stream_n}]
set_output_delay 100.0000 -clock [get_clocks {stream}] -max -add_delay [get_ports {coll_reset_stream_n}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[0]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[0]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[1]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[1]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[2]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[2]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[3]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[3]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[4]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[4]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[5]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[5]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[6]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[6]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[7]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[7]}]
set_output_delay 25.0000 -clock [get_clocks {link}] -min -add_delay [get_ports {link_reset_n[8]}]
set_output_delay 100.0000 -clock [get_clocks {link}] -max -add_delay [get_ports {link_reset_n[8]}]
set_output_delay 25.0000 -clock [get_clocks {hbm}] -min -add_delay [get_ports {phy_reset_n[0]}]
set_output_delay 100.0000 -clock [get_clocks {hbm}] -max -add_delay [get_ports {phy_reset_n[0]}]
set_output_delay 25.0000 -clock [get_clocks {hbm}] -min -add_delay [get_ports {phy_reset_n[1]}]
set_output_delay 100.0000 -clock [get_clocks {hbm}] -max -add_delay [get_ports {phy_reset_n[1]}]
set_output_delay 25.0000 -clock [get_clocks {hbm}] -min -add_delay [get_ports {phy_reset_n[2]}]
set_output_delay 100.0000 -clock [get_clocks {hbm}] -max -add_delay [get_ports {phy_reset_n[2]}]
set_output_delay 25.0000 -clock [get_clocks {hbm}] -min -add_delay [get_ports {phy_reset_n[3]}]
set_output_delay 100.0000 -clock [get_clocks {hbm}] -max -add_delay [get_ports {phy_reset_n[3]}]
set_output_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {pll_reset_n}]
set_output_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {pll_reset_n}]
set_output_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {ready}]
set_output_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {ready}]
set_output_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {state[0]}]
set_output_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {state[0]}]
set_output_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {state[1]}]
set_output_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {state[1]}]
set_output_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {state[2]}]
set_output_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {state[2]}]
set_output_delay 25.0000 -clock [get_clocks {aon}] -min -add_delay [get_ports {state[3]}]
set_output_delay 100.0000 -clock [get_clocks {aon}] -max -add_delay [get_ports {state[3]}]
set_min_delay -ignore_clock_latency\
    -from [list [get_ports {bist_done}]\
           [get_ports {bist_pass}]\
           [get_ports {links_ready[0]}]\
           [get_ports {links_ready[1]}]\
           [get_ports {links_ready[2]}]\
           [get_ports {links_ready[3]}]\
           [get_ports {links_ready[4]}]\
           [get_ports {links_ready[5]}]\
           [get_ports {links_ready[6]}]\
           [get_ports {links_ready[7]}]\
           [get_ports {links_ready[8]}]\
           [get_ports {phy_ready[0]}]\
           [get_ports {phy_ready[1]}]\
           [get_ports {phy_ready[2]}]\
           [get_ports {phy_ready[3]}]\
           [get_ports {pll_lock}]\
           [get_ports {por_n}]\
           [get_ports {power_good}]]\
    -to [list [get_cells {collars.cmd_serial.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.cmd_serial.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.cmd_stream.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.cmd_stream.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.coll_serial.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.coll_serial.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.coll_stream.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.coll_stream.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.link[0].c.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.link[0].c.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.phy[0].c.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.phy[0].c.sync_q[1]$_DFF_PN0_}]] 0.0000
set_min_delay -ignore_clock_latency\
    -from [list [get_ports {bist_done}]\
           [get_ports {bist_pass}]\
           [get_ports {links_ready[0]}]\
           [get_ports {links_ready[1]}]\
           [get_ports {links_ready[2]}]\
           [get_ports {links_ready[3]}]\
           [get_ports {links_ready[4]}]\
           [get_ports {links_ready[5]}]\
           [get_ports {links_ready[6]}]\
           [get_ports {links_ready[7]}]\
           [get_ports {links_ready[8]}]\
           [get_ports {phy_ready[0]}]\
           [get_ports {phy_ready[1]}]\
           [get_ports {phy_ready[2]}]\
           [get_ports {phy_ready[3]}]\
           [get_ports {pll_lock}]\
           [get_ports {por_n}]\
           [get_ports {power_good}]]\
    -to [list [get_cells {sequence_control.status_meta[0]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[10]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[11]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[12]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[13]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[14]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[15]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[16]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[1]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[2]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[3]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[4]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[5]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[6]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[7]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[8]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[9]$_DFF_PN0_}]] 0.0000
set_max_delay -ignore_clock_latency\
    -from [get_clocks {aon}]\
    -to [list [get_cells {collars.cmd_serial.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.cmd_serial.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.cmd_stream.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.cmd_stream.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.coll_serial.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.coll_serial.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.coll_stream.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.coll_stream.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.link[0].c.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.link[0].c.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.phy[0].c.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.phy[0].c.sync_q[1]$_DFF_PN0_}]] 500.0000
set_max_delay -ignore_clock_latency\
    -from [list [get_clocks {hbm}]\
           [get_clocks {link}]\
           [get_clocks {serial}]\
           [get_clocks {stream}]]\
    -to [list [get_cells {rel_sync_q0[0]$_DFF_PN0_}]\
           [get_cells {rel_sync_q0[12]$_DFF_PN0_}]\
           [get_cells {rel_sync_q0[15]$_DFF_PN0_}]\
           [get_cells {rel_sync_q0[1]$_DFF_PN0_}]\
           [get_cells {rel_sync_q0[2]$_DFF_PN0_}]\
           [get_cells {rel_sync_q0[3]$_DFF_PN0_}]] 500.0000
set_max_delay -ignore_clock_latency\
    -from [list [get_ports {bist_done}]\
           [get_ports {bist_pass}]\
           [get_ports {links_ready[0]}]\
           [get_ports {links_ready[1]}]\
           [get_ports {links_ready[2]}]\
           [get_ports {links_ready[3]}]\
           [get_ports {links_ready[4]}]\
           [get_ports {links_ready[5]}]\
           [get_ports {links_ready[6]}]\
           [get_ports {links_ready[7]}]\
           [get_ports {links_ready[8]}]\
           [get_ports {phy_ready[0]}]\
           [get_ports {phy_ready[1]}]\
           [get_ports {phy_ready[2]}]\
           [get_ports {phy_ready[3]}]\
           [get_ports {pll_lock}]\
           [get_ports {por_n}]\
           [get_ports {power_good}]]\
    -to [list [get_cells {collars.cmd_serial.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.cmd_serial.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.cmd_stream.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.cmd_stream.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.coll_serial.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.coll_serial.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.coll_stream.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.coll_stream.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.link[0].c.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.link[0].c.sync_q[1]$_DFF_PN0_}]\
           [get_cells {collars.phy[0].c.sync_q[0]$_DFF_PN0_}]\
           [get_cells {collars.phy[0].c.sync_q[1]$_DFF_PN0_}]] 500.0000
set_max_delay -ignore_clock_latency\
    -from [list [get_ports {bist_done}]\
           [get_ports {bist_pass}]\
           [get_ports {links_ready[0]}]\
           [get_ports {links_ready[1]}]\
           [get_ports {links_ready[2]}]\
           [get_ports {links_ready[3]}]\
           [get_ports {links_ready[4]}]\
           [get_ports {links_ready[5]}]\
           [get_ports {links_ready[6]}]\
           [get_ports {links_ready[7]}]\
           [get_ports {links_ready[8]}]\
           [get_ports {phy_ready[0]}]\
           [get_ports {phy_ready[1]}]\
           [get_ports {phy_ready[2]}]\
           [get_ports {phy_ready[3]}]\
           [get_ports {pll_lock}]\
           [get_ports {por_n}]\
           [get_ports {power_good}]]\
    -to [list [get_cells {sequence_control.status_meta[0]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[10]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[11]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[12]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[13]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[14]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[15]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[16]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[1]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[2]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[3]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[4]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[5]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[6]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[7]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[8]$_DFF_PN0_}]\
           [get_cells {sequence_control.status_meta[9]$_DFF_PN0_}]] 500.0000
###############################################################################
# Environment
###############################################################################
###############################################################################
# Design Rules
###############################################################################
set_max_fanout 32.0000 [current_design]
