// struct-close 2026-10-09 ("-cl" line, templates C + D): HEAD-PIPELINED successor of ot_ha2_truecredit_receiver_p.
// SAME module name and ports (a route / bench uses ONE of rxp.sv / rxph.sv; tools take OT_HA2_RXP_FILE).
// ha2_tccr_x1_hm10_79315a431 (rx_c, CREDIT=1): TT -105.7 / FF +5.0 / DRC 0; inputs +38.9, outputs +0.5; the ONLY failing
// class is reg->reg: rd_oh[r] (ONE flop per slot) -> 64:1 x 560-bit AND-OR head mux -> send_data (1,199 D pins).
// Change (HP=1): per-lane read-ring COPIES (one 64-bit copy per 40-bit slice of the queue word, keep_hierarchy so
// synthesis cannot merge them) and a REGISTERED two-level head: 8 partial heads (8:1 each, from the copies) are
// registered, then send_data <= OR of the 8 partials.  send_v is delayed one cycle with it (+1 cycle on the send
// side; return_v / return_tag / the tag check keep their timing: head_tag is still read combinationally from the
// master ring, 16 bits).  A popped slot is captured into the partials on the pop edge, before any later write can
// reuse it.  quiet also waits for the extra send stage.  HP=0 is the rxp.sv design.  HP acts only with CREDIT=1: the
// same-cycle ready contract (CREDIT=0) needs send_v one cycle after ready, so CREDIT=0 keeps the rxp.sv timing.
// Pipelined true-credit receiver (drive-1043-timing, 2026-10-08).
// Transaction-exact successor of ot_ha2_truecredit_receiver for the hardened rx block
// (W=544, INJ=2, 64-deep flop queue, ~73k flops). The original failed TT setup by -278 ps:
//   * arrival_tag pin -> tag compare -> push -> 35k-flop write enable (input budget 316 ps),
//   * rd pointer -> 64:1 x 560-bit read mux (reg2reg -219 ps),
//   * quiet/fault combinational to the output ports, rst_n pin -> 130 async flops.
// Changes (structural, no squeeze):
//   1. every arrival pin lands in a flop first (av_q/tag_q/data_q): +1 cycle on arrival;
//   2. queue write enable no longer waits for the tag compare: a slot is written whenever a
//      registered arrival is present and the queue is not full; the write pointer advances
//      only on a valid (tag-matching) arrival, so a rejected beat lands in a free slot that is
//      never read (slot wp is free unless full, and full is excluded);
//   3. one-hot write/read rings (registered) replace the binary decode; the read mux is AND-OR;
//   4. send_data loads the head every cycle (consumers sample it only with send_v);
//   5. quiet/fault are registered (lag one cycle; quiet stays covered by the sender's
//      outstanding credit, exactly as the original ignores a beat still on the arrival wire);
//   6. reset: rst_n asserts asynchronously, deasserts through one local flop per lane;
//      the arrival-valid flop keeps the raw reset so no beat after deassertion is lost.
// receiver_ready stays a same-cycle input (contract unchanged); it reaches ~100 control
// flops only (pop -> send_v/return_v/return_tag/rd ring/expect_retire/bad), not the data.
// MUTANT 2 corrupts the returned tag (as the original); MUTANT 4 misaligns the read ring.
//
// CREDIT (credit-ready, 2026-10-08; OWNER: credit-based ready accepted; default 0 = the same-cycle contract above).
// CREDIT=1 changes the meaning of receiver_ready[i]: it carries a one-cycle CREDIT-RETURN PULSE from the consumer
// (one pulse per item the consumer has freed from its buffer), not a level ready. The pulse lands in a pin flop
// (+1 cycle on the credit loop only); a per-lane counter starts at CRD (= the consumer's buffer depth, which must
// cover the credit round trip for full rate) and pop = !empty && cr_ok && !bad uses only registers (cr_ok is
// computed from the next counter value). A credit that would raise the counter above CRD (credit overflow) sets the
// sticky fault. idle additionally needs every credit home (counter == CRD, no pulse in the pin flop).
// MUTANT 5 starts the counter one above CRD (over-issue: the consumer buffer overflows).
module ot_ha2_truecredit_receiver_p #(
 parameter integer W=544, INJ=2, AW=6, TAGW=16, MUTANT=0,
 parameter integer CREDIT=0, CRD=8,
 parameter integer HP=1, RG=40
)(input wire clk,rst_n,
 input wire[INJ-1:0] arrival_v,receiver_ready,
 input wire[INJ*W-1:0] arrival_data,
 input wire[INJ*TAGW-1:0] arrival_tag,
 output reg[INJ-1:0] send_v,return_v,
 output reg[INJ*W-1:0] send_data,
 output reg[INJ*TAGW-1:0] return_tag,
 output reg quiet,fault);
 initial if(TAGW<=AW)$fatal(1,"HA2 truecredit tags must exceed slot address width");
 localparam integer D=1<<AW;
 localparam integer FW=W+TAGW;
 wire[INJ-1:0] bads,idle;
 for(genvar i=0;i<INJ;i=i+1)begin:g_lane
  // 6. local reset release
  reg rst_l;
  always @(posedge clk or negedge rst_n)if(!rst_n)rst_l<=1'b0;else rst_l<=1'b1;
  // 1. pin capture
  reg av_q;
  reg[TAGW-1:0] tag_q;
  reg[W-1:0] data_q;
  always @(posedge clk or negedge rst_n)if(!rst_n)av_q<=1'b0;else av_q<=arrival_v[i];
  always @(posedge clk)begin tag_q<=arrival_tag[i*TAGW+:TAGW];data_q<=arrival_data[i*W+:W];end
  // queue state
  reg[TAGW-1:0] expect_arrival,expect_retire;
  reg bad,ovf;
  reg[AW:0] wp,rp;
  reg[D-1:0] wr_oh,rd_oh;
  reg[FW-1:0] mem[0:D-1];
  wire empty=wp==rp;
  wire full=(wp[AW]!=rp[AW])&&(wp[AW-1:0]==rp[AW-1:0]);
  wire valid_arrival=av_q&&tag_q==expect_arrival&&!bad;
  // credit ready (CREDIT=1) or the same-cycle ready (CREDIT=0)
  localparam integer CRW=$clog2(CRD+2)+1;
  localparam integer CR0=CRD+((MUTANT==5)?1:0);
  wire cr_ok,cr_home,cr_ovf;
  wire pop=!empty&&cr_ok&&!bad;
  if(CREDIT!=0)begin:g_credit
   initial if(CRD<1)$fatal(1,"HA2 truecredit receiver CRD must be >= 1");
   reg cr_q,cr_ok_r,home_r,ovf_r;
   reg[CRW-1:0] cred;
   wire[CRW-1:0] cred_n=cred+CRW'(cr_q)-CRW'(pop);
   always @(posedge clk or negedge rst_l)
    if(!rst_l)begin cr_q<=1'b0;cred<=CRW'(CR0);cr_ok_r<=1'b1;home_r<=1'b1;ovf_r<=1'b0;end
    else begin
     cr_q<=receiver_ready[i];cred<=cred_n;cr_ok_r<=cred_n!=0;home_r<=cred_n==CRW'(CR0);
     if(cr_q&&!pop&&cred==CRW'(CR0))ovf_r<=1'b1;
    end
   assign cr_ok=cr_ok_r;assign cr_home=home_r&&!cr_q;assign cr_ovf=ovf_r;
  end else begin:g_ready
   assign cr_ok=receiver_ready[i];assign cr_home=1'b1;assign cr_ovf=1'b0;
  end
  // 3. AND-OR read mux over the registered one-hot read ring
  wire[D-1:0] rd_sel=(MUTANT==4)?{rd_oh[D-2:0],rd_oh[D-1]}:rd_oh;
  reg[FW-1:0] head;
  always @* begin
   head={FW{1'b0}};
   for(integer r=0;r<D;r=r+1)head=head|({FW{rd_sel[r]}}&mem[r]);
  end
  wire[TAGW-1:0] head_tag=head[W+:TAGW];
  // HP: registered two-level head over per-slice ring copies
  localparam integer NRG=(W+RG-1)/RG;
  wire[W-1:0] head_d;
  reg sv1;
  if(HP!=0&&CREDIT!=0)begin:g_hp
   reg[W-1:0] part_q[0:7];
   wire[D-1:0] rd_nx=pop?{rd_oh[D-2:0],rd_oh[D-1]}:rd_oh;
   for(genvar g=0;g<NRG;g=g+1)begin:g_rc
    localparam integer LO=g*RG;
    localparam integer GW=(W-LO<RG)?(W-LO):RG;
    wire[D-1:0] rcq;
    ot_ha2_rep_vec #(.N(D)) u_rc(.clk(clk),.rst_n(rst_l),.d(rd_nx),.q(rcq));
    wire[D-1:0] rc=(MUTANT==4)?{rcq[D-2:0],rcq[D-1]}:rcq;
    for(genvar k=0;k<8;k=k+1)begin:g_k
     reg[GW-1:0] p;
     always @* begin
      p={GW{1'b0}};
      for(integer r=k*(D/8);r<(k+1)*(D/8);r=r+1)p=p|({GW{rc[r]}}&mem[r][LO+:GW]);
     end
     always @(posedge clk)part_q[k][LO+:GW]<=p;
    end
   end
   assign head_d=part_q[0]|part_q[1]|part_q[2]|part_q[3]|part_q[4]|part_q[5]|part_q[6]|part_q[7];
  end else begin:g_nhp
   assign head_d=head[W-1:0];
  end
  // 2. write enable: registered arrival present, not full, one-hot slot
  wire wr=av_q&&!full;
  for(genvar r=0;r<D;r=r+1)begin:g_slot
   always @(posedge clk)if(wr&&wr_oh[r])mem[r]<={tag_q,data_q};
  end
  assign bads[i]=bad||ovf||cr_ovf;
  assign idle[i]=empty&&!av_q&&!send_v[i]&&!(HP!=0&&CREDIT!=0&&sv1)&&!return_v[i]&&cr_home;
  always @(posedge clk or negedge rst_l)
   if(!rst_l)begin
    expect_arrival<=0;expect_retire<=0;bad<=0;ovf<=0;wp<=0;rp<=0;
    wr_oh<={{(D-1){1'b0}},1'b1};rd_oh<={{(D-1){1'b0}},1'b1};
    send_v[i]<=0;return_v[i]<=0;return_tag[i*TAGW+:TAGW]<=0;sv1<=0;
   end else begin
    if(HP!=0&&CREDIT!=0)begin sv1<=pop;send_v[i]<=sv1;end else send_v[i]<=pop;
    return_v[i]<=pop;
    if(av_q&&!valid_arrival)bad<=1;
    if(valid_arrival)begin
     expect_arrival<=expect_arrival+1'b1;
     if(full)ovf<=1'b1;
     else begin wp<=wp+1'b1;wr_oh<={wr_oh[D-2:0],wr_oh[D-1]};end
    end
    if(pop)begin
     if(head_tag!=expect_retire)bad<=1;
     return_tag[i*TAGW+:TAGW]<=head_tag ^ ((MUTANT==2)?TAGW'(1):TAGW'(0));
     expect_retire<=expect_retire+1'b1;
     rp<=rp+1'b1;rd_oh<={rd_oh[D-2:0],rd_oh[D-1]};
    end
   end
  // 4. head loads every cycle
  always @(posedge clk)send_data[i*W+:W]<=head_d;
 end
 // 5. registered status
 always @(posedge clk or negedge rst_n)
  if(!rst_n)begin quiet<=1'b1;fault<=1'b0;end
  else begin quiet<=&idle;fault<=|bads;end
endmodule

// Replicated register vector; keep_hierarchy stops opt_merge from folding identical copies (struct-close 2026-10-09).
(* keep_hierarchy *)
module ot_ha2_rep_vec #(parameter integer N=1)(input wire clk,rst_n,input wire[N-1:0] d,output reg[N-1:0] q);
 always @(posedge clk or negedge rst_n)if(!rst_n)q<={{(N-1){1'b0}},1'b1};else q<=d;
endmodule
