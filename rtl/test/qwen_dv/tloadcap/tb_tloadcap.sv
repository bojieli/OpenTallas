`timescale 1ns/1ps
// HARD-QC-FORMS-1 11-13 (R-RTL-6 lock-step bench for the QC stm form OT_QC_TLOADCAP).
//   OLD = qfd_dv_slice_tload #(CAPTURE_STAGE 0, LOCAL_JOIN 0)   = today's QC stm kit / bound RTL (no OT_S6_SIM)
//   NEW = qfd_dv_slice_tload #(CAPTURE_STAGE 1, LOCAL_JOIN 1)   = the stm type built with +define+OT_QC_TLOADCAP
// Claim: (a) every loader-origin table write of NEW is the same write as OLD, exactly N = 1 edge later (tw_we, tw_kind,
//        tw_addr, tw_data, and the write count); (b) a stream-origin write (loader idle) passes on the SAME edge in
//        both; (c) fault stays 0 in both; through cold reset and a warm reset in the middle of a load.
// plusargs: +N=<n> expected loader delay (default 1; +N=0 must FAIL), +MUT=1 NEW with CAPTURE_MUT 1 (metadata bypass,
//           must FAIL), +MUT=2 warm reset not applied to NEW (reset not moved with the data, must FAIL).
// Compiled with -DSYNTHESIS (the loader then instantiates the ROM without the INSTANCE string; the model reads its
// index m0..m3 from its instance name).  The ROM is a bench model (same contents for OLD and NEW): deterministic words with legal kind / address fields.
module ot_rom_4096x266_m8 (input wire clk, input wire ce_in, input wire [11:0] addr_in, output reg [265:0] rd_out);
    function automatic [1063:0] word(input [11:0] a);
        reg [1063:0] w; reg [31:0] h; integer i; reg [1:0] k; reg [23:0] la; reg [4:0] q5;
        begin
            for (i = 0; i < 34; i = i + 1) begin
                h = {a, 20'h0} ^ (32'h9e3779b9 * (i + 1)); h = h ^ (h >> 15); h = h * 32'h2c1b3c6d; h = h ^ (h >> 12); h = h * 32'h297a2d39; h = h ^ (h >> 15);
                if (i < 33) w[32*i +: 32] = h; else w[1063:1056] = h[7:0];
            end
            k = (a % 3) + 1;                                   // kind 1..3
            q5 = a[6:2] % 5'd18;
            la = (k == 3) ? {18'd0, a[5:0]} : (k == 2) ? {17'd0, q5, 2'b00} : {17'd0, a[6:0]};
            w[1024] = (a[3:0] != 4'd7);                        // a few rows carry no write
            w[1026:1025] = k; w[1050:1027] = la; w[1063:1051] = 13'd0;
            word = w;
        end
    endfunction
    integer mi;
    reg [8*256-1:0] nm;
    initial begin $sformat(nm, "%m"); mi = nm[7:0] - "0"; if (mi < 0 || mi > 3) begin $display("TLOADCAP_ROM_NAME_BAD %m"); $finish; end end
    reg [1063:0] ww;
    always @(posedge clk) if (ce_in) begin
        ww = word(addr_in);
        case (mi) 0: rd_out <= ww[265:0]; 1: rd_out <= ww[531:266]; 2: rd_out <= ww[797:532]; default: rd_out <= ww[1063:798]; endcase
    end
endmodule

module tb_tloadcap;
    reg ck = 0; always #0.4165 ck = ~ck;
    reg rst_o = 0, rst_n_new = 0; reg [8:0] treq = 0;
    reg s_we = 0; reg [1:0] s_kind = 0; reg [23:0] s_addr = 0; reg [1023:0] s_data = 0;
    wire o_we, n_we, o_busy, n_busy, o_done, n_done, o_fault, n_fault;
    wire [1:0] o_kind, n_kind; wire [23:0] o_addr, n_addr; wire [1023:0] o_data, n_data;
    integer N = 1, MUT = 0;
    qfd_dv_slice_tload #(.SLICE(0), .CAPTURE_STAGE(0), .LOCAL_JOIN(0)) u_old (.ck(ck), .rst_n(rst_o), .treq(treq), .s_we(s_we), .s_kind(s_kind), .s_addr(s_addr), .s_data(s_data),
        .tw_we(o_we), .tw_kind(o_kind), .tw_addr(o_addr), .tw_data(o_data), .busy(o_busy), .done(o_done), .fault(o_fault));
`ifdef TB_CAPTURE_MUT
    qfd_dv_slice_tload #(.SLICE(0), .CAPTURE_STAGE(1), .LOCAL_JOIN(1), .CAPTURE_MUT(1)) u_new
`else
    qfd_dv_slice_tload #(.SLICE(0), .CAPTURE_STAGE(1), .LOCAL_JOIN(1)) u_new
`endif
        (.ck(ck), .rst_n(rst_n_new), .treq(treq), .s_we(s_we), .s_kind(s_kind), .s_addr(s_addr), .s_data(s_data),
        .tw_we(n_we), .tw_kind(n_kind), .tw_addr(n_addr), .tw_data(n_data), .busy(n_busy), .done(n_done), .fault(n_fault));
    // history of OLD for the N-edge compare
    reg [1049:0] oh [0:3]; reg ohv [0:3]; integer i, errs = 0, lw_o = 0, lw_n = 0, sw_o = 0, sw_n = 0, cmp = 0;
    reg phase_stream = 0, cmp_on = 0;
    always @(negedge ck) begin
        for (i = 3; i > 0; i = i - 1) begin oh[i] = oh[i-1]; ohv[i] = ohv[i-1]; end
        oh[0] = {o_kind, o_addr, o_data}; ohv[0] = o_we;
        if (cmp_on) begin
            if (!phase_stream) begin
                // oh[k] is OLD k edges ago after the shift above (oh[0] = this edge)
                if (n_we !== ohv[N]) begin errs = errs + 1; if (errs < 6) $display("TLOADCAP_MISMATCH we t=%0t new=%b old(t-%0d)=%b", $time, n_we, N, ohv[N]); end
                else if (n_we && {n_kind, n_addr, n_data} !== oh[N]) begin errs = errs + 1; if (errs < 6) $display("TLOADCAP_MISMATCH payload t=%0t", $time); end
                if (n_we) lw_n = lw_n + 1; if (ohv[N]) lw_o = lw_o + 1; cmp = cmp + 1;   // OLD counted at its N-delayed edge (a warm
                // reset in the middle of a load cuts the load in both; the compare window opens after the reset)
            end else begin
                if (n_we !== o_we || (o_we && {n_kind, n_addr, n_data} !== {o_kind, o_addr, o_data})) begin errs = errs + 1; if (errs < 6) $display("TLOADCAP_MISMATCH stream t=%0t", $time); end
                if (n_we) sw_n = sw_n + 1; if (o_we) sw_o = sw_o + 1; cmp = cmp + 1;
            end
            if (o_fault !== 1'b0 || n_fault !== 1'b0) begin errs = errs + 1; if (errs < 6) $display("TLOADCAP_FAULT t=%0t old=%b new=%b", $time, o_fault, n_fault); end
        end
    end
    task load(input [5:0] st, input [1:0] u); begin
        @(negedge ck); treq = {1'b1, st, u}; @(negedge ck); treq = 0; repeat (110) @(negedge ck);
    end endtask
    task reset_both(input integer warm); begin
        cmp_on = 0; rst_o = 0; if (!(warm && MUT == 2)) rst_n_new = 0;
        repeat (6) @(negedge ck); rst_o = 1; rst_n_new = 1; repeat (12) @(negedge ck); for (i = 0; i < 4; i = i + 1) ohv[i] = 0; cmp_on = 1;
    end endtask
    integer k; reg [31:0] hk;
    initial begin
        if (!$value$plusargs("N=%d", N)) N = 1;
        if (!$value$plusargs("MUT=%d", MUT)) MUT = 0;
        for (i = 0; i < 4; i = i + 1) begin ohv[i] = 0; oh[i] = 0; end
        reset_both(0);
        phase_stream = 0; load(6'd1, 2'd0); load(6'd36, 2'd3); load(6'd17, 2'd2);
        // warm reset in the middle of a load, then a full load again
        @(negedge ck); treq = {1'b1, 6'd5, 2'd1}; @(negedge ck); treq = 0; repeat (40) @(negedge ck);
        reset_both(1); load(6'd5, 2'd1); load(6'd22, 2'd0);
        // stream-origin writes, loader idle
        repeat (4) @(negedge ck); phase_stream = 1;
        for (k = 0; k < 64; k = k + 1) begin
            @(negedge ck); s_we = (k % 3 != 1); s_kind = k[1:0]; s_addr = 24'h1000 + k; hk = 32'h13579bdf * (k + 1); s_data = {32{hk}};
        end
        @(negedge ck); s_we = 0; repeat (6) @(negedge ck); cmp_on = 0;
        if (errs == 0 && lw_o == lw_n && lw_o > 300 && sw_o == sw_n && sw_o > 30)
            $display("TLOADCAP_LOCKSTEP PASS N=%0d loader_writes %0d stream_writes %0d compared_edges %0d", N, lw_o, sw_o, cmp);
        else $display("TLOADCAP_LOCKSTEP FAIL N=%0d MUT=%0d errs %0d loader_writes old %0d new %0d stream_writes old %0d new %0d", N, MUT, errs, lw_o, lw_n, sw_o, sw_n);
        $finish;
    end
endmodule
