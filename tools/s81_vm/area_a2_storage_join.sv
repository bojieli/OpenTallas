`timescale 1ns/1ps
// Component-only storage join. Bank-linear A2 outputs bypass legacy capture.
// A legacy logical packet interface would require J=8*(bank%4)+bank/4.
module s81_a2_storage_join(
 input wire [180:0] ck_front,rst_front_n,
 input wire [15:0] ck_scatter,rst_scatter_n,
 input wire [47:0] ck_req,ck_rsp,rst_relay_n,
 input wire [127:0] ck_bank,rst_bank_n,
 input wire [52:0] i_v,input wire [741:0] i_row,input wire [423:0] i_tag,
 input wire [847:0] i_mask,input wire [27135:0] i_data,
 input wire [31:0] i_rv,input wire [287:0] i_ra,input wire [255:0] i_rt,
 output wire [127:0] o_rv,o_commit,output wire [16383:0] o_rd,
 output wire [1023:0] o_rt,o_ct,output wire [1151:0] o_ca,
 output wire [511:0] o_cm,output wire [15:0] o_front_fault,o_scatter_fault
);
 wire [127:0] fv;wire [1791:0] fr;wire [1023:0] ft;
 wire [511:0] fm;wire [16383:0] fd;
 s81_a2_controlled u_front(
  .ck_header(ck_front[0]),.ck_payload(ck_front[1+:4]),
  .ck_control(ck_front[5+:16]),.ck_meta(ck_front[21+:16]),
  .ck_fault(ck_front[37+:16]),.ck_data(ck_front[53+:128]),
  .rst_header_n(rst_front_n[0]),.rst_payload_n(rst_front_n[1+:4]),
  .rst_control_n(rst_front_n[5+:16]),.rst_meta_n(rst_front_n[21+:16]),
  .rst_fault_n(rst_front_n[37+:16]),.rst_data_n(rst_front_n[53+:128]),
  .i_v(i_v),.i_row(i_row),.i_tag(i_tag),.i_mask(i_mask),.i_data(i_data),
  .o_slice_v(fv),.o_slice_row(fr),.o_slice_tag(ft),.o_mask(fm),.o_data(fd),.o_fault(o_front_fault));
 genvar x,q,h,b;
 generate for(x=0;x<4;x=x+1)begin:slice
  for(q=0;q<4;q=q+1)begin:group
   localparam I=x*4+q;
   wire [31:0] wi_mask;wire [1023:0] wi_data;
   wire [7:0] sv,swe;wire [71:0] sa;wire [31:0] sm;
   wire [1023:0] sd;wire [63:0] st;
   wire [7:0] r8v,w8v;wire [71:0] r8a,w8a;wire [63:0] r8t,w8t;
   wire [31:0] w8m;wire [1023:0] w8d;
   wire [7:0] bs_v,bc_v;wire [1023:0] bs_d;
   wire [63:0] bs_t,bc_t;wire [71:0] bc_a;wire [31:0] bc_m;
   wire [7:0] rs_v,rc_v;wire [1023:0] rs_d;
   wire [63:0] rs_t,rc_t;wire [71:0] rc_a;wire [31:0] rc_m;
   for(b=0;b<8;b=b+1)begin:scatter_packet
    assign wi_mask[b*4+:4]=fm[(q*8+b)*16+x*4+:4];
    assign wi_data[b*128+:128]=fd[(q*8+b)*512+x*128+:128];
    assign o_rd[(q*8+b)*512+x*128+:128]=rs_d[b*128+:128];
   end
   dsfd_vm_static_scatter_b8_out #(.BANK_BASE(q*8),.PIPE(1)) u_scatter(
    ck_scatter[I],rst_scatter_n[I],fv[x*32+q*8+:8],fv[x*32+q*8+:8],
    fr[(x*32+q*8)*14+:112],wi_mask,wi_data,ft[(x*32+q*8)*8+:64],
    sv,swe,sa,sm,sd,st,o_scatter_fault[I]);
   dsfd_vm_static_relay128_b8 u_b8(
    .ck_req(ck_req[I]),.ck_rsp(ck_rsp[I]),.rst_n(rst_relay_n[I]),
    .i_rv(i_rv[q*8+:8]),.i_ra(i_ra[q*72+:72]),.i_rt(i_rt[q*64+:64]),
    .i_wv(sv),.i_wa(sa),.i_wt(st),.i_wm(sm),.i_wd(sd),
    .o_rv(r8v),.o_ra(r8a),.o_rt(r8t),.o_wv(w8v),.o_wa(w8a),.o_wt(w8t),.o_wm(w8m),.o_wd(w8d),
    .i_sv(bs_v),.i_sd(bs_d),.i_st(bs_t),.i_cv(bc_v),.i_ca(bc_a),.i_cm(bc_m),.i_ct(bc_t),
    .o_sv(rs_v),.o_sd(rs_d),.o_st(rs_t),.o_cv(rc_v),.o_ca(rc_a),.o_cm(rc_m),.o_ct(rc_t));
   assign o_rv[x*32+q*8+:8]=rs_v;
   assign o_rt[(x*32+q*8)*8+:64]=rs_t;
   assign o_commit[x*32+q*8+:8]=rc_v;
   assign o_ca[(x*32+q*8)*9+:72]=rc_a;
   assign o_cm[(x*32+q*8)*4+:32]=rc_m;
   assign o_ct[(x*32+q*8)*8+:64]=rc_t;
   for(h=0;h<2;h=h+1)begin:half
    localparam H=16+I*2+h;
    wire [3:0] r4v,w4v;wire [35:0] r4a,w4a;wire [31:0] r4t,w4t;
    wire [15:0] w4m;wire [511:0] w4d;
    wire [3:0] bsv,bcv;wire [511:0] bsd;
    wire [31:0] bst,bct;wire [35:0] bca;wire [15:0] bcm;
    dsfd_vm_static_relay128_b4 u_b4(
     .ck_req(ck_req[H]),.ck_rsp(ck_rsp[H]),.rst_n(rst_relay_n[H]),
     .i_rv(r8v[h*4+:4]),.i_ra(r8a[h*36+:36]),.i_rt(r8t[h*32+:32]),
     .i_wv(w8v[h*4+:4]),.i_wa(w8a[h*36+:36]),.i_wt(w8t[h*32+:32]),.i_wm(w8m[h*16+:16]),.i_wd(w8d[h*512+:512]),
     .o_rv(r4v),.o_ra(r4a),.o_rt(r4t),.o_wv(w4v),.o_wa(w4a),.o_wt(w4t),.o_wm(w4m),.o_wd(w4d),
     .i_sv(bsv),.i_sd(bsd),.i_st(bst),.i_cv(bcv),.i_ca(bca),.i_cm(bcm),.i_ct(bct),
     .o_sv(bs_v[h*4+:4]),.o_sd(bs_d[h*512+:512]),.o_st(bs_t[h*32+:32]),
     .o_cv(bc_v[h*4+:4]),.o_ca(bc_a[h*36+:36]),.o_cm(bc_m[h*16+:16]),.o_ct(bc_t[h*32+:32]));
    for(b=0;b<4;b=b+1)begin:bank
     localparam K=x*32+q*8+h*4+b;
     dsfd_vm_static_bank128 u_bank(
      ck_bank[K],rst_bank_n[K],r4v[b],r4a[b*9+:9],r4t[b*8+:8],
      w4v[b],w4a[b*9+:9],w4d[b*128+:128],w4m[b*4+:4],w4t[b*8+:8],
      bsv[b],bsd[b*128+:128],bst[b*8+:8],bcv[b],bca[b*9+:9],bcm[b*4+:4],bct[b*8+:8]);
    end
   end
  end
 end endgenerate
endmodule
