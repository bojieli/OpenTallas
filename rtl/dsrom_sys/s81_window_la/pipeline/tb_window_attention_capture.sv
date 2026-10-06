`timescale 1ns/1ps
// One retained golden corpus/config, actual full staging/capture shape.
// Compile with OT_MEM_NO_INIT and the existing priced SRAM functional view.
module tb_window_attention_capture;
    reg clk=0, rst_n=0, act=0, kv_v=0;
    reg [15:0] wptr=36, T=640;
    reg [3:0] kv_m=15;
    reg [16959:0] kv_w;
    reg [7:0] rd_addr=9;
    reg rd_qk_s=0;
    wire kv_ready;
    wire [70655:0] captures;
    wire [35:0] tags;
    reg [4223:0] rows[0:127];
    reg [4223:0] expected[0:3];
    string rows_path;
    integer lane, x, checks=0;
    ot_dsrom_window_attention_capture_context dut (
        .clk(clk),.rst_n(rst_n),.act(act),.wptr(wptr),.T(T),
        .kv_v(kv_v),.kv_ready(kv_ready),.kv_m(kv_m),.kv_w(kv_w),
        .rd_addr(rd_addr),.r0_qk(16'd36),.r0_qk_s(16'd36),.rd_qk_s(rd_qk_s),
        .pv_e(1'b0),.q_go(1'b0),.p_go(1'b0),.p_w2v(1'b0),
        .pl_word(8'd0),.q_cnt(8'd0),.nb_p(2'd0),.pl_bank(2'd0),
        .nb_q(2'd1),.q_bank(2'd0),.e_iss_bank(2'd0),.rd_bank_s(2'd2),
        .p_w_i(512'd0),.q_w(8192'd0),.tr_col(36864'd0),
        .e_iss_final(1'b0),.e_iss_blk(16'd0),.e_iss_c(8'd0),
        .r0_captures(captures),.e_tags(tags));
    task tick;
        begin #5; clk=1; #1; #4; clk=0; end
    endtask
    task input_rows(input integer first);
        integer l,g;
        begin
            for(l=0;l<4;l=l+1)
                for(g=0;g<16;g=g+1)
                    kv_w[l*4240+g*265 +:265] =
                        {1'b0,rows[first+l][4096+8*g +:8],rows[first+l][256*g +:256]};
        end
    endtask
    task golden_capture;
        integer l,j,tile;
        reg [17:0] gold;
        begin
            for(l=0;l<4;l=l+1)
                for(j=0;j<512;j=j+1) begin
                    tile=l*16+j/32;
                    gold={2'b00,expected[l][8*j +:8],expected[l][4096+8*(j/32) +:8]};
                    if(captures[tile*1104+18*(j%32) +:18] !== gold)
                        $fatal(1,"golden mismatch lane=%0d elem=%0d got=%h expected=%h",l,j,
                            captures[tile*1104+18*(j%32) +:18],gold);
                    if(captures[tile*1104+578] !== 1'b1)
                        $fatal(1,"missing actual R0 valid tile=%0d",tile);
                end
            checks=checks+1;
        end
    endtask
    task reset_valid_low;
        integer t;
        begin
            for(t=0;t<64;t=t+1)
                if(captures[t*1104+578] !== 1'b0 || captures[t*1104+1103] !== 1'b0)
                    $fatal(1,"reset failed to guard uninitialized capture tile=%0d",t);
        end
    endtask
    initial begin
        if(!$value$plusargs("ROWS=%s",rows_path)) $fatal(1,"retained golden ROWS required");
        $readmemh(rows_path,rows);
        for(lane=0;lane<4;lane=lane+1) expected[lane]=rows[lane];
        input_rows(0);
        tick(); tick(); reset_valid_low();
        if((^captures[575:0]) !== 1'bx)
            $fatal(1,"unknown SRAM content was silently initialized or cleared");
        rst_n=1; act=1; kv_v=1;
        #1; if(kv_ready !== 1'b1) $fatal(1,"valid write was not ready");
        tick(); kv_v=0;
        tick(); // actual macro read returns the newly written row
        rd_qk_s=1;
        tick(); // original E1 capture edge, R0 still carries old unknown data
        if((^captures[575:0]) !== 1'bx) $fatal(1,"R0 capture occurred one edge early");
        tick(); golden_capture(); // original R0 edge, no added pipeline edge

        // A prior ready cycle cannot authorize a later out-of-bounds or idle write.
        input_rows(4); kv_v=1; wptr=T;
        #1; if(kv_ready !== 1'b0) $fatal(1,"out-of-bounds write ready");
        tick(); tick(); tick(); tick(); golden_capture();
        wptr=36; act=0;
        #1; if(kv_ready !== 1'b0) $fatal(1,"idle write ready");
        tick(); tick(); tick(); tick(); golden_capture();

        // Read-before-write and lane mask must survive the real striped macros.
        act=1; kv_m=4'b0010;
        tick(); kv_v=0;
        tick(); golden_capture();
        tick(); golden_capture();
        expected[1]=rows[5];
        tick(); golden_capture();

        // Reset protects control validity; it must not fake-clear mutable payload.
        rst_n=0; #1; reset_valid_low();
        tick(); tick(); reset_valid_low();
        rst_n=1; rd_qk_s=0;
        tick(); rd_qk_s=1; tick(); tick(); golden_capture();
        $display("PASS actual68macro/full64tile golden captures=%0d blocked_writes=2 masked_write=1 no_init/reset_guard/read_before_write",checks);
        $finish;
    end
endmodule
