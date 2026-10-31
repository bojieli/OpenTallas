// DIE-KV-50: o side = the KV bound ectl (kiss_st at the bound params); n side = the four-column composition (legacy shim)
module qkd_ectlk_o (input wire [15:0] rsp_epoch, input wire [5:0] rsp_layer, input wire [13:0] rsp_t, input wire [0:0] rsp_v,
  input wire [0:0] rsp_valid, input wire [33:0] s2, input wire [33:0] s3, output wire [412:0] so, output wire [1558:0] t0,
  output wire [1558:0] t1, input wire [2:0] ck, output wire [15:0] e0, output wire [15:0] e1, input wire [0:0] rst_n,
  input wire [33:0] s0, input wire [33:0] s1, input wire [632:0] si, input wire [4:0] cfg, output wire [15:0] e2,
  output wire [15:0] e3, input wire [15:0] epoch, output wire [0:0] fault, input wire [0:0] kgo, input wire [5:0] layer,
  output wire [15:0] req_epoch, output wire [5:0] req_layer, output wire [13:0] req_t, output wire [0:0] req_v,
  output wire [0:0] req_valid, input wire [1023:0] rsp_data);
  qkd_ectl3_kiss_st #(.HXK(13), .MUT(0), .QK_ISSUE_AGE(`O_AGE), .RESPONSE_LAT(`O_LAT)) u (.rsp_epoch(rsp_epoch), .rsp_layer(rsp_layer),
    .rsp_t(rsp_t), .rsp_v(rsp_v), .rsp_valid(rsp_valid), .s2(s2), .s3(s3), .so(so), .t0(t0), .t1(t1), .ck(ck), .e0(e0), .e1(e1),
    .rst_n(rst_n), .s0(s0), .s1(s1), .si(si), .cfg(cfg), .e2(e2), .e3(e3), .epoch(epoch), .fault(fault), .kgo(kgo), .layer(layer),
    .req_epoch(req_epoch), .req_layer(req_layer), .req_t(req_t), .req_v(req_v), .req_valid(req_valid), .rsp_data(rsp_data));
endmodule
module qkd_ectlk (input wire [15:0] rsp_epoch, input wire [5:0] rsp_layer, input wire [13:0] rsp_t, input wire [0:0] rsp_v,
  input wire [0:0] rsp_valid, input wire [33:0] s2, input wire [33:0] s3, output wire [412:0] so, output wire [1558:0] t0,
  output wire [1558:0] t1, input wire [2:0] ck, output wire [15:0] e0, output wire [15:0] e1, input wire [0:0] rst_n,
  input wire [33:0] s0, input wire [33:0] s1, input wire [632:0] si, input wire [4:0] cfg, output wire [15:0] e2,
  output wire [15:0] e3, input wire [15:0] epoch, output wire [0:0] fault, input wire [0:0] kgo, input wire [5:0] layer,
  output wire [15:0] req_epoch, output wire [5:0] req_layer, output wire [13:0] req_t, output wire [0:0] req_v,
  output wire [0:0] req_valid, input wire [1023:0] rsp_data);
  qkd_ectlk_columns_legacy u (.rsp_epoch(rsp_epoch), .rsp_layer(rsp_layer),
    .rsp_t(rsp_t), .rsp_v(rsp_v), .rsp_valid(rsp_valid), .s2(s2), .s3(s3), .so(so), .t0(t0), .t1(t1), .ck(ck), .e0(e0), .e1(e1),
    .rst_n(rst_n), .s0(s0), .s1(s1), .si(si), .cfg(cfg), .e2(e2), .e3(e3), .epoch(epoch), .fault(fault), .kgo(kgo), .layer(layer),
    .req_epoch(req_epoch), .req_layer(req_layer), .req_t(req_t), .req_v(req_v), .req_valid(req_valid), .rsp_data(rsp_data));
endmodule
