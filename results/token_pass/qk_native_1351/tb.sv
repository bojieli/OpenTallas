`timescale 1ns/1ps
module tb;
reg ck=0;always #0.4165 ck=~ck;
reg rst_n=0,reload=0,epoch_go=0,halt=0,tx=0,rx=0;
reg [5:0] addr=0;reg [31:0] data=0;
wire fault; integer mode=0, i;reg[63:0] words[0:65];
qkd_d2d_cal_seq_pin_bc4 dut(.ck(ck),.rst_n(rst_n),.reload(reload),.epoch_go(epoch_go),.halt(halt),.bcfg_tx_we(tx),.bcfg_rx_we(rx),.bcfg_addr(addr),.bcfg_data(data),.fault(fault));
initial begin
void'($value$plusargs("MUT=%d",mode));$readmemh("link.hex",words);
repeat(12)@(negedge ck);rst_n=1;repeat(120)@(negedge ck);
$display("PROFILE tx=%0d rx=%0d period=%0d ready=%b",dut.profile_tx_seg2,dut.profile_rx_seg2,dut.profile_period,dut.cal_ready);
for(i=0;i<66;i=i+1)begin
 tx=(i<32||i==64);rx=(i>=32&&i<64||i==65);addr=(i>=64?32:(i%32));data=words[i][31:0];
 if(mode==1&&i==65)data=data^1;
 if(mode==2)data=(i==0?0:words[i-1][31:0]);
 @(negedge ck);
end
tx=0;rx=0;repeat(12)@(negedge ck);
$display("RESULT mode=%0d fault=%b col=%b run=%b stale=%b early=%b seq=%b",mode,fault,dut.f_col,dut.f_run,dut.f_stale,dut.f_early,dut.s_fault);
if(mode==0&&fault)$fatal(1,"nominal fault");if(mode!=0&&!fault)$fatal(1,"mutant missed");$display("DCAL_BOOT_REPLAY PASS");$finish;
end
endmodule
