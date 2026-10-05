`timescale 1ps/1fs
// Two-entry Gray FIFO; actual data storage and synchronizer bits enumerated.
// No unilateral reset credit: either reset flushes both domains.
module ot_hbm_r14_fifo2 #(parameter integer WIDTH=471)(
 input wire wc,wrn,wv,output wire wr,input wire [WIDTH-1:0] wd,
 input wire rc,rrn,output wire rv,input wire rr,output wire [WIDTH-1:0] rd);
 reg [WIDTH-1:0] mem[0:1];
 reg [1:0] wb,wg,rb,rg,rgw1,rgw2,wgr1,wgr2;
 reg [1:0] wrsync,rrsync;reg won,ron,ronw1,ronw2,wonr1,wonr2;
 wire arst=wrn&&rrn;
 always @(posedge wc or negedge arst) if(!arst) wrsync<=0;else wrsync<={wrsync[0],1'b1};
 always @(posedge rc or negedge arst) if(!arst) rrsync<=0;else rrsync<={rrsync[0],1'b1};
 wire full=(wg=={~rgw2[1],~rgw2[0]});
 wire empty=(rg==wgr2);
 assign wr=wrsync[1]&&ronw2&&!full;
 assign rv=rrsync[1]&&wonr2&&!empty;
 assign rd=mem[rb[0]];
 always @(posedge wc or negedge arst) begin
   if(!arst)begin wb<=0;wg<=0;rgw1<=0;rgw2<=0;won<=0;ronw1<=0;ronw2<=0;end
   else if(wrsync[1])begin won<=1;ronw1<=ron;ronw2<=ronw1;rgw1<=rg;rgw2<=rgw1;
     if(wv&&wr)begin mem[wb[0]]<=wd;wb<=wb+1'b1;wg<=((wb+2'd1)>>1)^(wb+2'd1);end
   end
 end
 always @(posedge rc or negedge arst) begin
   if(!arst)begin rb<=0;rg<=0;wgr1<=0;wgr2<=0;ron<=0;wonr1<=0;wonr2<=0;end
   else if(rrsync[1])begin ron<=1;wonr1<=won;wonr2<=wonr1;wgr1<=wg;wgr2<=wgr1;
     if(rv&&rr)begin rb<=rb+1'b1;rg<=((rb+2'd1)>>1)^(rb+2'd1);end
   end
 end
endmodule
