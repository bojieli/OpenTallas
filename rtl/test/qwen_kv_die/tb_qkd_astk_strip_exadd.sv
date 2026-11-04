`timescale 1ns/1ps
// HG-SPLIT 11-03 (DIE-KV-64 ruling: EX join fix): cosim A/B of the static ASTK strip.
//   A = qkd_astk_strip_st (original leaves, no cut).
//   B = qkd_astk_strip_st_exadd: the plan leaf ep variants (ep_0 = qkd_astk_ep_s_head_e, ep_1..7 = qkd_astk_ep_s_e) with EX
//       lanes 2, 3 behind CD relay registers each way and EX_ADD2/3 = 2 CD (FIX 1), so EXM = max(2 CD, PADX).
// Phase 1 (tb_qkd_astk_strip_st's functional stimulus: T 8192, 8,192 score words, M, Z calendar): B must raise no fault and
// match A edge for edge on ap / af / lt / si, except si's committed-e flags (si[568:537] an engine), which follow the Z
// return chain and must equal A's EXM edges later (not within EXM edges of a start, which clears both at once).
// Phase 2 faults (random words): af_b equals af_a at the same edge or EXM edges later (the join-path checks).  Phase 2: restart, T 600, random words (the same comparison).
// Must FAIL: FIX 0 (the cut without the fix), +define+KVD_STMUT=6 (DT not raised), =7 (near lanes not padded).
`ifndef KVD_STMUT
`define KVD_STMUT 0
`endif
module tb_qkd_astk_strip_exadd #(parameter integer CD = 2, parameter integer FIX = 1, parameter integer PADX = 0);
 localparam integer EXM = (PADX > 2*CD) ? PADX : 2*CD;
 localparam integer SW = 16;   // >= the aq -> ep start latency + the xd -> si register pair
 localparam integer EXP_AGE=500, LMAX_AGE=350, Z_AGE=1000, Z_STRIDE=16;
 function automatic [31:0] score_word(input integer eng,addr,head);
  score_word=32'h30000000 | (eng<<12) | (addr<<2) | head;
 endfunction
 reg ck=0,rst_n=0;always #1 ck=~ck;
 reg [539:0] aq=0;reg [35:0] am=0;reg [47:0] cal={16'(EXP_AGE),16'(Z_AGE),16'(LMAX_AGE)};
 reg [413*8-1:0] so=0;
 wire [633*8-1:0] si_a,si_b;wire [42:0] ap_a,ap_b;wire af_a,af_b;wire [20:0] lt_a,lt_b;
 qkd_astk_strip_st #(.RL(1),.Z_STRIDE(Z_STRIDE)) ua(.ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),.ck_e({8{ck}}),.ck_r(ck),
  .rst_n(rst_n),.st(2'd0),.aq(aq),.am(am),.cal(cal),.ap(ap_a),.af(af_a),.lt(lt_a),.so(so),.si(si_a));
 qkd_astk_strip_st_exadd #(.RL(1),.Z_STRIDE(Z_STRIDE),.CD(CD),.FIX(FIX),.PADX(PADX)) ub(.ck_c(ck),.ck_z({4{ck}}),.ck_x({32{ck}}),
  .ck_e({8{ck}}),.ck_r(ck),.rst_n(rst_n),.st(2'd0),.aq(aq),.am(am),.cal(cal),.ap(ap_b),.af(af_b),.lt(lt_b),.so(so),.si(si_b));
 // committed-e flags (32 b an engine) vs the rest of si
 reg [633*8-1:0] FM;integer n;
 initial begin FM=0;for(n=0;n<8;n=n+1)FM[633*n+537+:32]={32{1'b1}};end
 reg [633*8-1:0] sia_d [0:63];integer k;
 always @(posedge ck)begin for(k=63;k>0;k=k-1)sia_d[k]<=sia_d[k-1];sia_d[0]<=si_a;end
 reg [63:0] afa_d=0;integer since_start=0;
 always @(posedge ck)begin afa_d<={afa_d[62:0],af_a};since_start<=aq[0]?0:since_start+1;end
 integer cycle=0,errors=0,m_si=0,m_fl=0,m_ap=0,m_af=0,m_lt=0,afb=0,afa=0,fb=0;
 integer e_;
 always @(negedge ck)if(rst_n)begin
  cycle=cycle+1;
  if((si_b&~FM)!==(si_a&~FM))begin m_si=m_si+1;if(m_si<4)$display("MISMATCH cycle=%0d si (non-flag)",cycle);end
  // a start clears xd on both at the ep's own start edge (aq -> ep start latency SW): within SW + EXM edges of a start the
  // EXM-delayed reference still shows the pre-start flags, so there B's flags need only be a subset of A's (no stray set)
  if(cycle>EXM+2 && since_start>SW+EXM && (si_b&FM)!==(sia_d[EXM-1]&FM))begin m_fl=m_fl+1;if(m_fl<4)$display("MISMATCH cycle=%0d si committed flags (A delayed %0d)",cycle,EXM);end
  if(cycle>EXM+2 && since_start<=SW+EXM && (si_b&FM&~sia_d[EXM-1])!==0)begin m_fl=m_fl+1;if(m_fl<4)$display("MISMATCH cycle=%0d si committed flag set on B only near a start",cycle);end
  if(ap_b!==ap_a)begin m_ap=m_ap+1;if(m_ap<4)$display("MISMATCH cycle=%0d ap a=%h b=%h",cycle,ap_a,ap_b);end
  // the join / adder faults leave EXM edges later on B (its join is EXM later); the others at the same edge
  if(af_b!==af_a && af_b!==afa_d[EXM-1])begin m_af=m_af+1;if(m_af<4)$display("MISMATCH cycle=%0d af a=%b b=%b",cycle,af_a,af_b);end
  if(lt_b!==lt_a)begin m_lt=m_lt+1;if(m_lt<4)$display("MISMATCH cycle=%0d lt",cycle);end
 end
 reg chk=1;
 always @(negedge ck)if(rst_n&&chk)begin afa=afa|af_a;afb=afb|af_b;
  if(ub.g_ep[0].g_head.u_ep.f)fb=fb|1;
  for(e_=1;e_<8;e_=e_+1)begin end
 end
 genvar ge;
 generate for(ge=1;ge<8;ge=ge+1)begin:g_f
  always @(negedge ck)if(rst_n&&chk&&ub.g_ep[ge].g_body.u_ep.f)fb=fb|(1<<ge);
 end endgenerate
 integer t,i,h,seed=17;
 initial begin
  repeat(6)@(negedge ck);rst_n=1;repeat(10)@(negedge ck);
  aq[14:1]=8192;aq[0]=1;@(negedge ck);aq[0]=0;
  for(t=0;t<3500;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[413*i+:413]=0;so[413*i+410]=1;
    if(t>=40 && t<296)begin so[413*i+13]=1;so[413*i+14+:12]={1'b0,8'(t-40),3'(i)};
     for(h=0;h<4;h=h+1)so[413*i+26+32*h+:32]=score_word(i,t-40,h);end
    if(t>=1300&&t<3348&&((t-1300)%8==i))begin so[413*i]=1;so[413*i+1+:12]=12'(t-1300);end
   end
   am=0;
   if(t>=360&&t<364)am={32'd0,2'(t-360),1'b0,1'b1};
   @(negedge ck);
  end
  if(afa!==0)begin errors=errors+1;$display("FAIL reference A faulted in phase 1");end
  if(afb!==0||fb!==0)begin errors=errors+1;$display("FAIL B fault in phase 1 af=%b ep_f=%b",afb,fb);end
  chk=0;
  aq[14:1]=600;aq[0]=1;@(negedge ck);aq[0]=0;
  for(t=0;t<2500;t=t+1)begin
   for(i=0;i<8;i=i+1)begin
    so[413*i+:413]={13{$random(seed)}};so[413*i]=0;so[413*i+412]=(t==2400&&i==3);
    so[413*i+13]=(t<300)&&($random(seed)%3==0);
   end
   am=(t>=300&&t<304)?{$random(seed),2'(t-300),1'b0,1'b1}:36'd0;
   @(negedge ck);
  end
  if(m_si+m_fl+m_ap+m_af+m_lt!=0)begin errors=errors+1;$display("FAIL A/B mismatches si=%0d flags=%0d ap=%0d af=%0d lt=%0d",m_si,m_fl,m_ap,m_af,m_lt);end
  if(errors==0)$display("PASS qkd_astk_strip_exadd A/B: %0d edges, CD %0d FIX %0d PADX %0d EXM %0d mut %0d",cycle,CD,FIX,PADX,EXM,`KVD_STMUT);
  else $display("FAIL qkd_astk_strip_exadd errors=%0d CD %0d FIX %0d PADX %0d mut %0d",errors,CD,FIX,PADX,`KVD_STMUT);
  $finish;
 end
endmodule
