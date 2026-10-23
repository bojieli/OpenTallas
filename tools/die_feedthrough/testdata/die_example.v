module die_top (input wire ck, input wire rs_n);
  wire [7:0] a_x, c_x, h01, h12;
  wire ck1, ck2, ck3; wire [1:0] ay, cy;
  src_m u_a (.x({a_x[7], a_x[6], a_x[5], a_x[4], a_x[3], a_x[2], a_x[1], a_x[0]}), .y(ay));
  dsfd_dvrlyh_8_WE u_r0 (.ck(ck), .rs(rs_n), .i({a_x[7], a_x[6], a_x[5], a_x[4], a_x[3], a_x[2], a_x[1], a_x[0]}), .o({h01[7], h01[6], h01[5], h01[4], h01[3], h01[2], h01[1], h01[0]}), .ck_o(ck1));
  dsfd_dvrlyh_8_WE u_r1 (.ck(ck1), .rs(rs_n), .i({h01[7], h01[6], h01[5], h01[4], h01[3], h01[2], h01[1], h01[0]}), .o({h12[7], h12[6], h12[5], h12[4], h12[3], h12[2], h12[1], h12[0]}), .ck_o(ck2));
  dsfd_dvrlyh_8_WE u_r2 (.ck(ck2), .rs(rs_n), .i({h12[7], h12[6], h12[5], h12[4], h12[3], h12[2], h12[1], h12[0]}),
      .o({c_x[7], c_x[6], c_x[5], c_x[4], c_x[3], c_x[2], c_x[1], c_x[0]}), .ck_o(ck3));
  dsfd_rly_2 u_q0 (.ck(ck), .rs(rs_n), .i(ay), .o(cy));
  blk_m__ft0a1b2c3d u_blk (.rst_n(rs_n));
  dst_m u_c (.x({c_x[7], c_x[6], c_x[5], c_x[4], c_x[3], c_x[2], c_x[1], c_x[0]}), .y(cy));
endmodule
