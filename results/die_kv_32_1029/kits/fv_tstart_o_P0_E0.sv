module fvtop(input wire clk, input wire raw, input wire rraw, input wire p_start, output wire ok);
  wire cland_start, cland_start_d, cland_tstart_out;
  wire cland_start_raw = raw;
  ot_dp_landing_origin_s #(.PADW(1)) u_cland_origin (.clk(clk), .rst_raw_n(raw), .p_start(p_start), .strap_efall(1'b0),
      .strap_pad(1'd0), .start(cland_start), .start_d(cland_start_d));
  ot_dp_landing_relay u_cland_tstart_o (.clk(clk), .rst_raw_n(cland_start_raw), .d(cland_start_d), .q(cland_tstart_out));
  assign ok = (cland_start == cland_tstart_out);
endmodule
