// Default-off SRAM replacement preserves the original four-edge prefetch path.
`ifndef OT_HOST_GUARD_SRAM_DEFAULT
`define OT_HOST_GUARD_SRAM_DEFAULT 0
`endif
`ifndef OT_HOST_GUARD_SRAM_MUTANT
`define OT_HOST_GUARD_SRAM_MUTANT 0
`endif
module qkd_host_guard_fifo #(parameter W=8,
 parameter SRAM_FIFO=`OT_HOST_GUARD_SRAM_DEFAULT)(input wire ck,rst_n,
 input wire push,input wire[W-1:0]din,input wire pop,
 output wire valid,output wire[W-1:0]dout,output reg[7:0]count,
 output wire overflow,underflow);
 generate if(SRAM_FIFO && W==64)begin:g_sram
 localparam MUT=`OT_HOST_GUARD_SRAM_MUTANT;
 reg[6:0]wp,rp;reg[7:0]unread;reg[3:0]credits,fc;
 reg[2:0]fw,fr;reg v1,v2,v3;
 wire[63:0]stage1;reg[63:0]stage2,last,front[0:7];
 wire take=pop&&valid;
 wire put=push&&(count<(MUT==3?127:128)||take);
 wire fetch=unread!=0&&credits!=0;
 wire enqueue=MUT==2?v2:v3;
 wire[6:0]read_addr=MUT==1?rp+7'd1:rp;
 assign valid=fc!=0;assign dout=front[fr];
 assign overflow=push&&!put;assign underflow=pop&&!valid;
 // The primitive provides stage1 on fetch. Stage2, last and front consume
 // v1, v2 and v3 respectively, exactly as the old bank/half/last/front path.
 // A push to an empty FIFO cannot fetch until the following edge. The real
 // primitive's read-before-write behavior therefore needs no RAW forwarding.
 ot_sram_1r1w_128x64_m1_p192 u_storage(
 .clk(ck),.r_ce_in(rst_n&&fetch),.r_addr_in(read_addr),.rd_out(stage1),
 .w_ce_in(rst_n&&put),.w_addr_in(wp),.wd_in(din),.w_mask_in(64'hffffffffffffffff));
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
 wp<=0;rp<=0;unread<=0;count<=0;credits<=8;fc<=0;fw<=0;fr<=0;
 v1<=0;v2<=0;v3<=0;stage2<=0;last<=0;
 end else begin
 if(put)wp<=wp+1'b1;
 if(fetch)rp<=rp+1'b1;
 v1<=fetch;v2<=v1;v3<=v2;
 if(v1)stage2<=stage1;
 if(v2)last<=stage2;
 if(enqueue)begin front[fw]<=MUT==2?stage2:last;fw<=fw+1'b1;end
 if(take)fr<=fr+1'b1;
 case({put,take})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;endcase
 case({put,fetch})2'b10:unread<=unread+1'b1;2'b01:unread<=unread-1'b1;endcase
 case({take,fetch})2'b10:credits<=credits+1'b1;2'b01:credits<=credits-1'b1;endcase
 case({enqueue,take})2'b10:fc<=fc+1'b1;2'b01:fc<=fc-1'b1;endcase
 end
 end else begin:g_legacy
 reg[W-1:0]mem[0:127],bank[0:15],half[0:1],last,front[0:7];
 reg[6:0]wp,rp; reg[7:0]unread;reg[3:0]credits,fc;
 reg[2:0]fw,fr;reg[3:0]sel1;reg sel2;reg v1,v2,v3;
 wire take=pop&&valid;wire put=push&&(count<128||take);
 wire fetch=unread!=0&&credits!=0;
 assign valid=fc!=0;assign dout=front[fr];
 assign overflow=push&&!put;assign underflow=pop&&!valid;
 integer b;
 always @(posedge ck or negedge rst_n)if(!rst_n)begin
 wp<=0;rp<=0;unread<=0;count<=0;credits<=8;fc<=0;fw<=0;fr<=0;
 sel1<=0;sel2<=0;v1<=0;v2<=0;v3<=0;last<=0;
 for(b=0;b<16;b=b+1)bank[b]<=0;
 for(b=0;b<2;b=b+1)half[b]<=0;
 end else begin
 if(put)begin mem[wp]<=din;wp<=wp+1'b1;end
 if(fetch)begin
 for(b=0;b<16;b=b+1)bank[b]<=mem[b*8+rp[2:0]];
 sel1<=rp[6:3];rp<=rp+1'b1;
 end
 v1<=fetch;v2<=v1;v3<=v2;
 if(v1)begin half[0]<=bank[sel1[2:0]];half[1]<=bank[8+sel1[2:0]];sel2<=sel1[3];end
 if(v2)last<=half[sel2];
 if(v3)begin front[fw]<=last;fw<=fw+1'b1;end
 if(take)fr<=fr+1'b1;
 case({put,take})2'b10:count<=count+1'b1;2'b01:count<=count-1'b1;endcase
 case({put,fetch})2'b10:unread<=unread+1'b1;2'b01:unread<=unread-1'b1;endcase
 case({take,fetch})2'b10:credits<=credits+1'b1;2'b01:credits<=credits-1'b1;endcase
 case({v3,take})2'b10:fc<=fc+1'b1;2'b01:fc<=fc-1'b1;endcase
 end
 end endgenerate
endmodule
