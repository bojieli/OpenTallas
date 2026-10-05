`timescale 1ns/1ps
// Source-bound opt-in port hook for measured TU AR8x8 and gather1x96.
// Not a switch or endpoint replacement. Peer rearm_ready/quiet signals MUST
// come from actual queue/pipe/CDC/debt taps, and release from matched fabric
// authority AFTER result publication. No timeout or reset-based debt clearing.
module ot_hbm_tu_shared8 #(parameter integer ENABLE=0)(
 input wire clk,rst_n,pclk,prst_n,
 input wire request_valid,output wire request_ready,input wire request_mode,
 input wire [7:0] request_rank,input wire [15:0] request_pf,
 input wire [63:0] request_operation,input wire [31:0] request_phase,
 input wire [1:0] endpoint_rearm_ready,endpoint_quiet_core,endpoint_quiet_phy,
 input wire finish_valid,input wire [63:0] finish_operation,input wire [31:0] finish_phase,
 input wire fabric_release_valid,input wire [63:0] fabric_release_operation,
 input wire [31:0] fabric_release_phase,
 input wire [7:0] ar_tx_v,ga_tx_v,input wire [4359:0] ar_tx_flit,ga_tx_flit,
 output reg [7:0] ph_tx_v,output reg [4359:0] ph_tx_flit,
 input wire [7:0] ph_rx_v,input wire [4359:0] ph_rx_flit,
 output wire [7:0] ar_rx_v,ga_rx_v,output wire [4359:0] endpoint_rx_flit,
 input wire [7:0] sw_cr_ret,output wire [7:0] ar_cr_ret,ga_cr_ret,
 input wire [7:0] ar_rx_credit,ga_rx_credit,output wire [7:0] rx_credit,
 output reg [1:0] endpoint_go,output reg retired,
 output reg [7:0] held_rank,output reg [15:0] held_pf,
 output reg [63:0] held_operation,output reg [31:0] held_phase,
 output wire busy,output wire held_mode,output wire fault
);
 generate if(!ENABLE) begin:g_off
 assign request_ready=0;assign ar_rx_v=0;assign ga_rx_v=0;assign endpoint_rx_flit=0;
 assign ar_cr_ret=0;assign ga_cr_ret=0;assign rx_credit=0;assign busy=0;assign held_mode=0;assign fault=0;
 always @* begin ph_tx_v=0;ph_tx_flit=0;endpoint_go=0;retired=0;held_rank=0;held_pf=0;held_operation=0;held_phase=0;end
 end else begin:g_on
 localparam [2:0] IDLE=0,ARM=1,RUN=2,DRAIN=3,OFF=4;
 reg [2:0] state;
 reg active,mode,sticky,phy_fault,finished;
 (* ASYNC_REG="TRUE" *) reg a1,a2,m1,m2;
 (* ASYNC_REG="TRUE" *) reg ack1,ack2,q1,q2,pf1,pf2;
 // Mode changes only while inactive. Two-domain acknowledgement keeps the
 // PHY owner stable before any GO; immutable context held through OFF.
 always @(posedge pclk or negedge prst_n) if(!prst_n)begin
 a1<=0;a2<=0;m1<=0;m2<=0;phy_fault<=0;ph_tx_v<=0;ph_tx_flit<=0;
 end else begin
 a1<=active;a2<=a1;m1<=mode;m2<=m1;
 ph_tx_v<=a2?(m2?ga_tx_v:ar_tx_v):8'b0;
 ph_tx_flit<=a2?(m2?ga_tx_flit:ar_tx_flit):4360'b0;
 if((a2&&|(m2?ar_tx_v:ga_tx_v))||(!a2&&(|ph_rx_v|| |ar_tx_v|| |ga_tx_v)))phy_fault<=1;
 end
 wire phy_quiet=endpoint_quiet_phy[m2]&&!ph_tx_v&&!ph_rx_v&&!ar_tx_v&&!ga_tx_v;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 ack1<=0;ack2<=0;q1<=0;q2<=0;pf1<=0;pf2<=0;
 end else begin ack1<=a2;ack2<=ack1;q1<=phy_quiet;q2<=q1;pf1<=phy_fault;pf2<=pf1;end
 assign request_ready=state==IDLE&&!sticky&&!pf2&&!ack2&&endpoint_rearm_ready[request_mode];
 assign ar_rx_v=(a2&&!m2)?ph_rx_v:8'b0;
 assign ga_rx_v=(a2&&m2)?ph_rx_v:8'b0;
 assign endpoint_rx_flit=ph_rx_flit; // only selected valid qualifies these bits
 assign ar_cr_ret=(active&&!mode)?sw_cr_ret:8'b0;
 assign ga_cr_ret=(active&&mode)?sw_cr_ret:8'b0;
 assign rx_credit=active?(mode?ga_rx_credit:ar_rx_credit):8'b0;
 assign busy=state!=IDLE;assign held_mode=mode;assign fault=sticky||pf2;
 wire matched_finish=finish_operation==held_operation&&finish_phase==held_phase;
 wire matched_release=fabric_release_operation==held_operation&&fabric_release_phase==held_phase;
 always @(posedge clk or negedge rst_n)if(!rst_n)begin
 state<=IDLE;active<=0;mode<=0;sticky<=0;finished<=0;endpoint_go<=0;retired<=0;
 held_rank<=0;held_pf<=0;held_operation<=0;held_phase<=0;
 end else begin
 endpoint_go<=0;retired<=0;
 if(!active&&|sw_cr_ret)sticky<=1;
 if(finish_valid&&(state!=RUN||!matched_finish))sticky<=1;
 if(fabric_release_valid&&(state!=DRAIN||!matched_release))sticky<=1;
 case(state)
 IDLE:if(request_valid&&request_ready)begin
   if(request_rank>=96||request_pf==0||request_pf>384||(!request_mode&&request_pf[3:0]!=0))sticky<=1;
   else begin held_rank<=request_rank;held_pf<=request_pf;held_operation<=request_operation;
    held_phase<=request_phase;mode<=request_mode;active<=1;finished<=0;state<=ARM;end
 end
 ARM:if(ack2&&!sticky&&!pf2)begin endpoint_go<=mode?2'b10:2'b01;state<=RUN;end
 RUN:if(finish_valid&&matched_finish&&!sticky&&!pf2)begin finished<=1;state<=DRAIN;end
 DRAIN:if(finished&&fabric_release_valid&&matched_release&&endpoint_quiet_core[mode]&&q2&&!sticky&&!pf2)begin
   active<=0;state<=OFF;
 end
 OFF:if(!ack2&&!sticky&&!pf2)begin retired<=1;state<=IDLE;end
 default:sticky<=1;
 endcase
 end
 end endgenerate
endmodule
