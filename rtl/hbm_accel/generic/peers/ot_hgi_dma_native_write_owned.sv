`timescale 1ps/1fs
`default_nettype none
// One legacy mover WL post per edge, backed by its explicit per-lane LQ8
// reservation. Dequeue credits return per lane; commits serialize without loss.
module ot_hgi_dma_native_write_owned #(parameter integer MUT=0)(
 input wire clk,rst_n,input wire[63:0]leaf_clk,
 input wire[279:0]wl,input wire busy,
 output wire[31:0]wl_credit,output reg wl_done,
 input wire[3:0]wgrant,wack,output wire[3:0]wreq,drained,
 output wire[8991:0]native_wq,input wire[31:0]native_credit,native_done,
 output wire[65:0]fault
);
 reg[8960:0]legacy_q;wire[31:0]commits;wire[3:0]wd;wire[64:0]wf;
 reg[9:0]count,count_n;reg sf;reg[5:0]arrivals;
 always @*begin
  legacy_q=0;legacy_q[8960]=busy;
  legacy_q[wl[268:264]*280+:280]=wl;
  arrivals=0;for(integer l=0;l<32;l++)arrivals=arrivals+6'(commits[l]);
 end
 ot_hgi_sv_native_write_owned #(.LEGACY_SLOTS(8),.HARD_CLOCKS(1),.MUT(MUT)) writer(
  .clk(clk),.rst_n(rst_n),.leaf_clk(leaf_clk),.legacy_q(legacy_q),.legacy_credit(wl_credit),.legacy_done(commits),.legacy_grant(),
  .wgrant(wgrant),.wack(wack),.wreq(wreq),.drained(wd),.released(),
  .native_wq(native_wq),.native_credit(native_credit),.native_done(native_done),.fault(wf));
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin count<=0;count_n<='1;sf<=0;wl_done<=0;end
  else begin
   reg[10:0]n;n={1'b0,count}+11'(arrivals)-11'(count!=0);
   count<=n[9:0];count_n<=~n[9:0];wl_done<=count!=0;
   if(count!=~count_n||n>64)sf<=1; // native mover KOUT64 bounds outstanding commits
  end
 end
 assign drained=wd&{4{count==0&&!wl_done&&!wl[279]&&!busy}};
 assign fault={sf,wf};
endmodule
`default_nettype wire
