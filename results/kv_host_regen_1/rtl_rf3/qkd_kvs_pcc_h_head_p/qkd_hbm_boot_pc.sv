`timescale 1ns/1ps
// Destructive cold-boot check of one explicitly reserved scratch sector.
// Connect behind the actual static-port arbiter while execution is held reset.
// A credit is command acceptance, never success: only returned read data can
// assert boot_ok. Writes and reads use the controller's ordered static queue.
module qkd_hbm_boot_pc #(parameter integer TIMEOUT=20000,MUT=0)(
 input wire ck,rst_n,start,input wire[4:0]bank,col,input wire[18:0]row,
 output reg[287:0]es,input wire[260:0]er,
 output wire busy,output reg done,ok,output reg[3:0]cause);
 localparam IDLE=0,WR=1,WAIT_WR=2,RD=3,WAIT_RD=4,FIN=5;
 reg[2:0]state;reg phase;reg[31:0]timer;
 reg[4:0]bank_q,col_q;reg[18:0]row_q;
 wire[255:0]pattern=phase?256'hfedcba9876543210_0011223344556677_8899aabbccddeeff_0123456789abcdef:
                             256'h0123456789abcdef_ffeeddccbbaa9988_7766554433221100_fedcba9876543210;
 assign busy=state!=IDLE&&state!=FIN;
 always @(posedge ck or negedge rst_n)begin
  if(!rst_n)begin es<=0;state<=IDLE;phase<=0;timer<=0;done<=0;ok<=0;cause<=0;bank_q<=0;col_q<=0;row_q<=0;end
  else begin
   es[0]<=0;
   if(busy)timer<=timer+1;
   if(busy&&er[260])begin done<=1;ok<=0;cause<=1;state<=FIN;end
   else if(busy&&timer>=TIMEOUT)begin done<=1;ok<=0;cause<=2;state<=FIN;end
   else case(state)
    IDLE,FIN:if(start)begin bank_q<=bank;col_q<=col;row_q<=row;state<=WR;phase<=0;timer<=0;done<=0;ok<=0;cause<=0;end
    WR:begin es<={1'b1,1'b1,bank_q,col_q,row_q,pattern,1'b1};state<=WAIT_WR;end
    WAIT_WR:if(er[259])state<=RD;
    RD:begin es<={1'b0,1'b0,bank_q,col_q,row_q,256'b0,1'b1};state<=WAIT_RD;end
    WAIT_RD:if(er[0])begin
     if(er[258]||((er[256:1]!=pattern)&&MUT==0))begin done<=1;ok<=0;cause<=3;state<=FIN;end
     else if(phase)begin done<=1;ok<=1;state<=FIN;end
     else begin phase<=1;state<=WR;end
    end
    default:state<=IDLE;
   endcase
  end
 end
endmodule
