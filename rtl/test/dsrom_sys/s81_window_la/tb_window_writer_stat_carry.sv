`timescale 1ns/1ps
// Minimum writer mechanism: bounds/order/poison rejection and accepted write
// debt under live region mutation. Full-shape row/tag tables remain 128 deep.
module tb_window_writer_stat_carry;
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
    wire [31:0] blocks, sectors, rows, read_sectors;
    ot_dsrom_window_writer_pipeline #(.REFILL_OWNER_SAFE(1),.REFILL_CREDITS(8)) dut (
        .clk(clk),.rst_n(rst_n),.region_base_sector(region_base_sector),.region_sector_count(region_sector_count),
        .prime_v(prime_v),.prime_ready(prime_ready),.prime_user(10'd0),.prime_row(prime_row),
        .blk_v(blk_v),.blk_ready(blk_ready),.blk_user(10'd0),.blk_row(blk_row),.blk_idx(blk_idx),
        .blk_codes(blk_codes),.blk_scale(blk_scale),
        .prefetch_v(1'b0),.prefetch_user(10'd0),.prefetch_row(21'd0),.re(1'b0),.ruser(10'd0),.rrow(21'd0),.relem(9'd0),
        .packed_re(1'b0),.packed_ruser(10'd0),.packed_rrow(21'd0),.packed_ridx(4'd0),
        .bank_req_v(1'b0),.bank_req_user(10'd0),.bank_req_first(21'd0),.bank_req_mask(4'd0),
        .fault(fault),.fault_code(fault_code),.st_blocks_written(blocks),.st_sectors_written(sectors),.st_rows_fetched(rows),.st_sectors_read(read_sectors),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_tag(m_tag),.m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),
        .m_wr_done(m_wr_done),.s_v(4'd0),.s_tag(64'd0),.s_beat(16'd0),.s_data(1024'd0));
    wire ref_prime_ready, ref_blk_ready, ref_fault;
    wire [4:0] ref_fault_code;
    wire [3:0] ref_m_v, ref_m_we;
    wire [119:0] ref_m_addr;
    wire [63:0] ref_m_tag;
    wire [1023:0] ref_m_wdata;
    wire [127:0] ref_m_wstrb;
    wire [31:0] ref_blocks, ref_sectors, ref_rows, ref_read_sectors;
    ot_dsrom_window_writer_pipeline_reference #(.REFILL_OWNER_SAFE(1),.REFILL_CREDITS(8)) reference (
        .clk(clk),.rst_n(rst_n),.region_base_sector(region_base_sector),.region_sector_count(region_sector_count),
        .prime_v(prime_v),.prime_ready(ref_prime_ready),.prime_user(10'd0),.prime_row(prime_row),
        .blk_v(blk_v),.blk_ready(ref_blk_ready),.blk_user(10'd0),.blk_row(blk_row),.blk_idx(blk_idx),
        .blk_codes(blk_codes),.blk_scale(blk_scale),
        .prefetch_v(1'b0),.prefetch_user(10'd0),.prefetch_row(21'd0),.re(1'b0),.ruser(10'd0),.rrow(21'd0),.relem(9'd0),
        .packed_re(1'b0),.packed_ruser(10'd0),.packed_rrow(21'd0),.packed_ridx(4'd0),
        .bank_req_v(1'b0),.bank_req_user(10'd0),.bank_req_first(21'd0),.bank_req_mask(4'd0),
        .fault(ref_fault),.fault_code(ref_fault_code),.st_blocks_written(ref_blocks),.st_sectors_written(ref_sectors),.st_rows_fetched(ref_rows),.st_sectors_read(ref_read_sectors),
        .m_v(ref_m_v),.m_rdy(m_rdy),.m_addr(ref_m_addr),.m_tag(ref_m_tag),.m_we(ref_m_we),.m_wdata(ref_m_wdata),.m_wstrb(ref_m_wstrb),
        .m_wr_done(m_wr_done),.s_v(4'd0),.s_tag(64'd0),.s_beat(16'd0),.s_data(1024'd0));
    integer compared_cycles=0, wrap_cases=0;
    always @(posedge clk) begin
        #1;
        if (rst_n) begin
            compared_cycles=compared_cycles+1;
            if ({prime_ready,blk_ready,fault,fault_code,m_v,m_we,m_addr,m_tag,m_wdata,m_wstrb,blocks,sectors,rows,read_sectors} !==
                {ref_prime_ready,ref_blk_ready,ref_fault,ref_fault_code,ref_m_v,ref_m_we,ref_m_addr,ref_m_tag,ref_m_wdata,ref_m_wstrb,ref_blocks,ref_sectors,ref_rows,ref_read_sectors})
                $fatal(1,"writer cycle/identity/debt/stat mismatch blocks=%h/%h sectors=%h/%h",blocks,ref_blocks,sectors,ref_sectors);
        end
    end
    function automatic [2:0] carry_for_value(input [31:0] value);
        carry_for_value={&value[23:0],&value[15:0],&value[7:0]};
    endfunction
    reg [31:0] boundary[0:7];
    reg [31:0] expected_next;
    task seed_reachable_status(input [31:0] value);
        begin
            // Directly enter a mathematically reachable status state rather
            // than simulate billions of otherwise identical write commands.
            @(negedge clk);
            dut.st_blocks_written=value; reference.st_blocks_written=value;
            dut.st_sectors_written=value; reference.st_sectors_written=value;
            dut.st_rows_fetched=value; reference.st_rows_fetched=value;
            dut.st_sectors_read=value; reference.st_sectors_read=value;
            dut.blocks_written_carry=carry_for_value(value);
            dut.sectors_written_carry=carry_for_value(value);
            dut.rows_fetched_carry=carry_for_value(value);
            dut.sectors_read_carry=carry_for_value(value);
            expected_next=value+32'd1;
            if (dut.stat_increment(value,carry_for_value(value)) !== expected_next ||
                dut.stat_carry_after_increment(value) !== carry_for_value(expected_next))
                $fatal(1,"full32 modular increment/predicate mismatch at %h",value);
            $display("COUNTER_BOUNDARY_ENTER value=%h",value);
        end
    endtask
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
        boundary[0]=32'h000000fe; boundary[1]=32'h000000ff;
        boundary[2]=32'h0000fffe; boundary[3]=32'h0000ffff;
        boundary[4]=32'h00fffffe; boundary[5]=32'h00ffffff;
        boundary[6]=32'hfffffffe; boundary[7]=32'hffffffff;
        for(integer w=0;w<8;w=w+1) begin
            reset(); seed_reachable_status(boundary[w]);
            blk_idx=0; blk_codes={32{8'h11}}; blk_scale=8'h70; block_take();
            blk_codes='x; blk_scale='x;
            write_ack(0,0); write_ack(0,1);
            repeat(3) @(negedge clk);
            if (fault || blocks !== boundary[w]+32'd1 || sectors !== boundary[w]+32'd2)
                $fatal(1,"same-edge modular boundary count failure at %h",boundary[w]);
            wrap_cases=wrap_cases+1;
        end
        // A held request that has never been granted is safe to cancel at
        // reset; no accepted external debt is erased by this reset check.
        reset(); blk_codes={32{8'h11}}; block_take();
        while(!m_v[0]) @(negedge clk);
        if(m_rdy!=0 || sectors!=0) $fatal(1,"reset case unexpectedly accepted debt");
        reset();
        if ({blocks,sectors,rows,read_sectors,dut.blocks_written_carry,dut.sectors_written_carry,
             dut.rows_fetched_carry,dut.sectors_read_carry} !== 140'd0)
            $fatal(1,"counter/predicate reset mismatch");
        for(integer k=0;k<16;k=k+1) begin
            blk_idx=4'(k); blk_codes={32{8'h11}}; blk_scale=8'h70; block_take();
            // Unaccepted input changes cannot replace the original held payload.
            blk_codes='x; blk_scale='x;
            write_ack(k,0); write_ack(k,1);
        end
        repeat(3) @(negedge clk);
        if(fault || blocks!=16 || sectors!=32) $fatal(1,"good row exact/debt failure");
        $display("WINDOW_WRITER_STAT_CARRY_PASS negatives=5 wrap_cases=%0d final_blocks=16 final_writes=32 compared_cycles=%0d",wrap_cases,compared_cycles); $finish;
    end
endmodule
