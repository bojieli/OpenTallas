`timescale 1ns/1ps
`default_nettype none
// Registered 12-bit carry slices. Throughput one operand pair per clock.
module ot_hgi_dma_addpipe(input wire clk,rst_n,v_i, input wire [59:0] a,b,
 input wire ci,input wire [91:0] meta_i,output wire v_o, output wire [59:0] y,output wire [91:0] meta_o,output wire [4:0] valid_states);
 reg [4:0] v; reg [59:0] aa[0:4],bb[0:4],ss[0:4]; reg cc[0:4]; reg [91:0] mm[0:4];
 always @(posedge clk or negedge rst_n) if(!rst_n) v<=0; else v<={v[3:0],v_i};
 for(genvar g=0;g<5;g=g+1) begin: stage
 wire [59:0] ax = g==0?a:aa[g-1]; wire [59:0] bx=g==0?b:bb[g-1];
 wire cin=g==0?ci:cc[g-1]; wire [12:0] part={1'b0,ax[g*12+:12]}+{1'b0,bx[g*12+:12]}+cin;
 wire en=g==0?v_i:v[g-1];
 always @(posedge clk) if(en) begin
 aa[g]<=ax; bb[g]<=bx; cc[g]<=part[12]; mm[g]<=g==0?meta_i:mm[g-1];
 ss[g]<=g==0?60'd0:ss[g-1]; ss[g][g*12+:12]<=part[11:0];
 end
 end
 assign valid_states=v; assign v_o=v[4]; assign y=ss[4]; assign meta_o=mm[4];
endmodule
// Four source bits per cycle absorbed with carry-save compressors; no multiplier or wide carry in a stage.
module ot_hgi_dma_ixpipe #(parameter integer MUT=0)(input wire clk,rst_n,v_i,
 input wire [31:0] id,dw,input wire [26:0] mul,input wire [39:0] abase,input wire rebase,first,
 output wire v_o,output wire [59:0] addr,output wire [31:0] dw_o,output wire [23:0] active);
 reg [7:0] v; reg [59:0] s[0:7],c[0:7]; reg [31:0] ix[0:7],dd[0:7]; reg [26:0] mt[0:7];
 always @(posedge clk or negedge rst_n) if(!rst_n)v<=0;else v<={v[6:0],v_i};
 for(genvar g=0;g<8;g=g+1) begin: stage
 reg [59:0] sx,cx,z,t; wire en=g==0?v_i:v[g-1];
 wire [31:0] ii=g==0?id:ix[g-1]; wire [26:0] mu=g==0?mul:mt[g-1];
 always @* begin
 sx=g==0?60'd0:s[g-1]; cx=g==0?60'd0:c[g-1];
 for(integer bitn=0;bitn<4;bitn=bitn+1)begin
 z=(ii[g*4+bitn] && !(MUT==3 && g>=4)) ? ({33'd0,mu} << (g*4+bitn)):60'd0;
 t=sx^cx^z; cx=((sx&cx)|(sx&z)|(cx&z))<<1; sx=t;
 end
 end
 always @(posedge clk) if(en)begin s[g]<=sx;c[g]<=cx;ix[g]<=ii;mt[g]<=mu;dd[g]<=g==0?dw:dd[g-1];end
 end
 wire [4:0] vp,vb,vr; wire pv,bv; wire [59:0] prod,sum; wire [91:0] pm,bm,om; reg [59:0] p0; reg seen;
 always @(posedge clk or negedge rst_n) if(!rst_n)seen<=0;else if(first)seen<=0;else if(pv)seen<=1;
 always @(posedge clk) if(pv&&!seen)p0<=prod;
 wire [59:0] refp=(MUT==5||!rebase)?60'd0:seen?p0:prod;
 ot_hgi_dma_addpipe p(clk,rst_n,v[7],s[7],c[7],1'b0,{60'd0,dd[7]},pv,prod,pm,vp);
 ot_hgi_dma_addpipe b(clk,rst_n,pv,prod,{20'd0,abase},1'b0,{refp,pm[31:0]},bv,sum,bm,vb);
 ot_hgi_dma_addpipe r(clk,rst_n,bv,sum,~bm[91:32],1'b1,bm,v_o,addr,om,vr);
 assign dw_o=om[31:0];
 // Occupancy taps are actual valid flops, used to bound the finite row queue.
 assign active={1'b0,vr,vb,vp,v};
endmodule
`default_nettype wire
