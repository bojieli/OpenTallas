`timescale 1ns/1ps
// lockstep equivalence: ot_hdc_v41x_idx_quarter_join (new) vs the compare form (ref: the module at 7361f422, renamed
// ot_hdc_v41x_idx_quarter_join_ref); every output port compared on every cycle under random commands and back-pressure
module tb_w11_join_lockstep #(parameter integer NCMD = 400, MAXN = 3000, VP = 80, RP = 75) (input wire clk);
    reg rst_n = 0, cmd_v = 0, o_ready = 0;
    reg [29:0] cmd_nkeys = 0;
    reg [39:0] cmd_skip = 0;
    reg [3:0] i_valid = 0;
    reg [63:0] i_kv = 0;
    reg [4*16*544-1:0] i_key = 0;
    wire busy_r, busy_n, fault_r, fault_n, ov_r, ov_n;
    wire [3:0] ir_r, ir_n, ol_r, ol_n;
    wire [63:0] okv_r, okv_n, oref_r, oref_n;
    wire [64*544-1:0] ok_r, ok_n;
    ot_hdc_v41x_idx_quarter_join_ref u_r (.clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(cmd_nkeys),.cmd_skip(cmd_skip),
        .busy(busy_r),.fault(fault_r),.i_valid(i_valid),.i_ready(ir_r),.i_kv(i_kv),.i_key(i_key),.o_valid(ov_r),
        .o_ready(o_ready),.o_kv(okv_r),.o_last(ol_r),.o_key(ok_r),.o_ref(oref_r));
    ot_hdc_v41x_idx_quarter_join u_n (.clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(cmd_nkeys),.cmd_skip(cmd_skip),
        .busy(busy_n),.fault(fault_n),.i_valid(i_valid),.i_ready(ir_n),.i_kv(i_kv),.i_key(i_key),.o_valid(ov_n),
        .o_ready(o_ready),.o_kv(okv_n),.o_last(ol_n),.o_key(ok_n),.o_ref(oref_n));
    integer cyc = 0, ncmd = 0, mism = 0, beats = 0, k, q, r;
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 3) rst_n <= 1;
        for (k = 0; k < 64; k = k + 1) i_key[32*((cyc*64 + k*17) % (4*16*544/32)) +: 32] <= $random;
        for (q = 0; q < 4; q = q + 1) begin
            i_valid[q] <= ($unsigned($random) % 100) < VP;
            i_kv[16*q +: 16] <= ($unsigned($random) % 8 == 0) ? 16'($random) : 16'hffff;
        end
        o_ready <= ($unsigned($random) % 100) < RP;
        if (rst_n) begin
            if ({busy_r, fault_r, ov_r, ir_r, ol_r, okv_r, oref_r, ok_r} !== {busy_n, fault_n, ov_n, ir_n, ol_n, okv_n, oref_n, ok_n}) begin
                mism = mism + 1;
                if (mism < 10) $display("MISMATCH cyc=%0d cmd=%0d busy %b/%b fault %b/%b ov %b/%b ir %b/%b ol %b/%b okv %h/%h key_eq=%0d",
                    cyc, ncmd, busy_r, busy_n, fault_r, fault_n, ov_r, ov_n, ir_r, ir_n, ol_r, ol_n, okv_r, okv_n, ok_r == ok_n);
            end
            if (ov_r && o_ready) beats = beats + 1;
            cmd_v <= 0;
            if (!busy_r && !cmd_v && ($unsigned($random) % 3 == 0)) begin
                if (ncmd == NCMD) begin
                    $display("W11_JOIN_LOCKSTEP %s cmds=%0d cycles=%0d beats=%0d mismatches=%0d", mism == 0 ? "PASS" : "FAIL", ncmd, cyc, beats, mism);
                    $finish;
                end
                ncmd = ncmd + 1;
                cmd_v <= 1;
                r = $unsigned($random) % 10;
                cmd_nkeys <= (r == 0) ? 30'($unsigned($random) % 40) : (r == 1) ? 30'(32 * ($unsigned($random) % 20) + ($unsigned($random) % 3)) :
                             (r == 2) ? 30'($unsigned($random) % 70000) : 30'($unsigned($random) % MAXN);
                for (q = 0; q < 4; q = q + 1)
                    cmd_skip[10*q +: 10] <= ($unsigned($random) % 20 == 0) ? 10'($random) : 10'(8 * ($unsigned($random) % 12));
            end else if (busy_r && ($unsigned($random) % 40 == 0)) begin
                cmd_v <= 1; cmd_nkeys <= $random; cmd_skip <= {$random, $random};
            end
        end
    end
endmodule
