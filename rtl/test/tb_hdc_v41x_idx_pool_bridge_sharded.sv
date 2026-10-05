`timescale 1ns/1ps
module tb_hdc_v41x_idx_pool_bridge_sharded;
    localparam NPC=4, AW=28, N=4*NPC;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0,w_v=0;
    reg [3:0] mask=0;
    reg [27:0] code_sec=0,scale_sec=0;
    reg [511:0] codes=0;
    reg [31:0] scales=0;
    wire w_rdy,busy;
    reg [N-1:0] r_v=0;
    wire [N-1:0] r_rdy,h_v,h_rdy,h_we,h_wr_done,rsp_v;
    reg [N*AW-1:0] r_addr=0;
    wire [N*AW-1:0] h_addr;
    wire [N*4-1:0] h_len,rsp_beat;
    wire [N*16-1:0] h_tag,rsp_tag;
    wire [N*256-1:0] h_wdata,rsp_data;
    wire [N*32-1:0] h_wstrb;
    wire [31:0] records,writes,highwater,read_stalls,writer_stalls;
    ot_hdc_v41x_idx_pool_hbm_bridge #(.NPC(NPC)) bridge (
        .clk(clk),.rst_n(rst_n),.w_v(w_v),.w_rdy(w_rdy),.w_stack_mask(mask),
        .w_csec(code_sec),.w_codes(codes),.w_ssec(scale_sec),.w_sslot(3'd0),
        .w_scales(scales),.r_v(r_v),.r_rdy(r_rdy),.r_addr(r_addr),.r_len({N{4'b0001}}),
        .r_tag({N{16'd1}}),.h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),
        .h_len(h_len),.h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),.h_wstrb(h_wstrb),
        .h_wr_done(h_wr_done),.busy(busy),.dbg_records(records),.dbg_writes(writes),
        .dbg_fifo_highwater(highwater),.dbg_read_stalls(read_stalls),.dbg_writer_stalls(writer_stalls));
    for(genvar s=0;s<4;s=s+1) begin:g_stack
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(256),.MEM_WORDS(512),
            .TAGW(16),.LENW(4),.BEATW(4),.QD(16),.RQD(8),.REFPB(3),.MEM_MODE(0)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_v[s*NPC +: NPC]),.req_rdy(h_rdy[s*NPC +: NPC]),
            .req_addr(h_addr[s*NPC*AW +: NPC*AW]),.req_len(h_len[s*NPC*4 +: NPC*4]),
            .req_tag(h_tag[s*NPC*16 +: NPC*16]),.req_we(h_we[s*NPC +: NPC]),
            .req_wdata(h_wdata[s*NPC*256 +: NPC*256]),.req_wstrb(h_wstrb[s*NPC*32 +: NPC*32]),
            .wr_done(h_wr_done[s*NPC +: NPC]),.rsp_v(rsp_v[s*NPC +: NPC]),
            .rsp_rdy({NPC{1'b1}}),.rsp_tag(rsp_tag[s*NPC*16 +: NPC*16]),
            .rsp_beat(rsp_beat[s*NPC*4 +: NPC*4]),.rsp_data(rsp_data[s*NPC*256 +: NPC*256]));
        initial for(integer i=0;i<512;i=i+1) hm.mem[i]=0;
    end
    integer errors=0,reads=0,stalls=0;
    function automatic integer pc(input integer sec);
        pc=((sec>>2)^(sec>>4)^(sec>>6)) & (NPC-1);
    endfunction
    task automatic write_one(input integer stack,input integer sec,input [255:0] value);
        integer p,guard;
        begin
            p=stack*NPC+pc(sec);
            @(negedge clk); mask=4'b1<<stack;code_sec=sec;scale_sec=0;
            codes={256'd0,value};scales=32'(stack+1);w_v=1;
            if(stack==0) begin
                r_v[p]=1;r_addr[p*AW +: AW]=sec;
                #1;if(r_rdy[p]) errors=errors+1;
            end
            @(negedge clk);w_v=0;
            if(stack==0) begin
                guard=0;
                while(busy && guard<1000) begin
                    if(r_rdy[p]) errors=errors+1;
                    @(negedge clk);guard=guard+1;
                end
                if(guard>=1000) $fatal(1,"write collision timeout");
                wait(r_rdy[p]);
                @(posedge clk);
                @(negedge clk);r_v[p]=0;
                wait(rsp_v[p]);
                if(rsp_data[p*256 +: 256] !== value) errors=errors+1;
                @(negedge clk);
            end
            wait(!busy);
        end
    endtask
    task automatic read_one(input integer stack,input integer sec,input [255:0] expected);
        integer p,cycles;
        begin
            p=stack*NPC+pc(sec);
            @(negedge clk);r_v[p]=1;r_addr[p*AW +: AW]=sec;
            cycles=0;
            while(!r_rdy[p] && cycles<1000) begin @(negedge clk);cycles=cycles+1;stalls=stalls+1;end
            if(cycles>=1000) $fatal(1,"read blocked");
            @(posedge clk); if(!r_rdy[p]) errors=errors+1;
            @(negedge clk);r_v[p]=0;
            cycles=0;
            while(!rsp_v[p] && cycles<1000) begin @(negedge clk);cycles=cycles+1;end
            if(cycles>=1000) $fatal(1,"read response timeout");
            if(rsp_data[p*256 +: 256] !== expected) errors=errors+1;
            reads=reads+1;
            @(negedge clk);
        end
    endtask
    initial begin
        repeat(3) @(negedge clk);rst_n=1;
        write_one(0,128,256'h1111);write_one(1,128,256'h2222);
        write_one(2,128,256'h3333);write_one(3,128,256'h4444);
        read_one(0,128,256'h1111);read_one(1,128,256'h2222);
        read_one(2,128,256'h3333);read_one(3,128,256'h4444);
        read_one(0,0,256'h1);read_one(1,0,256'h2);
        read_one(2,0,256'h3);read_one(3,0,256'h4);
        if(records!=4 || writes!=12 || reads!=8) errors=errors+1;
        $display("V41XPOOLBRIDGESHARD records=%0d writes=%0d reads=%0d errors=%0d",records,writes,reads,errors);
        if(errors) $fatal(1,"sharded bridge mismatch");
        $finish;
    end
    initial begin #300000;$fatal(1,"sharded bridge timeout");end
endmodule
