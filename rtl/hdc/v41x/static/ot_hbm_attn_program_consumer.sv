`timescale 1ns/1ps
`default_nettype none
// Actual target49 native programme consumer. Four resident event profiles share
// one mapped SRAM word (4x7 bits), eliminating per-record event reprogramming.
// Opcode one-hot bits[3:0]: 1=profile config,2=launch,4=query fetch,8=idle.
// Config: addr[11:4], packed events[39:12]. Launch: profile[5:4],last[13:6],
// rows[29:14],PV-only[30],query epoch[31]. Fetch: epoch[4],head[8:5],
// burst[11:9],canonical sector[27:12]. Upper bits222:40 must be zero.
module ot_hbm_attn_program_consumer(
 input wire clk,rst_n,input wire instruction_v,input wire[222:0]instruction,
 output wire[6:0]events,output wire[7:0]phase,output wire event_valid,
 output reg[15:0]rows,output reg pv_only,output reg query_epoch,
 output wire fetch_v,fetch_epoch,output wire[3:0]fetch_head,
 output wire[2:0]fetch_burst,output wire[15:0]fetch_base_sector,
 output wire running,output wire fault
);
 reg iv;reg[222:0]word;reg own_fault;wire core_fault;
 wire write_event=iv&&word[0],launch=iv&&word[1];
 wire[3:0]op=word[3:0];
 assign fetch_v=iv&&word[2];assign fetch_epoch=word[4];assign fetch_head=word[8:5];
 assign fetch_burst=word[11:9];assign fetch_base_sector=word[27:12];
 always @(posedge clk or negedge rst_n)if(!rst_n)begin iv<=0;rows<=0;pv_only<=0;query_epoch<=0;own_fault<=0;end
 else begin
  iv<=instruction_v;
  if(iv)begin
   if(|word[222:40] || !(op==1||op==2||op==4||op==8))own_fault<=1;
   if(launch)begin rows<=word[29:14];pv_only<=word[30];query_epoch<=word[31];
    if(word[29:14]==0||word[29:14]>640)own_fault<=1;
   end
  end
 end
 always @(posedge clk)word<=instruction;
 ot_hbm_attn_event_program u_events(.clk(clk),.rst_n(rst_n),
  .program_we(write_event),.program_addr(word[11:4]),.program_events(word[39:12]),
  .launch(launch),.program_last(word[13:6]),.program_profile(word[5:4]),
  .events(events),.phase(phase),.valid(event_valid),.running(running),.fault(core_fault));
 assign fault=own_fault|core_fault;
endmodule
`default_nettype wire
