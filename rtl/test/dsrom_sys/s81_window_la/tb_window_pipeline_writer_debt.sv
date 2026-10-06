`timescale 1ns/1ps
// Minimum writer mechanism: bounds/order/poison rejection and accepted write
// debt under live region mutation. Full-shape row/tag tables remain 128 deep.
module tb_window_pipeline_writer_debt;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, prime_v=0, blk_v=0;
    reg [29:0] region_base_sector=30'h300000, region_sector_count=2176;
    reg [20:0] prime_row=0, blk_row=0;
    reg [3:0] blk_idx=0;
    reg [255:0] blk_codes=0;
    reg [7:0] blk_scale=8'h70;
    reg [3:0] m_rdy=0, m_wr_done=0;
    wire prime_ready, blk_ready, fault;
    wire [4:0] fault_code;
    wire [3:0] m_v, m_we;
    wire [119:0] m_addr;
    wire [63:0] m_tag;
    wire [1023:0] m_wdata;
    wire [127:0] m_wstrb;
    wire [31:0] blocks, sectors;
    ot_dsrom_window_writer_pipeline #(.REFILL_OWNER_SAFE(1),.REFILL_CREDITS(8)) dut (
        .clk(clk),.rst_n(rst_n),.region_base_sector(region_base_sector),.region_sector_count(region_sector_count),
        .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(10'd0),.prime_row(prime_row),
        .blk_v(blk_v),.blk_ready(blk_ready),.blk_user(10'd0),.blk_row(blk_row),.blk_idx(blk_idx),
        .blk_codes(blk_codes),.blk_scale(blk_scale),
        .prefetch_v(1'b0),.prefetch_user(10'd0),.prefetch_row(21'd0),.re(1'b0),.ruser(10'd0),.rrow(21'd0),.relem(9'd0),
        .packed_re(1'b0),.packed_ruser(10'd0),.packed_rrow(21'd0),.packed_ridx(4'd0),
        .bank_req_v(1'b0),.bank_req_user(10'd0),.bank_req_first(21'd0),.bank_req_mask(4'd0),
        .fault(fault),.fault_code(fault_code),.st_blocks_written(blocks),.st_sectors_written(sectors),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_tag(m_tag),.m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done),.s_v(4'd0),.s_tag(64'd0),.s_beat(16'd0),.s_data(1024'd0));
    task reset;
        begin
            @(negedge clk); rst_n=0; prime_v=0; blk_v=0; m_rdy=0; m_wr_done=0;
            region_base_sector=30'h300000; region_sector_count=2176;
            blk_row=0; blk_idx=0; blk_codes=0; blk_scale=8'h70;
            repeat(3) @(negedge clk); rst_n=1; @(negedge clk);
        end
    endtask
    task block_take;
        begin
            while(!blk_ready) @(negedge clk);
            blk_v=1; @(negedge clk); blk_v=0;
        end
    endtask
    task assert_reject(input integer code);
        begin
            repeat(12) begin @(negedge clk); if(m_v!=0) $fatal(1,"rejected command issued write"); end
            if(!fault || !fault_code[code] || blocks!=0 || sectors!=0) $fatal(1,"wrong rejection/debt counters");
        end
    endtask
    task write_ack(input integer index, input integer scale_write);
        reg [1023:0] data_hold;
        reg [119:0] addr_hold;
        begin
            while(!m_v[0]) @(negedge clk);
            if(!m_we[0] || m_tag[15:0]!=(scale_write ? 16 : index)) $fatal(1,"write identity changed");
            if(m_addr[29:0]!=30'h300000+(scale_write ? 16 : index)) $fatal(1,"write address changed");
            if(!scale_write && m_wdata[255:0]!={32{8'h11}}) $fatal(1,"captured codes changed");
            if(scale_write && (m_wdata[255:0]!=(256'(8'h70)<<(8*index)) || m_wstrb[31:0]!=(32'h1<<index)))
                $fatal(1,"golden scale/strobe changed");
            data_hold=m_wdata; addr_hold=m_addr;
            repeat(3) begin @(negedge clk); if(m_wdata!=data_hold || m_addr!=addr_hold || !m_v[0]) $fatal(1,"stalled request changed"); end
            m_rdy=1; @(negedge clk); m_rdy=0;
            repeat(5) begin @(negedge clk); if(blk_ready || prime_ready || m_v!=0) $fatal(1,"accepted debt falsely cleared"); end
            m_wr_done=1; @(negedge clk); m_wr_done=0;
        end
    endtask
    initial begin
        reset(); blk_codes[7:0]=8'h7f; block_take(); assert_reject(1);
        reset(); blk_idx=1; block_take(); assert_reject(1);
        reset(); prime_row=21'd1048576; prime_v=1; @(negedge clk); prime_v=0; assert_reject(0);
        reset(); block_take(); region_sector_count=0; assert_reject(1);
        reset(); blk_codes={32{8'h11}}; block_take();
        while(!m_v[0]) @(negedge clk);
        m_rdy=1; @(negedge clk); m_rdy=0; region_base_sector=30'h400000;
        repeat(8) begin @(negedge clk); if(blk_ready || m_v!=0 || blocks!=0 || sectors!=1) $fatal(1,"lost accepted debt"); end
        m_wr_done=1; @(negedge clk); m_wr_done=0;
        repeat(8) @(negedge clk);
        if(!fault || !fault_code[0] || sectors!=1 || blocks!=0 || m_v!=0) $fatal(1,"region mutation published incomplete block");
        reset();
        for(integer k=0;k<16;k=k+1) begin
            blk_idx=4'(k); blk_codes={32{8'h11}}; blk_scale=8'h70; block_take();
            // Unaccepted input changes cannot replace the original held payload.
            blk_codes='1; blk_scale='1;
            write_ack(k,0); write_ack(k,1);
        end
        repeat(3) @(negedge clk);
        if(fault || blocks!=16 || sectors!=32) $fatal(1,"good row exact/debt failure");
        $display("WINDOW_PIPELINE_WRITER_PASS negatives=5 good_blocks=16 writes=32"); $finish;
    end
endmodule
