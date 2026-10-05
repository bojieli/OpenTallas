`timescale 1ns/1ps
module tb_hdc_v41x_idx_pool_hbm_bridge;
    localparam NPC=4, AW=28, N=4*NPC;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,w_v=0;
    wire w_rdy,busy;
    reg [N-1:0] r_v=0;
    wire [N-1:0] r_rdy,h_v,h_rdy,h_we,h_wr_done;
    reg [N*AW-1:0] r_addr=0;
    reg [N*4-1:0] r_len=0;
    reg [N*16-1:0] r_tag=0;
    wire [N*AW-1:0] h_addr;
    wire [N*4-1:0] h_len;
    wire [N*16-1:0] h_tag;
    wire [N*256-1:0] h_wdata;
    wire [N*32-1:0] h_wstrb;
    wire [N-1:0] rsp_v;
    wire [N*256-1:0] rsp_data;
    wire [31:0] records,writes,highwater,read_stalls,writer_stalls;
    localparam [255:0] C0=256'h0123456789abcdef;
    localparam [255:0] C1=256'hfedcba9876543210;
    ot_hdc_v41x_idx_pool_hbm_bridge #(.NPC(NPC)) bridge (
        .clk(clk),.rst_n(rst_n),.w_v(w_v),.w_rdy(w_rdy),.w_stack_mask(4'hf),
        .w_csec(28'd128),.w_codes({C1,C0}),.w_ssec(28'd0),.w_sslot(3'd3),
        .w_scales(32'h78563412),.r_v(r_v),.r_rdy(r_rdy),.r_addr(r_addr),.r_len(r_len),
        .r_tag(r_tag),.h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),.h_len(h_len),
        .h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),.h_wstrb(h_wstrb),
        .h_wr_done(h_wr_done),.busy(busy),.dbg_records(records),.dbg_writes(writes),
        .dbg_fifo_highwater(highwater),.dbg_read_stalls(read_stalls),
        .dbg_writer_stalls(writer_stalls));
    for(genvar s=0;s<4;s=s+1) begin : g_stack
        wire [NPC*16-1:0] rt;
        wire [NPC*4-1:0] rb;
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(256),.MEM_WORDS(256),
            .TAGW(16),.LENW(4),.BEATW(4),.QD(16),.RQD(8),.REFPB(3),.MEM_MODE(0)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_v[s*NPC +: NPC]),.req_rdy(h_rdy[s*NPC +: NPC]),
            .req_addr(h_addr[s*NPC*AW +: NPC*AW]),.req_len(h_len[s*NPC*4 +: NPC*4]),
            .req_tag(h_tag[s*NPC*16 +: NPC*16]),.req_we(h_we[s*NPC +: NPC]),
            .req_wdata(h_wdata[s*NPC*256 +: NPC*256]),.req_wstrb(h_wstrb[s*NPC*32 +: NPC*32]),
            .wr_done(h_wr_done[s*NPC +: NPC]),.rsp_v(rsp_v[s*NPC +: NPC]),
            .rsp_rdy({NPC{1'b1}}),.rsp_tag(rt),.rsp_beat(rb),
            .rsp_data(rsp_data[s*NPC*256 +: NPC*256]));
        initial for(integer i=0;i<256;i=i+1) hm.mem[i]=0;
    end
    integer errors=0,accepted=0,returned=0;
    function automatic integer pc(input integer sec);
        pc=((sec>>2)^(sec>>4)^(sec>>6)) & (NPC-1);
    endfunction
    task automatic read_all(input integer sec,input [255:0] expected);
        integer p;
        begin
            accepted=0;returned=0;
            @(negedge clk);
            for(integer s=0;s<4;s=s+1) begin
                p=s*NPC+pc(sec);
                r_v[p]=1;
                r_addr[p*AW +: AW]=sec;
                r_len[p*4 +: 4]=1;
                r_tag[p*16 +: 16]=sec;
            end
            while(returned<4) begin
                @(posedge clk);
                for(integer s=0;s<4;s=s+1) begin
                    p=s*NPC+pc(sec);
                    if(r_v[p] && r_rdy[p]) begin r_v[p]=0;accepted=accepted+1;end
                    if(rsp_v[p]) begin
                        returned=returned+1;
                        if(rsp_data[p*256 +: 256]!==expected) errors=errors+1;
                    end
                end
            end
            if(accepted!=4) errors=errors+1;
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        @(negedge clk);w_v=1;
        r_v[pc(128)]=1;r_addr[pc(128)*AW +: AW]=128;r_len[pc(128)*4 +: 4]=1;
        #1;if(r_rdy[pc(128)]) errors=errors+1;
        @(negedge clk);w_v=0;
        // A read presented during a write must remain held until all stacks
        // have committed both code sectors and the masked scale update.
        repeat(3) begin @(posedge clk);if(r_rdy[pc(128)]) errors=errors+1;end
        @(negedge clk);r_v=0;
        wait(!busy);
        if(records!=1 || writes!=12) errors=errors+1;
        read_all(128,C0);
        read_all(129,C1);
        read_all(0,({224'd0,32'h78563412} << 96));
        // Fill the four-record queue, then hold one more record while HBM
        // drains. The fifth handshake must occur only after a slot opens.
        @(negedge clk);w_v=1;
        repeat(4) @(posedge clk);
        @(negedge clk);
        if(w_rdy) errors=errors+1;
        wait(w_rdy);
        @(posedge clk);
        @(negedge clk);w_v=0;
        wait(!busy);
        if(records!=6 || writes!=72 || highwater!=4 || read_stalls==0 || writer_stalls==0) errors=errors+1;
        $display("V41XPOOLHBMWR records=%0d writes=%0d reads=%0d highwater=%0d read_stalls=%0d writer_stalls=%0d errors=%0d",
            records,writes,returned,highwater,read_stalls,writer_stalls,errors);
        $finish;
    end
    initial begin #200000;$display("V41XPOOLHBMWR TIMEOUT");$finish;end
endmodule
