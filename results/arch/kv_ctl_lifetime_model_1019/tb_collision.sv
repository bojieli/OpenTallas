module tb;
reg ck=0; always #5 ck=~ck;
reg rst_n=0,cfg_we=0,start=0; reg[7:0]cfg_addr=0;reg[63:0]cfg_data=4;
wire fault,active;
qkd_kv_native_programme #(.SRAM(1)) d(.ck(ck),.rst_n(rst_n),.cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start(start),.stage(6'd1),.epoch(16'd0),.token(18'd0),.position(13'd0),.generation(2'd0),.fault(fault),.active(active));
integer collisions=0;
always @(posedge ck) if(d.start_p && d.wq_v && d.g_sr.wq_row==d.selected_stage-1)begin
collisions=collisions+1;
$display("WRITER_RAW_START_COLLISION t=%0t configured=%b active=%b fault=%b row=%d accepted_cfg=%b",$time,d.configured,active,fault,d.g_sr.wq_row,d.accept_cfg);
end
initial begin
repeat(4)@(negedge ck);rst_n=1;
repeat(3)@(negedge ck);cfg_we=1;
@(negedge ck);cfg_we=0;start=1;
@(negedge ck);start=0;
repeat(3)@(negedge ck);
if(collisions!=1 || fault!==1 || active!==0)$fatal(1,"missing witness");
$display("PASS real source collision is reachable and rejected start remains inactive");$finish;
end
endmodule
