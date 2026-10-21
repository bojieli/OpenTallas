module cxbits_cdc(input wclk,rclk,rst_n,wr,rd,input[63:0]wdata,output wfull,ovf,rempty,output[4:0]wfreed,rcount,output reg[63:0]q,output reg q_v);
wire[3:0]wb,rb;wire wn=wb[0],rn=rb[0];wire[63:0]raw,local_valid;
ot_host_reset_bank #(.N(4)) uw(.clk(wclk),.async_rst_n(rst_n),.sync_rst_n(wb));
ot_host_reset_bank #(.N(4)) ur(.clk(rclk),.async_rst_n(rst_n),.sync_rst_n(rb));
qkc_afifo_bits_1021 #(.RESET_BUSES(1)) u(.wrst_bits({64{wn}}),.rrst_bits({64{rn}}),.wclk(wclk),.wrst_n(wn),.wr(wr),.wdata(wdata),.wfull(wfull),.wfreed(wfreed),.ovf(ovf),.rclk(rclk),.rrst_n(rn),.rd(rd),.rempty(rempty),.rdata(raw),.rd_valid(local_valid),.rcount(rcount));
for(genvar b=0;b<64;b=b+1)begin:g_capture
 always @(posedge rclk)if(rd&&local_valid[b])q[b]<=raw[b];
end
always @(posedge rclk or negedge rn)if(!rn)q_v<=0;else q_v<=rd&&!rempty;
endmodule
