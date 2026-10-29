module candidate(input clk, input raw_0, input raw_1, input raw_2, input root_raw,
 input cland_fstart_in_a, input cland_fstart_in_b, input cland_fstart_in_c,
 input [1:0] strap_ca_tsel, input [1:0] strap_ca_pad, input strap_ca_efall,
 input strap_ca_root, output cland_start, output cland_start_d, output cland_start_raw);
    wire cland_oraw = (strap_ca_tsel == 2'd0) ? raw_0 : (strap_ca_tsel == 2'd1) ? raw_1 : raw_2;
    wire cland_start_child, cland_start_root, cland_start_child_d, cland_start_root_d;
    wire cland_raw_sel = strap_ca_root ? root_raw : cland_oraw;
    ot_dp_landing_root #(.SETTLE(40)) u_cland_root (.clk(clk), .rst_raw_n(root_raw), .start(cland_start_root), .start_d(cland_start_root_d));
    assign cland_start = strap_ca_root ? cland_start_root : cland_start_child;
    assign cland_start_d = strap_ca_root ? cland_start_root_d : cland_start_child_d;
    assign cland_start_raw = cland_raw_sel;
    wire cland_start_t0, cland_start_t1, cland_start_t2, cland_start_t0_d, cland_start_t1_d, cland_start_t2_d;
    ot_dp_landing_origin_s #(.PADW(2), .FWD_COPY(1)) u_cland_origin_t0 (
        .clk(clk), .rst_raw_n(raw_0), .p_start(cland_fstart_in_a), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start_t0), .start_d(cland_start_t0_d));
    ot_dp_landing_origin_s #(.PADW(2), .FWD_COPY(1)) u_cland_origin_t1 (
        .clk(clk), .rst_raw_n(raw_1), .p_start(cland_fstart_in_b), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start_t1), .start_d(cland_start_t1_d));
    ot_dp_landing_origin_s #(.PADW(2), .FWD_COPY(1)) u_cland_origin_t2 (
        .clk(clk), .rst_raw_n(raw_2), .p_start(cland_fstart_in_c), .strap_efall(strap_ca_efall), .strap_pad(strap_ca_pad), .start(cland_start_t2), .start_d(cland_start_t2_d));
    assign cland_start_child = (strap_ca_tsel == 2'd0) ? cland_start_t0 : (strap_ca_tsel == 2'd1) ? cland_start_t1 : cland_start_t2;
    assign cland_start_child_d = (strap_ca_tsel == 2'd0) ? cland_start_t0_d : (strap_ca_tsel == 2'd1) ? cland_start_t1_d : cland_start_t2_d;
endmodule
