`timescale 1ns/1ps
// DS ROM (DeepSeek-V4.1) packed WINDOW KV load at full stack bandwidth -- HBM path audit 2026-10-04.
// Default-off (ENABLE=0 ties every output to zero); nothing pinned instantiates it.
//
// The as-built WINDOW refill (ot_chip_v41x_window_kv_prefetch[_owner_safe]) fetches one 544-B row per
// prefetch command, one 32-B sector per request, with REFILL_CREDITS (1 default, 8 opt-in) reads in flight
// inside that row, and publishes the scale sector only after the 16 code sectors: every row pays at least
// one HBM round trip (two with credits), so 128 rows cost 128-2,176 serial round trips.
// This loader reads the same bytes of the same region layout (slot s, sector k at base + s*17 + k; 16 code
// sectors then the scale sector whose low 16 B are E8M0 scales) as one contiguous sector range:
//   * 4-sector (128-B) requests, the HBM map's pseudo-channel granule, IW of them a cycle on IW distinct
//     pseudo-channels (an aligned group of 8 granules spans 8 distinct PCs in the stack's XOR map);
//   * every pseudo-channel port of the stack in parallel, tags = granule index, so the whole window is in
//     flight up to the controller queues (no per-row barrier, no credit loop);
//   * responses land by sector index into the same 128 x 4224-b staging rows (stage[slot][256*k] for
//     k < 16, stage[slot][4096 +: 128] for k = 16); a row is published when its 17 sectors have landed,
//     with the as-built poison checks (FP8 code 0x7f/0xff, E8M0 scale 0xff) -> fault.
// Exactness: bytes are moved, never transformed; the bench compares every staged row with the backing
// array and with the as-built prefetch's staged rows.
module ot_dsrom_window_stream_la #(
    parameter integer ENABLE = 0,
    parameter integer NPC    = 32,
    parameter integer AW     = 24,
    parameter integer TAGW   = 16,
    parameter integer LENW   = 5,
    parameter integer BEATW  = 4,
    parameter integer SLOTS  = 128,
    parameter integer IW     = 8          // granules issued per cycle (peak stack rate at 1.2 GHz is 6.5)
) (
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  start,              // pulse: load SLOTS rows from base
    input  wire [AW-1:0]         base,               // must be a multiple of 32 sectors
    output wire                  busy,
    output wire                  done,               // all rows published (level until next start)
    output wire [SLOTS-1:0]      row_valid,
    output reg                   fault,
    output wire [NPC-1:0]        req_v,
    input  wire [NPC-1:0]        req_rdy,
    output wire [NPC*AW-1:0]     req_addr,
    output wire [NPC*LENW-1:0]   req_len,
    output wire [NPC*TAGW-1:0]   req_tag,
    output wire [NPC-1:0]        req_we,
    output wire [NPC*256-1:0]    req_wdata,
    output wire [NPC*32-1:0]     req_wstrb,
    input  wire [NPC-1:0]        rsp_v,
    output wire [NPC-1:0]        rsp_rdy,
    input  wire [NPC*TAGW-1:0]   rsp_tag,
    input  wire [NPC*BEATW-1:0]  rsp_beat,
    input  wire [NPC*256-1:0]    rsp_data,
    input  wire [6:0]            rd_slot,
    output wire [4223:0]         rd_row
);
    localparam integer PITCH = 17;
    localparam integer NSECT = SLOTS * PITCH;            // 2,176
    localparam integer NGRAN = NSECT / 4;                // 544
    localparam integer LPC = $clog2(NPC);
    assign req_we = '0; assign req_wdata = '0; assign req_wstrb = '0;
    generate if (!ENABLE) begin : g_off
        assign busy = 0; assign done = 0; assign row_valid = 0; assign req_v = 0; assign req_addr = 0;
        assign req_len = 0; assign req_tag = 0; assign rsp_rdy = 0; assign rd_row = 0;
        always @(posedge clk) fault <= 1'b0;
    end else begin : g_on
        initial if (NSECT % 4 != 0 || NPC % IW != 0) $fatal(1, "window stream geometry");
        function automatic integer pc_of(input [AW-1:0] s);
            pc_of = (((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC))) & (NPC - 1));
        endfunction
        function automatic poison_codes(input [255:0] c);
            poison_codes = 1'b0;
            for (integer z = 0; z < 32; z = z + 1) if (c[8*z +: 7] == 7'h7f) poison_codes = 1'b1;
        endfunction
        function automatic poison_scales(input [127:0] s);
            poison_scales = 1'b0;
            for (integer z = 0; z < 16; z = z + 1) if (s[8*z +: 8] == 8'hff) poison_scales = 1'b1;
        endfunction
        reg [AW-1:0] b;
        reg [15:0] gnext;                                // next granule to issue (multiple of IW)
        reg run;
        reg [4:0] cnt [0:SLOTS-1];
        reg [SLOTS-1:0] valid;
        reg [4223:0] stage [0:SLOTS-1];
        reg [15:0] landed;
        // ---- issue: the next aligned group of IW granules, all-or-nothing on their PCs' ready ----
        reg [NPC-1:0] v_c; reg [NPC*AW-1:0] a_c; reg [NPC*TAGW-1:0] t_c; reg [NPC*LENW-1:0] l_c;
        reg grp_ok;
        always @* begin
            v_c = 0; a_c = 0; t_c = 0; l_c = 0; grp_ok = run && gnext < NGRAN;
            for (integer i = 0; i < IW; i = i + 1) begin
                automatic reg [AW-1:0] s = b + AW'((gnext + i) * 4);
                automatic integer p = pc_of(s);
                if (!req_rdy[p] || v_c[p]) grp_ok = 0;
                v_c[p] = 1'b1;
                a_c[p*AW +: AW] = s; t_c[p*TAGW +: TAGW] = TAGW'(gnext + i); l_c[p*LENW +: LENW] = LENW'(4);
            end
            if (!grp_ok) v_c = 0;
        end
        assign req_v = v_c; assign req_addr = a_c; assign req_tag = t_c; assign req_len = l_c;
        assign rsp_rdy = {NPC{1'b1}};
        assign busy = run; assign done = !run && &valid; assign row_valid = valid;
        assign rd_row = stage[rd_slot];
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) begin
                run <= 0; gnext <= 0; valid <= 0; fault <= 0; landed <= 0; b <= 0;
                for (integer r = 0; r < SLOTS; r = r + 1) cnt[r] <= 0;
            end else begin
                if (start && !run) begin
                    run <= 1; gnext <= 0; valid <= 0; landed <= 0; b <= base;
                    if (base[4:0] != 0) fault <= 1'b1;
                    for (integer r = 0; r < SLOTS; r = r + 1) cnt[r] <= 0;
                end else if (run) begin
                    automatic reg [15:0] nl = landed;
                    if (grp_ok) gnext <= gnext + 16'(IW);
                    for (integer p = 0; p < NPC; p = p + 1) if (rsp_v[p]) begin
                        automatic integer sec = int'(rsp_tag[p*TAGW +: TAGW]) * 4 + int'(rsp_beat[p*BEATW +: BEATW]);
                        automatic integer sl = sec / PITCH;
                        automatic integer k = sec % PITCH;
                        automatic reg [255:0] d = rsp_data[p*256 +: 256];
                        if (sec >= NSECT || pc_of(b + AW'(sec)) != p) fault <= 1'b1;
                        else begin
                            if (k < 16) begin
                                if (poison_codes(d)) fault <= 1'b1;
                                stage[sl][256*k +: 256] <= d;
                            end else begin
                                if (poison_scales(d[127:0])) fault <= 1'b1;
                                stage[sl][4096 +: 128] <= d[127:0];
                            end
                            nl = nl + 1;
                        end
                    end
                    // per-row completion (a row's 17 sectors can land on up to 5 PCs in one cycle)
                    for (integer r = 0; r < SLOTS; r = r + 1) begin
                        automatic integer add = 0;
                        for (integer p = 0; p < NPC; p = p + 1) if (rsp_v[p]) begin
                            automatic integer sec = int'(rsp_tag[p*TAGW +: TAGW]) * 4 + int'(rsp_beat[p*BEATW +: BEATW]);
                            if (sec < NSECT && sec / PITCH == r) add = add + 1;
                        end
                        if (add != 0) begin
                            cnt[r] <= cnt[r] + 5'(add);
                            if (int'(cnt[r]) + add == PITCH) valid[r] <= 1'b1;
                            if (int'(cnt[r]) + add > PITCH) fault <= 1'b1;
                        end
                    end
                    landed <= nl;
                    if (int'(nl) == NSECT) run <= 0;
                end
            end
        end
    end endgenerate
endmodule
