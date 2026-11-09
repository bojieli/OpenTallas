`timescale 1ns/1ps
// Mechanism cut of the actual dsdv_svc_rs_c fold state machine. Arithmetic,
// SX transport and owner parser are separate gates; only folded frame edges
// and exact P-bit placement are checked here. Source: codex/svc-rtl-0222.
module svc_h8_pfold_cut(input ck,rn,go,rtp,input[1075:0]rt_d,input[9:0]tjob,input[7:0]tagj,output reg pp_v,output reg[512:0]pp_d,output reg p_f);
 localparam H=8,LW=1076,P2=1;
 reg sek,pl_v;reg[5:0]pb_n;reg[7:0]pk;
 wire pfire=0,l_v=0,sm_st=0,w_v=0,pb_w=0,pinj=0;wire[1:0]hst=0;wire[3:0]sm_kind=0;
    function automatic [64*H-1:0] pbeat(input [LW-1:0] b);
        for (int jj = 0; jj < 4; jj++) for (int h = 0; h < H; h++) pbeat[16*(H*jj + h) +: 16] = b[4*H + 32*(H*jj + h) + 16 +: 16];
    endfunction
    function automatic bad_beat(input [LW-1:0] b);
        bad_beat = |b[4*H-1:0];
        for (int l = 0; l < 4*H; l++) if (b[4*H + 32*l +: 16] != 16'h0000) bad_beat = 1'b1;
    endfunction
    wire [9:0] pn = P2 ? (tjob + 10'd3) >> 2 : (tjob + 10'd1) >> 1;   // words of the job's PV frame

    reg [1:0] pph; reg phd; reg [9:0] pwc; reg [64*H-1:0] phold;
    always @(posedge ck or negedge rn)
        if (!rn) begin sek <= 1'b0; pb_n <= 6'd0; pk <= 8'd0; pl_v <= 1'b0; pph <= 2'd0; phd <= 1'b0; pwc <= 10'd0; pp_v <= 1'b0; p_f <= 1'b0; end
        else begin
            if (sm_st) begin sek <= sm_kind == 4'd4; if (sm_kind == 4'd4) pb_n <= 6'd0; end
            else if (pb_w) pb_n <= pb_n + 1'b1;
            if (w_v && sek && pb_n == 6'd40) p_f <= 1'b1;                          // more e rows than pbuf holds
            pl_v <= pfire;
            if (go) pk <= 8'd0; else if (pfire) pk <= pk + 1'b1;
            if (pfire && {2'b00, pb_n} <= {2'b00, pk[7:2]}) p_f <= 1'b1;             // the beat's e row is not in pbuf yet
            if (pl_v && l_v) p_f <= 1'b1;                                           // a P beat on an engine score beat
            pp_v <= 1'b0;
            if (go) begin pph <= 2'd0; phd <= 1'b0; pwc <= 10'd0; end
            else if (P2) begin
                // R5 H 8: one PV word a beat, emitted the cycle after the beat (header on the first beat)
                if (rtp) begin
                    if (bad_beat(rt_d)) p_f <= 1'b1;
                    if (!phd) begin pp_v <= 1'b1; phd <= 1'b1; pph <= 2'd1; end
                    else if (pph == 2'd0) pph <= 2'd1;
                    else p_f <= 1'b1;                                               // off the 2-cycle cadence
                end else if (pph == 2'd1) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd0; end
            end
            else if (rtp) begin
                if (bad_beat(rt_d)) p_f <= 1'b1;                                    // a lane that is not an exact BF16
                if (!phd) begin pp_v <= 1'b1; phd <= 1'b1; pph <= 2'd1; end         // header
                else if (pph == 2'd2) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd1; end
                else p_f <= 1'b1;                                                   // off the 2-cycle cadence
            end else if (pph == 2'd1) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd2; end
            else if (pph == 2'd2) begin pp_v <= pwc < pn; pwc <= pwc + 1'b1; pph <= 2'd0; end
            if (pinj && hst[0]) p_f <= 1'b1;                                        // an injected word on a host q word
        end
    always @(posedge ck) begin
        if (rtp) phold <= pbeat(rt_d);
        if (rtp && !phd) pp_d <= {1'b0, 4'd5, 1'b0, 4'b0001, tagj, 3'd0, 12'(pn), 480'd0};
        else if (pph == 2'd1 || P2) pp_d <= {1'b0, phold[511:0]};
        else pp_d <= {1'b0, phold[64*H-1 -: 512]};
    end

endmodule
module tb_svc_h8_pfold;
 reg ck=0;always#0.5 ck=~ck;reg rn=0,rtp=0;reg[1075:0]rt_d=0;
 wire pp_v,p_f;wire[512:0]pp_d;
 integer cyc=0,n=0,err=0,first=-1,last=-1,mut=0;
 reg[511:0]gold[0:31];
 svc_h8_pfold_cut u(ck,rn,1'b0,rtp,rt_d,10'd128,8'h21,pp_v,pp_d,p_f);
 initial begin
  void'($value$plusargs("mut=%d",mut));
  for(integer k=0;k<32;k++)for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)gold[k][16*(r*8+h)+:16]=16'(16'h3f00+k*32+r*8+h);
 end
 always@(posedge ck)begin
  cyc<=cyc+1;
  if(pp_v)begin
   if(first<0)first=cyc;
   if(n==0)begin if(pp_d[511:508]!=5||pp_d[491:480]!=32)err++;end
   else begin
    if(pp_d[511:0]!==gold[n-1])err++;
    if(cyc!=first+2*n-1)err++;
   end
   last=cyc;n++;
  end
  if(cyc==100)begin
   $display("H8_PFOLD mut=%0d words=%0d first=%0d last=%0d errors=%0d fault=%0d",mut,n,first,last,err,p_f);
   if(n==33&&first==21&&last==84&&err==0&&!p_f)$display("H8_PFOLD PASS");else $display("H8_PFOLD FAIL");$finish;
  end
 end
 always@(negedge ck)begin
  rn=cyc>=5;rtp=0;rt_d=0;
  if(cyc>=20&&cyc<84&&((cyc-20)%2==0))begin
   rtp=1;rt_d[1075:1060]=16'(2*(cyc-20));rt_d[1059:1056]=4'hf;
   for(integer r=0;r<4;r++)for(integer h=0;h<8;h++)rt_d[32+32*(r*8+h)+:32]={gold[(cyc-20)/2][16*(r*8+h)+:16],16'd0};
   if(mut==1&&cyc==20)rt_d[48]=~rt_d[48];
  end
 end
endmodule
