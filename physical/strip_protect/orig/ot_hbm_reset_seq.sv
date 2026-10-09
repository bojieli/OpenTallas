`timescale 1ns/1ps
`default_nettype none
// POR asserts all resets asynchronously. Status crossings terminate in AON;
// each output must pass ot_hbm_reset_release in its actual destination clock.
module ot_hbm_reset_seq #(parameter integer PORTS=4)(
 input wire aon_clk, por_n, power_good, pll_lock,
 input wire [3:0] phy_ready, input wire [PORTS-1:0] links_ready,
 input wire bist_done,bist_pass,fatal_error,requalify,
 output wire pll_reset_n, output wire [3:0] phy_reset_n,
 output wire [PORTS-1:0] link_reset_n,
 output wire coll_reset_n,cmd_reset_n,ready,
 output reg [3:0] state
);
 localparam OFF=0,PLL=1,PHY=2,LINK=3,BIST=4,RUN=5,FAULT=6;
 localparam N=PORTS+8;
 wire [N-1:0] async_status={bist_pass,bist_done,links_ready,phy_ready,pll_lock,power_good};
 (* async_reg="true" *) reg [N-1:0] status_meta,status_sync;
 wire pg=status_sync[0],lock=status_sync[1];
 wire phys=&status_sync[5:2],links=&status_sync[PORTS+5:6];
 wire bd=status_sync[PORTS+6],bp=status_sync[PORTS+7];
 always @(posedge aon_clk or negedge por_n)
  if (!por_n) begin status_meta<=0;status_sync<=0; end
  else begin status_meta<=async_status;status_sync<=status_meta;end
 always @(posedge aon_clk or negedge por_n)
  if (!por_n) state<=OFF;
  else if (fatal_error || (state!=OFF && state!=FAULT && !pg) || ((state>=PHY && state<=RUN) && !lock)) state<=FAULT;
  else case(state)
   OFF: if(pg) state<=PLL;
   PLL: if(lock) state<=PHY;
   PHY: if(phys) state<=LINK;
   LINK: if(links) state<=BIST;
   BIST: if(bd) state<=bp ? RUN : FAULT;
   RUN: if(!phys || !links || !bp) state<=FAULT;
   FAULT: if(requalify && pg && !fatal_error) state<=OFF;
   default:state<=FAULT;
  endcase
 assign pll_reset_n=por_n && state>=PLL && state<=RUN;
 assign phy_reset_n={4{por_n && state>=PHY && state<=RUN}};
 assign link_reset_n={PORTS{por_n && state>=LINK && state<=RUN}};
 assign coll_reset_n=por_n && (state==BIST || state==RUN);
 assign cmd_reset_n=por_n && state==RUN;
 assign ready=cmd_reset_n;
endmodule

module ot_hbm_reset_release #(parameter integer STAGES=3)(
 input wire clk,async_reset_n, output wire reset_n
);
 (* async_reg="true" *) reg [STAGES-1:0] release_pipe;
 always @(posedge clk or negedge async_reset_n)
  if(!async_reset_n) release_pipe<=0;
  else release_pipe<={release_pipe[STAGES-2:0],1'b1};
 assign reset_n=release_pipe[STAGES-1];
endmodule
`default_nettype wire
