`timescale 1ns/1ps
// Existing debug replay-count capture on the original edge, isolated from PHY root.
module ot_lkep_status_shared #(parameter integer NS=3,parameter integer MUT_STATUS=0)(
 input wire clk,rst_n,input wire[NS*32-1:0] rp_flat,output reg[31:0] st_replays);
 reg[1:0] rs;
 always @(posedge clk or negedge rst_n) if(!rst_n)rs<=0;else rs<={rs[0],1'b1};
 (* keep *) reg rr;
 always @(posedge clk)rr<=rs[1];
 wire[31:0]rp_t[0:NS-1];genvar g;
 generate for(g=0;g<NS;g=g+1)begin:g_rp
 assign rp_t[g]=rp_flat[g*32+:32];end endgenerate
    // Three counters sum on the original status capture edge. Carry-save
    // reduction and parallel prefix avoid two serial ripple additions.
    function automatic [31:0] add32_prefix(input [31:0] a,input [31:0] b);
      reg [31:0] p,g,base; integer d;
      begin
        base=a^b; p=base; g=a&b;
        for(d=1;d<32;d=d*2) begin
          g=g|(p&(g<<d));
          p=p&((p<<d)|((32'h1<<d)-1));
        end
        add32_prefix=base^(g<<1);
      end
    endfunction
    wire [31:0] rep_sum;
    generate if(NS==3) begin:g_sum3
      wire [31:0] sx=rp_t[0]^rp_t[1]^rp_t[2];
      wire [31:0] sy=((rp_t[0]&rp_t[1])|(rp_t[0]&rp_t[2])|(rp_t[1]&rp_t[2]))<<1;
      assign rep_sum=add32_prefix(sx,sy);
    end else begin:g_sum_other
      integer v; reg [31:0] sum;
      always @(*) begin sum=0;for(v=0;v<NS;v=v+1) sum=sum+rp_t[v];end
      assign rep_sum=sum;
    end endgenerate
    always @(posedge clk or negedge rr)
      if(!rr)st_replays<=0;
      else st_replays<=rep_sum ^ ((MUT_STATUS!=0 && rep_sum!=0)?32'h1:32'h0);
endmodule
