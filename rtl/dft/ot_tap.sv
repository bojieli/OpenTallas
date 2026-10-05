`timescale 1ns/1ps
// IEEE 1149.1 test access port (a subset) for the OpenTallas decode dies.
//
// Implemented:
//   * the 16-state TAP controller, TRST_N (asynchronous) and the five-TMS-high
//     synchronous reset;
//   * a 4-bit instruction register; Capture-IR loads 4'b0001 (LSBs "01" as the
//     standard requires); Test-Logic-Reset selects IDCODE;
//   * IDCODE (32-bit, LSB 1) and BYPASS (1 bit, captures 0); every opcode not
//     listed below selects BYPASS, as the standard requires of unused codes;
//   * three user data registers that give access to design-for-test:
//       SCAN_CFG    test_mode, TCK-clocked scan select, serial/one-chain mode
//                   and the chain index;
//       SCAN_ACCESS the internal scan chains themselves: Shift-DR shifts them
//                   one bit per TCK with scan_en = 1, Capture-DR applies one
//                   capture clock with scan_en = 0 -- so a scan test through
//                   the TAP is load (Shift-DR), capture (Capture-DR), unload
//                   while loading the next (Shift-DR);
//       MBIST_CTRL  one shift register that Capture-DR loads with the memory
//                   BIST status word and Update-DR copies into the BIST
//                   control register (with a one-TCK update strobe), so a
//                   single scan writes the next command and reads the status;
//     and a read-only DFT_STATUS word.
// Not implemented: boundary scan (EXTEST, SAMPLE/PRELOAD and the boundary
// register), which the standard makes mandatory; the die's pads are not in the
// RTL yet.  That is the documented deviation (docs/DFT.md).
//
// Timing follows 1149.1: TDI and TMS are sampled and shift registers move on
// the rising edge of TCK; TDO, the instruction and every update register
// change on the falling edge.
//
// Scan chains are clocked by the core's own clock tree.  scan_clk_en tells the
// clock controller (ot_dft_scan_clock.sv) which TCK cycles to pass to the core
// when scan_clk_sel is set: every cycle spent in Shift-DR or Capture-DR under
// SCAN_ACCESS.  It is a function of the TAP state, which changes on the rising
// edge, so a latch-based gate that samples it while TCK is low passes exactly
// the next rising edge.
module ot_tap #(
    parameter [31:0] IDCODE         = 32'h0f7a_1c01,  // version 0, part 0xF7A1, manufacturer 0x600 (unassigned), LSB 1
    parameter int    NCHAINS        = 8,
    parameter int    MBIST_CTRL_W   = 32,
    parameter int    MBIST_STATUS_W = 32,
    parameter int    STATUS_W       = 16
) (
    input  logic                      tck,
    input  logic                      tms,
    input  logic                      tdi,
    input  logic                      trst_n,
    output logic                      tdo,
    output logic                      tdo_en,

    // --- scan access -------------------------------------------------------
    output logic                      test_mode,      // SCAN_CFG[0]: hold async resets/ICGs in test state
    output logic                      scan_clk_sel,   // SCAN_CFG[1]: core clocks from TCK through the gate
    output logic                      scan_en,        // 1 = shift, during Shift-DR under SCAN_ACCESS
    output logic                      scan_clk_en,    // pass this TCK cycle to the core
    output logic [NCHAINS-1:0]        scan_in,        // to the chains' scan_in ports
    input  logic [NCHAINS-1:0]        scan_out,       // from the chains' scan_out ports

    // --- memory BIST -------------------------------------------------------
    output logic [MBIST_CTRL_W-1:0]   mbist_ctrl,
    output logic                      mbist_ctrl_update,  // one TCK cycle after Update-DR of MBIST_CTRL
    input  logic [MBIST_STATUS_W-1:0] mbist_status,

    // --- read-only status --------------------------------------------------
    input  logic [STATUS_W-1:0]       dft_status,

    // --- observability for integration and test ----------------------------
    output logic [3:0]                ir,
    output logic [3:0]                tap_state
);
    localparam int CHAIN_SEL_W = (NCHAINS > 1) ? $clog2(NCHAINS) : 1;
    localparam int SCAN_CFG_W  = 3 + CHAIN_SEL_W;

    // Instruction opcodes.
    localparam logic [3:0] I_IDCODE      = 4'b0001;
    localparam logic [3:0] I_SCAN_CFG    = 4'b1000;
    localparam logic [3:0] I_SCAN_ACCESS = 4'b1001;
    localparam logic [3:0] I_MBIST_CTRL  = 4'b1010;
    localparam logic [3:0] I_DFT_STATUS  = 4'b1011;
    localparam logic [3:0] I_BYPASS      = 4'b1111;

    // TAP controller states (the encoding used by IEEE 1149.1 Table 6-3's
    // common implementation).
    localparam logic [3:0]
        S_EXIT2_DR  = 4'h0, S_EXIT1_DR  = 4'h1, S_SHIFT_DR  = 4'h2, S_PAUSE_DR  = 4'h3,
        S_SELECT_IR = 4'h4, S_UPDATE_DR = 4'h5, S_CAPTURE_DR = 4'h6, S_SELECT_DR = 4'h7,
        S_EXIT2_IR  = 4'h8, S_EXIT1_IR  = 4'h9, S_SHIFT_IR  = 4'hA, S_PAUSE_IR  = 4'hB,
        S_IDLE      = 4'hC, S_UPDATE_IR = 4'hD, S_CAPTURE_IR = 4'hE, S_RESET     = 4'hF;

    logic [3:0] state, next_state;

    always_comb begin
        unique case (state)
            S_RESET:      next_state = tms ? S_RESET     : S_IDLE;
            S_IDLE:       next_state = tms ? S_SELECT_DR : S_IDLE;
            S_SELECT_DR:  next_state = tms ? S_SELECT_IR : S_CAPTURE_DR;
            S_CAPTURE_DR: next_state = tms ? S_EXIT1_DR  : S_SHIFT_DR;
            S_SHIFT_DR:   next_state = tms ? S_EXIT1_DR  : S_SHIFT_DR;
            S_EXIT1_DR:   next_state = tms ? S_UPDATE_DR : S_PAUSE_DR;
            S_PAUSE_DR:   next_state = tms ? S_EXIT2_DR  : S_PAUSE_DR;
            S_EXIT2_DR:   next_state = tms ? S_UPDATE_DR : S_SHIFT_DR;
            S_UPDATE_DR:  next_state = tms ? S_SELECT_DR : S_IDLE;
            S_SELECT_IR:  next_state = tms ? S_RESET     : S_CAPTURE_IR;
            S_CAPTURE_IR: next_state = tms ? S_EXIT1_IR  : S_SHIFT_IR;
            S_SHIFT_IR:   next_state = tms ? S_EXIT1_IR  : S_SHIFT_IR;
            S_EXIT1_IR:   next_state = tms ? S_UPDATE_IR : S_PAUSE_IR;
            S_PAUSE_IR:   next_state = tms ? S_EXIT2_IR  : S_PAUSE_IR;
            S_EXIT2_IR:   next_state = tms ? S_UPDATE_IR : S_SHIFT_IR;
            S_UPDATE_IR:  next_state = tms ? S_SELECT_DR : S_IDLE;
            default:      next_state = S_RESET;
        endcase
    end

    always_ff @(posedge tck or negedge trst_n) begin
        if (!trst_n) state <= S_RESET;
        else         state <= next_state;
    end
    assign tap_state = state;

    // ---------------------------------------------------------------- IR
    logic [3:0] ir_shift;
    always_ff @(posedge tck or negedge trst_n) begin
        if (!trst_n) begin
            ir_shift <= I_IDCODE;
        end else if (state == S_CAPTURE_IR) begin
            ir_shift <= 4'b0001;
        end else if (state == S_SHIFT_IR) begin
            ir_shift <= {tdi, ir_shift[3:1]};
        end
    end
    always_ff @(negedge tck or negedge trst_n) begin
        if (!trst_n)                 ir <= I_IDCODE;
        else if (state == S_RESET)   ir <= I_IDCODE;
        else if (state == S_UPDATE_IR) ir <= ir_shift;
    end

    // Decoded instruction; unknown opcodes behave as BYPASS.
    logic sel_idcode, sel_scan_cfg, sel_scan_access, sel_mbist, sel_status, sel_bypass;
    always_comb begin
        sel_idcode      = (ir == I_IDCODE);
        sel_scan_cfg    = (ir == I_SCAN_CFG);
        sel_scan_access = (ir == I_SCAN_ACCESS);
        sel_mbist       = (ir == I_MBIST_CTRL);
        sel_status      = (ir == I_DFT_STATUS);
        sel_bypass      = (ir == I_BYPASS) || !(sel_idcode || sel_scan_cfg || sel_scan_access || sel_mbist || sel_status);
    end

    // ---------------------------------------------------------------- DRs
    logic                      bypass_q;
    logic [31:0]               idcode_shift;
    logic [SCAN_CFG_W-1:0]     cfg_shift, cfg_q;
    localparam int MBIST_W = (MBIST_CTRL_W > MBIST_STATUS_W) ? MBIST_CTRL_W : MBIST_STATUS_W;
    logic [MBIST_W-1:0]        mbist_shift;
    logic [STATUS_W-1:0]       status_shift;

    wire capture_dr = (state == S_CAPTURE_DR);
    wire shift_dr   = (state == S_SHIFT_DR);

    always_ff @(posedge tck or negedge trst_n) begin
        if (!trst_n) begin
            bypass_q           <= 1'b0;
            idcode_shift       <= IDCODE;
            cfg_shift          <= '0;
            mbist_shift        <= '0;
            status_shift       <= '0;
        end else begin
            if (capture_dr) begin
                bypass_q     <= 1'b0;
                idcode_shift <= IDCODE;
                cfg_shift    <= cfg_q;
                mbist_shift  <= MBIST_W'(mbist_status);
                status_shift <= dft_status;
            end else if (shift_dr) begin
                if (sel_bypass)   bypass_q     <= tdi;
                if (sel_idcode)   idcode_shift <= {tdi, idcode_shift[31:1]};
                if (sel_scan_cfg) cfg_shift    <= {tdi, cfg_shift[SCAN_CFG_W-1:1]};
                if (sel_status)   status_shift <= {tdi, status_shift[STATUS_W-1:1]};
                if (sel_mbist)    mbist_shift  <= {tdi, mbist_shift[MBIST_W-1:1]};
            end
        end
    end

    // Update registers change on the falling edge in Update-DR.
    always_ff @(negedge tck or negedge trst_n) begin
        if (!trst_n) begin
            cfg_q      <= '0;
            mbist_ctrl <= '0;
        end else if (state == S_RESET) begin
            cfg_q      <= '0;
            mbist_ctrl <= '0;
        end else if (state == S_UPDATE_DR) begin
            if (sel_scan_cfg) cfg_q      <= cfg_shift;
            if (sel_mbist)    mbist_ctrl <= mbist_shift[MBIST_CTRL_W-1:0];
        end
    end
    // A strobe the BIST side can synchronise: high for the TCK cycle after the
    // update (set on the Update-DR falling edge, cleared on the next one).
    always_ff @(negedge tck or negedge trst_n) begin
        if (!trst_n) mbist_ctrl_update <= 1'b0;
        else         mbist_ctrl_update <= (state == S_UPDATE_DR) && sel_mbist;
    end

    // ---------------------------------------------------------------- scan
    logic                   serial_mode;
    logic [CHAIN_SEL_W-1:0] chain_sel;
    assign test_mode    = cfg_q[0];
    assign scan_clk_sel = cfg_q[1];
    assign serial_mode  = cfg_q[2];   // 1: all chains in series, TDI -> chain 0 -> ... -> chain N-1 -> TDO
    assign chain_sel    = cfg_q[3 +: CHAIN_SEL_W];

    assign scan_en     = sel_scan_access && shift_dr;
    assign scan_clk_en = sel_scan_access && (shift_dr || capture_dr);

    logic scan_tdo;
    always_comb begin
        scan_in = '0;
        if (serial_mode) begin
            scan_in[0] = tdi;
            for (int c = 1; c < NCHAINS; c++) scan_in[c] = scan_out[c - 1];
            scan_tdo = scan_out[NCHAINS - 1];
        end else begin
            for (int c = 0; c < NCHAINS; c++) scan_in[c] = (CHAIN_SEL_W'(c) == chain_sel) ? tdi : 1'b0;
            scan_tdo = scan_out[chain_sel];
        end
    end

    // ---------------------------------------------------------------- TDO
    logic tdo_mux;
    always_comb begin
        if (state == S_SHIFT_IR)   tdo_mux = ir_shift[0];
        else if (sel_idcode)       tdo_mux = idcode_shift[0];
        else if (sel_scan_cfg)     tdo_mux = cfg_shift[0];
        else if (sel_scan_access)  tdo_mux = scan_tdo;
        else if (sel_mbist)        tdo_mux = mbist_shift[0];
        else if (sel_status)       tdo_mux = status_shift[0];
        else                       tdo_mux = bypass_q;
    end
    always_ff @(negedge tck or negedge trst_n) begin
        if (!trst_n) begin
            tdo    <= 1'b0;
            tdo_en <= 1'b0;
        end else begin
            tdo    <= tdo_mux;
            tdo_en <= (state == S_SHIFT_IR) || (state == S_SHIFT_DR);
        end
    end
endmodule
