`timescale 1ps/1ps
`default_nettype none
// HBM-SU3 2026-10-17: ot_hbm_su_static_cxport_split (4 delivery leaves + inject leaf + RED_CARRY leaf) in lockstep with
// the hub ot_hbm_su_static_cxport at the die parameters (INJ_RET 11, RQ/RQC/SD 0), QID 2 and QID 0 (B39_NOOP 1).
// Serial 4 / stream 3 quanta on one lattice; rst_n released between a common edge pair (phase zero).
// Random traffic on every input under the compiler calendar: no SU-bound valid at stream phase 2, delivery lane j only
// to slice j; addresses mostly inside the aperture (out-of-aperture and phase-2 valids in later phases exercise faults).
// Every output bit (inj_d, rc_*, dw_*, rr_w*, fault) equal (!==) at every edge of both clocks; the split's SFU operand
// is commanded one serial edge later (red_sel delayed, the compiler's E+1 rule): its sfu_x equals the hub's sfu_x of the
// previous serial edge, and an ro_v fault may report one serial edge later.
// MUT (both sides): 1/2/3/4 change both identically -> must still PASS (sanity) unless MUTONE=1 (split only) -> FAIL.
module tb_hbm_su_cxport_split;
 parameter integer QID=2, B39=0, MUT=0, MUTONE=0, NRST=3, EDGES=4000, OBR=0;  // OBR: ij_s seam pin registers (TW2-NATIVE-IJS 10-19)
 localparam integer TS=1200, TP=900, T0=600;
 reg clk_q=0, clk_s=0;
 initial begin #(T0); forever begin clk_q=1; #(TS/2); clk_q=0; #(TS/2); end end
 initial begin #(T0); forever begin clk_s=1; #(TP/2); clk_s=0; #(TP/2); end end
 reg rst_n=0, active=0, viol=0, legal=0;
 reg [1:0] inj_rd; reg [159:0] inj_addr; reg [3:0] del_valid; reg [2179:0] del_flit; reg [159:0] del_obase;
 reg rr_v; reg [2:0] rr_tag; reg [255:0] rr_d; reg [4095:0] inj_q; reg red_sv; reg [31:0] red_tag, red_x;
 reg [15:0] ro_v; reg [511:0] ro_x; reg [11:0] red_sel;
 integer sph=0;  // stream phase as the DUT sees it (edges since release)
 always @(posedge clk_s) sph <= rst_n ? (sph+1)%4 : 0;
 function automatic [39:0] saddr(input integer g, input integer bad);
  reg [39:0] a; begin a=0; a[2:0]=0; a[3]=$urandom; a[5:4]=g; a[6]=$urandom; a[15:7]=$urandom; a[17:16]=QID;
   if(B39 && ($urandom%5)==0) a[39]=1; if(bad) a[17:16]=QID^1; saddr=a; end endfunction
 function automatic [39:0] daddr(input integer j, input integer bad);
  reg [39:0] a; begin a=0; a[5:4]=j; a[6]=$urandom; a[15:7]=$urandom; a[17:16]=QID; if(bad) a[3:0]=1; daddr=a; end endfunction
 integer i;
 always @(negedge clk_s) begin
  if(active && (sph!=2 || viol)) begin      // sph = the DUT phase counter seen by the next stream edge (never 2)
   inj_rd=$urandom; for(i=0;i<4;i=i+1) begin inj_addr[40*i+:40]=saddr($urandom%4, viol && ($urandom%50)==0); if(i%2) inj_addr[40*i+39]=1'b0; end
   del_valid=$urandom;
   for(i=0;i<4;i=i+1) begin del_obase[40*i+:40]=daddr(i, viol && ($urandom%50)==0);
    del_flit[545*i+:545]={1'b1,32'($urandom),{16{32'($urandom)}}}; if(viol && ($urandom%60)==0) del_flit[545*i+544]=0; end
   rr_v=!legal && ($urandom%3)==0; rr_tag=$urandom; for(i=0;i<8;i=i+1) rr_d[32*i+:32]=$urandom;
   ro_v=legal ? 16'd0 : 16'($urandom); for(i=0;i<16;i=i+1) ro_x[32*i+:32]=$urandom;
  end else begin inj_rd=0; del_valid=0; rr_v=0; ro_v=0; end
 end
 always @(negedge clk_q) begin
  if(active) begin
   for(i=0;i<128;i=i+1) inj_q[32*i+:32]=$urandom;
   red_sv=!legal && ($urandom%3)==0; red_x=$urandom;
   red_tag=0; red_tag[9]=$urandom; red_tag[12:10]=$urandom; red_tag[13]=($urandom%4)==0; red_tag[16:14]=$urandom;
   red_tag[17]=$urandom; red_tag[22:18]=$urandom; red_tag[23]=$urandom;
   red_sel={!legal && ($urandom%3)==0,3'($urandom),1'($urandom),7'($urandom)};
  end else begin red_sv=0; red_sel=0; end
 end
 initial begin inj_rd=0; inj_addr=0; del_valid=0; del_flit=0; del_obase=0; rr_v=0; rr_tag=0; rr_d=0; inj_q=0; red_sv=0;
  red_tag=0; red_x=0; ro_v=0; ro_x=0; red_sel=0; end
 wire [1023:0] h_ij, s_ij; wire h_rcv, s_rcv; wire [2:0] h_rct, s_rct; wire [255:0] h_rcd, s_rcd;
 wire [7:0] h_dwv, s_dwv; wire [71:0] h_dwr, s_dwr; wire [4095:0] h_dwd, s_dwd; wire h_rrv, s_rrv; wire [4:0] h_rra, s_rra;
 wire [255:0] h_rrd, s_rrd; wire [31:0] h_sfu, s_sfu; wire h_f, s_f;
 ot_hbm_su_static_cxport #(.QID(QID),.B39_NOOP(B39),.INJ_RET(11),.MUT(MUTONE?0:MUT)) hub(.clk_s(clk_s),.clk_q(clk_q),.rst_n(rst_n),
  .inj_rd(inj_rd),.inj_addr(inj_addr),.inj_d(h_ij),.del_valid(del_valid),.del_flit(del_flit),.del_obase(del_obase),
  .rc_v(h_rcv),.rc_tag(h_rct),.rc_d(h_rcd),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.inj_q(inj_q),.dw_v(h_dwv),.dw_row(h_dwr),
  .dw_d(h_dwd),.red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.rr_wv(h_rrv),.rr_wa(h_rra),.rr_wd(h_rrd),.ro_v(ro_v),
  .ro_x(ro_x),.red_sel(red_sel),.sfu_x(h_sfu),.fault(h_f));
 reg [11:0] red_sel_d = 12'd0; always @(posedge clk_q) red_sel_d <= red_sel;   // E+1 SFU-operand rule
 ot_hbm_su_static_cxport_split #(.QID(QID),.B39_NOOP(B39),.INJ_RET(11),.MUT(MUT),.OBR(OBR)) spl(.clk_s(clk_s),.clk_q(clk_q),.rst_n(rst_n),
  .inj_rd(inj_rd),.inj_addr(inj_addr),.inj_d(s_ij),.del_valid(del_valid),.del_flit(del_flit),.del_obase(del_obase),
  .rc_v(s_rcv),.rc_tag(s_rct),.rc_d(s_rcd),.rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.inj_q(inj_q),.dw_v(s_dwv),.dw_row(s_dwr),
  .dw_d(s_dwd),.red_sv(red_sv),.red_tag(red_tag),.red_x(red_x),.rr_wv(s_rrv),.rr_wa(s_rra),.rr_wd(s_rrd),.ro_v(ro_v),
  .ro_x(ro_x),.red_sel(red_sel_d),.sfu_x(s_sfu),.fault(s_f));
 wire [6000:0] oh={h_ij,h_rcv,h_rct,h_rcd,h_dwv,h_dwr,h_dwd,h_rrv,h_rra,h_rrd};
 wire [6000:0] os={s_ij,s_rcv,s_rct,s_rcd,s_dwv,s_dwr,s_dwd,s_rrv,s_rra,s_rrd};
 reg [31:0] h_sfu_q; reg h_f_q=0; integer sfn=0, flag=0;
 always @(posedge clk_q) if(cmp) begin #2; if((^h_sfu_q)!==1'bx && s_sfu!==h_sfu_q) begin errors=errors+1; if(errors<6) $display("SFU MISMATCH t=%0t %h/%h", $time, s_sfu, h_sfu_q); end
  sfn=sfn+1; h_sfu_q=h_sfu; end else h_sfu_q=h_sfu;
 // HBM-SU6: a bit the hub leaves X (inject word before the first written slot: the hub's unreset g/b select reads X)
 // may be defined in the split (its one-hot select is reset); every hub-defined bit must still match exactly.
 function automatic hub_def_diff(input [6000:0] h, input [6000:0] s);
  integer b; begin hub_def_diff=0; for(b=0;b<=6000;b=b+1) if(h[b]!==1'bx && h[b]!==s[b]) hub_def_diff=1; end
 endfunction
 integer checks=0, errors=0, cmp=0, dwn=0, ijn=0, rcn=0, rrn=0, fn=0, legal_f=0;
 always @(posedge clk_s or posedge clk_q) if(cmp) begin
  #1; checks=checks+1; dwn=dwn+((|h_dwv)===1'b1); ijn=ijn+((|h_ij)===1'b1); if(legal && h_f) begin legal_f=legal_f+1; if(legal_f==1) $display("DBG first legal fault t=%0t sfs %b ibad %b dbad %b rbad %b robad %b", $time, hub.sfault_s, hub.ibad, hub.dbad, hub.rbad, hub.ro_bad); end rcn=rcn+h_rcv; rrn=rrn+h_rrv; fn=fn+h_f;
  if(h_f!==s_f && !(h_f===1'b1 && s_f===1'b0 && h_f_q===1'b0)) begin errors=errors+1; if(errors<6) $display("FAULT MISMATCH t=%0t %b/%b", $time, h_f, s_f); end
  else if(h_f!==s_f) flag=flag+1;
  h_f_q=h_f;
  if(oh!==os && hub_def_diff(oh,os)) begin errors=errors+1;
   if(errors<6) $display("MISMATCH t=%0t ij %0d rc %0d dw %0d/%0d/%0d rr %0d sfu %0d fault %b/%b", $time, h_ij!==s_ij,
    {h_rcv,h_rct,h_rcd}!=={s_rcv,s_rct,s_rcd}, h_dwv!==s_dwv, h_dwr!==s_dwr, h_dwd!==s_dwd, {h_rrv,h_rra,h_rrd}!=={s_rrv,s_rra,s_rrd}, h_sfu!==s_sfu, h_f, s_f); end
 end
 integer k;
 initial begin
  for(k=0;k<NRST;k=k+1) begin
   rst_n=0; cmp=0; active=0; viol=(k==NRST-1); legal=(k==0);
   repeat(4) @(posedge clk_q);
   while((($time-T0)%(3*TS)) != 2*TS) @(posedge clk_q);   // serial edge E0-4q; release at E0-150 (after stream E0-3q)
   #(TS-150); rst_n=1;
   repeat(2) @(negedge clk_q); cmp=1; active=1;
   repeat(EDGES) @(negedge clk_q);
   active=0; repeat(30) @(negedge clk_q);
  end
  if(errors==0 && legal_f==0 && checks>NRST*EDGES && dwn>0 && ijn>0 && rcn>0 && rrn>0 && fn>0)
   $display("CXPORT_SPLIT PASS checks=%0d dw=%0d inj=%0d rc=%0d rr=%0d sfu_checks=%0d fault_lags=%0d fault_edges=%0d", checks, dwn, ijn, rcn, rrn, sfn, flag, fn);
  else $display("CXPORT_SPLIT FAIL legal_phase_faults=%0d errors=%0d checks=%0d dw=%0d inj=%0d rc=%0d rr=%0d fault_edges=%0d", legal_f, errors, checks, dwn, ijn, rcn, rrn, fn);
  $finish;
 end
endmodule
`default_nettype wire
