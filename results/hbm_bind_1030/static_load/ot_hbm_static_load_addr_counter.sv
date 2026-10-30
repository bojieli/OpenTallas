`default_nettype none
// SOURCE-ONLY component: resolved native227 LOAD descriptor, no indexed resolver,
// calendar producer, window ownership, PHY or destination router is invented here.
// step_i is a dated command, never a ready/credit. II1 scalar=one4B VM word/step.
module ot_hbm_static_load_addr_counter #(parameter integer MUT_ZERO_STRIDE=0,MUT_STRIPE=0)(
 input wire clk,rst_n,desc_v_i,input wire[226:0]desc_i,input wire step_i,
 output reg active_o,fault_o,addr_v_o,last_o,
 output reg[39:0]src_byte_o,dst_word_o,output reg[2:0]format_o
);
 reg[39:0]srow,drow,sa,da;
 reg[31:0]sst,dst;
 reg[17:0]sstep;reg[15:0]dstep;
 reg[19:0]m,row;reg[20:0]n,col;
 reg[2:0]fmt;reg stripe;reg[1:0]stack;
 // Five8bit carry-select blocks: full40bit row/element additions are explicit;
 // this is an unmapped timing topology proposal, not833ps signoff.
 function automatic[40:0]add40(input[39:0]a,input[39:0]b);
 reg[40:0]r;reg c;reg[8:0]z,o;integer k;
 begin r=0;c=0;
 for(k=0;k<5;k=k+1)begin
 z={1'b0,a[k*8+:8]}+{1'b0,b[k*8+:8]};o=z+9'd1;
 r[k*8+:8]=c?o[7:0]:z[7:0];c=c?o[8]:z[8];end
 r[40]=c;add40=r;end endfunction
 wire last_col=col==n-21'd1;
 wire last_row=row==m-20'd1;
 wire[40:0]snext=add40(last_col?srow:sa,last_col?{8'd0,sst}:{22'd0,sstep});
 wire[40:0]dnext=add40(last_col?drow:da,last_col?{8'd0,dst}:{24'd0,dstep});
 wire[2:0]dfmt=desc_i[4:2];
 wire[1:0]eszshift=(dfmt==0||dfmt==5)?2'd2:(dfmt==1)?2'd1:2'd0;
 wire[15:0]sis=(MUT_ZERO_STRIDE!=0&&desc_i[92:77]==0)?16'd1:desc_i[92:77];
 wire badshape=desc_i[1:0]!=0||desc_i[94:93]!=1||desc_i[44:42]>1||dfmt==3||dfmt==7||desc_i[205:186]==0||desc_i[226:206]==0;
 wire[2:0]esize=(fmt==0||fmt==5)?3'd4:fmt==1?3'd2:3'd1;
 wire badsource=(stripe?(|sa[39:35]):(|sa[39:37]))||({5'd0,sa[34:0]}>40'd22500000000-{37'd0,esize});
 wire badalign=(fmt==0||fmt==5)?(|sa[1:0]):fmt==1?sa[0]:1'b0;
 always @(posedge clk)begin
 if(!rst_n)begin active_o<=0;fault_o<=0;addr_v_o<=0;last_o<=0;src_byte_o<=0;dst_word_o<=0;format_o<=0;
 srow<=0;drow<=0;sa<=0;da<=0;sst<=0;dst<=0;sstep<=0;dstep<=0;m<=0;n<=0;row<=0;col<=0;fmt<=0;stripe<=0;stack<=0;end
 else begin
 addr_v_o<=0;last_o<=0;
 if(desc_v_i)begin
 if(active_o||step_i||badshape||fault_o)begin fault_o<=1;active_o<=0;end
 else begin
 active_o<=1;srow<=desc_i[44:42]==1?{5'd0,desc_i[39:5]}:{3'd0,desc_i[41:5]};sa<=desc_i[44:42]==1?{5'd0,desc_i[39:5]}:{3'd0,desc_i[41:5]};stripe<=desc_i[44:42]==1;stack<=desc_i[41:40];drow<=desc_i[137:98];da<=desc_i[137:98];
 sst<=desc_i[76:45];dst<=desc_i[169:138];sstep<={2'd0,sis}<<eszshift;dstep<=desc_i[185:170];
 m<=desc_i[205:186];n<=desc_i[226:206];row<=0;col<=0;fmt<=dfmt;end
 end else if(step_i)begin
 if(!active_o||fault_o||badalign||badsource)begin fault_o<=1;active_o<=0;end
 else begin
 addr_v_o<=1;src_byte_o<=stripe?{3'd0,stack,sa[34:0]}:{3'd0,sa[36:0]};dst_word_o<=da;format_o<=fmt;last_o<=last_col&&last_row;
 if(last_col&&last_row)active_o<=0;
 else if((stripe?(|snext[40:35]):(|snext[40:37]))||dnext[40])begin fault_o<=1;active_o<=0;end
 else begin sa<=snext[39:0];da<=dnext[39:0];
 if(last_col)begin srow<=snext[39:0];drow<=dnext[39:0];col<=0;row<=row+20'd1;if(stripe&&MUT_STRIPE==0)stack<=stack+2'd1;end
 else col<=col+21'd1;end
 end end
 end end
endmodule
`default_nettype wire
