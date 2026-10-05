// ATTENTION.SPARSE's AV accumulation: the block rescale, then the ordered
// probability-weighted sum of the selected KV rows.
//
// ``_accumulate_context`` in runtime/tensor_accelerator/sparse_attention.py is
// the authority, and its docstring fixes the schedule:
//
//   "Lane ``l`` updates every ``(head, channel)`` accumulator at once, so each
//    channel still accumulates its lanes in ascending slot order."
//
// LANE ON THE OUTSIDE, CHANNEL ON THE INSIDE -- the transpose of the QK walk,
// and for the same reason: the inner index selects the accumulator, so the inner
// loop's iterations are mutually independent and the MAC's latency hides inside
// one pass. Here that inner extent is head_dim, which is a RUNTIME value, so the
// accumulator hazard cannot be closed at elaboration the way the QK walk closes
// it against a fixed lane count. It is refused at admission instead.
//
// The caller's block loop supplies rescale = exp(max_old - max_new) per block,
// and ``_execute_tile`` applies it to the accumulator BEFORE the lane sum:
//
//   np.multiply(accumulator, rescale[:, :, None], out=accumulator)
//   if bool(np.any(rescale == 0)):
//       np.add(accumulator, _BINARY32_ZERO, out=accumulator)
//
// so this walk does both, in that order, and only canonicalizes behind the
// reference's own guard -- an unconditional canonicalization would differ from
// the authority on an accumulator that is already negative zero at a block whose
// rescale is one.
//
// Each product-add is ONE rounding of ``accumulator + probability * element``:
// the reference adds with two roundings and then repairs exactly the terms where
// ``_rounds_twice`` says the two differ, so the single-rounding fused MAC IS the
// contract, not an approximation of it. Probabilities arrive already narrowed to
// BF16 (``probability_codes, _ = _narrow(probabilities)``) and the KV elements
// are BF16 codes, so ot_mac_bf16_fp32_pipe computes the contract directly.
module ot_a3_attention_av_walk #(
    parameter integer CHANNELS_MAX = 512,
    parameter integer LANES_MAX    = 64,
    //: SIX, not five: this walk instantiates the product-add with its rounding
    //: stage split, which is what lifts the block off the MAC's own 1.716 ns
    //: final cone. Both depths are bit-identical to
    //: ot_fp32_rne_pkg::bf16_bf16_fp32_product_add_rne over 901,440 cases, so
    //: the choice is purely a timing one.
    parameter integer MAC_ROUND_STAGE = 1,
    parameter integer MAC_LAT      = 6,
    parameter integer MUL_LAT      = 5
) (
    input  wire        clk,
    input  wire        rst_n,
    input  wire        start,

    //: Zero the accumulator before this block instead of rescaling it -- the
    //: first source block of a tile, where the reference starts from np.zeros.
    input  wire        cfg_clear,
    input  wire [31:0] cfg_channels,
    input  wire [31:0] cfg_lanes,
    input  wire [31:0] cfg_rescale_code,
    input  wire [31:0] cfg_kv_base,
    input  wire [31:0] cfg_kv_stride,
    input  wire [LANES_MAX-1:0]      lane_valid,
    input  wire [LANES_MAX*32-1:0]   lane_row,
    //: The block's probabilities, ALREADY BF16, which is where the descriptor
    //: puts the narrowing: "binary32_to_bf16_rne_once_before_av". They arrive on
    //: a bus because that is the form ot_a3_attention_denominator emits them in;
    //: a memory port here would mean writing 64 words to a scratch buffer and
    //: reading them straight back.
    input  wire [LANES_MAX*16-1:0]   lane_prob,

    output reg         kv_rd_en,
    output reg  [31:0] kv_rd_addr,
    input  wire [31:0] kv_rd_data,

    //: The accumulator is up to CHANNELS_MAX wide, so it leaves through a read
    //: port rather than a bus.
    input  wire [31:0] out_rd_addr,
    //: REGISTERED, not a combinational read of the accumulator array.
    //:
    //: Routed on ASAP7 at 1.2 ns the block's only violating path was this port
    //: to that one -- out_rd_addr[3] to out_rd_data[9] at -22.5 ps, a 128-entry
    //: 32-bit mux straddling the block boundary with the flow's input and
    //: output delay budgets on either end. It is also what the consumer already
    //: assumes: ot_a3_attention_epilogue spends a cycle between presenting an
    //: address and sampling, commented "one edge for the memory to capture the
    //: address", so a registered read is the shape it was written against.
    output reg  [31:0] out_rd_data,

    output reg         busy,
    output reg         done,
    output reg  [7:0]  error_code,
    output reg         nonfinite,
    output reg  [31:0] mac_count
);
    //: The error codes are referenced through the package scope rather than
    //: wildcard-imported: pinned Yosys 0.68 rejects a body-level `import`
    //: outright ("syntax error, unexpected TOK_IMPORT"), while Verilator
    //: and Icarus both accept it, so the import passes every functional
    //: gate and fails only at synthesis.

    //: Read address to issue is one edge and the MAC retires MAC_LAT after that,
    //: so a channel's accumulator is busy for MAC_LAT + 2 issues and the inner
    //: pass must be longer than that for the schedule to be hazard-free.
    localparam integer PIPE_DEPTH = MAC_LAT + 2;

    localparam [2:0] S_IDLE   = 3'd0;
    localparam [2:0] S_SCALE  = 3'd1;
    localparam [2:0] S_SDRAIN = 3'd2;
    localparam [2:0] S_PHOLD  = 3'd3;
    localparam [2:0] S_ACCUM  = 3'd4;
    localparam [2:0] S_ADRAIN = 3'd5;
    localparam [2:0] S_DONE   = 3'd6;

    reg [2:0]  state;
    reg [31:0] chan, lane, drain;
    //: THE PROBABILITY TRAVELS WITH ITS ELEMENT. Holding it in one register
    //: across the channel pass leaves the pass's last product-add sampling it
    //: one cycle after the next lane has overwritten it, so the final channel of
    //: every lane would take the next lane's weight. Carrying it through the
    //: same two stages as the channel index removes the hazard outright instead
    //: of leaving it standing off a one-cycle margin.
    reg [15:0] kv_rd_prob;
    reg [15:0] b_prob;
    //: The lane's row base, multiplied ONCE per lane instead of once per
    //: channel: the inner loop runs cfg_channels times per lane, so computing
    //: lane_row * cfg_kv_stride inside it would put a 32x32 multiply in the
    //: address path of every issue cycle to save one register.
    //:
    //: AND THE MULTIPLY IS SPLIT ACROSS S_PHOLD's THREE PHASES, because static
    //: timing does not care how often a path runs -- a multiply reached once
    //: per lane is still a multiply in a one-cycle path, and in the QK walk the
    //: same expression was that block's critical path at -239 ps in 1.2 ns once
    //: the product-add stopped being it. Two 16x32 halves with a register
    //: between cost two extra cycles per lane, against cfg_channels issue
    //: cycles: 3 in 512 at the shipped head width.
    reg [31:0] row_base;
    reg [31:0] mul_row, mul_stride;
    reg [47:0] part_lo, part_hi;
    reg [1:0]  pphase;
    reg [31:0] acc [0:CHANNELS_MAX-1];
    integer i;

    //: The channel that produced the address now on the kv bus, latched by the
    //: same edge as the address so the element and its accumulator cannot drift.
    reg [31:0] kv_rd_chan;
    reg        kv_rd_live;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) out_rd_data <= 32'd0;
        else out_rd_data <= acc[out_rd_addr[$clog2(CHANNELS_MAX)-1:0]];
    end

    // -- the rescale multiply -------------------------------------------------
    reg        mul_vin;
    reg [31:0] mul_a;
    wire        mul_vout;
    wire [31:0] mul_y;
    wire [1:0]  mul_err;
    ot_fp32_mul_rne_pipe rescale_mul (
        .clk(clk), .rst_n(rst_n), .valid_in(mul_vin),
        .a(mul_a), .b(cfg_rescale_code),
        .y(mul_y), .err(mul_err), .valid_out(mul_vout)
    );
    //: MUL_LAT + 1 DEEP, WHERE THE PRODUCT-ADD's COMPANION BELOW IS MAC_LAT.
    //: The two are not inconsistent, they are anchored differently. A companion
    //: must be as deep as the latency counted FROM THE ISSUE CYCLE, and the
    //: issue cycle is the one in which valid_in is high. b_chan below is already
    //: registered, so it is valid DURING its issue cycle and MAC_LAT stages
    //: carry it to the retirement. `chan` here is the live cursor, latched into
    //: the companion by the same edge that latches mul_a -- one edge BEFORE the
    //: cycle in which mul_vin is high -- so it needs one stage more to arrive
    //: with its own product. Getting this wrong does not lose a rescale: it
    //: writes each scaled channel into its neighbour, which is how this walk
    //: first failed, on 970 of 1,104 channels.
    localparam integer MUL_PIPE = MUL_LAT + 1;
    reg [31:0] mul_chan [0:MUL_PIPE-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) for (i = 0; i < MUL_PIPE; i = i + 1) mul_chan[i] <= 32'd0;
        else begin
            mul_chan[0] <= chan;
            for (i = 0; i < MUL_PIPE-1; i = i + 1) mul_chan[i+1] <= mul_chan[i];
        end
    end
    wire [31:0] mul_retire_chan = mul_chan[MUL_PIPE-1];

    //: ``np.add(accumulator, _BINARY32_ZERO)`` behind the reference's own
    //: rescale == 0 guard. Adding positive zero is the identity on every value
    //: a rescaled accumulator can hold except negative zero, which it collapses,
    //: so this mux is that add exactly and costs no adder.
    //:
    //: IT IS ALSO UNREACHABLE HERE, and deliberately kept anyway.
    //: ot_fp32_mul_rne_pipe documents that "a zero operand gives +0 whatever the
    //: signs", so mul_y is never 0x80000000 and the reference's canonicalizing
    //: add has nothing to correct against THIS multiplier. Keeping the mux makes
    //: the walk right against a multiplier that preserves signed zero instead of
    //: silently depending on one that does not -- the same reason the reference
    //: keeps its own round-to-odd step, which it measured over 414,099 triples
    //: and found never fires: "it is kept because it makes the function correct
    //: for any operand pair rather than only for this one".
    wire rescale_is_zero = (cfg_rescale_code[30:0] == 31'd0);
    wire [31:0] scaled_canon =
        (rescale_is_zero && mul_y == 32'h8000_0000) ? 32'h0000_0000 : mul_y;

    // -- the product-add ------------------------------------------------------
    reg        b_valid;
    reg [31:0] b_chan;
    reg        b_live;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            b_valid <= 1'b0; b_chan <= 32'd0; b_live <= 1'b0;
            b_prob <= 16'd0;
        end else begin
            b_valid <= kv_rd_en;
            b_chan  <= kv_rd_chan;
            b_live  <= kv_rd_live;
            b_prob  <= kv_rd_prob;
        end
    end
    //: The contract's KV block is zero on a padding lane, and this walk supplies
    //: that zero rather than trusting the row the placement table points at.
    wire [15:0] kv_element = b_live ? kv_rd_data[15:0] : 16'h0000;
    wire [31:0] acc_in = acc[b_chan[$clog2(CHANNELS_MAX)-1:0]];

    wire        mac_vout;
    wire [31:0] mac_y;
    wire [1:0]  mac_err;
    ot_mac_bf16_fp32_pipe #(.ROUND_STAGE(MAC_ROUND_STAGE)) product_add (
        .clk(clk), .rst_n(rst_n), .valid_in(b_valid),
        .a(b_prob), .b(kv_element), .c(acc_in),
        .y(mac_y), .err(mac_err), .valid_out(mac_vout)
    );
    reg [31:0] mac_chan [0:MAC_LAT-1];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) for (i = 0; i < MAC_LAT; i = i + 1) mac_chan[i] <= 32'd0;
        else begin
            mac_chan[0] <= b_chan;
            for (i = 0; i < MAC_LAT-1; i = i + 1) mac_chan[i+1] <= mac_chan[i];
        end
    end
    wire [31:0] mac_retire_chan = mac_chan[MAC_LAT-1];

    wire lane_is_live = lane_valid[lane[$clog2(LANES_MAX)-1:0]];

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state <= S_IDLE; busy <= 1'b0; done <= 1'b0;
            error_code <= ot_a3_engine_pkg::ERR_NONE; nonfinite <= 1'b0; mac_count <= 32'd0;
            chan <= 32'd0; lane <= 32'd0; drain <= 32'd0;
            kv_rd_prob <= 16'd0;
            kv_rd_en <= 1'b0; kv_rd_addr <= 32'd0;
            kv_rd_chan <= 32'd0; kv_rd_live <= 1'b0;
            row_base <= 32'd0; pphase <= 2'd0;
            mul_row <= 32'd0; mul_stride <= 32'd0;
            part_lo <= 48'd0; part_hi <= 48'd0;
            mul_vin <= 1'b0; mul_a <= 32'd0;
            for (i = 0; i < CHANNELS_MAX; i = i + 1) acc[i] <= 32'd0;
        end else begin
            done <= 1'b0;
            kv_rd_en <= 1'b0;
            mul_vin <= 1'b0;

            //: Retirements are independent of the state machine's cursor.
            if (mul_vout) begin
                acc[mul_retire_chan[$clog2(CHANNELS_MAX)-1:0]] <= scaled_canon;
                if (mul_err != 2'd0) nonfinite <= 1'b1;
            end
            if (mac_vout) begin
                acc[mac_retire_chan[$clog2(CHANNELS_MAX)-1:0]] <= mac_y;
                mac_count <= mac_count + 32'd1;
                if (mac_err != 2'd0) nonfinite <= 1'b1;
            end

            case (state)
                S_IDLE: begin
                    if (start) begin
                        if (cfg_channels == 32'd0 ||
                            cfg_channels > CHANNELS_MAX[31:0] ||
                            cfg_lanes == 32'd0 ||
                            cfg_lanes > LANES_MAX[31:0] ||
                            //: The hazard the QK walk closes at elaboration is
                            //: closed here at admission, because the inner
                            //: extent is head_dim. Every shipped
                            //: ATTENTION.SPARSE head_dim is 16, 128 or 512, so
                            //: the floor of MAC_LAT + 3 = 9 refuses nothing the
                            //: device is asked to run -- but it DOES move with
                            //: the product-add's depth, and splitting that
                            //: unit's rounding stage raised the floor from 8 to
                            //: 9 and turned a head_dim of 8 into a refusal.
                            cfg_channels <= PIPE_DEPTH[31:0]) begin
                            error_code <= ot_a3_engine_pkg::ERR_SHAPE;
                            done <= 1'b1;
                            busy <= 1'b0;
                        end else begin
                            error_code <= ot_a3_engine_pkg::ERR_NONE;
                            busy <= 1'b1;
                            nonfinite <= 1'b0;
                            mac_count <= 32'd0;
                            chan <= 32'd0;
                            if (cfg_clear) begin
                                for (i = 0; i < CHANNELS_MAX; i = i + 1)
                                    acc[i] <= 32'd0;
                                lane <= 32'd0;
                                pphase <= 2'd0;
                                state <= S_PHOLD;
                            end else begin
                                state <= S_SCALE;
                            end
                        end
                    end
                end

                //: One rescale multiply per channel. No channel repeats, so this
                //: pass has no accumulator hazard of its own.
                S_SCALE: begin
                    mul_vin <= 1'b1;
                    mul_a <= acc[chan[$clog2(CHANNELS_MAX)-1:0]];
                    if (chan + 32'd1 >= cfg_channels) begin
                        drain <= 32'd0;
                        state <= S_SDRAIN;
                    end else begin
                        chan <= chan + 32'd1;
                    end
                end

                //: The rescale must land before the first product reads it --
                //: and, given the admission bound, IT ALREADY HAS. Channel c's
                //: rescale retires c + MUL_LAT + 1 cycles into the pass; without
                //: this state channel c's first product-add would read it at
                //: cofs + c + 4 where cofs = cfg_channels, so the read trails
                //: the write whenever cfg_channels > MUL_LAT - 3, and admission
                //: already refuses anything at or below MAC_LAT + 2 = 7.
                //:
                //: A mutation that replaces this wait with a straight-through
                //: transition therefore SURVIVES the whole vector suite, which
                //: is how that was established rather than argued. The state is
                //: kept because the inequality depends on MUL_LAT, MAC_LAT and
                //: the admission bound jointly, and a later change to any one of
                //: them would otherwise turn a passing engine into a silently
                //: wrong one. It costs MUL_LAT + 3 cycles against a block of
                //: cfg_lanes * cfg_channels product-adds -- 8 cycles in 32,768
                //: at the shipped head_dim.
                S_SDRAIN: begin
                    if (drain >= MUL_LAT[31:0] + 32'd2) begin
                        lane <= 32'd0;
                        pphase <= 2'd0;
                        state <= S_PHOLD;
                    end else begin
                        drain <= drain + 32'd1;
                    end
                end

                //: Three cycles per lane, to multiply the row base in two
                //: halves. The probability needs no read: it is on the bus.
                S_PHOLD: begin
                    if (pphase == 2'd0) begin
                        mul_row <= lane_row[lane[$clog2(LANES_MAX)-1:0]*32 +: 32];
                        mul_stride <= cfg_kv_stride;
                        pphase <= 2'd1;
                    end else if (pphase == 2'd1) begin
                        part_lo <= {16'd0, mul_row[15:0]} * {16'd0, mul_stride};
                        part_hi <= {16'd0, mul_row[31:16]} * {16'd0, mul_stride};
                        pphase <= 2'd2;
                    end else begin
                        row_base <= part_lo[31:0] + {part_hi[15:0], 16'd0};
                        pphase <= 2'd0;
                        chan <= 32'd0;
                        state <= S_ACCUM;
                    end
                end

                //: lane OUTSIDE, channel INSIDE -- the reference's schedule.
                S_ACCUM: begin
                    kv_rd_en <= 1'b1;
                    kv_rd_chan <= chan;
                    kv_rd_live <= lane_is_live;
                    kv_rd_prob <= lane_prob[lane[$clog2(LANES_MAX)-1:0]*16 +: 16];
                    kv_rd_addr <= cfg_kv_base + row_base + chan;
                    if (chan + 32'd1 >= cfg_channels) begin
                        if (lane + 32'd1 >= cfg_lanes) begin
                            drain <= 32'd0;
                            state <= S_ADRAIN;
                        end else begin
                            lane <= lane + 32'd1;
                            pphase <= 2'd0;
                            state <= S_PHOLD;
                        end
                    end else begin
                        chan <= chan + 32'd1;
                    end
                end

                S_ADRAIN: begin
                    if (drain >= PIPE_DEPTH[31:0] + 32'd2) state <= S_DONE;
                    else drain <= drain + 32'd1;
                end

                S_DONE: begin
                    busy <= 1'b0;
                    done <= 1'b1;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end
endmodule
