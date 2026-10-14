`timescale 1ns/1ps
// Logical full32 gather. No physical coordinates or production price claimed.
// Every relay is the closed W512/MEREG1 master, with its own clock entry.
module ot_qfd_vm_band_gather #(parameter integer LAT=3, PHW=2, MUT=0)(
 input wire [10*LAT-1:0] clk_child,
 input wire me_e,
 input wire [4095:0] plane_data,
 input wire [895:0] column_tags,
 output wire [4095:0] root_words,
 output wire [895:0] root_tags
);
 wire [4095:0] mapped;
 wire [5119:0] stages[0:LAT];
 // Form the whole transpose in one combinational expression. This avoids
 // thousands of partial-vector delta events in the production-size bench.
 function automatic [4095:0] transpose(input [4095:0] v);
   integer ri,ci,ki;
   reg [4095:0] temp;
   begin
     temp=0;
     for(ri=0;ri<32;ri=ri+1)
       for(ki=0;ki<4;ki=ki+1)
         for(ci=0;ci<32;ci=ci+1)
           temp[128*ri+((MUT==1)?4*ci+ki:32*ki+ci)]=v[128*ci+4*ri+ki];
     transpose=temp;
   end
 endfunction
 assign mapped=transpose(plane_data);
 genvar r,s,b;
 assign stages[0]={128'b0,column_tags,mapped};
 generate for(s=0;s<LAT;s=s+1)begin: pipeline
   for(b=0;b<10;b=b+1)begin: banks
     ot_qfd_vm_xrelay_t #(.W(512),.MEREG(1),.MUT((MUT==2 && s==LAT-1 && b==1)?1:0)) u_relay
      (.clk(clk_child[10*s+b]),.me_e(me_e),.d(stages[s][512*b+:512]),.q(stages[s+1][512*b+:512]));
   end
 end endgenerate
 assign root_words=stages[LAT][4095:0];
 generate for(r=0;r<32;r=r+1)begin: tags
   // Logical designated source column r. Actual root station contract pending.
   assign root_tags[28*r+:28]=stages[LAT][4096+28*((MUT==4)?((r+1)%32):r)+:28] ^ ((MUT==3 && r==13)?(28'h1<<(PHW+1)):28'h0);
 end endgenerate
endmodule
