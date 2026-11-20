// QC-TTCTLM-1119 form (a): lockstep qfd_dv_calendar_rom HIREG=0 vs HIREG=1.
// valid/data/out_* must match on every edge; fault(HIREG=1) must lie between fault(HIREG=0) one edge ago and now
// (never early, at most one edge late), with hi-word faults observed one edge late and other causes on the same edge.
module ot_rom_4096x266_m8 #(parameter INSTANCE="x") (input clk, input ce_in, input [11:0] addr_in, output reg [265:0] rd_out);
    function automatic [265:0] word(input [11:0] a);
        integer i; reg [31:0] s; reg [265:0] w;
        begin
            s = {20'h0, a} * 32'h9E3779B1 + ((INSTANCE == "calendar_m1") ? 32'h7F4A7C15 : 32'h1234567);
            w = 0;
            for (i = 0; i < 9; i = i + 1) begin s = s ^ (s << 13); s = s ^ (s >> 17); s = s ^ (s << 5); w = (w << 32) | s; end
            // m1 bits [265:246] = raw[531:512] (hi word): non-zero on ~1/16 of addresses only
            if (INSTANCE == "calendar_m1" && a[3:0] != 4'h5) w[265:246] = 0;
            word = w;
        end
    endfunction
    always @(posedge clk) if (ce_in) rd_out <= word(addr_in);
endmodule

module tb_calrom_hireg;
    reg ck = 0, rst_n = 0, req = 0, install = 0, running = 0;
    reg [9:0] first = 0; reg [2:0] count = 1; reg [1:0] user_id = 0; reg [5:0] stage = 0;
    wire v0, v1, f0, f1; wire [511:0] d0, d1; wire [1:0] u0, u1; wire [5:0] s0, s1; wire [2:0] n0, n1;
    qfd_dv_calendar_rom #(.NENT(1023), .HIREG(0)) a (.ck(ck), .rst_n(rst_n), .req(req), .first(first), .count(count),
        .user_id(user_id), .stage(stage), .install(install), .running(running), .valid(v0), .data(d0), .out_user(u0),
        .out_stage(s0), .out_count(n0), .fault(f0));
    qfd_dv_calendar_rom #(.NENT(1023), .HIREG(1)) b (.ck(ck), .rst_n(rst_n), .req(req), .first(first), .count(count),
        .user_id(user_id), .stage(stage), .install(install), .running(running), .valid(v1), .data(d1), .out_user(u1),
        .out_stage(s1), .out_count(n1), .fault(f1));
    always #5 ck = ~ck;
    integer cyc = 0, errs = 0, late = 0, same = 0, valids = 0, resets = 0, sincerst = 0;
    reg f0p = 0;
    always @(posedge ck) begin
        #1;
        cyc = cyc + 1;
        if ({v0, d0, u0, s0, n0} !== {v1, d1, u1, s1, n1}) begin
            errs = errs + 1; if (errs < 5) $display("MISMATCH data cyc %0d v %b/%b", cyc, v0, v1);
        end
        if (rst_n && sincerst > 2) begin
            if (f1 && !f0) begin errs = errs + 1; if (errs < 5) $display("EARLY fault cyc %0d", cyc); end
            if (f0p && !f1) begin errs = errs + 1; if (errs < 5) $display("LATE>1 fault cyc %0d", cyc); end
            if (f0 && !f0p && f1) same = same + 1;
            if (f0 && !f0p && !f1) late = late + 1;
        end
        valids = valids + v0;
        f0p = f0;
        // stimulus for the next edge
        sincerst = sincerst + 1;
        if (f0 && f1 && ($urandom % 4 == 0)) begin rst_n = 0; resets = resets + 1; sincerst = 0; end
        else if (!rst_n && ($urandom % 2 == 0)) begin rst_n = 1; sincerst = 0; end
        req = ($urandom % 3) != 0;
        first = {$urandom % 256, (($urandom % 64) == 0) ? 2'b01 : 2'b00};
        count = (($urandom % 64) == 0) ? 3'd5 : 3'd1 + ($urandom % 4);
        user_id = $urandom; stage = $urandom % 38;
        install = ($urandom % 400) == 0; running = 0;
        if (cyc == 200000) begin
            $display("TB_CALROM_HIREG cyc %0d valids %0d resets %0d fault_rise same-edge %0d one-late %0d errs %0d",
                     cyc, valids, resets, same, late, errs);
            if (errs == 0 && late > 0 && same > 0 && valids > 1000) $display("TB_CALROM_HIREG PASS");
            else $display("TB_CALROM_HIREG FAIL");
            $finish;
        end
    end
endmodule
