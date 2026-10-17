`timescale 1ns/1ps
`default_nettype none
// ot_s81_pq_seq_slot (S-ELEM-B 2026-10-15): the die producer of the PQ issue face (dsfd_sp_pq_produced f_iss) on an S81
// layer die.  Static-cycle rule (owner 10-14 18:59): every PQ edge comes from the stage sequencer's compiled calendar.
//
//  * PQ engine slot = sequencer engine 11 (the layer die's spare engine; dsfd_stage_seq_static_c8 +define+DSFD_SSEQ_PQ11).
//    The sequencer command {slot,user10,pos21,tok21,arg24,op7} carries a PQ CLASS in arg[23:22]:
//      arg[23]=0           GO: forwarded to ot_s81_pq_command_endpoint with arg[23:22] cleared (descriptor index arg[21:0]);
//                          arg[22]=1 additionally pulses the PQ calendar stage_start on the same command edge.
//      arg[23]=1           CALENDAR PRIME: not forwarded; pulses calendar prime on the command edge and returns its own
//                          done {1,slot,op} at the FIXED edge command-pin + 3 (compiled row done = issue + 3).
//    prime / stage_start / forwarded command are combinational decodes of the sequencer pins; the endpoint and the calendar
//    reader pin-register them (PINREG 1), so GO / calendar timing is the produced bench's (0 added cycles).
//  * Descriptor image + calendar window: one real ot_rom_1024x72_m8 mask ROM (INSTANCE pq_desc_image), read once after
//    reset by a fixed counter (no handshake):  row0 = {cfg_ok[71], 0, length13[24:12], base12[11:0]};  rows 1.. =
//    {last[70], 0, pw35[34:0]} (the endpoint's PW36 word without its valid bit).  The ROM output is captured in flops
//    before any decode (macro clk->q never meets logic).  f_desc_pw = registered {1, pw35}, one word per edge; base /
//    length are static registers.  The compiler places the first PQ command after the boot image seal (c_st available).
//  * Faults (sticky, into c_st[0]): image row0 not cfg_ok, a row without last within 1023 rows, a PQ command before the
//    image is loaded, a prime-done colliding with an endpoint done on one edge (the compiler forbids it).
// MUT 1 (bench negative): prime done one edge late.  MUT 2: stage_start never pulsed.
module ot_s81_pq_seq_slot #(parameter integer MUT=0)(
 input wire ck,rst_n,
 input wire[84:0]s_cmd,output wire[8:0]s_done,output wire[1:0]s_st,
 output wire[84:0]ep_cmd,input wire[8:0]ep_done,input wire[1:0]ep_st,
 output wire[35:0]desc_pw,
 output wire cal_prime,cal_start,output reg[11:0]cal_base,output reg[12:0]cal_length,
 output wire image_loaded
);
 wire rst_r;
 ot_rst_relay #(.REGIONS(1),.SYNC_STAGES(2),.TREE_STAGES(1)) u_rr(.clk(ck),.rst_n_in(rst_n),.rst_n(rst_r));
 // ---- command class decode (sequencer pins -> endpoint / calendar pin flops) ----
 wire v=s_cmd[84];wire prime_cls=s_cmd[30];wire start_flag=s_cmd[29];
 assign ep_cmd={v&!prime_cls,s_cmd[83:31],2'b00,s_cmd[28:0]};
 assign cal_prime=v&prime_cls;
 assign cal_start=(MUT==2)?1'b0:(v&!prime_cls&start_flag);
 // ---- prime done at command pin + 3 (capture, output register) ----
 reg[8:0]pd1,pd2,pd3;reg fault;
 wire[8:0]prime_done=(MUT==1)?pd3:pd2;
 assign s_done=ep_done|prime_done;
 // ---- descriptor image loader: real mask ROM, fixed counter ----
 reg[9:0]ra;reg rd_v,cap_v,run,loaded,cfg_seen;reg[71:0]rq_q;reg[9:0]cap_a;reg[35:0]pw_q;
 wire[71:0]rq;reg[9:0]rd_a;
 ot_rom_1024x72_m8 #(.INSTANCE("pq_desc_image"))u_image(.clk(ck),.ce_in(run),.addr_in(ra),.rd_out(rq));
 assign desc_pw=pw_q;assign image_loaded=loaded;
 assign s_st={ep_st[1]&loaded&!fault,ep_st[0]|fault};
 always @(posedge ck or negedge rst_r)begin
  if(!rst_r)begin
   ra<=0;rd_v<=0;rd_a<=0;cap_v<=0;cap_a<=0;rq_q<=0;run<=1;loaded<=0;cfg_seen<=0;pw_q<=0;
   cal_base<=0;cal_length<=0;fault<=0;pd1<=0;pd2<=0;pd3<=0;
  end else begin
   // macro samples ra at this edge, rd_out valid after it; capture into rq_q on the next edge (pure flop)
   rd_v<=run;rd_a<=ra;if(run)ra<=ra+1'b1;
   cap_v<=rd_v&&run;cap_a<=rd_a;if(rd_v)rq_q<=rq;
   pw_q<=0;
   if(cap_v&&!loaded)begin
    if(cap_a==0)begin
     if(!rq_q[71])fault<=1;
     cfg_seen<=1;cal_base<=rq_q[11:0];cal_length<=rq_q[24:12];
    end else begin
     pw_q<={1'b1,rq_q[34:0]};
     if(rq_q[70])begin loaded<=1;run<=0;end
    end
   end
   if(run&&ra==10'h3ff)begin run<=0;if(!loaded)fault<=1;end
   if(v&&!loaded)fault<=1;
   pd1<={cal_prime,s_cmd[83],s_cmd[6:0]};pd2<=pd1[8]?pd1:9'd0;pd3<=pd2;
   if(prime_done[8]&&ep_done[8])fault<=1;
  end
 end
endmodule
`default_nettype wire
