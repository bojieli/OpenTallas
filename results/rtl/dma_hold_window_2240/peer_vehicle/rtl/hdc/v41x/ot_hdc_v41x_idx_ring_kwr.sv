`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// ot_hdc_v41x_idx_ring_kwr -- index-key WRITER for the quarter-per-stack ring
// layout (W11; geometry in ot_hdc_v41x_idx_ring_ranges).
//
// Takes encoded 68-B keys ({scales[31:0], codes[511:0]}, the output of the
// FP8 -> E2M1 encoder of ot_hdc_v41x_idx_pool_kwr) and places them:
//   op 0, STEP:  a decode step appends the key of position n (the user's count
//                before the step) and the count becomes n + 1.  The new key
//                always belongs to quarter 3 (stack 3).  When n + 1 is a
//                multiple of 32 the quarter boundaries move (Qs grows by 8):
//                positions [q Qs, q Qs + 8 q) join stack q - 1, q = 1..3 --
//                48 keys, six 8-key groups -- from their old quarter's stack
//                (stack q once Qs >= 8 q; stack 3 or q + 1 while Qs < 24).  A key keeps its ring
//                slot (p mod C) on every stack, so a group is copied SECTOR FOR
//                SECTOR to the same addresses one stack down: one scale sector
//                and sixteen code sectors, 17 reads + 17 writes per group.
//   op 1, PLACE: a prefill places position `pos` of a count-n scan directly
//                on its quarter's stack (no migration).
// A key is three one-sector writes: its two code sectors and its 4-byte scale
// slot (byte strobes) in the shared scale sector.  The user's region starts at
// block cfg_key_base_block + user x UBLK on every stack.
//
// HBM side: the per-pseudo-channel ports of the four stacks' controllers
// (ot_hdc_v41x_idx_hbm: valid/ready requests, one-sector writes with strobes,
// reads returned per channel); one request per cycle, sector -> channel by
// the controller's address map.  A new command is taken as soon as the last
// one's requests are issued (a migration read of a sector written earlier is
// ordered behind that write by the controller: same sector, same channel
// queue, never reordered past a write); `busy` stays high until every write
// has completed (wr_done), so a following scan sees the data.  Storage: one 17 x
// 256-bit group buffer.  Faults: a position outside the ring's valid range.
// ---------------------------------------------------------------------------
module ot_hdc_v41x_idx_ring_kwr #(
    parameter integer NPC=32, AW=30, HW=23, TAGW=16, LENW=4, BEATW=4, DW=256,
    parameter integer UW=10, RSB=64, RTAIL=32
) (
    input  wire              clk, rst_n,
    input  wire [HW-1:0]     cfg_key_base_block,
    input  wire              c_v,
    output wire              c_rdy,
    input  wire              c_op,           // 0 step (append + migrate), 1 place
    input  wire [UW-1:0]     c_user,
    input  wire [HW+9:0]     c_n,
    input  wire [HW+9:0]     c_pos,
    input  wire [543:0]      c_key,
    output wire              busy,
    output reg               fault,
    output wire [4*NPC-1:0]        h_req_v,
    input  wire [4*NPC-1:0]        h_req_rdy,
    output wire [4*NPC*AW-1:0]     h_req_addr,
    output wire [4*NPC*LENW-1:0]   h_req_len,
    output wire [4*NPC*TAGW-1:0]   h_req_tag,
    output wire [4*NPC-1:0]        h_req_we,
    output wire [4*NPC*DW-1:0]     h_req_wdata,
    output wire [4*NPC*(DW/8)-1:0] h_req_wstrb,
    input  wire [4*NPC-1:0]        h_wr_done,
    input  wire [4*NPC-1:0]        h_rsp_v,
    output wire [4*NPC-1:0]        h_rsp_rdy,
    input  wire [4*NPC*TAGW-1:0]   h_rsp_tag,
    input  wire [4*NPC*DW-1:0]     h_rsp_data,
    output reg  [47:0]       cnt_keys,
    output reg  [47:0]       cnt_migrations,
    output reg  [47:0]       cnt_copied_sectors
);
    localparam integer C = RSB*1024 + RTAIL;
    localparam integer UBLK = RSB*17 + ((RTAIL != 0) ? 1 + (RTAIL + 63) / 64 : 0);
    localparam integer NW = HW + 10;
    localparam integer LPC = $clog2(NPC);
    initial if (AW != HW + 7 || NPC != 32 || RTAIL % 16 != 0)
        $fatal(1, "ot_hdc_v41x_idx_ring_kwr: AW = HW + 7, NPC = 32, RTAIL multiple of 16");

    function automatic [LPC-1:0] pc_of(input [AW-1:0] s);
        pc_of = LPC'((s >> 2) ^ (s >> (2 + LPC)) ^ (s >> (2 + 2 * LPC)));
    endfunction
    function automatic [NW-1:0] modc(input [NW+1:0] x);
        reg [NW+1:0] y;
        begin
            y = x;
            if (y >= (NW+2)'(C)) y = y - (NW+2)'(C);
            if (y >= (NW+2)'(C)) y = y - (NW+2)'(C);
            if (y >= (NW+2)'(C)) y = y - (NW+2)'(C);
            modc = y[NW-1:0];
        end
    endfunction
    // sectors of ring slot t in the region starting at block ub
    function automatic [AW-1:0] scale_sec(input [HW-1:0] ub, input [NW-1:0] t);
        scale_sec = {ub + HW'(17) * HW'(t >> 10), 7'd0} + AW'(t[9:3]);
    endfunction
    function automatic [AW-1:0] code_sec(input [HW-1:0] ub, input [NW-1:0] t);
        code_sec = {ub + HW'(17) * HW'(t >> 10) + HW'(1) + HW'(t[9:6]), 7'd0} + AW'({t[5:0], 1'b0});
    endfunction

    // ---- command state --------------------------------------------------------------
    localparam [2:0] S_IDLE=0, S_KEY=1, S_MRD=2, S_MWAIT=3, S_MWR=4;
    reg [2:0]      st;
    reg [HW-1:0]   ub;
    reg [543:0]    key;
    reg [1:0]      kstack;
    reg [NW-1:0]   kslot;
    reg [1:0]      kidx;          // 0, 1 code sectors; 2 scale
    reg            mig;
    reg [NW-1:0]   qs_old;
    reg [1:0]      mq, mg;        // migration: source stack q, group g < q
    reg [4:0]      mi, mgot;      // sector index 0..16, responses collected
    reg [17*DW-1:0] gbuf;         // the group being copied: 17 sectors
    reg [15:0]     outst;         // writes issued, not yet done

    // group g of the keys stack q - 1 gains: positions p0 .. p0 + 7, p0 = q Qs + 8 g;
    // their old owner is their quarter under the old Qs (stack q once Qs >= 8 q;
    // stack 3 or q + 1 in the first migrations, when quarters are shorter)
    wire [NW-1:0] m_p0 = NW'(mq) * qs_old + NW'({mg, 3'b000});
    wire [1:0]    m_src = (m_p0 < qs_old) ? 2'd0 : (m_p0 < 2 * qs_old) ? 2'd1 : (m_p0 < 3 * qs_old) ? 2'd2 : 2'd3;
    wire [NW-1:0] m_slot = modc((NW+2)'(m_p0));
    wire [AW-1:0] m_sec = (mi == 0) ? scale_sec(ub, m_slot) : code_sec(ub, m_slot) + AW'(mi - 1);

    // ---- one registered request ----------------------------------------------------
    reg            rq_v, rq_we;
    reg [1:0]      rq_st;
    reg [AW-1:0]   rq_addr;
    reg [DW-1:0]   rq_data;
    reg [DW/8-1:0] rq_strb;
    reg [TAGW-1:0] rq_tag;
    wire [LPC-1:0] rq_pc = pc_of(rq_addr);
    wire [$clog2(4*NPC)-1:0] rq_port = {rq_st, rq_pc};
    wire           rq_take = rq_v && h_req_rdy[rq_port];
    genvar gp;
    generate for (gp = 0; gp < 4*NPC; gp = gp + 1) begin : g_port
        assign h_req_v[gp] = rq_v && (rq_port == gp);
        assign h_req_addr[gp*AW +: AW] = rq_addr;
        assign h_req_len[gp*LENW +: LENW] = LENW'(1);
        assign h_req_tag[gp*TAGW +: TAGW] = rq_tag;
        assign h_req_we[gp] = rq_we;
        assign h_req_wdata[gp*DW +: DW] = rq_data;
        assign h_req_wstrb[gp*(DW/8) +: DW/8] = rq_strb;
        assign h_rsp_rdy[gp] = 1'b1;
    end endgenerate
    // the request slot is free for a new request this edge
    wire rq_free = !rq_v || rq_take;

    integer i, ndone;
    assign c_rdy = (st == S_IDLE) && !rq_v;
    assign busy = (st != S_IDLE) || rq_v || outst != 0 || ndone != 0;

    // command decode (combinational, taken on c_v && c_rdy)
    wire [NW-1:0] c_count = c_op ? c_n : c_n + 1'b1;
    wire [NW-1:0] c_p     = c_op ? c_pos : c_n;
    wire [NW-1:0] c_qs    = (c_count >> 5) << 3;
    wire [1:0]    c_stack = (c_p < c_qs) ? 2'd0 : (c_p < 2 * c_qs) ? 2'd1 : (c_p < 3 * c_qs) ? 2'd2 : 2'd3;
    wire          c_bad   = (c_qs > NW'(C)) || (c_count - 3 * c_qs > NW'(C)) || (c_p >= c_count);

    always @* begin
        ndone = 0;
        for (i = 0; i < 4*NPC; i = i + 1) ndone = ndone + (h_wr_done[i] ? 1 : 0);
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; rq_v <= 1'b0; fault <= 1'b0; outst <= 0; mgot <= 0;
            cnt_keys <= 0; cnt_migrations <= 0; cnt_copied_sectors <= 0;
        end else begin
            outst <= outst + ((rq_take && rq_we) ? 16'd1 : 16'd0) - 16'(ndone);
            if (rq_take) rq_v <= 1'b0;
            // migration read data
            for (i = 0; i < 4*NPC; i = i + 1)
                if (h_rsp_v[i]) gbuf[h_rsp_tag[i*TAGW +: 5]*DW +: DW] <= h_rsp_data[i*DW +: DW];
            if (st == S_MRD || st == S_MWAIT) mgot <= mgot + 5'($countones(h_rsp_v));
            case (st)
            S_IDLE: if (c_v && c_rdy) begin
                if (c_bad) fault <= 1'b1;
                else begin
                    ub <= cfg_key_base_block + HW'(c_user) * HW'(UBLK);
                    key <= c_key;
                    kstack <= c_stack;
                    kslot <= modc((NW+2)'(c_p));
                    kidx <= 0;
                    mig <= !c_op && c_count[4:0] == 0 && c_count >= 32;
                    qs_old <= c_qs - 8;
                    st <= S_KEY;
                end
            end
            S_KEY: if (rq_free) begin
                rq_v <= 1'b1; rq_we <= 1'b1; rq_st <= kstack; rq_tag <= 0;
                case (kidx)
                0: begin rq_addr <= code_sec(ub, kslot);      rq_data <= key[255:0];   rq_strb <= '1; end
                1: begin rq_addr <= code_sec(ub, kslot) + 1;  rq_data <= key[511:256]; rq_strb <= '1; end
                default: begin
                    rq_addr <= scale_sec(ub, kslot);
                    rq_data <= DW'(key[543:512]) << (32 * kslot[2:0]);
                    rq_strb <= (DW/8)'(4'hf) << (4 * kslot[2:0]);
                end
                endcase
                kidx <= kidx + 1'b1;
                if (kidx == 2) begin
                    cnt_keys <= cnt_keys + 1;
                    if (mig) begin
                        st <= S_MRD; mq <= 1; mg <= 0; mi <= 0;
                        cnt_migrations <= cnt_migrations + 1;
                    end else st <= S_IDLE;
                end
            end
            S_MRD: if (rq_free) begin
                rq_v <= 1'b1; rq_we <= 1'b0; rq_st <= m_src; rq_addr <= m_sec; rq_tag <= TAGW'(mi);
                rq_strb <= '0;
                if (mi == 16) begin st <= S_MWAIT; mi <= 0; end
                else mi <= mi + 1'b1;
            end
            S_MWAIT: if (mgot == 17) begin st <= S_MWR; mgot <= 0; end
            S_MWR: if (rq_free) begin
                rq_v <= 1'b1; rq_we <= 1'b1; rq_st <= mq - 1'b1; rq_addr <= m_sec; rq_tag <= 0;
                rq_data <= gbuf[mi*DW +: DW]; rq_strb <= '1;
                cnt_copied_sectors <= cnt_copied_sectors + 1;
                if (mi == 16) begin
                    mi <= 0;
                    if (mg + 1'b1 == mq) begin
                        mg <= 0;
                        if (mq == 3) st <= S_IDLE;
                        else begin mq <= mq + 1'b1; st <= S_MRD; end
                    end else begin mg <= mg + 1'b1; st <= S_MRD; end
                end else mi <= mi + 1'b1;
            end
            default: st <= S_IDLE;
            endcase
        end
    end
endmodule
