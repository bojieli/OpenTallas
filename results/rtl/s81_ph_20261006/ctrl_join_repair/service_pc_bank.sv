// Generated service-PC boundary only. Full dsfd_svc quadrant/IO assembly is absent.
module dsfd_svc_pc_bank (
 input wire ck, rst,
 input wire [8895:0] rd,
 output wire [10911:0] rq,
 input wire [31:0] rk, wd,
 input wire [10911:0] qrq,
 output wire [31:0] qrk, qwd,
 output wire [8895:0] qrd
);
 genvar p;
 generate for(p=0;p<32;p=p+1) begin: g_pc
  dsfd_svc_pc u_pc (.ck(ck), .rst(rst),
   .rq(rq[p*341 +: 341]), .qrq(qrq[p*341 +: 341]),
   .rk(rk[p]), .qrk(qrk[p]), .wd(wd[p]), .qwd(qwd[p]),
   .rv(rd[8864+p]), .qrv(qrd[8864+p]),
   .r_data(rd[p*256 +: 256]), .qr_data(qrd[p*256 +: 256]),
   .r_tag(rd[8192+p*17 +: 17]), .qr_tag(qrd[8192+p*17 +: 17]),
   .r_beat(rd[8736+p*4 +: 4]), .qr_beat(qrd[8736+p*4 +: 4]));
 end endgenerate
endmodule
