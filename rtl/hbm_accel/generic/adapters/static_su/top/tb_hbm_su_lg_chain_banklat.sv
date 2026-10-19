`timescale 1ns/1ps
`default_nettype none
// HBM-BANKLAT-SU 2026-10-19: LG tap CHAIN round trip against a pin-registered VM bank (d4g faces bank) + die lanes.
// Real RTL: 2 x ot_hbm_su_multirate_bridge (serial 900 / stream 1200, 3:4 phase-zero epoch, as pgslice MULTIRATE=1)
// -> 2 x ot_hbm_su_static_vm_bank_leaf -> ot_hbm_su_static_pg_lg_tap (SU tap) -> LQ/LR lane relays -> bank model;
// SU tap far port <- FQ/FR lanes <- ot_hgi_sfu_lg_pair_tap_leaf (SFU); SFU far <- HQ/HR lanes <- ot_hgi_sfu_lg_pair_tap_leaf_term (HC).
// Bank model (behavioural, the bank CONTRACT): rq/wq sampled at edge e; read answer register updated at e+6+PIN,
// write done at e+3+PIN (PIN 1 = hfd_vms_bank_native_q0_faces input pin flop; PIN 0 = ot_vms_bank_static n+6 / n+3).
// Traffic (static, compiler-style, time-partitioned so no select collides): phase A serial SU writes then reads (both
// bridges); phase B SFU writes then reads through the SU tap's far port; phase C HC writes then reads through SFU + SU.
// PASS needs: every fault output 0, every read datum exact (SU: at serial edge n+SRD exactly; SFU/HC: in order, count),
// every write done (SU at serial n+SWD). Calibration: PIN 0, lanes 0, 10/7 14/11 18/15 must PASS (the reference).
module tb_hbm_su_lg_chain_banklat;
 parameter integer PIN=1;
 parameter integer RR_SU=10, WR_SU=7, RR_SFU=14, WR_SFU=11, RR_HC=18, WR_HC=15;
 parameter integer LQ=0, LR=0;      // bank lanes per direction (rq/wq and rr/done), both banks (die-padded equal)
 parameter integer FQ=0, FR=0;      // SFU near -> SU far lanes, SU far -> SFU near lanes
 parameter integer HQ=0, HR=0;      // HC near -> SFU far, SFU far -> HC near
 localparam integer SRD=(3*RR_SU+18+3)/4, SWD=(3*WR_SU+18+3)/4;

 reg serial_clk=0, stream_clk=0, rst_n=0;
 initial begin #7; rst_n=1; end
 initial begin #12; forever begin stream_clk=1; #3; stream_clk=0; #3; end end
 initial begin #12; forever begin serial_clk=1; #4; serial_clk=0; #4; end end

 // ------------------------------------------------------------------ data patterns
 function automatic [255:0] pat(input integer tag, input integer h, input integer i);
  reg [255:0] d; begin for(integer k=0;k<8;k=k+1) d[k*32+:32]=32'(tag*1000003 + h*7919 + i*131 + k); pat=d; end
 endfunction
 function automatic [15:0] sec(input integer h, input integer i); sec=16'((i<<3)|h); endfunction   // QID 0, bank h
 localparam integer NA=96;
 // serial programme of bridge h at serial edge n: writes idx n (n<32), reads idx n-40 (40..71), reads init idx 200+ (72..79)
 function automatic [16:0] s_rq(input integer h, input integer n);
  if(n>=40 && n<72) s_rq={1'b1,sec(h,n-40)};
  else if(n>=72 && n<80) s_rq={1'b1,sec(h,200+n-72)};
  else s_rq=17'd0;
 endfunction
 function automatic [280:0] s_wq(input integer h, input integer n);
  if(n>=0 && n<32) s_wq={1'b1,sec(h,n),pat(1,h,n),8'hff}; else s_wq=281'd0;
 endfunction
 function automatic [256:0] s_want(input integer h, input integer n);   // serial_rr expected for source n
  if(n>=40 && n<72) s_want={1'b1,pat(1,h,n-40)};
  else if(n>=72 && n<80) s_want={1'b1,pat(0,h,200+n-72)};
  else s_want=257'd0;
 endfunction

 // ------------------------------------------------------------------ SU side: bridges + leaves + SU tap
 reg [2*17-1:0] ser_rq; reg [2*281-1:0] ser_wq;
 wire [2*257-1:0] ser_rr; wire [1:0] ser_done, br_fault, leaf_fault;
 wire [2*17-1:0] st_rq, lf_rq; wire [2*281-1:0] st_wq, lf_wq; wire [2*257-1:0] st_rr, lf_rr; wire [1:0] st_done, lf_done;
 for(genvar h=0;h<2;h=h+1)begin:g_h
  ot_hbm_su_multirate_bridge #(.READ_RETURN(RR_SU),.WRITE_RETURN(WR_SU)) u_br(.serial_clk(serial_clk),.stream_clk(stream_clk),
   .rst_n(rst_n),.serial_rq(ser_rq[h*17+:17]),.serial_wq(ser_wq[h*281+:281]),.serial_rr(ser_rr[h*257+:257]),
   .serial_done(ser_done[h]),.stream_rq(st_rq[h*17+:17]),.stream_wq(st_wq[h*281+:281]),.stream_rr(st_rr[h*257+:257]),
   .stream_done(st_done[h]),.fault(br_fault[h]));
  ot_hbm_su_static_vm_bank_leaf #(.QID(0),.B(h),.READ_RETURN(RR_SU),.WRITE_RETURN(WR_SU)) u_leaf(.clk(stream_clk),.rst_n(rst_n),
   .su_rq(st_rq[h*17+:17]),.su_wq(st_wq[h*281+:281]),.su_rr(st_rr[h*257+:257]),.su_w_done(st_done[h]),
   .lg_rq(lf_rq[h*17+:17]),.lg_wq(lf_wq[h*281+:281]),.lg_rr(lf_rr[h*257+:257]),.lg_w_done(lf_done[h]),.fault(leaf_fault[h]));
 end
 // the SU-level calendar selects: the slot the compiler gave the SU request (valid of the leaf request, same edge)
 wire [1:0] su_lread={lf_rq[17+16],lf_rq[16]}, su_lwrite={lf_wq[281+280],lf_wq[280]};
 wire [33:0] su_near_rq, su_far_rq; wire [561:0] su_near_wq, su_far_wq; wire [513:0] su_near_rr, su_far_rr;
 wire [1:0] su_near_done, su_far_done; wire su_fault;
 ot_hbm_su_static_pg_lg_tap #(.READ_RETURN(RR_SU),.WRITE_RETURN(WR_SU)) u_su(.clk_ctl(serial_clk),.pg_clk(stream_clk),
  .rst_n(rst_n),.local_rq(lf_rq),.far_rq(su_far_rq),.local_wq(lf_wq),.far_wq(su_far_wq),.local_read(su_lread),
  .local_write(su_lwrite),.near_rq(su_near_rq),.near_wq(su_near_wq),.near_rr(su_near_rr),.near_w_done(su_near_done),
  .local_rr(lf_rr),.far_rr(su_far_rr),.local_w_done(lf_done),.far_w_done(su_far_done),.fault(su_fault));

 // ------------------------------------------------------------------ bank lanes + bank models (banks 0, 1)
 wire [33:0] b_rq; wire [561:0] b_wq; wire [513:0] b_rr; wire [1:0] b_done;
 tb_lane #(34,LQ)  l_q (stream_clk, su_near_rq, b_rq);
 tb_lane #(562,LQ) l_w (stream_clk, su_near_wq, b_wq);
 tb_lane #(514,LR) l_r (stream_clk, b_rr, su_near_rr);
 tb_lane #(2,LR)   l_d (stream_clk, b_done, su_near_done);
 for(genvar h=0;h<2;h=h+1)begin:g_bank
  tb_bank_model #(.PIN(PIN),.H(h)) u_bank(.clk(stream_clk),.rq(b_rq[h*17+:17]),.wq(b_wq[h*281+:281]),.rr(b_rr[h*257+:257]),.done(b_done[h]));
 end

 // ------------------------------------------------------------------ SFU tap (+ its pair leaf) and HC term tap
 reg [33:0] sfu_crq=0, hc_crq=0; reg [561:0] sfu_cwq=0, hc_cwq=0; reg [1:0] sfu_lr=0, sfu_lw=0, hc_lr=0, hc_lw=0;
 wire [513:0] sfu_crr, hc_crr; wire [1:0] sfu_cdone, hc_cdone; wire sfu_fault, hc_fault;
 wire [33:0] sfu_near_rq, sfu_far_rq, hc_near_rq; wire [561:0] sfu_near_wq, sfu_far_wq, hc_near_wq;
 wire [513:0] sfu_near_rr, sfu_far_rr, hc_near_rr; wire [1:0] sfu_near_done, sfu_far_done, hc_near_done;
 ot_hgi_sfu_lg_pair_tap_leaf #(.READ_RETURN(RR_SFU),.WRITE_RETURN(WR_SFU)) u_sfu(.clk(stream_clk),.rst_n(rst_n),
  .c_rq(sfu_crq),.c_wq(sfu_cwq),.c_rr(sfu_crr),.c_w_done(sfu_cdone),.local_read(sfu_lr),.local_write(sfu_lw),
  .far_rq(sfu_far_rq),.far_wq(sfu_far_wq),.far_rr(sfu_far_rr),.far_w_done(sfu_far_done),
  .near_rq(sfu_near_rq),.near_wq(sfu_near_wq),.near_rr(sfu_near_rr),.near_w_done(sfu_near_done),.fault(sfu_fault));
 tb_lane #(34,FQ)  f_q (stream_clk, sfu_near_rq, su_far_rq);
 tb_lane #(562,FQ) f_w (stream_clk, sfu_near_wq, su_far_wq);
 tb_lane #(514,FR) f_r (stream_clk, su_far_rr, sfu_near_rr);
 tb_lane #(2,FR)   f_d (stream_clk, su_far_done, sfu_near_done);
 ot_hgi_sfu_lg_pair_tap_leaf_term #(.READ_RETURN(RR_HC),.WRITE_RETURN(WR_HC)) u_hc(.clk(stream_clk),.rst_n(rst_n),
  .c_rq(hc_crq),.c_wq(hc_cwq),.c_rr(hc_crr),.c_w_done(hc_cdone),.local_read(hc_lr),.local_write(hc_lw),
  .near_rq(hc_near_rq),.near_wq(hc_near_wq),.near_rr(hc_near_rr),.near_w_done(hc_near_done),.fault(hc_fault));
 tb_lane #(34,HQ)  h_q (stream_clk, hc_near_rq, sfu_far_rq);
 tb_lane #(562,HQ) h_w (stream_clk, hc_near_wq, sfu_far_wq);
 tb_lane #(514,HR) h_r (stream_clk, sfu_far_rr, hc_near_rr);
 tb_lane #(2,HR)   h_d (stream_clk, sfu_far_done, hc_near_done);

 // ------------------------------------------------------------------ serial driver + exact-edge serial checks
 integer sn=0, s_reads=0, s_writes=0, errors=0;
 always @(negedge serial_clk) for(integer h=0;h<2;h=h+1) begin ser_rq[h*17+:17]=s_rq(h,sn); ser_wq[h*281+:281]=s_wq(h,sn); end
 // the first serial edge (t=12) comes before any negedge: source 0 is preset (as tb_su_multirate)
 initial for(integer h=0;h<2;h=h+1) begin ser_rq[h*17+:17]=s_rq(h,0); ser_wq[h*281+:281]=s_wq(h,0); end
 always @(posedge serial_clk) if(rst_n) begin
  integer e; e=sn; #1;
  for(integer h=0;h<2;h=h+1) begin
   // valid must match exactly; data is compared when a return is due (an idle slot may carry stale data)
   if(ser_rr[h*257+256]!==s_want(h,e-SRD)>>256 || (ser_rr[h*257+256]===1'b1 && ser_rr[h*257+:257]!==s_want(h,e-SRD))) begin errors=errors+1;
    if(errors<6) $display("CHAIN_ERR su serial edge %0d bank %0d rr v=%b want v=%b data_ok=%b", e, h, ser_rr[h*257+256],
      s_want(h,e-SRD)>>256, ser_rr[h*257+:256]===s_want(h,e-SRD)); end
   else if(ser_rr[h*257+256]) s_reads=s_reads+1;
   if(ser_done[h]!==(s_wq(h,e-SWD)>>280)) begin errors=errors+1;
    if(errors<6) $display("CHAIN_ERR su serial edge %0d bank %0d done=%b", e, h, ser_done[h]); end
   else if(ser_done[h]) s_writes=s_writes+1;
  end
  sn=sn+1;
 end

 // ------------------------------------------------------------------ SFU / HC stream drivers (phases B, C) + checks
 localparam integer PB=420, PC=640;   // stream edges (serial phase A ends by stream ~ (NA+SRD)*4/3)
 integer pn=0, f_reads=0, f_writes=0, c_reads=0, c_writes=0;
 reg [256:0] qf[0:1][0:63], qc[0:1][0:63]; integer qfw[0:1], qfr[0:1], qcw[0:1], qcr[0:1];
 initial for(integer h=0;h<2;h=h+1) begin qfw[h]=0; qfr[h]=0; qcw[h]=0; qcr[h]=0; end
 integer f_wexp=0, c_wexp=0;
 always @(posedge stream_clk) if(rst_n) begin
  integer t; t=pn;
  // selects follow the request by the pair leaf's one edge
  sfu_lr <= {sfu_crq[17+16],sfu_crq[16]}; sfu_lw <= {sfu_cwq[281+280],sfu_cwq[280]};
  hc_lr <= {hc_crq[17+16],hc_crq[16]};    hc_lw <= {hc_cwq[281+280],hc_cwq[280]};
  for(integer h=0;h<2;h=h+1) begin
   // SFU: writes idx 64+k (k<16) at PB+k, reads idx 64+k at PB+40+k
   if(t>=PB && t<PB+16) begin sfu_cwq[h*281+:281] <= {1'b1,sec(h,64+t-PB),pat(2,h,t-PB),8'hff}; f_wexp=f_wexp+1; end
   else sfu_cwq[h*281+:281] <= 281'd0;
   if(t>=PB+40 && t<PB+56) begin sfu_crq[h*17+:17] <= {1'b1,sec(h,64+t-PB-40)}; qf[h][qfw[h]]={1'b1,pat(2,h,t-PB-40)}; qfw[h]=qfw[h]+1; end
   else if(t>=PB+56 && t<PB+60) begin sfu_crq[h*17+:17] <= {1'b1,sec(h,t-PB-56)}; qf[h][qfw[h]]={1'b1,pat(1,h,t-PB-56)}; qfw[h]=qfw[h]+1; end
   else sfu_crq[h*17+:17] <= 17'd0;
   // HC: writes idx 128+k at PC+k, reads idx 128+k at PC+40+k, then the SFU-written idx 64..67
   if(t>=PC && t<PC+16) begin hc_cwq[h*281+:281] <= {1'b1,sec(h,128+t-PC),pat(3,h,t-PC),8'hff}; c_wexp=c_wexp+1; end
   else hc_cwq[h*281+:281] <= 281'd0;
   if(t>=PC+40 && t<PC+56) begin hc_crq[h*17+:17] <= {1'b1,sec(h,128+t-PC-40)}; qc[h][qcw[h]]={1'b1,pat(3,h,t-PC-40)}; qcw[h]=qcw[h]+1; end
   else if(t>=PC+56 && t<PC+60) begin hc_crq[h*17+:17] <= {1'b1,sec(h,64+t-PC-56)}; qc[h][qcw[h]]={1'b1,pat(2,h,t-PC-56)}; qcw[h]=qcw[h]+1; end
   else hc_crq[h*17+:17] <= 17'd0;
   // returns (in order per bank)
   if(sfu_crr[h*257+256]) begin
    if(qfr[h]>=qfw[h] || sfu_crr[h*257+:257]!==qf[h][qfr[h]]) begin errors=errors+1; if(errors<6) $display("CHAIN_ERR sfu rr bank %0d #%0d edge %0d", h, qfr[h], t); end
    else f_reads=f_reads+1;
    qfr[h]=qfr[h]+1;
   end
   if(hc_crr[h*257+256]) begin
    if(qcr[h]>=qcw[h] || hc_crr[h*257+:257]!==qc[h][qcr[h]]) begin errors=errors+1; if(errors<6) $display("CHAIN_ERR hc rr bank %0d #%0d edge %0d", h, qcr[h], t); end
    else c_reads=c_reads+1;
    qcr[h]=qcr[h]+1;
   end
   if(sfu_cdone[h]) f_writes=f_writes+1;
   if(hc_cdone[h]) c_writes=c_writes+1;
  end
  pn=pn+1;
  if(pn==PC+200) begin
   integer bad; bad=errors;
   if(br_fault|leaf_fault) bad=bad+1;
   if(su_fault|sfu_fault|hc_fault) bad=bad+1;
   if(s_reads!=2*40 || s_writes!=2*32 || f_reads!=2*20 || f_writes!=2*16 || c_reads!=2*20 || c_writes!=2*16) bad=bad+1;
   $display("CHAIN %s PIN=%0d SU %0d/%0d SFU %0d/%0d HC %0d/%0d lanes bank %0d/%0d sfu %0d/%0d hc %0d/%0d SRD=%0d SWD=%0d | su r%0d w%0d sfu r%0d w%0d hc r%0d w%0d | faults bridge=%b leaf=%b su=%b sfu=%b hc=%b errors=%0d checks=%0d",
     bad==0?"PASS":"FAIL", PIN, RR_SU, WR_SU, RR_SFU, WR_SFU, RR_HC, WR_HC, LQ, LR, FQ, FR, HQ, HR, SRD, SWD,
     s_reads, s_writes, f_reads, f_writes, c_reads, c_writes, br_fault, leaf_fault, su_fault, sfu_fault, hc_fault, errors,
     s_reads+s_writes+f_reads+f_writes+c_reads+c_writes);
   $finish;
  end
 end
endmodule

// D registers (D=0: wire) -- one hbfd relay station per register
module tb_lane #(parameter integer W=1, parameter integer D=0)(input wire clk, input wire [W-1:0] d, output wire [W-1:0] q);
 if(D==0) begin:g_w assign q=d; end
 else begin:g_r
  reg [W-1:0] s [0:D-1];
  initial for(integer i=0;i<D;i=i+1) s[i]=0;
  always @(posedge clk) begin s[0]<=d; for(integer i=1;i<D;i=i+1) s[i]<=s[i-1]; end
  assign q=s[D-1];
 end
endmodule

// VM bank contract model: request sampled at edge e; read answer register updated at e+6+PIN; write commit (memory and
// done register) at e+3+PIN. Memory starts at pat(0,H,i).
module tb_bank_model #(parameter integer PIN=1, parameter integer H=0)(input wire clk, input wire [16:0] rq, input wire [280:0] wq,
                                                                 output wire [256:0] rr, output wire done);
 localparam integer LR=7+PIN, LW=4+PIN;    // rp[0] is the sample register (edge e); rp[LR-1] updates at e+6+PIN
 reg [255:0] mem [0:255];
 initial for(integer i=0;i<256;i=i+1) for(integer k=0;k<8;k=k+1) mem[i][k*32+:32]=32'(0*1000003 + H*7919 + i*131 + k);
 reg [256:0] rp [0:LR-1]; reg wp [0:LW-1]; reg [7:0] wa [0:LW-1]; reg [255:0] wd [0:LW-1];
 initial begin for(integer i=0;i<LR;i=i+1) rp[i]=0; for(integer i=0;i<LW;i=i+1) begin wp[i]=0; wa[i]=0; wd[i]=0; end end
 always @(posedge clk) begin
  rp[0] <= rq[16] ? {1'b1, mem[rq[10:3]]} : 257'd0;
  for(integer i=1;i<LR;i=i+1) rp[i] <= rp[i-1];
  wp[0] <= wq[280]; wa[0] <= wq[274:267]; wd[0] <= wq[263:8];
  for(integer i=1;i<LW;i=i+1) begin wp[i] <= wp[i-1]; wa[i] <= wa[i-1]; wd[i] <= wd[i-1]; end
  if(wp[LW-1]) mem[wa[LW-1]] <= wd[LW-1];
  if(rq[16] && rq[2:0]!=3'(H)) $display("CHAIN_ERR bank %0d got a request for bank %0d", H, rq[2:0]);
 end
 assign rr = rp[LR-1];
 assign done = wp[LW-1];
endmodule
`default_nettype wire
