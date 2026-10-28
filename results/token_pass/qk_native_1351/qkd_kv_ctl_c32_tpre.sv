module qkd_kv_ctl_c32_tpre(input wire[3:0]t, output wire[3:0]hi, output wire[3:0]lo);
 assign hi={t[3:2]==2'd3,t[3:2]==2'd2,t[3:2]==2'd1,t[3:2]==2'd0};
 assign lo={t[1:0]==2'd3,t[1:0]==2'd2,t[1:0]==2'd1,t[1:0]==2'd0};
endmodule
