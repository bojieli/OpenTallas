`timescale 1ns/1ps
// Physicalstage interfaces of the actual existing xwrite pipeline. This parent
// is wiresonly; every listedclock terminates on one explicit hardleaf root.
module ot_smh_static_north_hard #(parameter integer MUT=0)(
 input wire [79:0] data_clk,input wire [8:0] ctrl_clk,input wire [3:0] row_clk,
 input wire rst_n,xw_en,input wire [6:0] xw_addr,xw_grp,input wire [2047:0] xw_data,
 input wire [817:0] row0,
 output wire [2068:0] fx_b,bl0,br0,output wire [817:0] rl0,rr0
);
 wire [2047:0] d1,d2,d3,dfx,dwa,dwm,dwo,dea,dem,deo;
 for(genvar s=0;s<8;s=s+1)begin:g_slice
   ot_smh_static_stage256 #(.MUT((s==0)?MUT:0)) u_wl(.clk(data_clk[s*10]),.d(xw_data[s*256+:256]),.q(d1[s*256+:256]));
   ot_smh_static_stage256 u_wm(.clk(data_clk[s*10+1]),.d(d1[s*256+:256]),.q(d2[s*256+:256]));
   ot_smh_static_stage256 u_w0(.clk(data_clk[s*10+2]),.d(d2[s*256+:256]),.q(d3[s*256+:256]));
   ot_smh_static_stage256 u_fx(.clk(data_clk[s*10+3]),.d(d3[s*256+:256]),.q(dfx[s*256+:256]));
   ot_smh_static_stage256 u_wa(.clk(data_clk[s*10+4]),.d(d3[s*256+:256]),.q(dwa[s*256+:256]));
   ot_smh_static_stage256 u_wm1(.clk(data_clk[s*10+5]),.d(dwa[s*256+:256]),.q(dwm[s*256+:256]));
   ot_smh_static_stage256 u_wo(.clk(data_clk[s*10+6]),.d(dwm[s*256+:256]),.q(dwo[s*256+:256]));
   ot_smh_static_stage256 u_ea(.clk(data_clk[s*10+7]),.d(d3[s*256+:256]),.q(dea[s*256+:256]));
   ot_smh_static_stage256 u_em(.clk(data_clk[s*10+8]),.d(dea[s*256+:256]),.q(dem[s*256+:256]));
   ot_smh_static_stage256 u_eo(.clk(data_clk[s*10+9]),.d(dem[s*256+:256]),.q(deo[s*256+:256]));
 end
 wire [14:0] raw1;
 wire [20:0] c3,cfx,cwa,cwm,cwo,cea,cem,ceo;
 ot_smh_static_ctrl15 u_raw(.clk(ctrl_clk[0]),.rst_n(rst_n),.d({xw_en,xw_addr,xw_grp}),.q(raw1));
 ot_smh_static_decode21 u_decode(.clk(ctrl_clk[1]),.rst_n(rst_n),.d(raw1),.q(c3));
 ot_smh_static_ctrl21 u_fx(.clk(ctrl_clk[2]),.rst_n(rst_n),.d(c3),.q(cfx));
 ot_smh_static_ctrl21 u_wa(.clk(ctrl_clk[3]),.rst_n(rst_n),.d(c3),.q(cwa));
 ot_smh_static_ctrl21 u_wm(.clk(ctrl_clk[4]),.rst_n(rst_n),.d(cwa),.q(cwm));
 ot_smh_static_ctrl21 u_wo(.clk(ctrl_clk[5]),.rst_n(rst_n),.d(cwm),.q(cwo));
 ot_smh_static_ctrl21 u_ea(.clk(ctrl_clk[6]),.rst_n(rst_n),.d(c3),.q(cea));
 ot_smh_static_ctrl21 u_em(.clk(ctrl_clk[7]),.rst_n(rst_n),.d(cea),.q(cem));
 ot_smh_static_ctrl21 u_eo(.clk(ctrl_clk[8]),.rst_n(rst_n),.d(cem),.q(ceo));
 assign fx_b={cfx,dfx};assign bl0={cwo,dwo};assign br0={ceo,deo};
 wire [817:0] rw,re;
 ot_smh_static_row818 u_row_wl(.clk(row_clk[0]),.rst_n(rst_n),.d(row0),.q(rw));
 ot_smh_static_row818 u_row_el(.clk(row_clk[1]),.rst_n(rst_n),.d(row0),.q(re));
 ot_smh_static_row818 u_row_wo(.clk(row_clk[2]),.rst_n(rst_n),.d(rw),.q(rl0));
 ot_smh_static_row818 u_row_eo(.clk(row_clk[3]),.rst_n(rst_n),.d(re),.q(rr0));
endmodule

module ot_smh_static_ctrl15(input wire clk,rst_n,input wire [14:0] d,output wire [14:0] q);
 reg [13:0] payload;reg valid;
 always @(posedge clk)payload<=d[13:0];
 always @(posedge clk or negedge rst_n)if(!rst_n)valid<=0;else valid<=d[14];
 assign q={valid,payload};
endmodule
module ot_smh_static_ctrl21(input wire clk,rst_n,input wire [20:0] d,output wire [20:0] q);
 reg [19:0] payload;reg valid;
 always @(posedge clk)payload<=d[19:0];
 always @(posedge clk or negedge rst_n)if(!rst_n)valid<=0;else valid<=d[20];
 assign q={valid,payload};
endmodule
// Inputlanding captures all15bits before the local onehotdecode. This reuses
// original WM and W0 edges; no combinational path enters from another leaf.
module ot_smh_static_decode21(input wire clk,rst_n,input wire [14:0] d,output wire [20:0] q);
 reg [13:0] landing;reg landing_v,valid;reg [19:0] payload;
 always @(posedge clk)begin
   landing<=d[13:0];payload[19:13]<=landing[13:7];
   for(integer g=0;g<13;g=g+1)payload[g]<=landing[6:0]==7'(g);
 end
 always @(posedge clk or negedge rst_n)
   if(!rst_n)begin landing_v<=0;valid<=0;end
   else begin landing_v<=d[14];valid<=landing_v;end
 assign q={valid,payload};
endmodule
module ot_smh_static_row818(input wire clk,rst_n,input wire [817:0] d,output wire [817:0] q);
 localparam [817:0] RM=(818'b11<<816)|(818'b1<<7);
 for(genvar b=0;b<818;b=b+1)begin:g_bit
   reg state;
   if(RM[b])begin:g_reset
     always @(posedge clk or negedge rst_n)if(!rst_n)state<=0;else state<=d[b];
   end else begin:g_data
     always @(posedge clk)state<=d[b];
   end
   assign q[b]=state;
 end
endmodule
