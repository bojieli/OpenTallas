`timescale 1ns/1ps
// Arendt owns captured-frame lifetime, bank FSM/owners, XVM and native release.
// This default-off leaf only validates literal W1 firstphase, broadcasts one
// checked old-read response, and selects one native masked writer group.
module ot_qwen_rom_w1_frame_leaf #(parameter integer ENABLE=0)(
 input wire clk,rst_n,frame_start,frame_clear,frame_ue,
 output wire frame_ready,output reg w1_valid,fallback_v,fault,
 input wire [2255:0] ren,input wire [2256*24-1:0] raddr,
 input wire [864:0] wen,input wire [865*24-1:0] waddr,
 input wire [865*32-1:0] wdata,
 input wire window_v,input wire [14:0] window_base,
 input wire [2047:0] window_words,output wire window_ready,
 output wire read_put_v,input wire read_put_ready,
 output wire [2255:0] read_put_mask,output wire [2256*32-1:0] read_put_data,
 input wire select_v,input wire [6:0] select_group,output wire select_ready,
 output wire pack_v,input wire pack_ready,
 output wire [14:0] pack_word,output wire [15:0] pack_mask,
 output wire [511:0] pack_data
);
 import ot_gpu_w6_secded_pkg::*;
 reg [1:0] guard_state;reg [11:0] index;
 reg [2:0] rstep,wstep;reg rbusy,wbusy;
 reg [71:0] rcode[0:5][0:32],wcode[0:6][0:8];
 wire live=ENABLE && rst_n && w1_valid && !fault && !frame_ue;
 assign frame_ready=ENABLE && rst_n && guard_state==0 && !w1_valid && !fallback_v && !fault;
 assign window_ready=live && !rbusy;
 assign select_ready=live && !wbusy;
 wire [2047:0] decoded_words;wire [32:0] rue;
 wire [5:0] returned_window;
 wire [511:0] decoded_pack;wire [8:0] wue;
 genvar k,i;
 generate for(k=0;k<32;k=k+1)begin:g_rdecode
   wire [65:0] d=decode64(rcode[5][k]);
   assign decoded_words[k*64+:64]=d[63:0];assign rue[k]=d[65];
 end
 for(k=0;k<8;k=k+1)begin:g_wdecode
   wire [65:0] d=decode64(wcode[6][k]);
   assign decoded_pack[k*64+:64]=d[63:0];assign wue[k]=d[65];
 end
 for(i=0;i<2256;i=i+1)begin:g_put
   if(i>=208)begin:g_vx
     localparam integer P=i-208;
     assign read_put_mask[i]=read_put_v && ((P%128)/2==returned_window);
     assign read_put_data[i*32+:32]=(P%2)?decoded_words[1024+:32]:decoded_words[0+:32];
   end else begin:g_other
     assign read_put_mask[i]=0;assign read_put_data[i*32+:32]=0;
   end
 end endgenerate
 wire [65:0] rm=decode64(rcode[5][32]);
 assign returned_window=rm[5:0];assign rue[32]=rm[65];
 wire [65:0] wm=decode64(wcode[6][8]);
 assign pack_word=wm[14:0];assign pack_mask=wm[30:15];
 assign wue[8]=wm[65];assign pack_data=decoded_pack;
 assign read_put_v=live && rbusy && rstep==6 && !(|rue);
 assign pack_v=live && wbusy && wstep==7 && !(|wue);
 wire expect_r=index>=208;
 wire [23:0] expect_ra=24'd4096+((index-208)%128)*32;
 wire expect_w=index<768;
 wire [23:0] expect_wa=(24'd5175+(index/16)*8)*16+index%16;
 always @(posedge clk)begin
   if(!rst_n)begin
     guard_state<=0;index<=0;w1_valid<=0;fallback_v<=0;fault<=0;
     rstep<=0;wstep<=0;rbusy<=0;wbusy<=0;
     for(integer p=0;p<6;p=p+1)for(integer c=0;c<33;c=c+1)rcode[p][c]<=encode64(0);
     for(integer p=0;p<7;p=p+1)for(integer c=0;c<9;c=c+1)wcode[p][c]<=encode64(0);
   end else if(ENABLE && !fault)begin
     if((guard_state!=0||w1_valid) && frame_ue)fault<=1;
     if(frame_clear)begin
       if(rbusy||wbusy||guard_state!=0)fault<=1;
       else begin w1_valid<=0;fallback_v<=0;end
     end else if(frame_start)begin
       if(!frame_ready||frame_ue)fault<=1;
       else begin guard_state<=1;index<=0;end
     end
     case(guard_state)
       1:if(ren[index]!=expect_r || (expect_r && raddr[index*24+:24]!=expect_ra))begin
           fallback_v<=1;guard_state<=0;
         end else if(index==2255)begin index<=0;guard_state<=2;end
         else index<=index+1;
       2:if(wen[index]!=expect_w || (expect_w && waddr[index*24+:24]!=expect_wa))begin
           fallback_v<=1;guard_state<=0;
         end else if(index==864)begin w1_valid<=1;guard_state<=0;end
         else index<=index+1;
       default:begin end
     endcase
     if(window_v)begin
       if(!window_ready||window_base<256||window_base>508||window_base[1:0]!=0)fault<=1;
       else begin
         for(integer c=0;c<32;c=c+1)rcode[0][c]<=encode64(window_words[c*64+:64]);
         rcode[0][32]<=encode64({58'b0,window_base[7:2]});
         rbusy<=1;rstep<=1;
       end
     end else if(rbusy && rstep<6)begin
       for(integer c=0;c<33;c=c+1)rcode[rstep][c]<=rcode[rstep-1][c];
       rstep<=rstep+1;
     end else if(read_put_v && read_put_ready)rbusy<=0;
     if(rbusy && rstep==6 && |rue)fault<=1;
     if(select_v)begin
       if(!select_ready||select_group>=48)fault<=1;
       else begin
         for(integer c=0;c<8;c=c+1)wcode[0][c]<=encode64(wdata[select_group*512+c*64+:64]);
         wcode[0][8]<=encode64({33'b0,16'hffff,waddr[select_group*16*24+4+:15]});
         wbusy<=1;wstep<=1;
       end
     end else if(wbusy && wstep<7)begin
       for(integer c=0;c<9;c=c+1)wcode[wstep][c]<=wcode[wstep-1][c];
       wstep<=wstep+1;
     end else if(pack_v && pack_ready)wbusy<=0;
     if(wbusy && wstep==7 && |wue)fault<=1;
   end
 end
`ifndef SYNTHESIS
 always @(negedge rst_n)if(ENABLE && (rbusy||wbusy))$fatal(1,"W1 leaf reset with owned payload");
`endif
endmodule
