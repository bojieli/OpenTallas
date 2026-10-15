`timescale 1ns/1ps
`default_nettype none
// Local target validity, not host-provided readiness. Observe the actual
// programme write port after target transport. A descriptor is ready only
// after every row of its range has been physically configured. SRAM payload
// stays in the real programme macro; this bitmap is finite control state.
// Same synchronous clock family as the actual native programme. Write commit
// takes two edges after cfg_we reaches the native programme input (capture,
// then macro write). No config/validation activity is permitted in execution.
module ot_hbm_program_block_ready #(parameter integer PCW=10, MUT=0, parameter [7:0] TARGET=48)(
 input wire clk,rst_n,
 input wire cfg_we,input wire[PCW-1:0] cfg_addr,
 input wire desc_v,input wire[7:0] desc_target,
 input wire[11:0] desc_base,input wire[12:0] desc_limit,input wire[15:0] desc_loops,
 input wire program_active,launch_v,
 output wire block_ready,output reg fault
);
 localparam integer ROWS=1<<PCW;
 reg[ROWS-1:0] loaded;
 reg dv;reg[7:0] target;reg[11:0] base;reg[12:0] lim;reg[15:0] loops;
 reg scanning,validated,bad;reg[PCW-1:0] row;reg[PCW:0] limit;
 reg[1:0] commit;
 initial if(PCW<8||PCW>12)$fatal(1,"block ready PCW must be8..12");
 assign block_ready=validated&&!scanning&&commit==0&&!fault&&!program_active;
 always @(posedge clk)begin target<=desc_target;base<=desc_base;lim<=desc_limit;loops<=desc_loops;end
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)begin loaded<=0;dv<=0;scanning<=0;validated<=0;bad<=0;row<=0;limit<=0;commit<=0;fault<=0;end
  else begin
   dv<=desc_v;commit<={commit[0],cfg_we};
   if(cfg_we)begin
    loaded[cfg_addr]<=1;validated<=0;
    if(program_active||scanning||launch_v)fault<=1;
   end
   if(dv&&target==TARGET)begin
    validated<=0;
    if(program_active||scanning||cfg_we||launch_v||loops==0||lim<={1'b0,base}||lim>ROWS)fault<=1;
    else begin scanning<=1;row<=base[PCW-1:0];limit<=lim[PCW:0];bad<=0;end
   end
   if(scanning)begin
    if(!loaded[row]&&MUT==0)bad<=1;
    if({1'b0,row}+1'b1==limit)begin
     scanning<=0;
     if(MUT==0&&(bad||!loaded[row]))fault<=1;else validated<=1;
    end else row<=row+1'b1;
   end
   if(launch_v&&!block_ready)fault<=1;
  end
 end
endmodule
`default_nettype wire
