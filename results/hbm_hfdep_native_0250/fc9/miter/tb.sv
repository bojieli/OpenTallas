`timescale 1ns/1ps
module tb; reg clk=0; always #5 clk=~clk; integer c,j,checks=0,diff=0,nonzero_fault=0;
reg rst_n;
reg tx_v;
reg [611:0] tx_frame;
reg rx_arm_v;
reg rx_arm_bank;
reg [6:0] rx_block_words;
reg rx_release_v;
reg rx_release_bank;
reg rx_slot_v;
reg rx_slot_bank;
reg [5:0] rx_slot_index;
wire g_rx_pin_v;
wire n_rx_pin_v;
wire [611:0] g_rx_pin_flit;
wire [611:0] n_rx_pin_flit;
wire [1:0] g_rx_block_ready;
wire [1:0] n_rx_block_ready;
wire g_phy_up;
wire n_phy_up;
wire g_fault;
wire n_fault;
wire [10:0] g_fault_cause;
wire [8:0] n_fault_cause;
wire [511:0] g_sd_tx;
wire [511:0] n_sd_tx;
reg [511:0] sd_rx;
reg [1:0] sd_st;
hfd_ep_static #(.IDLE_K(204),.MUT(0)) g(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_frame(tx_frame),.rx_arm_v(rx_arm_v),.rx_arm_bank(rx_arm_bank),.rx_block_words(rx_block_words),.rx_release_v(rx_release_v),.rx_release_bank(rx_release_bank),.rx_slot_v(rx_slot_v),.rx_slot_bank(rx_slot_bank),.rx_slot_index(rx_slot_index),.rx_pin_v(g_rx_pin_v),.rx_pin_flit(g_rx_pin_flit),.rx_block_ready(g_rx_block_ready),.phy_up(g_phy_up),.fault(g_fault),.fault_cause(g_fault_cause),.sd_tx(g_sd_tx),.sd_rx(sd_rx),.sd_st(sd_st));
hfd_ep_static_fc9 #(.IDLE_K(204),.MUT(0)) n(.clk(clk),.rst_n(rst_n),.tx_v(tx_v),.tx_frame(tx_frame),.rx_arm_v(rx_arm_v),.rx_arm_bank(rx_arm_bank),.rx_block_words(rx_block_words),.rx_release_v(rx_release_v),.rx_release_bank(rx_release_bank),.rx_slot_v(rx_slot_v),.rx_slot_bank(rx_slot_bank),.rx_slot_index(rx_slot_index),.rx_pin_v(n_rx_pin_v),.rx_pin_flit(n_rx_pin_flit),.rx_block_ready(n_rx_block_ready),.phy_up(n_phy_up),.fault(n_fault),.fault_cause(n_fault_cause),.sd_tx(n_sd_tx),.sd_rx(sd_rx),.sd_st(sd_st));
initial begin
rst_n='0;
tx_v='0;
tx_frame='0;
rx_arm_v='0;
rx_arm_bank='0;
rx_block_words='0;
rx_release_v='0;
rx_release_bank='0;
rx_slot_v='0;
rx_slot_bank='0;
rx_slot_index='0;
sd_rx='0;
sd_st='0;
rst_n=1; #1; rst_n=0;
for(c=0;c<2600;c=c+1) begin @(negedge clk);
rst_n=!((c<4)||(c>=1200&&c<1204)||(c>=2450&&c<2454));
tx_v=$urandom;
for(j=0;j<19;j=j+1)tx_frame[j*32+:32]=$urandom;
tx_frame[611:608]=$urandom;
rx_arm_v=$urandom;
rx_arm_bank=$urandom;
rx_block_words=$urandom;
rx_release_v=$urandom;
rx_release_bank=$urandom;
rx_slot_v=$urandom;
rx_slot_bank=$urandom;
rx_slot_index=$urandom;
for(j=0;j<16;j=j+1)sd_rx[j*32+:32]=$urandom;
sd_st=$urandom;
if(c%7==0)rx_block_words=0; if(c%11==0)rx_block_words=65;
@(posedge clk);#1;
checks=checks+1;if(n_rx_pin_v !== g_rx_pin_v)begin diff=diff+1;if(diff<5)$display("DIFF rx_pin_v cycle%0d",c);end
checks=checks+1;if(n_rx_pin_flit !== g_rx_pin_flit)begin diff=diff+1;if(diff<5)$display("DIFF rx_pin_flit cycle%0d",c);end
checks=checks+1;if(n_rx_block_ready !== g_rx_block_ready)begin diff=diff+1;if(diff<5)$display("DIFF rx_block_ready cycle%0d",c);end
checks=checks+1;if(n_phy_up !== g_phy_up)begin diff=diff+1;if(diff<5)$display("DIFF phy_up cycle%0d",c);end
checks=checks+1;if(n_fault !== g_fault)begin diff=diff+1;if(diff<5)$display("DIFF fault cycle%0d",c);end
checks=checks+1;if(n_fault_cause !== {g_fault_cause[10:5],g_fault_cause[2:0]})begin diff=diff+1;if(diff<5)$display("DIFF fault_cause cycle%0d",c);end
checks=checks+1;if(n_sd_tx !== g_sd_tx)begin diff=diff+1;if(diff<5)$display("DIFF sd_tx cycle%0d",c);end
if(g_fault===1)nonzero_fault=nonzero_fault+1;
end
$display("HF_FC9 checks=%0d diff=%0d fault_active=%0d",checks,diff,nonzero_fault);if(diff)$fatal(1,"FC9 projected source mismatch");if(nonzero_fault==0)$fatal(1,"vacuousfault");$display("HF_FC9_EQ_PASS");$finish;end endmodule
