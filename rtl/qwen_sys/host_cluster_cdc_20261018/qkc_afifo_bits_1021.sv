// Opt-in bit-sliced completion FIFO. Each instance is the unmodified reviewed
// ot_link_afifo with W=1 and the original AW/SYNC. No extra cycle or handshake.
module qkc_afifo_bits_1021 #(
    parameter integer W=64, AW=4, SYNC=2,
    parameter integer MUT_ROTATE=0
)(
    input wire wclk,wrst_n,wr,
    input wire [W-1:0] wdata,
    output wire wfull,output wire [AW:0] wfreed,output wire ovf,
    input wire rclk,rrst_n,rd,
    output wire rempty,output wire [W-1:0] rdata,output wire [AW:0] rcount
);
    wire [W-1:0] full_b,empty_b,ovf_b,head;
    wire [(AW+1)*W-1:0] freed_b,count_b;
    for(genvar b=0;b<W;b=b+1)begin:g_bit
        (* keep_hierarchy="yes" *)
        ot_link_afifo #(.W(1),.AW(AW),.SYNC(SYNC)) u_fifo(
            .wclk(wclk),.wrst_n(wrst_n),.wr(wr),.wdata(wdata[b]),
            .wfull(full_b[b]),.wfreed(freed_b[(AW+1)*b +: AW+1]),.ovf(ovf_b[b]),
            .rclk(rclk),.rrst_n(rrst_n),.rd(rd),.rempty(empty_b[b]),
            .rdata(head[b]),.rcount(count_b[(AW+1)*b +: AW+1])
        );
    end
    // These control outputs depend only on the shared clocks/reset/wr/rd;
    // wdata does not affect them. Every slice therefore has the original state.
    assign wfull=full_b[0];assign wfreed=freed_b[AW:0];assign ovf=ovf_b[0];
    assign rempty=empty_b[0];assign rcount=count_b[AW:0];
    assign rdata=(MUT_ROTATE!=0)?{head[W-2:0],head[W-1]}:head;
endmodule
