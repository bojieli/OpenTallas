`timescale 1ns/1ps
// Pin-registered II=1 collective packet SRAM queue (stream drive-0532, 2026-10-08).
// Successor of ot_hbm_collective_packet_fifo_refill for the physical block hfd_coll_pkt_fifo_ii1: same storage
// (3 x 256x256 macros, 9 x SECDED(72,64) words per 545 b flit), same seal / overflow / single-correct /
// double-detect rules, same port list.  The refill failed at TT by -403 / -198 / -116 ps (TT re-STA of
// hbm_pkt_ii1b-36399d734-tt): din -> SECDED encode -> SRAM wd_in under the 518.67 ps die-link input budget;
// syn_q -> pad-bit fault -> ready under the same output budget; SRAM rd_out (413 ps clk->q) -> syndrome -> ue_q.
// A same-cycle valid/pop and a combinational ready cannot be pin-registered, so (as ot_hbm_su_result_pinshell):
//   * every input lands in a flop with no logic before it (push_p, din_p, cr_p), every output leaves a flop;
//   * ready is a REGISTERED level with a 2-slot reserve: ready_q <= unread_next <= DEPTH-2 (covers the push being
//     pin-registered this edge and the push the next cycle may make), so capacity stays DEPTH;
//   * the consumer side is CREDIT flow: valid is a one-edge pulse per delivered flit (dout held in a flop), pop is
//     a CREDIT-RETURN pulse (one per freed consumer slot), OCR consumer slots (default 8 >= the 7-edge loop);
//   * the read side is a fixed-latency pipeline that never stalls (a credit is taken at fetch):
//       fetch (r_ce) -> rd_out (macro latch) -> raw_q (capture flop, no logic before it)
//       -> syn_q / ovr_q / ue_q + raw2_q (syndrome stage) -> out_q (correct stage) -> dout pins;
//   * raw2_q is checked by per-word parity against ovr_q in the correct stage (an upset there is DETECTED:
//     fault, the flit is never delivered); the SRAM residency keeps full SECDED.
// Fault (sticky register): control seal mismatch (registered compare, detected one edge later), overflow
// (push while not ready), uncorrectable word, raw2 parity change, nonzero pad bits.  Fault freezes control,
// drops ready and valid.
// Cost: write +1 edge (pin flop), first-flit latency 2 -> 5 edges, ready reserve 2 slots (a 0-cycle-capacity
// loss: in-flight pushes still land), consumer needs OCR=8 x 545 b slots for full rate.
// IREL=1 (stream drive-0758, 2026-10-08): an INPUT RELAY flop on push / din / pop ahead of the pin flops.  The TC
// routes of ii1r/ii1rb/ii1rw failed TT setup -40/-63/-56 ps on din[*] -> din_p with zero logic: a 150-200 ps
// buffered wire from the right-edge pins to pin flops placed next to the encoder/SRAM, under the 518.67 ps die-link
// input budget.  The relay flop takes the pin under the budget; relay -> din_p is a full flop-to-flop cycle.  Cost:
// write +1 edge, ready reserve 3 slots (RSV=DEPTH-2-IREL: one more push in flight), credit loop 6 -> 7 edges
// (measured: OCR=6 is the minimum full-rate credit count at IREL=0, 7 at IREL=1; OCR=8 covers both, II1 drain and
// stream unchanged), count includes the relayed push.
module ot_hbm_collective_packet_fifo_ii1r #(parameter integer DEPTH=256, OCR=8, WREG=0, IREL=0)(
 input wire clk,rst_n,push,input wire [544:0] din,output wire ready,
 input wire pop,output wire valid,output wire [544:0] dout,
 output wire fault,output wire [8:0] count);
`ifndef SYNTHESIS
 initial if(DEPTH!=64&&DEPTH!=256)$fatal(1,"collective FIFO depth must be 64 or 256");
`endif
 localparam [7:0] LAST=DEPTH-1;
 localparam [8:0] DEPTH9=DEPTH,RSV=DEPTH-2-IREL;
 localparam [4:0] OCRV=OCR;
 // ---- pin flops ----
 reg push_p,cr_p;reg [544:0] din_p;
 // ---- IREL=1: input relay flops (pin -> relay -> pin flop, no logic on either hop) ----
 reg push_r,cr_r;reg [544:0] din_r;
 wire push_i=IREL?push_r:push,cr_i=IREL?cr_r:pop;wire [544:0] din_i=IREL?din_r:din;
 wire inflight=IREL?push_r:1'b0;
 // ---- control (sealed); c_unread = words resident or in flight to the macro (capacity) ----
 reg [7:0] c_wp,c_rp;reg [8:0] c_unread;reg [4:0] c_ocr;reg c_ovf;
 reg [71:0] seal;reg bad_q,fault_q,ready_q,ocr_nz;
 wire [63:0] c_word={37'b0,c_wp,c_rp,c_unread,c_ocr,c_ovf};
 // ---- read pipeline ----
 reg v1,v2,v3,out_v;reg [647:0] raw_q,raw2_q;reg [62:0] syn_q;reg [8:0] ovr_q;reg ue_q;reg [544:0] out_q;
 reg [8:0] count_q;
 wire [767:0] ram_q,ram_d;
 wire [575:0] din_pad={31'b0,din_p};
 function automatic [6:0] syndrome7(input [71:0] code);
  integer k,p;
  begin
   syndrome7=7'd0;
   for(k=0;k<7;k=k+1)for(p=1;p<=71;p=p+1)if((p&(1<<k))!=0)syndrome7[k]=syndrome7[k]^code[p-1];
  end
 endfunction
 function automatic [63:0] correct64(input [71:0] code,input [6:0] syn,input ovr);
  integer p,j;
  begin
   correct64=64'd0;j=0;
   for(p=1;p<=71;p=p+1)if((p&(p-1))!=0)begin correct64[j]=code[p-1]^(ovr&&syn==p[6:0]);j=j+1;end
  end
 endfunction
 genvar s;
 wire [62:0] syn_n;wire [8:0] ovr_n,ue_n,par2;wire [575:0] corr;
 generate for(s=0;s<9;s=s+1)begin:g_w
  assign ram_d[s*72+:72]=ot_gpu_w6_secded_pkg::encode64(din_pad[s*64+:64]);
  assign syn_n[s*7+:7]=syndrome7(raw_q[s*72+:72]);
  assign ovr_n[s]=^raw_q[s*72+:72];
  assign ue_n[s]=(syn_n[s*7+:7]!=0)&&!(ovr_n[s]&&syn_n[s*7+:7]<=7'd71);
  assign corr[s*64+:64]=correct64(raw2_q[s*72+:72],syn_q[s*7+:7],ovr_q[s]);
  assign par2[s]=^raw2_q[s*72+:72];
 end endgenerate
 assign ram_d[767:648]=120'b0;
 // ---- write side: pin flop -> encode -> macro (WREG=1: + a flop at the macro input) ----
 wire full=c_unread==DEPTH9;
 wire put=push_p&&!full&&!fault_q;
 wire ovf_now=push_p&&full;
 reg w_ce_q;
 // WREG=1: the word reaches the macro one edge after put, so it becomes readable one edge later
 wire readable=WREG?(c_unread>{8'b0,w_ce_q}):(c_unread!=9'd0);
 wire fetch=readable&&ocr_nz&&!fault_q;reg [7:0] w_addr_q;reg [767:0] wd_q;
 wire w_ce=WREG?w_ce_q:put;wire [7:0] w_addr=WREG?w_addr_q:c_wp;wire [767:0] wd=WREG?wd_q:ram_d;
 // ---- next state ----
 wire [7:0] n_wp=put?((c_wp==LAST)?8'd0:c_wp+8'd1):c_wp;
 wire [7:0] n_rp=fetch?((c_rp==LAST)?8'd0:c_rp+8'd1):c_rp;
 wire [8:0] n_unread=c_unread+{8'b0,put}-{8'b0,fetch};
 wire [4:0] n_ocr=c_ocr-{4'b0,fetch}+{4'b0,cr_p};
 wire n_ovf=c_ovf||ovf_now;
 wire [63:0] n_word={37'b0,n_wp,n_rp,n_unread,n_ocr,n_ovf};
 wire [63:0] r_word={37'b0,8'd0,8'd0,9'd0,OCRV,1'b0};
 // encoders as continuous wires (one call each; the package function is static)
 wire [71:0] enc_c=ot_gpu_w6_secded_pkg::encode64(c_word),enc_n=ot_gpu_w6_secded_pkg::encode64(n_word),
  enc_r=ot_gpu_w6_secded_pkg::encode64(r_word);
 // correct stage faults (v3): uncorrectable at the syndrome stage, raw2 parity change, nonzero pad bits
 wire f3=v3&&(ue_q||(par2!=ovr_q)||(|corr[575:545]));
 wire fault_n=fault_q||bad_q||c_ovf||f3;
 genvar m;
 generate for(m=0;m<3;m=m+1)begin:g_ram
  ot_sram_1r1w_256x256_m2_r2c2 storage(.clk(clk),.r_ce_in(fetch),.r_addr_in(c_rp),.rd_out(ram_q[m*256+:256]),
   .w_ce_in(w_ce),.w_addr_in(w_addr),.wd_in(wd[m*256+:256]),.w_mask_in({256{1'b1}}),
   .rr_en(2'b0),.rr_addr(14'b0),.cr_en(2'b0),.cr_sel(16'b0));
 end endgenerate
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin
   push_p<=0;cr_p<=0;push_r<=0;cr_r<=0;c_wp<=0;c_rp<=0;c_unread<=0;c_ocr<=OCRV;c_ovf<=0;seal<=enc_r;
   bad_q<=0;fault_q<=0;ready_q<=0;ocr_nz<=(OCR!=0);v1<=0;v2<=0;v3<=0;out_v<=0;count_q<=0;w_ce_q<=0;
  end else begin
   push_r<=push;cr_r<=pop;push_p<=push_i;cr_p<=cr_i;
   fault_q<=fault_n;
   bad_q<=seal!=enc_c;
   if(!fault_q)begin
    c_wp<=n_wp;c_rp<=n_rp;c_unread<=n_unread;c_ocr<=n_ocr;c_ovf<=n_ovf;
    seal<=enc_n;
    ocr_nz<=n_ocr!=5'd0;
    count_q<=n_unread+{8'b0,fetch}+{8'b0,v1}+{8'b0,v2}+{8'b0,inflight};
   end
   ready_q<=!fault_n&&(n_unread<=RSV);
   w_ce_q<=put;
   v1<=fetch;v2<=v1&&!fault_q;v3<=v2&&!fault_q;
   out_v<=v3&&!fault_n;
  end
 // data registers: no reset, no enable (validity is carried by v1..v3 / out_v)
 always @(posedge clk)begin
  din_r<=din;din_p<=din_i;w_addr_q<=c_wp;wd_q<=ram_d;
  raw_q<=ram_q[647:0];
  raw2_q<=raw_q;syn_q<=syn_n;ovr_q<=ovr_n;ue_q<=|ue_n;
  out_q<=corr[544:0];
 end
 assign ready=ready_q;assign valid=out_v;assign dout=out_q;assign fault=fault_q;assign count=count_q;
`ifndef SYNTHESIS
 always @(posedge clk)if(rst_n&&!fault_q&&n_ocr>OCRV)$fatal(1,"PKT_CREDIT credit count out of range (return beyond OCR=%0d or fetch without credit)",OCR);
`endif
endmodule
