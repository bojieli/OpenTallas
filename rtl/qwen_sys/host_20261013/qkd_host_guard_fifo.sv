// Internal soft FIFO, not an intertile seam. Three registered mux stages
// partition the 128 storage entries into 16 banks of eight.
module qkd_host_guard_fifo #(parameter W=8)(input wire ck,rst_n,
 input wire push,input wire[W-1:0]din,input wire pop,
 output wire valid,output wire[W-1:0]dout,output reg[7:0]count,
 output wire overflow,underflow);
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
endmodule
