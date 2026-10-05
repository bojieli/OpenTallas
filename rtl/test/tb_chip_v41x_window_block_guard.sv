`timescale 1ns/1ps
module tb_chip_v41x_window_block_guard;
    reg [20:0] step_pos, abs_row, local_row;
    reg [3:0] idx;
    reg [29:0] base, first;
    wire [6:0] slot;
    wire [30:0] expected;
    wire bad;
    integer cases;
    ot_chip_v41x_window_block_guard dut (
        .step_pos(step_pos), .blk_abs_row(abs_row), .blk_kvt_row(local_row),
        .blk_idx(idx), .kvt_base(base), .first_elem(first),
        .hbm_slot(slot), .expected_first(expected), .bad(bad));

    task automatic check_pos(input integer p, input integer want_slot);
        integer b;
        begin
            for (b = 0; b < 16; b = b + 1) begin
                step_pos = 21'(p); abs_row = 21'(p);
                local_row = 21'((p < 128) ? p : 127);
                idx = 4'(b); base = 30'h0100_0000;
                first = base + ((local_row >> 4) << 13) + (b << 9) + local_row[3:0];
                #1;
                if (bad || slot != 7'(want_slot) || expected != {1'b0,first})
                    $fatal(1, "valid position %0d block %0d failed",p,b);
                cases = cases + 1;
            end
        end
    endtask

    initial begin
        cases = 0;
        check_pos(0,0);
        check_pos(126,126);
        check_pos(127,127);
        check_pos(128,0);
        check_pos(129,1);
        check_pos(255,127);
        check_pos(256,0);
        check_pos(1048575,127);
        // The local KVT alias is identical across saturation; the packed
        // HBM slot must still rotate with the absolute position.
        step_pos = 21'd127; abs_row = step_pos; local_row = 21'd127;
        idx = 0; base = 30'h0100_0000;
        first = base + ((local_row >> 4) << 13) + local_row[3:0]; #1;
        if (bad || slot != 7'd127) $fatal(1,"position 127 alias failed");
        cases = cases + 1;
        step_pos = 21'd128; abs_row = step_pos; #1;
        if (bad || slot != 7'd0 || expected != {1'b0, first})
            $fatal(1,"position 128 did not rotate HBM slot with identical KVT alias");
        cases = cases + 1;
        abs_row = 21'd127; step_pos = 21'd128; #1;
        if (!bad) $fatal(1,"saturated local row as absolute position was accepted");
        cases = cases + 1;
        abs_row = step_pos; local_row = 21'd128; #1;
        if (!bad) $fatal(1,"wrong local KVT row was accepted");
        cases = cases + 1;
        local_row = 21'd127; first = first + 1; #1;
        if (!bad) $fatal(1,"wrong KVT first element was accepted");
        cases = cases + 1;
        step_pos = 21'd1048576; abs_row = step_pos;
        first = base + ((local_row >> 4) << 13) + (integer'(idx) << 9) + local_row[3:0]; #1;
        if (!bad) $fatal(1,"one-past-1M row was accepted");
        cases = cases + 1;
        step_pos = 21'd128; abs_row = step_pos; base = 30'h3fff_ffff;
        first = 30'(expected); #1;
        if (!bad) $fatal(1,"KVT address overflow was accepted");
        cases = cases + 1;
        $display("WINDOW_BLOCK_GUARD_PASS cases=%0d",cases);
        $finish;
    end
endmodule
