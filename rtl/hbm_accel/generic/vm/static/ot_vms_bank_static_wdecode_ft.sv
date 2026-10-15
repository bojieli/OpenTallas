`timescale 1ns/1ps
`default_nettype none
// Registered-write-decode successor. Prior ot_vms_bank_static source remains frozen.
// Write onehot is captured at the existing input edge; balanced payload selection
// adds no pipeline edge. Encoded identity and all downstream SRAM stages are retained.
// No input queues, request arbitration, credits, ready or runtime rescheduling.
// Slot selectors and requests are sampled together at input edge n. Selected operations
// reach S1 at n+1, macro pins at n+2, macro edge/commit at n+3, capture at n+4,
// syndrome at n+5 and registered response at n+6. Mirror wide-write egress: n+1.
// The compiler reserves one read and one write per bank/cycle, including packet/DMA/
// COLL/ring sources and downstream egress slots. Unselected active inputs fault and
// are never deferred. An empty selected source is an idle slot. Illegal addresses
// retain historical drain behavior; illegal writes have zero masks and sticky FAULT.
// Exactly the historical three real SRAM macros, sector decode and SECDED pipeline.
module ot_vms_bank_static_wdecode_ft #(
    parameter integer RG = 2,
    parameter integer WG = 2,
    parameter integer MUT = 0 // 1: wrong read owner; 2: write-sector permutation; 3: CE population fault
) (
    input wire clk, rst_n,
    input wire [2:0] bid,
    input wire [1:0] sid,
    input wire rslot_v,
    input wire [((RG+1>1)?$clog2(RG+1):1)-1:0] rslot,
    input wire wslot_v,
    input wire [((WG+5>1)?$clog2(WG+5):1)-1:0] wslot,
    input wire [RG*17-1:0] rq,
    output wire [RG*257-1:0] rr,
    input wire [WG*281-1:0] wq,
    output reg [WG-1:0] wq_done,
    input wire [280:0] dq,
    output reg dq_done,
    input wire [280:0] kq,
    output reg kq_done,
    input wire [275:0] xq,
    output reg xq_done,
    input wire [275:0] xq2,
    output reg xq2_done,
    output wire [275:0] eg,
    input wire [284:0] pq,
    output wire [265:0] pr,
    output reg [17:0] status
);
    // Pipeline identity fields retain the closed B2 4-bit encoding.
    initial begin
        if (RG < 1 || RG > 15 || WG < 1 || WG > 10) $fatal(1, "static bank lane bounds");
    end
    // ------------------------------------------------------------------ SECDED (39,32), same code as ot_hgi_vm_core
    function automatic [6:0] colv(input integer i);
        integer a, b, c, n; reg [6:0] v;
        begin
            n = 0; v = 7'd0;
            for (a = 0; a < 7; a = a + 1) for (b = a + 1; b < 7; b = b + 1) for (c = b + 1; c < 7; c = c + 1) begin
                if (n == i) v = (7'd1 << a) | (7'd1 << b) | (7'd1 << c);
                n = n + 1;
            end
            colv = v;
        end
    endfunction
    function automatic [32*7-1:0] cols_all(input integer dummy);
        integer i; reg [32*7-1:0] r;
        begin r = '0; for (i = 0; i < 32; i = i + 1) r[i*7 +: 7] = colv(i); cols_all = r; end
    endfunction
    localparam [32*7-1:0] COLS = cols_all(0);
    function automatic [7*32-1:0] rows_all(input integer dummy);
        integer i, j; reg [7*32-1:0] r;
        begin r = '0; for (j = 0; j < 7; j = j + 1) for (i = 0; i < 32; i = i + 1) r[j*32 + i] = COLS[i*7 + j]; rows_all = r; end
    endfunction
    localparam [7*32-1:0] ROWM = rows_all(0);
    function automatic [6:0] chk(input [31:0] d);
        integer j; reg [6:0] c;
        begin for (j = 0; j < 7; j = j + 1) c[j] = ^(d & ROWM[j*32 +: 32]); chk = c; end
    endfunction
    function automatic [311:0] enc8(input [255:0] d);
        integer k; reg [311:0] r;
        begin for (k = 0; k < 8; k = k + 1) r[k*39 +: 39] = {chk(d[k*32 +: 32]), d[k*32 +: 32]}; enc8 = r; end
    endfunction

    // ------------------------------------------------------------------ sector decode
    // returns {bad, rowm 11}
    function automatic [11:0] dsec(input [15:0] s, input [2:0] b, input [1:0] q);
        reg bad;
        begin
            bad = (s[2:0] != b) || (s[15] ? (s[14:13] != 2'd0) : (s[14:13] != q));
            dsec = {bad, s[15], s[12:3]};
        end
    endfunction

    // Local reset relay (H-ELEM-A 2026-10-15): the rst_n port drives only the relay (async assert, 2-stage sync
    // release + 1 relay stage = 3 edges); every bank flop resets from rn, so no port -> 6,400-flop recovery arc
    // (gate: in->reg -54.2 ps rq_v reset recovery).  Release latency belongs to the initialization mode: the
    // compiler's first slot is >= 3 edges after the port release (not a production-calendar edge).
    (* async_reg = "true" *) reg rst_s1, rst_s2;
    reg rst_rl;  // relay flop: the only driver of the bank-wide reset net
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin rst_s1 <= 1'b0; rst_s2 <= 1'b0; rst_rl <= 1'b0; end
        else begin rst_s1 <= 1'b1; rst_s2 <= rst_s1; rst_rl <= rst_s2; end
    wire rn = rst_rl;
    // ------------------------------------------------------------------ pin flops (payload: no reset)
    reg [RG*17-1:0] rq_d; reg [WG*281-1:0] wq_d; reg [280:0] dq_d, kq_d; reg [275:0] xq_d, x2_d; reg [284:0] pq_d;
    reg [RG-1:0] rq_v; reg [WG-1:0] wq_v; reg dq_v, kq_v, xq_v, x2_v, pq_v;
    reg [2:0] bid_r; reg [1:0] sid_r;
    reg [RG*17-1:0] rq_r; reg [WG*281-1:0] wq_r;
    always @* begin
        rq_r = rq_d; for (integer g = 0; g < RG; g = g + 1) rq_r[g*17 + 16] = rq_v[g];
        wq_r = wq_d; for (integer g = 0; g < WG; g = g + 1) wq_r[g*281 + 280] = wq_v[g];
    end
    wire [280:0] dq_r = {dq_v, dq_d[279:0]}, kq_r = {kq_v, kq_d[279:0]};
    wire [275:0] xq_r = {xq_v, xq_d[274:0]}, x2_r = {x2_v, x2_d[274:0]};
    wire [284:0] pq_r = {pq_v, pq_d[283:0]};
    always @(posedge clk) begin rq_d <= rq; wq_d <= wq; dq_d <= dq; kq_d <= kq; xq_d <= xq; x2_d <= xq2; pq_d <= pq; bid_r <= bid; sid_r <= sid; end
    always @(posedge clk or negedge rn)
        if (!rn) begin rq_v <= '0; wq_v <= '0; dq_v <= 1'b0; kq_v <= 1'b0; xq_v <= 1'b0; x2_v <= 1'b0; pq_v <= 1'b0; end
        else begin
            for (integer g = 0; g < RG; g = g + 1) rq_v[g] <= rq[g*17 + 16];
            for (integer g = 0; g < WG; g = g + 1) wq_v[g] <= wq[g*281 + 280];
            dq_v <= dq[280]; kq_v <= kq[280]; xq_v <= xq[275]; x2_v <= xq2[275]; pq_v <= pq[284];
        end
    // output registers: control valid + payload
    reg eg_v; reg [274:0] eg_d; reg [RG-1:0] rr_v; reg [RG*256-1:0] rr_d; reg pr_v; reg [264:0] pr_d;
    assign eg = {eg_v, eg_d}; assign pr = {pr_v, pr_d};
    genvar gr;
    for (gr = 0; gr < RG; gr = gr + 1) begin : g_rr
        assign rr[gr*257 +: 257] = {rr_v[gr], rr_d[gr*256 +: 256]};
    end

    // Read owners 0..RG-1 = wide lanes, RG = packet.
    // Write owners 0..WG-1 = wide, WG = COLL, WG+1 = CW ring,
    // WG+2 = packet, WG+3 = CCW ring, WG+4 = DMA.
    localparam integer RB = (RG+1>1)?$clog2(RG+1):1;
    localparam integer WB = (WG+5>1)?$clog2(WG+5):1;
    reg rslot_v_d, wslot_v_d;
    reg [RB-1:0] rslot_d;
    reg [WB-1:0] wslot_d;
    // Decode in the existing request pin-capture edge. The encoded owner is
    // retained only for metadata; payload selection never decodes it again.
    reg [WG+4:0] wslot_onehot_d;
    for (genvar wo = 0; wo < WG+5; wo = wo+1) begin : g_write_slot_capture
        always @(posedge clk) wslot_onehot_d[wo] <= wslot_v && (wslot == WB'(wo));
    end
    localparam integer WLEAVES = 1 << $clog2(WG+5);
    wire [275:0] write_tree [1:2*WLEAVES-1];
    for (genvar wl=0; wl<WLEAVES; wl=wl+1) begin : g_write_leaf
        wire [275:0] source_payload;
        if (wl<WG) begin : g_wide
            assign source_payload={dsec(wq_r[wl*281+264+:16],bid_r,sid_r),wq_r[wl*281+:264]};
        end else if (wl==WG) begin : g_coll
            assign source_payload={dsec(kq_r[279:264],bid_r,sid_r),kq_r[263:0]};
        end else if (wl==WG+1) begin : g_cw
            assign source_payload={1'b0,xq_r[274:0]};
        end else if (wl==WG+2) begin : g_packet
            assign source_payload={1'b0,pq_r[282:8]};
        end else if (wl==WG+3) begin : g_ccw
            assign source_payload={1'b0,x2_r[274:0]};
        end else if (wl==WG+4) begin : g_dma
            assign source_payload={dsec(dq_r[279:264] ^ (MUT==2?16'h0008:16'h0000),bid_r,sid_r),dq_r[263:0]};
        end else begin : g_padding
            assign source_payload=276'd0;
        end
        if (wl<WG+5) assign write_tree[WLEAVES+wl]=source_payload & {276{wslot_onehot_d[wl]}};
        else assign write_tree[WLEAVES+wl]=276'd0;
    end
    for (genvar wn=1;wn<WLEAVES;wn=wn+1) begin : g_write_or
        assign write_tree[wn]=write_tree[2*wn] | write_tree[2*wn+1];
    end
    always @(posedge clk) begin rslot_d <= rslot; wslot_d <= wslot; end
    always @(posedge clk or negedge rn)
        if (!rn) begin rslot_v_d <= 1'b0; wslot_v_d <= 1'b0; end
        else begin rslot_v_d <= rslot_v; wslot_v_d <= wslot_v; end
    wire [RB-1:0] read_owner = MUT == 1 ? (rslot_d == 0 ? RB'(1) : rslot_d) : rslot_d;
    reg [RG:0] r_active;
    reg [WG+4:0] w_active;
    reg [11:0] rd_decode;
    reg [275:0] wr_decode;
    reg [7:0] wr_tag, rd_tag;
    reg selected_read, selected_write;
    reg schedule_bad, r_bad, w_bad;
    always @* begin
        r_active = '0; w_active = '0;
        rd_decode = '0; wr_decode = '0; wr_tag = pq_r[7:0]; rd_tag = pq_r[7:0];
        for (integer g = 0; g < RG; g = g + 1) r_active[g] = rq_r[g*17+16];
        for (integer g = 0; g < WG; g = g + 1) w_active[g] = wq_r[g*281+280];
        r_active[RG] = pq_r[284] && !pq_r[283];
        w_active[WG] = kq_r[280]; w_active[WG+1] = xq_r[275];
        w_active[WG+2] = pq_r[284] && pq_r[283];
        w_active[WG+3] = x2_r[275]; w_active[WG+4] = dq_r[280];
        selected_read = 1'b0; selected_write = 1'b0;
        // Decode compiler slots against constant lane indices. This is a
        // bounded mux, not arbitration: no other active source can be chosen.
        // Constant slices also avoid a runtime cast/shift unsupported by the
        // synthesis frontend and the wide variable-part-select SHARE hazard.
        if (rslot_v_d) begin
            for (integer g = 0; g < RG; g = g + 1) if (read_owner == RB'(g)) begin
                selected_read = r_active[g];
                rd_decode = dsec(rq_r[g*17 +: 16],bid_r,sid_r);
            end
            if (read_owner == RB'(RG)) begin
                selected_read = r_active[RG]; rd_decode = {1'b0,pq_r[282:272]};
            end
        end
        // Explicit balanced OR of fixed compiler-selected payload leaves.
        // Selection is independent of source activity; no priority or replay.
        wr_decode=write_tree[1];
        if (wslot_v_d) begin
            for(integer g=0;g<WG+5;g=g+1)
                selected_write=selected_write | (wslot_onehot_d[g] & w_active[g]);
        end
        r_bad = rslot_v_d && int'(rslot_d)>RG;
        w_bad = wslot_v_d && int'(wslot_d)>WG+4;
        // Fault checks observe requests; they do not select or reschedule service.
        for (integer g = 0; g <= RG; g = g + 1)
            if (r_active[g] && !(rslot_v_d && int'(rslot_d)==g)) r_bad = 1'b1;
        for (integer g = 0; g <= WG+4; g = g + 1)
            if (w_active[g] && !(wslot_v_d && int'(wslot_d)==g)) w_bad = 1'b1;
        schedule_bad = r_bad | w_bad;
    end
    // Egress valid computed per wide leaf in parallel (H-ELEM-A 2026-10-15: gate reg->reg -65.5 ps ended at eg_v
    // through the 276-b write OR tree): identical to selected_write && wslot_d < WG && mirror && !bad of the leaf.
    reg eg_c;
    always @* begin : egc
        reg [11:0] ds;
        eg_c = 1'b0;
        for (integer g = 0; g < WG; g = g + 1) begin
            ds = dsec(wq_r[g*281+264 +: 16],bid_r,sid_r);
            if (wslot_onehot_d[g] && w_active[g] && wq_r[g*281 + 279] && !ds[11]) eg_c = 1'b1;
        end
    end
    reg s1w_v; reg [3:0] s1w_p; reg [10:0] s1w_row; reg [255:0] s1w_d; reg [7:0] s1w_m; reg [7:0] s1w_tag;
    reg s1r_v; reg [3:0] s1r_p; reg [10:0] s1r_row; reg [7:0] s1r_tag;
    // Sticky diagnostic fault as a registered 2-level tree (H-ELEM-A 2026-10-15; gate reg->reg -71 ps ended at flt
    // through the full schedule-compare cone): level 1 registers each fault source group, level 2 ORs them into the
    // sticky flt.  Status visibility +2 edges; no data, valid, slot or response path changes (faults never select).
    reg flt;
    reg flt_rs, flt_ws, flt_rd, flt_wd;
    always @(posedge clk or negedge rn)
        if (!rn) begin s1w_v <= 0; s1r_v <= 0; eg_v <= 0; flt <= 0; flt_rs <= 0; flt_ws <= 0; flt_rd <= 0; flt_wd <= 0; end
        else begin
            s1w_v <= selected_write; s1r_v <= selected_read;
            eg_v <= eg_c;
            flt_rs <= r_bad; flt_ws <= w_bad;
            flt_rd <= selected_read && rd_decode[11];
            flt_wd <= selected_write && wr_decode[275];
            if (flt_rs || flt_ws || flt_rd || flt_wd) flt <= 1;
        end
    always @(posedge clk) begin
        s1w_p <= 4'(wslot_d); s1w_row <= wr_decode[274:264];
        s1w_d <= wr_decode[263:8]; s1w_m <= wr_decode[275] ? 8'd0 : wr_decode[7:0]; s1w_tag <= wr_tag;
        s1r_p <= 4'(read_owner); s1r_row <= rd_decode[10:0]; s1r_tag <= rd_tag;
        // Dedicated boundary state: invalid egress payload is unspecified.
        // A qualified capture prevents merging it into the internal S1 data.
        // Unconditional capture (H-ELEM-A 2026-10-15: gate reg->reg -81 / -228 ps ended at the eg_d enable decode):
        // eg_v alone qualifies the egress beat; the payload register carries no enable from the slot/ECC decode.
        eg_d <= wr_decode[274:0];
    end
    // ------------------------------------------------------------------ S2: macro pins
    reg [9:0] m_ra, m_wa; reg m_rA, m_rC, m_rB, m_wA, m_wB, m_wC; reg [311:0] m_wd; reg [7:0] m_mA, m_mC; reg [15:0] m_mB;
    reg s2r_v; reg [3:0] s2r_p; reg s2r_mir; reg [7:0] s2r_tag;
    reg s2w_v; reg [3:0] s2w_p; reg [7:0] s2w_tag;
    always @(posedge clk or negedge rn)
        if (!rn) begin m_rA <= 1'b0; m_rB <= 1'b0; m_rC <= 1'b0; m_wA <= 1'b0; m_wB <= 1'b0; m_wC <= 1'b0; s2r_v <= 1'b0; s2w_v <= 1'b0; end
        else begin
            m_rA <= s1r_v && !s1r_row[10]; m_rC <= s1r_v && s1r_row[10]; m_rB <= s1r_v;
            m_wA <= s1w_v && !s1w_row[10]; m_wC <= s1w_v && s1w_row[10]; m_wB <= s1w_v;
            s2r_v <= s1r_v; s2w_v <= s1w_v;
        end
    always @(posedge clk) begin
        m_ra <= s1r_row[9:0]; m_wa <= s1w_row[9:0];
        m_wd <= enc8(s1w_d);
        m_mA <= s1w_row[10] ? 8'd0 : s1w_m; m_mC <= s1w_row[10] ? s1w_m : 8'd0;
        m_mB <= s1w_row[10] ? {s1w_m, 8'd0} : {8'd0, s1w_m};
        s2r_p <= s1r_p; s2r_mir <= s1r_row[10]; s2r_tag <= s1r_tag;
        s2w_p <= s1w_p; s2w_tag <= s1w_tag;
    end
    // mask expansion is wiring only (each word-mask flop drives its 39 bit-mask pins)
    wire [255:0] mskA, mskC, mskB;
    genvar gk;
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_m
        assign mskA[gk*32 +: 32] = {32{m_mA[gk]}};
        assign mskC[gk*32 +: 32] = {32{m_mC[gk]}};
    end
    // B holds the check bits: main word k -> B[k*7 +: 7], mirror word k -> B[56 + k*7 +: 7]
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_mb
        assign mskB[gk*7 +: 7]      = {7{m_mB[gk]}};
        assign mskB[56 + gk*7 +: 7] = {7{m_mB[8 + gk]}};
    end
    assign mskB[255:112] = '0;
    // data / check split: word k = {chk 7, data 32} at m_wd[k*39 +: 39]
    wire [255:0] wdat; wire [55:0] wchk;
    for (gk = 0; gk < 8; gk = gk + 1) begin : g_sp
        assign wdat[gk*32 +: 32] = m_wd[gk*39 +: 32];
        assign wchk[gk*7 +: 7]   = m_wd[gk*39 + 32 +: 7];
    end
    wire [255:0] rdA, rdB, rdC;
    ot_sram_1r1w_1024x256_m2_r2c2 u_a (.clk(clk), .r_ce_in(m_rA), .r_addr_in(m_ra), .rd_out(rdA),
        .w_ce_in(m_wA), .w_addr_in(m_wa), .wd_in(wdat), .w_mask_in(mskA), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_1024x256_m2_r2c2 u_b (.clk(clk), .r_ce_in(m_rB), .r_addr_in(m_ra), .rd_out(rdB),
        .w_ce_in(m_wB), .w_addr_in(m_wa), .wd_in({144'd0, wchk, wchk}), .w_mask_in(mskB), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    ot_sram_1r1w_1024x256_m2_r2c2 u_c (.clk(clk), .r_ce_in(m_rC), .r_addr_in(m_ra), .rd_out(rdC),
        .w_ce_in(m_wC), .w_addr_in(m_wa), .wd_in(wdat), .w_mask_in(mskC), .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));

    // ------------------------------------------------------------------ M (macro edge) -> C (capture) -> D -> R
    reg mr_v; reg [3:0] mr_p; reg mr_mir; reg [7:0] mr_tag; reg mw_v; reg [3:0] mw_p; reg [7:0] mw_tag;
    reg c_v; reg [3:0] c_p; reg c_mir; reg [7:0] c_tag; reg [255:0] c_a, c_c; reg [111:0] c_b; reg cw_v; reg [3:0] cw_p; reg [7:0] cw_tag;
    reg d_v; reg [3:0] d_p; reg [7:0] d_tag; reg [255:0] d_dat; reg [55:0] d_syn; reg dw_v; reg [3:0] dw_p; reg [7:0] dw_tag;
    always @(posedge clk or negedge rn)
        if (!rn) begin
            mr_v <= 1'b0; mw_v <= 1'b0; c_v <= 1'b0; cw_v <= 1'b0; d_v <= 1'b0; dw_v <= 1'b0;
            wq_done <= '0; dq_done <= 1'b0; kq_done <= 1'b0; xq_done <= 1'b0; xq2_done <= 1'b0;
        end else begin
            mr_v <= s2r_v; mw_v <= s2w_v;
            // done = the write is in the macro (this edge wrote it)
            for (integer g = 0; g < WG; g = g + 1) wq_done[g] <= s2w_v && s2w_p == 4'(g);
            dq_done <= s2w_v && s2w_p == 4'(WG+4); kq_done <= s2w_v && s2w_p == 4'(WG); xq_done <= s2w_v && s2w_p == 4'(WG + 1);
            xq2_done <= s2w_v && s2w_p == 4'(WG + 3);
            c_v <= mr_v; cw_v <= mw_v && mw_p == 4'(WG + 2);
            d_v <= c_v; dw_v <= cw_v;
        end
    // capture flops: the only load of the macro outputs (no enable, no reset)
    always @(posedge clk) begin : mcd
        reg [255:0] dat; reg [55:0] ck;
        mr_p <= s2r_p; mr_mir <= s2r_mir; mr_tag <= s2r_tag; mw_p <= s2w_p; mw_tag <= s2w_tag;
        c_p <= mr_p; c_mir <= mr_mir; c_tag <= mr_tag; c_a <= rdA; c_b <= rdB[111:0]; c_c <= rdC; cw_tag <= mw_tag;
        d_p <= c_p; d_tag <= c_tag; dw_tag <= cw_tag;
        dat = c_mir ? c_c : c_a; ck = c_mir ? c_b[111:56] : c_b[55:0];
        d_dat <= dat;
        for (integer k = 0; k < 8; k = k + 1) d_syn[k*7 +: 7] <= chk(dat[k*32 +: 32]) ^ ck[k*7 +: 7];
    end
    // R: correct, count, respond. Explicit balanced CE population tree keeps
    // the same response/count edge and avoids serial eight-word accumulation.
    reg [255:0] cor; wire [3:0] nce; reg [7:0] ce_word; reg nue;
    wire [1:0] ce_pair[0:3];wire [2:0] ce_quad[0:1];
    for(genvar cp=0;cp<4;cp=cp+1)begin:g_ce_pair
        assign ce_pair[cp]={1'b0,ce_word[2*cp]}+{1'b0,ce_word[2*cp+1]};
    end
    for(genvar cq=0;cq<2;cq=cq+1)begin:g_ce_quad
        assign ce_quad[cq]={1'b0,ce_pair[2*cq]}+{1'b0,ce_pair[2*cq+1]};
    end
    assign nce={1'b0,ce_quad[0]}+{1'b0,(MUT==3?3'd0:ce_quad[1])};
    always @* begin
        cor = d_dat; ce_word = 8'd0; nue = 1'b0;
        for (integer k = 0; k < 8; k = k + 1) begin : wk
            reg [6:0] s; reg hit; s = d_syn[k*7 +: 7]; hit = 1'b0;
            if (s != 7'd0) begin
                for (integer i = 0; i < 32; i = i + 1) if (s == COLS[i*7 +: 7]) begin cor[k*32 + i] = ~cor[k*32 + i]; hit = 1'b1; end
                if (s == 7'd1 || s == 7'd2 || s == 7'd4 || s == 7'd8 || s == 7'd16 || s == 7'd32 || s == 7'd64) hit = 1'b1;
                if (hit) ce_word[k] = 1'b1; else nue = 1'b1;
            end
        end
    end
    // nce is bounded by eight codewords. Split the low-nibble add from a
    // carry-prefix increment of the upper bits; preserve exact saturation and
    // the existing response/count edge without a full16bit add+compare path.
    function automatic [15:0] sat_ce_add(input [15:0] count, input [3:0] step);
        reg [4:0] low;
        reg [11:0] upper, prefix_mask;
        begin
            low = {1'b0,count[3:0]} + {1'b0,step};
            for (integer b = 0; b < 12; b = b + 1) begin
                prefix_mask = (12'd1 << b) - 12'd1;
                upper[b] = count[b+4] ^ (low[4] && ((count[15:4] & prefix_mask) == prefix_mask));
            end
            sat_ce_add = (low[4] && (&count[15:4])) ? 16'hffff : {upper,low[3:0]};
        end
    endfunction
    reg [15:0] ce; reg ue; reg ce_v_q, ue_q; reg [3:0] ce_n_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin rr_v <= '0; pr_v <= 1'b0; ce <= 16'd0; ue <= 1'b0; status <= 18'd0; ce_v_q <= 1'b0; ce_n_q <= 4'd0; ue_q <= 1'b0; end
        else begin
            for (integer g = 0; g < RG; g = g + 1) rr_v[g] <= d_v && d_p == 4'(g);
            // a packet read (d_p == RG) and a packet write echo are never on the same edge (one packet op a cycle)
            pr_v <= (d_v && d_p == 4'(RG)) || dw_v;
            // CE/UE accounting one registered edge after the syndrome decode (H-ELEM-A 2026-10-15: gate reg->reg
            // -135 ps ended at ce through syndrome match -> population -> saturating add).  Diagnostic status only.
            ce_v_q <= d_v; ce_n_q <= nce; ue_q <= d_v && nue;
            if (ce_v_q) ce <= sat_ce_add(ce,ce_n_q);
            if (ue_q) ue <= 1'b1;
            status <= {flt, ue, ce};
        end
    always @(posedge clk) begin
        // Each face/group retains its own last valid payload. These registers
        // must not collapse to one shared256bit state across all four faces.
        for (integer g = 0; g < RG; g = g + 1)
            if (d_v && d_p == 4'(g)) rr_d[g*256 +: 256] <= cor;
        pr_d <= (d_v && d_p == 4'(RG)) ? {1'b0, d_tag, cor} : {1'b1, dw_tag, 256'd0};
    end
endmodule
`default_nettype wire
