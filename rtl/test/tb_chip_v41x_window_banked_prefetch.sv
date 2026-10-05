`timescale 1ns/1ps
module tb_chip_v41x_window_banked_prefetch;
    localparam integer BASE=64, COUNT=2*2176, HAW=30, TAGW=16;
    reg clk=0; always #2 clk=~clk;
    reg rst_n=0, prime_v=0, prefetch_v=0, bank_req_v=0;
    reg [9:0] user=0, bank_user=0;
    reg [20:0] prime_row=0, prefetch_row=0, bank_first=0;
    reg [3:0] bank_mask=0;
    wire prime_ready, prefetch_ready, kv_ok, bank_ready, bank_rsp_v, bank_fault, fault;
    wire [9:0] bank_rsp_user;
    wire [20:0] bank_rsp_first;
    wire [3:0] bank_rsp_mask, bank_valid;
    wire [4*4224-1:0] bank_rows;
    wire [4:0] fault_code;
    wire [3:0] m_v,m_we,s_rdy;
    reg [3:0] m_rdy=4'hf, s_v=0;
    wire [4*HAW-1:0] m_addr;
    wire [15:0] m_len;
    wire [4*TAGW-1:0] m_tag;
    reg [4*TAGW-1:0] s_tag=0;
    wire [1023:0] m_wdata;
    wire [127:0] m_wstrb;
    reg [1023:0] s_data=0;
    wire [31:0] st_rows,st_blocks,st_reads,st_writes;
    reg [255:0] mem [0:BASE+COUNT-1];
    integer c=0, accepted=0, responses=0, lane;
    reg [4223:0] expected;
    ot_chip_v41x_window_kv_prefetch #(.BANKED_STAGE(1),.WIN_STACK(2)) dut (
        .clk(clk),.rst_n(rst_n),.region_base_sector(30'(BASE)),.region_sector_count(30'(COUNT)),
        .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(user),.prime_row(prime_row),
        .blk_v(1'b0),.blk_ready(),.blk_user(10'd0),.blk_row(21'd0),.blk_idx(4'd0),
        .blk_codes(256'd0),.blk_scale(8'd0),
        .prefetch_v(prefetch_v),.prefetch_ready(prefetch_ready),.prefetch_user(user),
        .prefetch_row(prefetch_row),.kv_ok(kv_ok),
        .re(1'b0),.ruser(user),.rrow(prefetch_row),.relem(9'd0),.q(),
        .packed_re(1'b0),.packed_ruser(user),.packed_rrow(prefetch_row),.packed_ridx(4'd0),
        .packed_valid(),.packed_row(),.packed_codes(),.packed_scale(),
        .bank_req_v(bank_req_v),.bank_req_ready(bank_ready),.bank_req_user(bank_user),
        .bank_req_first(bank_first),.bank_req_mask(bank_mask),
        .bank_rsp_v(bank_rsp_v),.bank_rsp_user(bank_rsp_user),.bank_rsp_first(bank_rsp_first),
        .bank_rsp_mask(bank_rsp_mask),.bank_rsp_valid_mask(bank_valid),
        .bank_rsp_rows(bank_rows),.bank_rsp_fault(bank_fault),
        .fault(fault),.fault_code(fault_code),.st_rows_fetched(st_rows),
        .st_blocks_written(st_blocks),.st_sectors_read(st_reads),.st_sectors_written(st_writes),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_len(m_len),.m_tag(m_tag),
        .m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),.m_wr_done(4'd0),
        .s_v(s_v),.s_rdy(s_rdy),.s_tag(s_tag),.s_beat(16'd0),.s_data(s_data));
    always @(posedge clk) begin
        c <= c+1; s_v <= 0;
        if (rst_n && m_v[2] && m_rdy[2]) begin
            if (m_we[2] || m_len[11:8] != 1 ||
                m_addr[2*HAW +: HAW] < BASE || m_addr[2*HAW +: HAW] >= BASE+COUNT)
                $fatal(1,"bad banked HBM request");
            s_tag[2*TAGW +: TAGW] <= m_tag[2*TAGW +: TAGW];
            s_data[2*256 +: 256] <= mem[m_addr[2*HAW +: HAW]];
            s_v[2] <= 1;
        end
    end
    task automatic prime(input integer p,input integer u);
        begin
            while(!prime_ready) @(negedge clk);
            @(negedge clk); prime_v=1; prime_row=21'(p); user=10'(u);
            @(negedge clk); prime_v=0;
        end
    endtask
    task automatic fetch(input integer p,input integer u);
        begin
            while(!prefetch_ready) @(negedge clk);
            @(negedge clk); prefetch_v=1; prefetch_row=21'(p); user=10'(u);
            @(negedge clk); prefetch_v=0;
            while(!kv_ok && !fault) @(negedge clk);
            if(fault || !kv_ok) $fatal(1,"banked prefetch failed row %0d",p);
        end
    endtask
    task automatic request(input integer p,input integer u,input [3:0] mask);
        begin
            if(!bank_ready) $fatal(1,"bank backpressure");
            @(negedge clk); bank_req_v=1; bank_user=10'(u); bank_first=21'(p); bank_mask=mask;
            accepted=accepted+1;
            @(negedge clk); bank_req_v=0;
            while(!bank_rsp_v) @(negedge clk);
            if(bank_rsp_user!==10'(u) || bank_rsp_first!==21'(p) || bank_rsp_mask!==mask)
                $fatal(1,"bank response tag mismatch");
            if(u==0 && p==126 && mask==4'hf) begin
                if(bank_fault || bank_valid!==4'hf) $fatal(1,"four bank rows unavailable");
                for(lane=0;lane<4;lane=lane+1) begin
                    expected=0;
                    for(integer s=0;s<16;s=s+1)
                        expected[256*s +: 256]=mem[BASE+17*(126+lane-128*(126+lane>=128))+s];
                    expected[4096 +: 128]=mem[BASE+17*(126+lane-128*(126+lane>=128))+16][127:0];
                    if(bank_rows[lane*4224 +: 4224]!==expected)
                        $fatal(1,"banked packed row mismatch lane %0d",lane);
                end
            end else if(u==1 && p==126 && mask==4'h1) begin
                if(!bank_fault || bank_valid!==0 || bank_rows[0 +: 4224]!==0)
                    $fatal(1,"wrong user row leaked");
            end
            responses=responses+1;
        end
    endtask
    integer i,s,p;
    initial begin
        for(i=0;i<BASE+COUNT;i=i+1) mem[i]=0;
        for(p=126;p<=129;p=p+1)
            for(s=0;s<17;s=s+1) begin
                mem[BASE+17*(p-128*(p>=128))+s]={32{8'(32+(p+s)%50)}};
                if(s==16) mem[BASE+17*(p-128*(p>=128))+s][255:128]=0;
            end
        repeat(4) @(negedge clk); rst_n=1;
        for(p=126;p<=129;p=p+1) begin prime(p,0); fetch(p,0); end
        request(126,0,4'hf);
        request(126,1,4'h1);
        if(st_rows!=4 || st_reads!=68 || fault || accepted!=2 || responses!=2)
            $fatal(1,"banked prefetch counters mismatch");
        // A poisoned HBM scale byte is rejected before the row becomes valid.
        mem[BASE+17*2+16][7:0]=8'hff;
        prime(130,0);
        while(!prefetch_ready) @(negedge clk);
        @(negedge clk); prefetch_v=1; prefetch_row=130; user=0;
        @(negedge clk); prefetch_v=0;
        while(!fault) @(negedge clk);
        if(!fault_code[4] || st_rows!=4) $fatal(1,"poisoned refill accepted");
        if(st_reads!=84) $fatal(1,"poisoned scale read count mismatch");
        // A poisoned FP8 code in the first sector likewise never publishes a row.
        mem[BASE+17*3][7:0]=8'h7f;
        prime(131,0);
        while(!prefetch_ready) @(negedge clk);
        @(negedge clk); prefetch_v=1; prefetch_row=131; user=0;
        @(negedge clk); prefetch_v=0;
        repeat(8) @(negedge clk);
        if(st_reads!=84 || st_rows!=4 || !fault_code[4])
            $fatal(1,"poisoned code refill accepted");
        $display("WINDOW_BANKED_PREFETCH_PASS fetched=4 sectors=68 rows_per_beat=4 users=2 poison=2");
        $finish;
    end
    initial begin #1000000; $fatal(1,"banked prefetch timeout"); end
endmodule
