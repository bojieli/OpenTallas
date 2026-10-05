`timescale 1ps/1fs
// Finite addressed HBM BACKING fixture outside controller area (off-die memory
// abstraction). Full34bit keys, one instance/stack. It journals real update
// edges and holds every completion until ready. This is test HBM, not licensed
// PHY or golden-model/checkpoint contents. Retrospective commands are impossible.
module ot_hbm_r14_backing_fixture #(parameter integer STACK=0,WORDS=2048)(
 input wire clk,rst_n,input wire [63:0] cyc,
 input wire cv,output wire cr,input ot_hbm_r14_pkg::command_t cmd,
 output reg [31:0] rv,input wire [31:0] rr,output reg [511:0] rtag,
 output reg [159:0] rbeat,output reg [8191:0] rdata,
 output reg [31:0] wv,input wire [31:0] wr,output reg [63:0] wslot,
 input wire [3:0] mutant,output reg fault);
 import ot_hbm_r14_pkg::*;
 reg [33:0] keys[0:WORDS-1];reg [255:0] memory[0:WORDS-1];reg [WORDS-1:0] valid;
 reg [31:0] reading,writing;reg [63:0] rd_due[0:31],wr_due[0:31];
 command_t read_cmd[0:31],write_cmd[0:31];
 integer p,k,index;reg found;reg [33:0] key;
 assign cr=(cmd.op==RD)?(!reading[cmd.pc]&&!rv[cmd.pc]):
           (cmd.op==WR)?(!writing[cmd.pc]&&!wv[cmd.pc]):1'b1;
 function automatic logic [255:0] initial_data(input logic [33:0] s);
   logic [255:0] value;
   begin for(integer j=0;j<32;j=j+1)value[j*8+:8]=8'((s+34'(j)+34'(STACK*17))&255);initial_data=value;end
 endfunction
 always @(posedge clk or negedge rst_n)begin
   if(!rst_n)begin valid<=0;reading<=0;writing<=0;rv<=0;wv<=0;rtag<=0;rbeat<=0;rdata<=0;wslot<=0;fault<=0;
     for(p=0;p<32;p=p+1)begin rd_due[p]<=0;wr_due[p]<=0;read_cmd[p]<='0;write_cmd[p]<='0;end
   end else begin
     if(cv&&cr)begin
       if(cmd.op==RD)begin reading[cmd.pc]<=1;read_cmd[cmd.pc]<=cmd;rd_due[cmd.pc]<=cyc+25;end
       if(cmd.op==WR)begin writing[cmd.pc]<=1;write_cmd[cmd.pc]<=cmd;wr_due[cmd.pc]<=cyc+((mutant==1)?1:8);end
     end
     for(p=0;p<32;p=p+1)begin
       if(rv[p]&&rr[p])rv[p]<=0;
       if(wv[p]&&wr[p])wv[p]<=0;
       if(writing[p]&&cyc>=wr_due[p]&&!wv[p])begin
         key=(mutant==2)?(write_cmd[p].sector&34'hfff):write_cmd[p].sector;
         index=-1;found=0;
         for(k=0;k<WORDS;k=k+1)if(valid[k]&&keys[k]==key)begin index=k;found=1;end
         if(!found)for(k=WORDS-1;k>=0;k=k-1)if(!valid[k])index=k;
         if(index<0)fault<=1;
         else begin valid[index]<=1;keys[index]<=key;memory[index]<=write_cmd[p].data;
           writing[p]<=0;wv[p]<=1;wslot[p*2+:2]<=write_cmd[p].tag[1:0];
           $display("HBM_BACKING stack=%0d cyc=%0d sector=%0d tag=%0d beat=%0d",STACK,cyc,write_cmd[p].sector,write_cmd[p].tag,write_cmd[p].beat);
         end
       end
       if(reading[p]&&cyc>=rd_due[p]&&!rv[p])begin
         key=(mutant==2)?(read_cmd[p].sector&34'hfff):read_cmd[p].sector;index=-1;
         for(k=0;k<WORDS;k=k+1)if(valid[k]&&keys[k]==key)index=k;
         rv[p]<=1;reading[p]<=0;rtag[p*16+:16]<={4'b0,read_cmd[p].tag};
         rbeat[p*5+:5]<=((mutant==3)?{1'b0,read_cmd[p].beat[3:0]}:read_cmd[p].beat);
         rdata[p*256+:256]<=(index<0)?initial_data(read_cmd[p].sector):memory[index];
       end
     end
   end
 end
endmodule
