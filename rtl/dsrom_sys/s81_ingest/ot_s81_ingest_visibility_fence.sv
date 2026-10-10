`timescale 1ns/1ps
// True controller host-write completions (ack_n) are counted in ck. A held
// snapshot crosses into clk_h using a toggle/ack MCP handshake, so multi-event
// increments cannot tear a Gray word. Done count is the engine cumulative
// sector count. Credits and SECDED completion storage are finite and protected.
// strip-protect 2026-10-09 (REVIEW_20261009 S4/X3): PROTECT=0 (default) removes the rejected flop-level protection;
// PROTECT=1 is the original, bit for bit.  Fault-free behaviour is identical (physical/strip_protect/bench.py).
// PROTECT=0: the 8-entry FLOP queue stores the raw 64-bit word (SECDED is for SRAM only, X2) and the pointer/credit/
// commit/snapshot/landed parity bits are not checked.  The add-overflow, snapshot-monotonic and credit range checks stay.
// PIPE=1 (sys-takeover 2026-10-09, opt-in; dsfd_host_native TT -194: the 8:1 head mux -> landed compare -> pop -> queue
// write enable / out_d / fh in one clk_h edge, 37-40 levels): the head's release condition is a REGISTER (hr_q), computed
// from the current state and cleared on the edge of every pop and while the queue is empty, so it can only be late
// (landed only grows); the overflow fault no longer looks at the pop (the sender's credits make count == 8 with in_v
// impossible).  +1 clk_h edge per completion word (the pop after a pop waits one edge).
// PIPE=2 (sys-takeover 2026-10-09, hostnative_pipe_a TT -47: landed -> snapshot < landed compare -> landed, 39 levels):
// PIPE 1 plus the monotonic check registered (snap_lt_q, computed every edge from the held snapshot: snapshot is written
// before req toggles and stays until the handshake, so the registered compare at the handshake edge is current).
module ot_s81_ingest_visibility_fence #(parameter integer ENABLE=0,PROTECT=0,PIPE=0)(
 input wire rst_n,ck,clk_h,input wire[7:0] ack_n,
 input wire in_v,input wire[63:0] in_d,output reg in_cr,
 output reg out_v,output reg[63:0] out_d,input wire out_cr,
 output wire fault,output wire[31:0] landed_debug
);
 generate if(!ENABLE)begin:g_off
  assign fault=0;assign landed_debug=0;
  always @(*)begin in_cr=0;out_v=0;out_d=0;end
 end else begin:g_on
  reg[31:0] commits,snapshot;reg commit_p,snapshot_p,req;
  reg ack_host,ac1,ac2;reg fc;
  wire[32:0] add={1'b0,commits}+ack_n;
  always @(posedge ck or negedge rst_n)begin
   if(!rst_n)begin commits<=0;snapshot<=0;commit_p<=0;snapshot_p<=0;req<=0;ac1<=0;ac2<=0;fc<=0;end
   else begin
    ac1<=ack_host;ac2<=ac1;
    if((PROTECT&&(commit_p!=(^commits)||snapshot_p!=(^{snapshot,req})))||add[32])fc<=1;
    if(!fc)begin
     commits<=add[31:0];commit_p<=^add[31:0];
     if(req==ac2&&commits!=snapshot)begin snapshot<=commits;req<=~req;snapshot_p<=^{commits,~req};end
    end
   end
  end
  reg rc1,rc2,fc1,fc2;reg[31:0] landed;reg landed_p,fh;reg snap_lt_q;
  always @(posedge clk_h) snap_lt_q<=snapshot<landed;
  localparam integer QW=PROTECT?72:64;
  reg[QW-1:0] q[0:7];reg[2:0] wp,rp;reg[3:0] count;reg qp;
  reg[2:0] host_credits;reg hp;
  wire[QW-1:0] encoded;wire[63:0] head;wire corrected,uncorrectable;
  if(PROTECT)begin:g_ecc
   ot_s81_secded_enc72 enc(in_d,encoded);
   ot_s81_secded_dec72 dec(q[rp],head,corrected,uncorrectable);
  end else begin:g_raw
   assign encoded=in_d;assign head=q[rp];assign corrected=1'b0;assign uncorrectable=1'b0;
  end
  wire is_done=head[63:56]==8'h01;
  wire bad_q=PROTECT&&(qp!=(^{wp,rp,count}));wire bad_h=PROTECT&&(hp!=(^host_credits));
  wire bad_land=PROTECT&&(landed_p!=(^landed));
  wire hr_now=count!=0&&(!is_done||landed>=head[31:0]);
  reg hr_q;
  wire pop=(PIPE!=0)?(hr_q&&host_credits!=0&&!fh&&!fc2&&!bad_q&&!bad_h&&!bad_land&&!uncorrectable):
       (count!=0&&host_credits!=0&&!fh&&!fc2&&!bad_q&&!bad_h&&!bad_land&&!uncorrectable&&(!is_done||landed>=head[31:0]));
  always @(posedge clk_h or negedge rst_n)
   if(!rst_n)hr_q<=1'b0;
`ifdef OT_FENCE_MUT_HRSTALE
   else hr_q<=hr_now;                                  // mutant: release flag not cleared on a pop (next head unchecked)
`else
   else hr_q<=hr_now&&!pop;
`endif
  assign fault=fc2|fh;assign landed_debug=landed;
  reg[2:0] nw,nr,nh;reg[3:0] nc;
  always @(posedge clk_h or negedge rst_n)begin
   if(!rst_n)begin rc1<=0;rc2<=0;ack_host<=0;fc1<=0;fc2<=0;landed<=0;landed_p<=0;fh<=0;
    wp<=0;rp<=0;count<=0;qp<=0;host_credits<=4;hp<=1;in_cr<=0;out_v<=0;out_d<=0;
   end else begin
    rc1<=req;rc2<=rc1;fc1<=fc;fc2<=fc1;in_cr<=0;out_v<=0;
    if(rc2!=ack_host)begin
`ifdef OT_FENCE_MUT_LTSTALE
     if((PROTECT&&snapshot_p!=(^{snapshot,rc2}))||((PIPE>=2)?1'b0:(snapshot<landed)))fh<=1;   // mutant: monotonic check dropped
`else
     if((PROTECT&&snapshot_p!=(^{snapshot,rc2}))||((PIPE>=2)?snap_lt_q:(snapshot<landed)))fh<=1;
`endif
     else begin landed<=snapshot;landed_p<=^snapshot;end
     ack_host<=rc2;
    end
    if(bad_q||bad_h||bad_land||(count!=0&&uncorrectable))fh<=1;
    nw=wp;nr=rp;nc=count;nh=host_credits;
    if(!fh&&!fc2&&!bad_q&&!bad_h&&!bad_land)begin
     if(in_v)begin
      if(count==8&&(PIPE!=0||!pop))fh<=1;
      else begin q[wp]<=encoded;nw=wp+1'b1;nc=nc+1'b1;end
     end
     if(out_cr)begin if(host_credits==4&&!pop)fh<=1;else nh=host_credits+1'b1;end
     if(pop)begin
      out_v<=1;out_d<=head;in_cr<=1;nr=rp+1'b1;nc=nc-1'b1;nh=nh-1'b1;
     end
    end
    wp<=nw;rp<=nr;count<=nc;qp<=^{nw,nr,nc};host_credits<=nh;hp<=^nh;
    if(fh||fc2||bad_q||bad_h||bad_land)begin out_v<=0;in_cr<=0;end
   end
  end
 end endgenerate
endmodule
