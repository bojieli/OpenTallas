`timescale 1ns/1ps
module tb_chip_v41x_window_stage4;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg inv_v = 0, fill_v = 0, fill_last = 0, req_v = 0;
    reg [20:0] inv_row = 0, fill_row = 0, req_first_row = 0;
    reg [9:0] fill_user = 0, req_user = 0;
    reg [4:0] fill_sector = 0;
    reg [255:0] fill_data = 0;
    reg [3:0] req_mask = 0;
    wire req_ready, rsp_v, rsp_fault;
    wire [9:0] rsp_user;
    wire [20:0] rsp_first_row;
    wire [3:0] rsp_mask, rsp_valid_mask;
    wire [4*4224-1:0] rsp_rows;
    integer cycle = 0, received = 0, last_cycle = -1;
    integer exp_p [0:15], exp_user [0:15];
    reg [3:0] exp_mask [0:15], exp_valid [0:15];
    reg exp_fault [0:15];
    integer sent = 0;
    integer j;
    reg [4223:0] want_row;
    ot_chip_v41x_window_stage4 dut (
        .clk(clk), .rst_n(rst_n), .inv_v(inv_v), .inv_row(inv_row),
        .fill_v(fill_v), .fill_user(fill_user), .fill_row(fill_row),
        .fill_sector(fill_sector), .fill_data(fill_data), .fill_last(fill_last),
        .req_v(req_v), .req_ready(req_ready), .req_user(req_user),
        .req_first_row(req_first_row), .req_mask(req_mask),
        .rsp_v(rsp_v), .rsp_user(rsp_user), .rsp_first_row(rsp_first_row),
        .rsp_mask(rsp_mask), .rsp_valid_mask(rsp_valid_mask),
        .rsp_rows(rsp_rows), .rsp_fault(rsp_fault));

    function automatic [4223:0] make_row(input integer p, input integer u);
        integer n;
        reg [4223:0] r;
        begin
            r = 0;
            for (n = 0; n < 512; n = n + 1)
                r[8*n +: 8] = 8'(p + 3*n + u);
            for (n = 0; n < 16; n = n + 1)
                r[4096+8*n +: 8] = 8'(p ^ (17*n) ^ u);
            make_row = r;
        end
    endfunction

    task automatic fill(input integer p, input integer u);
        integer s;
        reg [4223:0] bits;
        begin
            bits = make_row(p,u);
            for (s = 0; s < 17; s = s + 1) begin
                @(negedge clk);
                fill_v = 1; fill_row = 21'(p); fill_user = 10'(u);
                fill_sector = 5'(s); fill_last = s == 16;
                fill_data = (s == 16) ? {128'd0,bits[4096 +: 128]} : bits[256*s +: 256];
                inv_v = s == 0; inv_row = 21'(p);
            end
            @(negedge clk); fill_v = 0; fill_last = 0; inv_v = 0;
        end
    endtask

    task automatic send(input integer p, input integer u, input [3:0] mask,
                        input [3:0] valid_mask, input bit fault_expected);
        begin
            if (!req_ready) $fatal(1,"four-bank stage did not accept request");
            exp_p[sent] = p; exp_user[sent] = u;
            exp_mask[sent] = mask; exp_valid[sent] = valid_mask;
            exp_fault[sent] = fault_expected;
            sent = sent + 1;
            @(negedge clk); req_v = 1; req_first_row = 21'(p);
            req_user = 10'(u); req_mask = mask;
        end
    endtask

    always @(posedge clk) cycle <= cycle + 1;
    always @(negedge clk) if (rst_n && rsp_v) begin
        if (received >= sent) $fatal(1,"unsolicited bank response");
        if (rsp_first_row !== 21'(exp_p[received]) ||
            rsp_user !== 10'(exp_user[received]) ||
            rsp_mask !== exp_mask[received] ||
            rsp_valid_mask !== exp_valid[received] ||
            rsp_fault !== exp_fault[received])
            $fatal(1,"bank response metadata mismatch at request %0d",received);
        for (j=0; j<4; j=j+1) begin
            want_row = exp_valid[received][j] ?
                make_row(exp_p[received]+j, exp_user[received]) : 4224'd0;
            if (rsp_rows[j*4224 +: 4224] !== want_row)
                $fatal(1,"bank row mismatch request %0d lane %0d",received,j);
        end
        if (received > 0 && received < 4 && cycle != last_cycle + 1)
            $fatal(1,"four-row response did not sustain one beat/cycle");
        last_cycle = cycle;
        received = received + 1;
    end

    initial begin
        repeat (4) @(negedge clk); rst_n = 1;
        for (integer p = 126; p <= 132; p = p + 1) fill(p,0);
        send(126,0,4'hf,4'hf,0);
        send(127,0,4'hf,4'hf,0);
        send(128,0,4'hf,4'hf,0);
        send(129,0,4'hf,4'hf,0);
        @(negedge clk); req_v = 0;
        wait (received == 4);
        send(126,1,4'h1,4'h0,1);
        @(negedge clk); req_v = 0;
        wait (received == 5);
        fill(254,1); // same physical ring slot as absolute row 126
        send(254,1,4'h1,4'h1,0);
        send(126,0,4'h1,4'h0,1);
        @(negedge clk); req_v = 0;
        wait (received == 7);
        send(1048576,0,4'h1,4'h0,1);
        @(negedge clk); req_v = 0;
        wait (received == 8);
        $display("WINDOW_STAGE4_PASS requests=%0d rows=7 peak_rows_per_cycle=4 users=2 wrap=1",received);
        $finish;
    end
    initial begin #100000; $fatal(1,"window stage four-bank timeout"); end
endmodule
