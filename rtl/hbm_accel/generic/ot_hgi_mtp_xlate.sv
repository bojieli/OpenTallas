`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hgi-takeover 2026-10-09 (mtp-lead item 2; decision 3: the single CP block absorbs the MX1 MTP side): the generic-die
// BACKEND TRANSLATOR between the native DSpark controller's operations (hgi_mtp_native via the MX1 collar
// hfd_cmdproc_s_mtp_native_mx1_mtp: eng_cmd 201 + job / generation / sequence) and the HGI sequencer's doorbell.
//
// Expansion = ot_hbm_native_mtp_operation_backend_mx1 exactly (the launch order of tools/gpu_sys/v41_dspark.py
// expand(): op 0..5, the kind / token / position of every launch, the same shape checks), but each launch is ONE
// sequencer doorbell instead of a pair of legacy cmdproc20 doorbells:
//   doorbell {token 18 = {0, kind token 17}, pos 20 = position, job, gen, entry 3 = KERNEL, off = kent[kind]}
//   kent[11 x 32]: the per-model kernel entry offsets (16-byte units into the program image), MD words 16-26 (G23);
//   completion {token, pos, job, gen, status}: owned when job / gen / pos equal the launch's; status 0 required;
//   the RESULT kinds 4 (verify-row head) and 10 (draft head) raise am {valid, token 17} from the completion token
//   (the END-read merged argmax id, cp_vocab-checked by the sequencer) -- the MX1 collar's f_am (CTL.AMAX is not
//   needed: the legacy backend took am from the cmdproc20 completion token the same way).
// One launch in flight (the legacy backend's order and exactness; the sequencer runs one job at a time anyway).
// Faults (sticky until the drained reset, as the legacy backend): bad shape, a kernel entry of 0 (absent), a non-zero
// status, a completion not owned, a TOKX beat, external_fault.  MUT (bench): 1 am from the wrong kind (kind 1).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_mtp_xlate #(parameter integer MUT = 0) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          external_fault,
    input  wire          backend_quiescent,     // the die's units / services quiescent (MX1 f_backend[71])
    input  wire [351:0]  kent,                  // MD words 16 .. 26: kernel entry offsets for kinds 0 .. 10
    input  wire [16:0]   noise_token,           // the DSpark draft noise token (op 3 kind 6, column > 0)
    // native operation (MX1 collar t_backend / f_backend)
    input  wire          cmd_v,
    output wire          cmd_ready,
    input  wire [200:0]  cmd,
    input  wire [31:0]   cmd_job,
    input  wire [3:0]    cmd_generation,
    input  wire [31:0]   cmd_sequence,
    output wire          cpl_v,
    input  wire          cpl_ready,
    output wire [31:0]   cpl_job,
    output wire [3:0]    cpl_generation,
    output wire [31:0]   cpl_sequence,
    output wire          cpl_fault,
    output reg           am_v,
    output reg  [16:0]   am_idx,
    output wire          drained_ready,
    // sequencer doorbell / completion (the CP die arbitrates the host doorbell against this one)
    output reg           db_v,
    input  wire          db_rdy,
    output reg  [17:0]   db_token,
    output reg  [19:0]   db_pos,
    output wire [31:0]   db_job,
    output wire [3:0]    db_gen,
    output wire [1:0]    db_entry,
    output reg  [31:0]   db_off,
    input  wire          c_v,
    output wire          c_rdy,
    input  wire [17:0]   c_token,
    input  wire [19:0]   c_pos,
    input  wire [31:0]   c_job,
    input  wire [3:0]    c_gen,
    input  wire [3:0]    c_status,
    input  wire          c_tokx
);
    localparam IDLE = 3'd0, SELECT = 3'd1, DB = 3'd2, WAIT = 3'd3, CPL = 3'd4;
    reg [2:0] state; reg [5:0] cursor, total; reg fault;
    reg [285:0] raw;
    wire [200:0] held = raw[200:0];
    assign cpl_job = raw[232:201]; assign cpl_generation = raw[236:233]; assign cpl_sequence = raw[268:237];
    assign db_job = cpl_job; assign db_gen = cpl_generation; assign db_entry = 2'd3;
    wire [3:0] op = held[3:0]; wire [7:0] idx = held[11:4]; wire [31:0] pos = held[47:16];
    wire [16:0] tok1 = held[64:48]; wire [135:0] toks = held[200:65]; wire [16:0] held_noise = raw[285:269];
    wire [3:0] iop = cmd[3:0]; wire [7:0] iidx = cmd[11:4]; wire [3:0] inc = cmd[15:12]; wire [31:0] ipos = cmd[47:16];
    wire [32:0] vend = {1'b0, ipos} + inc;
    wire [32:0] dend = {1'b0, ipos} + 6;
    wire valid_shape = (iop <= 5) && ipos < 1048576 &&
        ((iop == 0 && iidx < 40 && inc >= 1 && inc <= 6 && vend <= 1048576) ||
         ((iop == 1 || iop == 2) && iidx == 0 && inc >= 1 && inc <= 6 && vend <= 1048576) ||
         (iop == 3 && iidx < 3 && inc == 5 && dend <= 1048576) ||
         (iop == 4 && iidx == 0 && inc == 5 && dend <= 1048576) ||
         (iop == 5 && iidx < 5 && inc == 1));
    assign cmd_ready = rst_n && state == IDLE && backend_quiescent && !external_fault;
    assign cpl_v = state == CPL; assign cpl_fault = fault;
    assign drained_ready = rst_n && state == IDLE && !db_v && backend_quiescent;
    assign c_rdy = 1'b1;                                        // completions are consumed the cycle they arrive
    // ---- the expansion (verbatim from the legacy backend)
    reg [3:0] kind; reg [16:0] token; reg [19:0] position;
    integer column, part, stride, first_group, local_cursor;
    always @* begin
        kind = 0; token = 0; position = 0; column = 0; part = 0; stride = 0; first_group = 0; local_cursor = 0;
        case (op)
            0: begin
                stride = (idx == 0) ? 4 : 3; column = cursor / stride; part = cursor % stride;
                if (part == 0) begin kind = 0; token = column; position = idx; end
                else if (idx == 0 && part == 1) begin kind = 2; token = toks[column*17 +: 17]; position = pos + column; end
                else if (part == stride - 1) begin kind = 1; token = column; position = pos + column; end
                else begin kind = 3; token = toks[column*17 +: 17]; position = pos + column; end
            end
            1: begin column = cursor / 2; if (!cursor[0]) begin kind = 0; token = column; position = 63; end
                     else begin kind = 4; position = pos + column; end end
            2: begin kind = 5; token = cursor; position = pos + cursor; end
            3: begin
                stride = (idx == 0) ? 4 : 3; first_group = 5 * stride;
                if (cursor < first_group) begin
                    column = cursor / stride; part = cursor % stride;
                    if (part == 0) begin kind = 0; token = 8 + column; position = 40 + idx; end
                    else if (idx == 0 && part == 1) begin kind = 6; token = (column == 0) ? tok1 : held_noise; position = 0; end
                    else if (part == stride - 1) begin kind = 1; token = 8 + column; position = 0; end
                    else begin kind = 7; token = column; position = pos + 1 + column; end
                end else begin
                    local_cursor = cursor - first_group; column = local_cursor / 3; part = local_cursor % 3;
                    if (part == 0) begin kind = 0; token = 8 + column; position = 40 + idx; end
                    else if (part == 1) begin kind = 8; token = column; position = pos + 1 + column; end
                    else begin kind = 1; token = 8 + column; position = 0; end
                end
            end
            4: begin column = cursor / 2;
                if (!cursor[0]) begin kind = 0; token = 8 + column; position = 63; end
                else begin kind = 9; token = column; position = pos + 1 + column; end
            end
            5: begin kind = 10; token = tok1; position = idx; end
            default: begin kind = 0; token = 0; position = 0; end
        endcase
    end
    wire [31:0] kofs = kent[kind*32 +: 32];
    reg [3:0] kind_q;
    wire result_kind = (MUT == 1) ? (kind_q == 1) : (kind_q == 4 || kind_q == 10);
    wire owned = c_job == cpl_job && c_gen == cpl_generation && c_pos == db_pos;
    wire [285:0] incoming = {noise_token, cmd_sequence, cmd_generation, cmd_job, cmd};
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= IDLE; cursor <= 0; total <= 0; fault <= 0; am_v <= 0; am_idx <= 0; raw <= 0; db_v <= 0;
            db_token <= 0; db_pos <= 0; db_off <= 0; kind_q <= 0;
        end else begin
            am_v <= 1'b0;
            if (cmd_v && cmd_ready) begin
                raw <= incoming; cursor <= 0; fault <= 0;
                total <= (iop == 0) ? inc * ((iidx == 0) ? 4 : 3) : (iop == 1) ? inc * 2 : (iop == 2) ? inc :
                         (iop == 3) ? ((iidx == 0) ? 35 : 30) : (iop == 4) ? 10 : 1;
                if (!valid_shape) begin fault <= 1; state <= CPL; end
                else state <= SELECT;
            end
            case (state)
                IDLE: ;
                SELECT: if (kofs == 32'd0) begin fault <= 1; state <= CPL; end           // kernel absent from the image
                    else begin
                        db_v <= 1'b1; db_token <= {1'b0, token}; db_pos <= position; db_off <= kofs; kind_q <= kind;
                        state <= DB;
                    end
                DB: if (db_rdy) begin db_v <= 1'b0; state <= WAIT; end
                WAIT: if (c_v) begin
                        if (c_tokx || !owned || c_status != 4'd0) begin fault <= 1; state <= CPL; end
                        else begin
                            if (result_kind) begin am_v <= 1'b1; am_idx <= c_token[16:0]; end
                            if (cursor + 1 == total) state <= CPL; else begin cursor <= cursor + 1'b1; state <= SELECT; end
                        end
                    end
                CPL: if (cpl_ready) state <= IDLE;
                default: state <= IDLE;
            endcase
            if (external_fault && state != IDLE) begin fault <= 1; db_v <= 1'b0; state <= CPL; end
        end
    end
endmodule
`default_nettype wire
