`timescale 1ns/1ps
module tb_chip_v41x_ckv_selected_dma;
    localparam integer BASE=96, COUNT=81, HAW=30, TAGW=16;
    reg clk=0; always #1 clk=~clk;
    reg rst_n=0, fetch_v=0, re=0;
    reg [9:0] local_row=0, rrow=0;
    reg [7:0] window_count=128;
    reg [20:0] source_id=0, published_source_count=8;
    reg [8:0] relem=0;
    wire fetch_ready, kv_ok, packed_valid, fault;
    wire [31:0] q, rows, sectors;
    wire [7:0] q_fp8;
    wire [2303:0] packed_row;
    wire [9:0] packed_local_row;
    wire [20:0] packed_source_id;
    wire [3:0] fault_code, m_v, m_we, s_rdy;
    wire [119:0] m_addr;
    wire [15:0] m_len, s_beat;
    wire [63:0] m_tag, s_tag;
    wire [1023:0] m_wdata, s_data;
    wire [127:0] m_wstrb;
    reg [3:0] s_v=0;
    reg [63:0] rsp_tag=0;
    reg [1023:0] rsp_data=0;
    reg [255:0] mem [0:BASE+COUNT-1];
    reg [255:0] fixture [0:17];
    reg [7:0] expected [0:1023];
    reg [31:0] expected_fp32 [0:1023];
    integer errors=0, checked=0, i, addr;
    ot_chip_v41x_ckv_selected_dma #(.SEL_STACK(1)) dut (
        .clk(clk), .rst_n(rst_n),
        .region_base_sector(30'(BASE)), .region_sector_count(30'(COUNT)),
        .published_source_count(published_source_count),
        .fetch_v(fetch_v), .fetch_ready(fetch_ready),
        .local_row(local_row), .window_count(window_count), .source_id(source_id),
        .kv_ok(kv_ok), .re(re), .rrow(rrow), .relem(relem),
        .q(q), .q_fp8(q_fp8), .packed_row(packed_row), .packed_valid(packed_valid),
        .packed_local_row(packed_local_row), .packed_source_id(packed_source_id),
        .fault(fault), .fault_code(fault_code),
        .st_rows_fetched(rows), .st_sectors_read(sectors),
        .m_v(m_v), .m_rdy(4'hf), .m_addr(m_addr), .m_len(m_len),
        .m_tag(m_tag), .m_we(m_we), .m_wdata(m_wdata), .m_wstrb(m_wstrb),
        .m_wr_done(4'b0), .s_v(s_v), .s_rdy(s_rdy),
        .s_tag(s_tag), .s_beat(s_beat), .s_data(s_data));
    assign s_tag=rsp_tag;
    assign s_data=rsp_data;
    assign s_beat=0;
    always @(posedge clk) begin
        s_v <= 0;
        if (rst_n && m_v[1]) begin
            addr=m_addr[HAW +: HAW];
            if (m_we[1] || m_len[4 +: 4] != 1 || addr < BASE || addr >= BASE+COUNT) begin
                $display("BAD COMMAND addr=%0d",addr); errors=errors+1;
            end else begin
                rsp_tag[TAGW +: TAGW] <= m_tag[TAGW +: TAGW];
                rsp_data[256 +: 256] <= mem[addr];
                s_v[1] <= 1;
            end
        end
    end
    task automatic fetch(input integer loc, input integer src);
        begin
            @(negedge clk);
            local_row=10'(loc); source_id=21'(src); fetch_v=1;
            @(negedge clk); fetch_v=0;
            while (!kv_ok && !fault) @(negedge clk);
        end
    endtask
    task automatic check_row(input integer loc, input integer src, input integer fixture_row);
        integer e, s;
        begin
            if (!kv_ok || !packed_valid) begin
                $display("NOT READY row=%0d",loc); errors=errors+1;
            end
            if (packed_local_row !== 10'(loc) || packed_source_id !== 21'(src))
                errors=errors+1;
            for (s=0; s<9; s=s+1)
                if (packed_row[256*s +: 256] !== fixture[9*fixture_row+s])
                    errors=errors+1;
            for (e=0; e<512; e=e+1) begin
                @(negedge clk); rrow=10'(loc); relem=9'(e); re=1;
                @(negedge clk); re=0;
                if (q_fp8 !== expected[fixture_row*512+e] ||
                    q !== expected_fp32[fixture_row*512+e]) begin
                    $display("BAD VALUE row=%0d elem=%0d got=%02h/%08h expected=%02h/%08h",
                             loc,e,q_fp8,q,expected[fixture_row*512+e],
                             expected_fp32[fixture_row*512+e]);
                    errors=errors+1;
                end else checked=checked+1;
            end
        end
    endtask
    initial begin
        $readmemh("tests/fixtures/v41_ckv_selected/sectors.hex",fixture);
        $readmemh("tests/fixtures/v41_ckv_selected/expected_fp8.hex",expected);
        $readmemh("tests/fixtures/v41_ckv_selected/expected_fp32.hex",expected_fp32);
        for (i=0;i<BASE+COUNT;i=i+1) mem[i]=0;
        for (i=0;i<9;i=i+1) begin
            mem[BASE+5*9+i]=fixture[i];
            mem[BASE+7*9+i]=fixture[9+i];
        end
        repeat (5) @(negedge clk); rst_n=1;
        fetch(128,5); check_row(128,5,0);
        fetch(639,7); check_row(639,7,1);
        if (fault || rows != 2 || sectors != 18) begin
            $display("BAD STATS rows=%0d sectors=%0d fault=%0d",rows,sectors,fault);
            errors=errors+1;
        end
        // The next source exists in address space but has not been published
        // by ingest.  The DMA must not issue any HBM request for it.
        @(negedge clk); local_row=10'd128; source_id=21'd8; fetch_v=1;
        @(negedge clk); fetch_v=0;
        @(negedge clk);
        if (!fault || !fault_code[0] || kv_ok || sectors != 18) errors=errors+1;
        // A local window row may not alias compressed source 5.
        @(negedge clk); local_row=10'd127; source_id=21'd5; fetch_v=1;
        @(negedge clk); fetch_v=0;
        @(negedge clk);
        if (!fault || !fault_code[0] || kv_ok) errors=errors+1;
        // A now-published source with a NaN E4M3 scale must fail before
        // staging, even when the first eight code sectors were valid.
        mem[BASE+8*9+8][7:0]=8'h7f;
        published_source_count=9;
        @(negedge clk); local_row=10'd128; source_id=21'd8; fetch_v=1;
        @(negedge clk); fetch_v=0;
        repeat (25) @(negedge clk);
        if (!fault_code[2] || kv_ok || sectors != 26) errors=errors+1;
        $display("CKV_SELECTED rows=%0d sectors=%0d checked=%0d fault=%h errors=%0d",
                 rows,sectors,checked,fault_code,errors);
        if (errors == 0 && checked == 1024) $display("PASS");
        else $display("FAIL");
        $finish;
    end
    initial begin #100000; $display("TIMEOUT"); $display("FAIL"); $finish; end
endmodule
