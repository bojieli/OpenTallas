`timescale 1ns/1ps
`default_nettype none
// Reusable source-bank CDC queue: actual write and read clock pins, Gray pointer crossings.
// Thirty-two protected producer reservations cover formatter flight plus this depth32 queue and held read head.
module ot_hgi_dma_vm_queue32(input wire wclk,rclk,rst_n,input wire in_v,input wire [279:0] in_d,
 output reg credit,output reg fault,output reg [7:0] head_v,head_epoch,
 output wire [8*280-1:0] head_d,input wire [7:0] ack_epoch);
 reg [279:0] mem[0:31],slots[0:7];reg [5:0] wp,rp,wg,rg;
 (* async_reg="true" *) reg [5:0] rg1,rg2,wg1,wg2;
 reg [5:0] credit_cursor;reg [2:0] head_t;reg [7:0] ack_q;
 function automatic [5:0] ungray(input [5:0] g);begin ungray[5]=g[5];for(integer i=4;i>=0;i--)ungray[i]=ungray[i+1]^g[i];end endfunction
 wire full=wg=={~rg2[5:4],rg2[3:0]};wire empty=rg==wg2;
 wire credit_available=ungray(rg2)!=credit_cursor;
 wire slot_free=!head_v[head_t]||ack_q[head_t]==head_epoch[head_t];
 wire load_head=slot_free&&!empty;
 always @(posedge wclk or negedge rst_n) if(!rst_n)begin wp<=0;wg<=0;rg1<=0;rg2<=0;credit_cursor<=0;credit<=0;fault<=0;end
 else begin
 rg1<=rg;rg2<=rg1;credit<=credit_available;if(credit_available)credit_cursor<=credit_cursor+1'b1;
 if(in_v)begin if(full)fault<=1;else begin wp<=wp+1'b1;wg<=((wp+6'd1)>>1)^(wp+6'd1);end end
 end
 always @(posedge wclk)if(in_v&&!full)mem[wp[4:0]]<=in_d;
 always @(posedge rclk or negedge rst_n)if(!rst_n)begin rp<=0;rg<=0;wg1<=0;wg2<=0;head_v<=0;head_epoch<=0;head_t<=0;ack_q<=0;end
 else begin
 wg1<=wg;wg2<=wg1;ack_q<=ack_epoch;
 for(integer h=0;h<8;h++)if(head_v[h]&&ack_q[h]==head_epoch[h])head_v[h]<=0;
 if(load_head)begin
 rp<=rp+1'b1;rg<=((rp+6'd1)>>1)^(rp+6'd1);
 head_v[head_t]<=1;head_epoch[head_t]<=!head_epoch[head_t];head_t<=head_t+1'b1;
 end
 end
 for(genvar h=0;h<8;h++)begin: held
 always @(posedge rclk)if(load_head&&head_t==3'(h))slots[h]<=mem[rp[4:0]];
 assign head_d[h*280+:280]=slots[h];
 end
endmodule
// Counted commit events cross back separately from queue capacity release.
module ot_hgi_dma_vm_events32(input wire vclk,sclk,rst_n,input wire [2:0] events,output reg pulse);
 reg [7:0] vb,vg,cursor;
 (* async_reg="true" *)reg [7:0] g1,g2;
 function automatic [7:0] ungray(input [7:0] g);begin ungray[7]=g[7];for(integer i=6;i>=0;i--)ungray[i]=ungray[i+1]^g[i];end endfunction
 wire [7:0] next_v=vb+{5'd0,events};
 always @(posedge vclk or negedge rst_n)if(!rst_n)begin vb<=0;vg<=0;end else begin vb<=next_v;vg<=next_v^(next_v>>1);end
 // Gray event counter changes multiple bits if multiple events occur. Serialize first.
 // Router guarantees <=1 completion event per source bank per VM edge after pending serialization.
 always @(posedge sclk or negedge rst_n)if(!rst_n)begin g1<=0;g2<=0;cursor<=0;pulse<=0;end else begin g1<=vg;g2<=g1;pulse<=available;if(available)cursor<=cursor+1'b1;end
 wire available=ungray(g2)!=cursor;
endmodule
`default_nettype wire
