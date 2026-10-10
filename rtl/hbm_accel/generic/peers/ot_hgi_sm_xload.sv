`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 SM x-load (hgi-adapters, 2026-10-09): the peer of ot_hgi_sm_record's x port.  Reads the activation rows of
// A (P slots, K elements each, VM FP32) through NXC hfd_hgi_vm packet clients and writes the SM x store over the
// EXISTING x-write port of every SM (xw_en / xw_addr / xw_grp / xw_data 2,048 b, broadcast to the 32 SMs), in the
// smh fragment layout (tools/dshbm_matched_sm_seq.gen_op, BF16 / INT8 front):
//   fragment address a = g x 8 + t (g < op_g = ceil(K / 512), t < 8); column p (slot) lane j (< 64) at bit
//   p x XC + LB x 266 + 16 j (XC = 3,152, LB x 266 = 2,128) holds to_bf16(x_p[k]), k = (g x 64 + j) x 8 + t (0 past K);
//   beat b (xw_grp) of address a carries fragment bits [b x 2,048 +: 2,048], b < ceil(P x XC / 2,048) (= op_xb).
// One VM sector = the 8 t values of one lane j, so a group g is 64 x P sector reads into a P x 64 x 8 BF16 tile, then
// 8 x op_xb beats.  to_bf16 = RNE (hdc_golden; the golden of SM.MATVEC fmt 0 / 3 rounds x to BF16).
// Refusals (x_fault): fmt 1 / 2 (the DS block-dot x is quant_fp8 codes + block exponents: the activation quantiser,
// not this loader), A not VM (STREAM x enters from the SU stream, not here), A.base / A.stride not 8-word aligned.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_sm_xload #(
    parameter integer NXC = 4,            // VM packet clients (reads in flight)
    parameter integer PMAX = 8,
    parameter integer MUT_T = 0           // mutant: lane j takes t from the wrong half (k = (g 64 + j) 8 + (7 - t))
) (
    input  wire               clk,
    input  wire               rst_n,
    input  wire               x_v,
    output wire               x_rdy,
    input  wire [39:0]        x_base,
    input  wire [20:0]        x_n,
    input  wire [3:0]         x_p,
    input  wire [31:0]        x_stride,
    input  wire [1:0]         x_space,
    input  wire [1:0]         x_fmt,
    output reg                x_done,
    output reg                x_fault,
    output reg                xw_en,
    output reg  [6:0]         xw_addr,
    output reg  [6:0]         xw_grp,
    output reg  [2047:0]      xw_data,
    output reg  [NXC*338-1:0] vmq,
    input  wire [NXC*274-1:0] vmr
);
    localparam integer XC = 3152, XOFF = 2128;
    reg busy; reg [17:0] base; reg [20:0] kk; reg [3:0] pp; reg [17:0] st;
    reg [7:0] gn, g; reg [3:0] p_rd; reg [6:0] j_rd; reg [9:0] outst; reg [3:0] t; reg [6:0] b; reg [6:0] nb;
    // STORAGE (register file, synthesis-friendly): 8 t-banks, each PMAX words of 1,024 b = one slot's 64 lanes x BF16;
    // a landing sector (slot p, lane j) writes the 16-b lane-j slice of word p in all 8 banks (one write port a bank),
    // one sector an edge (client responses are held until taken); emission reads ONE word of bank t a beat
    reg [1023:0] bk0 [0:PMAX-1], bk1 [0:PMAX-1], bk2 [0:PMAX-1], bk3 [0:PMAX-1],
                 bk4 [0:PMAX-1], bk5 [0:PMAX-1], bk6 [0:PMAX-1], bk7 [0:PMAX-1];
    reg [NXC-1:0] hv;                      // a client's response held, not yet landed
    reg [273:0] hdat [0:NXC-1];
    reg [10:0] got;                        // sectors landed for this group
    integer cl; reg [3:0] nland;
    reg lsel_v; integer lsel;
    always @* begin
        lsel_v = 1'b0; lsel = 0;
        for (cl = NXC - 1; cl >= 0; cl = cl - 1) if (hv[cl]) begin lsel_v = 1'b1; lsel = cl; end
        nland = {3'd0, lsel_v};
    end
    wire [10:0] got_n = got;
    reg [1:0] ph;                          // 0 read, 1 emit, 2 done
    assign x_rdy = !busy;
    reg [273:0] vr [0:NXC-1];
    integer c;
    always @(posedge clk) for (c = 0; c < NXC; c = c + 1) vr[c] <= vmr[c*274 +: 274];
    reg [NXC-1:0] cbusy;
    function automatic [15:0] bf16(input [31:0] x);
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) bf16 = x[31:16] | 16'h0040;
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; bf16 = r[31:16]; end
        end
    endfunction
    // beat b of fragment (g, t): the fragment holds slot p's lanes at [p XC + XOFF, + 1,024); slot blocks are 3,152
    // apart with a 2,128-b gap > the 2,048-b beat, so a beat overlaps AT MOST ONE slot: a static (p, offset) per b
    localparam integer NBMAX = (PMAX * XC + 2047) / 2048;
    function automatic integer bslot(input integer bb);       // the slot a beat overlaps, -1 none
        integer pp2; bslot = -1;
        for (pp2 = 0; pp2 < PMAX; pp2 = pp2 + 1)
            if (pp2 * XC + XOFF < bb * 2048 + 2048 && pp2 * XC + XOFF + 1024 > bb * 2048) bslot = pp2;
    endfunction
    wire [3:0] tt = MUT_T ? (4'd7 - t) : t;
    reg [6:0] b_q; reg [1023:0] rw;        // registered bank read (the beat's slot word)
    wire [2047:0] beat;
    wire [2047:0] beats [0:NBMAX-1];
    genvar gb;
    generate for (gb = 0; gb < NBMAX; gb = gb + 1) begin : g_beat
        localparam integer PS = bslot(gb);
        localparam integer OFF = (PS < 0) ? 0 : PS * XC + XOFF - gb * 2048;   // slot block start rel. to the beat
        if (PS < 0) begin : g_none
            assign beats[gb] = 2048'd0;
        end else if (OFF >= 0) begin : g_pos
            wire [4095:0] sh = {3072'd0, rw} << OFF;
            assign beats[gb] = sh[2047:0];
        end else begin : g_neg
            wire [1023:0] sh = rw >> (-OFF);
            assign beats[gb] = {1024'd0, sh};
        end
    end endgenerate
    assign beat = beats[b_q];
    function automatic [3:0] slot_of(input [6:0] bb);
        integer x; slot_of = 4'd0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0) slot_of = bslot(x);
    endfunction
    function automatic in_slot(input [6:0] bb, input [3:0] np);
        integer x; in_slot = 1'b0;
        for (x = 0; x < NBMAX; x = x + 1) if (bb == x && bslot(x) >= 0 && bslot(x) < np) in_slot = 1'b1;
    endfunction
    reg e_v; reg [6:0] e_addr; reg e_ok;
    integer w;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin busy <= 1'b0; x_done <= 1'b0; x_fault <= 1'b0; xw_en <= 1'b0; vmq <= 0; cbusy <= 0; ph <= 0;
                          hv <= 0; e_v <= 1'b0; end
        else begin
            x_done <= 1'b0; xw_en <= 1'b0; e_v <= 1'b0;
            // emission stage 2: the registered slot word -> the beat
            if (e_v) begin xw_en <= 1'b1; xw_addr <= e_addr; xw_grp <= b_q; xw_data <= e_ok ? beat : 2048'd0; end
            for (c = 0; c < NXC; c = c + 1) vmq[c*338 + 337] <= 1'b0;
            if (x_v && x_rdy) begin
                if (x_fmt == 2'd1 || x_fmt == 2'd2 || x_space != 2'd1 || |x_base[2:0] || |x_stride[2:0] || x_p > PMAX ||
                    x_p == 4'd0) x_fault <= 1'b1;
                else begin
                    busy <= 1'b1; base <= x_base[17:0]; kk <= x_n; pp <= x_p; st <= x_stride[17:0];
                    gn <= ((x_n - 21'd1) >> 9) + 8'd1; g <= 8'd0; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0; ph <= 2'd0;
                    nb <= ({12'd0, x_p} * 16'd3152 + 16'd2047) >> 11;    // 16 b: P x XC reaches 25,216
                end
            end
            if (busy && ph == 2'd0) begin
                // issue: one sector read a cycle on the lowest free client; lanes j, then columns p
                begin : iss
                    reg found; integer cf; reg [31:0] wd;
                    found = 1'b0; cf = 0;
                    for (c = NXC - 1; c >= 0; c = c - 1) if (!cbusy[c]) begin found = 1'b1; cf = c; end
                    wd = {14'd0, base} + p_rd * {14'd0, st} + {g, 9'd0} + {j_rd, 3'd0};
                    if (found && p_rd < pp) begin
                        vmq[cf*338 +: 338] <= {1'b1, 1'b0, wd[29:3], 5'd0, 256'd0, 32'd0, {5'd0, p_rd, j_rd}};
                        cbusy[cf] <= 1'b1;
                        if (j_rd == 7'd63) begin j_rd <= 7'd0; p_rd <= p_rd + 4'd1; end else j_rd <= j_rd + 7'd1;
                    end
                end
                for (c = 0; c < NXC; c = c + 1)                                  // hold every arriving response
                    if (cbusy[c] && !hv[c] && vr[c][273] && !vr[c][256]) begin hv[c] <= 1'b1; hdat[c] <= vr[c]; end
                if (lsel_v) begin : land                                        // land one held sector an edge
                    reg [3:0] lp; reg [6:0] lj; reg [15:0] v [0:7];
                    lp = hdat[lsel][267:264]; lj = hdat[lsel][263:257];      // tag [272:257] = {p 4, j 7} low bits
                    for (w = 0; w < 8; w = w + 1)
                        v[w] = (({13'd0, g, 9'd0} + {lj, 3'd0} + w) < kk) ? bf16(hdat[lsel][32*w +: 32]) : 16'd0;
                    bk0[lp][16*lj +: 16] <= v[0]; bk1[lp][16*lj +: 16] <= v[1]; bk2[lp][16*lj +: 16] <= v[2];
                    bk3[lp][16*lj +: 16] <= v[3]; bk4[lp][16*lj +: 16] <= v[4]; bk5[lp][16*lj +: 16] <= v[5];
                    bk6[lp][16*lj +: 16] <= v[6]; bk7[lp][16*lj +: 16] <= v[7];
                    hv[lsel] <= 1'b0; cbusy[lsel] <= 1'b0;
                end
                if (got_n == {pp, 6'd0}) begin ph <= 2'd1; t <= 4'd0; b <= 7'd0; end
            end
            if (busy && ph == 2'd0) got <= got + {7'd0, nland};
            if (busy && ph == 2'd1) begin                                     // emission stage 1: read bank t
                begin : rd
                    reg [3:0] sp; sp = slot_of(b);
                    case (tt[2:0])
                        3'd0: rw <= bk0[sp]; 3'd1: rw <= bk1[sp]; 3'd2: rw <= bk2[sp]; 3'd3: rw <= bk3[sp];
                        3'd4: rw <= bk4[sp]; 3'd5: rw <= bk5[sp]; 3'd6: rw <= bk6[sp]; default: rw <= bk7[sp];
                    endcase
                end
                e_v <= 1'b1; e_addr <= {g[3:0], t[2:0]}; b_q <= b; e_ok <= in_slot(b, pp);
                if (b == nb - 7'd1) begin
                    b <= 7'd0;
                    if (t == 4'd7) begin
                        if (g == gn - 8'd1) begin ph <= 2'd2; end
                        else begin g <= g + 8'd1; p_rd <= 4'd0; j_rd <= 7'd0; got <= 11'd0; ph <= 2'd0; end
                    end
                    t <= t + 4'd1;
                end else b <= b + 7'd1;
            end
            if (busy && ph == 2'd2 && !e_v) begin busy <= 1'b0; x_done <= 1'b1; ph <= 2'd0; end   // last beat out
        end
    end
endmodule
`default_nettype wire
