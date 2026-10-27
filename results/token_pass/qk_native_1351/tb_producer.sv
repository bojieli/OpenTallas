`timescale 1ns/1ps
module tb_producer;
reg ck=0;always #0.4165 ck=~ck; reg rst_n=0;
reg [142:0] pr=0;reg[3:0]target=0;reg ready=0;wire ptx,prx,pfault;wire[5:0]pa;wire[31:0]pd;wire[7:0]pcode;
qkd_static_kv_boot_dispatch_nc32 #(.LINKCFG(1),.DSTG(1),.SRQ(2)) p(.ck(ck),.rst_n(rst_n),.boot_pr(pr),.boot_addr_b(pr[73:64]),.boot_image_target(target),.boot_gix(5'(pr[73:64]/6)),.boot_rem6(3'(pr[73:64]%6)),.boot_seal(1'b0),.boot_addr_raw(pr[73:64]),.boot_image_ready(ready),.boot_image_fault(1'b0),.boot_image_epoch(16'd2827),.boot_image_digest(64'b0),.execution_active(1'b0),.sink_applied('1),.local_configured(3'b111),.sink_fault(1'b0),.diecfg_sealed(1'b1),.diecfg_fault(1'b0),.link_cfg_tx_we(ptx),.link_cfg_rx_we(prx),.link_cfg_addr(pa),.link_cfg_data(pd),.fault(pfault),.fault_code(pcode));
reg [1:0]tw=0,rw=0;reg[5:0]a0=0,a1=0;reg[31:0]d0=0,d1=0;
always @(posedge ck) begin tw<={tw[0],ptx};rw<={rw[0],prx};a0<=pa;a1<=a0;d0<=pd;d1<=d0;end
wire oldfault,goodfault;
qkd_d2d_cal_seq_pin_bc4 old(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(1'b0),.halt(1'b0),.bcfg_tx_we(tw[0]),.bcfg_rx_we(rw[0]),.bcfg_addr(a1),.bcfg_data(d1),.fault(oldfault));
qkd_d2d_cal_seq_pin_bc4 good(.ck(ck),.rst_n(rst_n),.reload(1'b0),.epoch_go(1'b0),.halt(1'b0),.bcfg_tx_we(tw[1]),.bcfg_rx_we(rw[1]),.bcfg_addr(a1),.bcfg_data(d1),.fault(goodfault));
reg[95:0]words[0:5067];integer i,n=0;
always @(negedge ck)if(rst_n&&pfault)$fatal(1,"PRODUCER fault=%h",pcode);
initial begin $readmemh("producer.hex",words);repeat(12)@(negedge ck);rst_n=1;repeat(120)@(negedge ck);
for(i=0;i<5068;i=i+1)begin
 target=words[i][83:80];ready=words[i][95];pr=0;
 if(!ready)begin pr[74]=1;pr[73:0]=words[i][73:0];end
 @(negedge ck);
 if(ready)begin ready=0;repeat(2)@(negedge ck);end
end
pr=0;ready=0;repeat(12)@(negedge ck);
$display("PRODUCER_REPLAY old_fault=%b stale=%b col=%b run=%b early=%b good_fault=%b",oldfault,old.f_stale,old.f_col,old.f_run,old.f_early,goodfault);
if(!oldfault||!old.f_stale||goodfault)$fatal(1,"R8 relation diagnosis failed");$display("DCAL_PRODUCER_R8 PASS");$finish;end
endmodule
