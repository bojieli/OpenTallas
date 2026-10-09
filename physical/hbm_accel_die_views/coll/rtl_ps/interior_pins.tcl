# Pin groups occupy separate faces with two existing signal layers per face.
# All intervals are outside the fixed interior macro footprint.
set_io_pin_constraint -group -region left:60-480 -pin_names {qp_din* qr_din* qp_push qr_push}
set_io_pin_constraint -group -region right:60-480 -pin_names {ph_tx_flit* rb_d* ph_tx_v rb_v stall fault}
set_io_pin_constraint -group -region bottom:60-420 -pin_names {ph_rx_flit* ph_rx_v}
set_io_pin_constraint -group -region top:60-420 -pin_names {clk rst_n sw_cr_ret rb_cr}
