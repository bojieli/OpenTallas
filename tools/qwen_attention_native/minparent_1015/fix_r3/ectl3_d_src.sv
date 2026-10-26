// debug: the b4 specialisation qkd_ectl3_epoch_direct_s_d (STATIC_QK=1, QK_ISSUE_AGE=34, ROW_RETURN_LAT=22) compiled from source
module qkd_ectl3_epoch_direct_s_d (input wire [2:0] ck, input wire rst_n, input wire [4:0] cfg,
  output wire [15:0] e0,e1,e2,e3, input wire [33:0] s0,s1,s2,s3, output wire [1558:0] t0,t1, output wire [16:0] rq,
  input wire [1024:0] rs, input wire [633:0] si, output wire [424:0] so);
  qkd_ectl3_epoch_direct_s #(.STATIC_QK(1),.QK_ISSUE_AGE(34),.ROW_RETURN_LAT(22)) u(.*);
endmodule
