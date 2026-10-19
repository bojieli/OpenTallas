`timescale 1ns/1ps
// Exact selected CALR seal, NU4/CTX_DW1. Header capacity only; no numerical execution.
// The 390 entry count is source-recovered; unlike CALD no PW base is encoded.
module tb_qready_calr_capacity;
 reg ck=0; always #0.416 ck=~ck;
 reg rst_n=0,pw_v=0,dw_v=0;
 reg[9:0]pw_addr=0;reg[63:0]pw_data=0;reg[2:0]dw_addr=0;
 wire[4:0]ready,fault;wire[7:0]fc[0:4];wire[63:0]dw_data[0:4];
 genvar g;
 generate for(g=0;g<5;g=g+1)begin:d
  localparam integer CNT=(g==0)?248:(g==1)?249:(g==2)?390:(g==3)?1023:1024;
  assign dw_data[g]=(dw_addr==0)?((64'h43414c52<<32)|CNT):
                     (dw_addr==2)?CNT:64'd0;
  qfd_dv_cmd_cal_mu #(.NU(4),.CALENDAR_ROM(1),.CTX_DW(1),.UFOLD(1),.UVM_STRIDE(4096),.PIDX_STRIDE(128),.UTAG_LSB(6)) dut(
   .ck(ck),.rst_n(rst_n),.pw_v(pw_v),.pw_addr(pw_addr),.pw_data(pw_data),
   .dw_v(dw_v),.dw_addr(dw_addr),.dw_data(dw_data[g]),
   .start(1'b0),.stage(6'd1),.start_user(2'd0),.start_rng(1'b0),.start_first(10'd0),.start_cnt(10'd0),
   .image_ready(ready[g]),.fault(fault[g]),.fault_code(fc[g]));
 end endgenerate
 integer a;
 initial begin
  repeat(4)@(negedge ck);rst_n=1;
  for(a=0;a<1024;a=a+1)begin
   @(negedge ck);pw_v=1;pw_addr=10'(a);pw_data=(a==1017)?(64'd30<<18):0;
  end
  @(negedge ck);pw_v=0;
  for(a=0;a<8;a=a+1)begin @(negedge ck);dw_v=1;dw_addr=3'(a);end
  @(negedge ck);dw_v=0;repeat(8)@(negedge ck);
  for(a=0;a<5;a=a+1)$display("CALR_CAPACITY case%0d ready%0d fault%0d fc%h",a,ready[a],fault[a],fc[a]);
  for(a=0;a<4;a=a+1)if(!ready[a]||fault[a])$fatal(1,"CALR_LEGAL_REJECT case%0d",a);
  if(ready[4]||!fault[4]||!fc[4][4])$fatal(1,"CALR_OVERFLOW1024_SURVIVED");
  $display("QREADY_CALR_CAPACITY_PASS 248_249_390_1023_accept_1024_reject");$finish;
 end
endmodule
