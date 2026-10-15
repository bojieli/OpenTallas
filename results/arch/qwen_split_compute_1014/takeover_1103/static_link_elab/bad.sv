module qwen_static_link_port_contract(input ck,input rst_n); wire[547:0] rx; qfd_d2d_static dut(.ck(ck),.rst_n(rst_n),.native_rx_payload(rx)); endmodule
