`timescale 1ns/1ps
// Testbench (Verilator 5 --timing, or Icarus) for rtl/dft/ot_tap.sv and ot_dft_scan_clock.sv.
//
// A toy scan-inserted core (two chains, 5 and 7 cells, muxed-D) is clocked
// through ot_dft_scan_clock and accessed only through the TAP pins.  The bench
// checks the TAP state machine, IDCODE, BYPASS (also for an unused opcode),
// the Capture-IR value, SCAN_CFG write and read-back, a full scan test through
// SCAN_ACCESS in serial mode (load, capture, unload against the core's next
// state), a single-chain flush in select mode, MBIST_CTRL write with status
// capture and the update strobe, DFT_STATUS, the TMS reset and TDO enable.
// It prints "CHECK name ok|FAIL ..." lines and a final "RESULT pass|fail N".
module tb_ot_tap;
    localparam int NCH = 2;
    localparam logic [31:0] IDCODE = 32'h1234_5679;

    logic tck = 0, tms = 1, tdi = 0, trst_n = 0;
    logic func_clk, rst_n = 0;
    wire  tdo, tdo_en;
    wire  test_mode, scan_clk_sel, scan_en, scan_clk_en;
    wire [NCH-1:0] scan_in, scan_out;
    wire [31:0] mbist_ctrl;
    wire mbist_ctrl_update;
    logic [31:0] mbist_status = 32'hC0DE_0A5A;
    logic [15:0] dft_status = 16'hBEEF;
    wire [3:0] ir, tap_state;
    wire core_clk;

    ot_tap #(.IDCODE(IDCODE), .NCHAINS(NCH), .MBIST_CTRL_W(32), .MBIST_STATUS_W(32), .STATUS_W(16)) u_tap (
        .tck, .tms, .tdi, .trst_n, .tdo, .tdo_en,
        .test_mode, .scan_clk_sel, .scan_en, .scan_clk_en, .scan_in, .scan_out,
        .mbist_ctrl, .mbist_ctrl_update, .mbist_status, .dft_status, .ir, .tap_state
    );
    ot_dft_scan_clock u_clk (
        .func_clk, .tck, .rst_n, .scan_clk_sel, .scan_clk_en, .core_clk
    );

    // Toy core: chain 0 = a[4] .. a[0], chain 1 = b[6] .. b[0].
    logic [4:0] a;
    logic [6:0] b;
    always_ff @(posedge core_clk) begin
        if (scan_en) begin
            a <= {scan_in[0], a[4:1]};
            b <= {scan_in[1], b[6:1]};
        end else begin
            a <= a + b[4:0];
            b <= {b[5:0], a[4] ^ b[6]};
        end
    end
    assign scan_out = {b[0], a[0]};

    function automatic logic [11:0] core_next(input logic [11:0] r);
        logic [4:0] ra;
        logic [6:0] rb;
        ra = r[11:7];
        rb = r[6:0];
        return {5'(ra + rb[4:0]), rb[5:0], ra[4] ^ rb[6]};
    endfunction

    initial begin
        func_clk = 0;
        forever #3.5 func_clk = ~func_clk;
    end

    int errors = 0;
    task automatic check(input string name, input logic ok, input string detail);
        if (ok) $display("CHECK %s ok", name);
        else begin
            $display("CHECK %s FAIL %s", name, detail);
            errors++;
        end
    endtask

    // One TCK cycle: drive TMS/TDI while TCK is low, sample TDO just before
    // the rising edge.
    task automatic clk_tap(input logic tms_v, input logic tdi_v, output logic tdo_v);
        tms = tms_v;
        tdi = tdi_v;
        #9;
        tdo_v = tdo;
        #1 tck = 1;
        #10 tck = 0;
    endtask

    task automatic idle(input int n);
        logic d;
        repeat (n) clk_tap(0, 0, d);
    endtask

    task automatic reset_by_tms();
        logic d;
        repeat (5) clk_tap(1, 0, d);
        clk_tap(0, 0, d);   // Run-Test/Idle
    endtask

    // From Run-Test/Idle; returns the captured IR bits (LSB first).
    task automatic shift_ir(input logic [3:0] value, output logic [3:0] captured);
        logic d;
        clk_tap(1, 0, d);  // Select-DR
        clk_tap(1, 0, d);  // Select-IR
        clk_tap(0, 0, d);  // Capture-IR
        clk_tap(0, 0, d);  // Shift-IR
        for (int i = 0; i < 4; i++) begin
            clk_tap(i == 3, value[i], d);
            captured[i] = d;
        end
        clk_tap(1, 0, d);  // Update-IR
        clk_tap(0, 0, d);  // Run-Test/Idle
    endtask

    // From Run-Test/Idle; shifts n bits of `value` (LSB first) and returns
    // the n bits that came out.
    task automatic shift_dr(input int n, input logic [127:0] value, output logic [127:0] out);
        logic d;
        out = '0;
        clk_tap(1, 0, d);  // Select-DR
        clk_tap(0, 0, d);  // Capture-DR
        clk_tap(0, 0, d);  // Shift-DR
        for (int i = 0; i < n; i++) begin
            clk_tap(i == n - 1, value[i], d);
            out[i] = d;
        end
        clk_tap(1, 0, d);  // Update-DR
        clk_tap(0, 0, d);  // Run-Test/Idle
    endtask

    logic [3:0]   cap;
    logic [127:0] got, pat;
    logic [11:0]  loaded, expect_next;
    logic         saw_update;
    logic         en_seen_outside_shift;

    always @(posedge mbist_ctrl_update) saw_update <= 1'b1;
    always @(posedge tck) if (tdo_en && !(tap_state == 4'h2 || tap_state == 4'hA || tap_state == 4'h1 || tap_state == 4'h9))
        en_seen_outside_shift <= 1'b1;

    initial begin
        saw_update = 0;
        en_seen_outside_shift = 0;
        #25 trst_n = 1;
        #20 rst_n = 1;
        reset_by_tms();

        // IDCODE is the instruction after reset.
        check("ir_after_reset", ir == 4'b0001, $sformatf("ir=%b", ir));
        shift_dr(32, '0, got);
        check("idcode", got[31:0] == IDCODE, $sformatf("got %h", got[31:0]));
        check("idcode_lsb", got[0] == 1'b1, "IDCODE LSB must be 1");

        // Capture-IR loads ...01, and BYPASS delays by one bit after a 0.
        shift_ir(4'b1111, cap);
        check("capture_ir", cap == 4'b0001, $sformatf("captured %b", cap));
        check("bypass_selected", ir == 4'b1111, $sformatf("ir=%b", ir));
        pat = 128'h0;
        pat[15:0] = 16'b1011_0010_1110_0101;
        shift_dr(17, pat, got);
        check("bypass", got[16:0] == {pat[15:0], 1'b0}, $sformatf("got %b", got[16:0]));

        shift_ir(4'b0110, cap);   // unused opcode behaves as BYPASS
        shift_dr(9, 128'h1A5, got);
        check("unused_opcode_bypass", got[8:0] == {8'hA5, 1'b0}, $sformatf("got %b", got[8:0]));

        // SCAN_CFG: test_mode=1, scan_clk_sel=1, serial=1, chain_sel=0 -> 4'b0111
        shift_ir(4'b1000, cap);
        shift_dr(4, 128'b0111, got);
        check("scan_cfg_outputs", test_mode && scan_clk_sel, $sformatf("tm=%b sel=%b", test_mode, scan_clk_sel));
        shift_dr(4, 128'b0111, got);
        check("scan_cfg_readback", got[3:0] == 4'b0111, $sformatf("got %b", got[3:0]));
        idle(6);   // let the clock controller switch to TCK
        check("clock_switched", u_clk.t_q2 && !u_clk.f_q2, "clock mux did not switch to TCK");

        // SCAN_ACCESS, serial mode: TDI -> a -> b -> TDO, 12 bits.
        shift_ir(4'b1001, cap);
        loaded = 12'b1011_0110_1001;
        shift_dr(12, {116'b0, loaded}, got);              // load
        check("scan_load", {a, b} == loaded, $sformatf("core %b want %b", {a, b}, loaded));
        idle(3);                                            // no core clocks outside Shift/Capture
        check("scan_hold_in_idle", {a, b} == loaded, $sformatf("core %b", {a, b}));
        expect_next = core_next(loaded);
        pat = 128'h0;
        pat[11:0] = 12'b0101_1100_0011;
        shift_dr(12, pat, got);                             // capture, unload, load next
        check("scan_capture_unload", got[11:0] == expect_next,
              $sformatf("unloaded %b want %b", got[11:0], expect_next));
        check("scan_second_load", {a, b} == pat[11:0], $sformatf("core %b", {a, b}));

        // Select mode, chain 1 only: a flush comes out 7 cycles later.
        shift_ir(4'b1000, cap);
        shift_dr(4, 128'b1011, got);                        // tm=1 sel=1 serial=0 chain=1
        shift_ir(4'b1001, cap);
        pat = 128'h0;
        pat[19:0] = 20'b1100_1010_0111_0001_1011;
        shift_dr(20, pat, got);
        // first bit out is the captured b[0]; after 7 captured cells the flush follows
        check("chain1_flush", got[19:7] == pat[12:0], $sformatf("got %b", got[19:0]));

        // MBIST_CTRL: status captured, control updated with a strobe.
        shift_ir(4'b1010, cap);
        saw_update = 0;
        shift_dr(32, 128'hDEAD_BEEF, got);
        check("mbist_status_capture", got[31:0] == mbist_status, $sformatf("got %h", got[31:0]));
        check("mbist_ctrl_update", mbist_ctrl == 32'hDEAD_BEEF, $sformatf("ctrl %h", mbist_ctrl));
        check("mbist_update_strobe", saw_update, "no update strobe");
        mbist_status = 32'h0000_0001;
        shift_dr(32, 128'h0000_0000, got);
        check("mbist_status_recapture", got[31:0] == 32'h1, $sformatf("got %h", got[31:0]));
        check("mbist_ctrl_rewrite", mbist_ctrl == 32'h0, $sformatf("ctrl %h", mbist_ctrl));

        // DFT_STATUS read-only word.
        shift_ir(4'b1011, cap);
        shift_dr(16, 128'hFFFF, got);
        check("dft_status", got[15:0] == dft_status, $sformatf("got %h", got[15:0]));

        // TMS reset: back to IDCODE, configuration cleared.
        reset_by_tms();
        check("tms_reset_ir", ir == 4'b0001, $sformatf("ir=%b", ir));
        check("tms_reset_cfg", !test_mode && !scan_clk_sel, "SCAN_CFG not cleared");
        check("tdo_en_only_in_shift", !en_seen_outside_shift, "tdo_en outside Shift");

        // TRST_N asynchronous reset.
        shift_ir(4'b1111, cap);
        #3 trst_n = 0;
        #3 trst_n = 1;
        check("trst_reset", ir == 4'b0001 && tap_state == 4'hF, $sformatf("ir=%b state=%h", ir, tap_state));

        $display("RESULT %s %0d", errors == 0 ? "pass" : "fail", errors);
        $finish;
    end
endmodule
