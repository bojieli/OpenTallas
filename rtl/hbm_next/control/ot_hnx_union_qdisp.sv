`timescale 1ns/1ps
`default_nettype none
// HBM-NEXT LH-P3UNITS/UNIONTILE 10-19: PER-QUADRANT factored ordered-cardinality union dispatcher (one copy per
// quadrant, beside its kernel store).  Same prefix + launch contract as the central ot_hnx_union_prefix (UNIONVAR
// c913ec2b5: loop 1 slot i at S + B1 + P1[i], loop 2 slot i at S + B1 + T1 + G + P2[i], tail at S + B1 + T1 + G + T2,
// kref = KB[loop] + c - 1), but fed by the landed head stream (ot_hnx_union_tap word, LQ edges after the head) and
// started at the COMPILED union-done edge instead of the forwarded union_v:
//   ARM     the stream's go (descriptor s_off = compiled done edge - go edge) loads cnt = s_off - LQ - 1; the edge that
//           sees cnt == 0 is S, the edge the central copy samples union_v on.  cfg LQ (addr 37) = stream latency of
//           this quadrant (relay stations + landing + the tile pin register).
//   PREFIX  E1/E2 exactly as the central copy (registered one-hot D1/D2[c] select, exclusive accumulators, one
//           masked metadata write per expert into the 1R1W SRAM macro); the D-sector word closes the table (rdy).
//   START   dispatch starts at max(S, first metadata word written): when the slot-0 c_u word has not landed by S
//           (short IDX records / far quadrants), the whole calendar of this record moves by the same static amount
//           (h = max(0, tap0 + LQ + 3 - S), a compile-time function of the IDX timeline and LQ; 0 for production
//           shapes, whose c stream lands ~100 edges early) instead of faulting.
//   DISPATCH READ -> CAP -> FORM -> WAIT per event.  A slot is read only once its metadata is written (di < ucnt) and
//           loop 2 / the loop-1 end only once the table is closed (rdy); until then the FSM holds its state, the
//           launch EDGE stays the compiled one, and an event whose data arrived too late FAULTS (evt < age) -- never
//           stalls a launch, no ready/credit on any interface.
//   VERIFY  the forwarded union_v must arrive exactly LQ + 1 edges after S with union_count == U and the table
//           closed, else FAULT.  A forwarded union_fault while armed / dispatching / verifying ABORTS (abort pulse:
//           at most LQ + 1 edges of speculative launches, the step is discarded as on any IDX fault).
// Writes (tap phase, write port) and reads (dispatch phase, read port) may now overlap in time on DIFFERENT
// addresses of the 1R1W macro (a slot is read only after its write edge).
// MUT (bench mutants): 1 neighbouring-cardinality kernel, 2 inclusive prefix, 3 U-only N-row kernel (as the central
//   copy); 4 = no origin prediction: dispatch starts at the forwarded union_v (the central latency at the quadrant).
module ot_hnx_union_qdisp #(
    parameter integer MUT = 0
)(
    input  wire          clk,
    input  wire          rst_n,
    // configuration (idle only): 0..15 D1[c], 16..31 D2[c], 32 B1, 33 G, 34 KB1, 35 KB2, 36 KBT, 37 LQ
    input  wire          cfg_we,
    input  wire [5:0]    cfg_addr,
    input  wire [31:0]   cfg_data,
    input  wire [49:0]   s,               // landed head stream word (already pin-registered by the tile)
    output reg           busy,
    output reg           fault,
    output reg           abort,
    output reg           done,
    output reg           launch_v,
    output reg  [1:0]    launch_loop,
    output reg  [6:0]    launch_slot,
    output reg  [4:0]    launch_c,
    output reg  [11:0]   launch_kref
);
    wire        s_go = s[0];  wire [4:0] s_n = s[5:1]; wire [15:0] s_off = s[21:6];
    wire        s_tv = s[22]; wire s_td = s[23]; wire [6:0] s_slot = s[30:24]; wire [4:0] s_c = s[35:31];
    wire        s_m = s[36];  wire s_cbad = s[37]; wire s_uv = s[38]; wire [9:0] s_uc = s[48:39]; wire s_uf = s[49];
    // ---------------------------------------------------------------- configuration
    reg [23:0] d1 [0:15];
    reg [23:0] d2 [0:15];
    reg [31:0] b1_q, g_q;
    reg [11:0] kb1_q, kb2_q, kbt_q;
    reg [7:0]  lq_q;
    reg cfg_bad, armed, vpend, opend;
    always @(posedge clk) if (cfg_we && !busy && !armed) begin
        if (cfg_addr < 6'd16) d1[cfg_addr[3:0]] <= cfg_data[23:0];
        else if (cfg_addr < 6'd32) d2[cfg_addr[3:0]] <= cfg_data[23:0];
        else case (cfg_addr)
            6'd32: b1_q <= cfg_data;
            6'd33: g_q <= cfg_data;
            6'd34: kb1_q <= cfg_data[11:0];
            6'd35: kb2_q <= cfg_data[11:0];
            6'd36: kbt_q <= cfg_data[11:0];
            6'd37: lq_q <= cfg_data[7:0];
            default: ;
        endcase
    end
    always @(posedge clk or negedge rst_n)
        if (!rst_n) cfg_bad <= 1'b0;
        else if (cfg_we && !busy && !armed)
            cfg_bad <= cfg_bad | ((cfg_addr < 6'd33) && cfg_data < 32'd4) | (cfg_addr < 6'd32 && cfg_data[31:24] != 8'd0)
                     | (cfg_addr == 6'd37 && (cfg_data[7:0] == 8'd0 || cfg_data[31:8] != 24'd0));
    // ---------------------------------------------------------------- prefix pipeline (E1, E2)
    reg [4:0] n_q;
    reg [6:0] nslot, ucnt;
    reg e1_v; reg [6:0] e1_slot; reg [4:0] e1_c; reg [23:0] e1_d1, e1_d2;
    reg [31:0] acc1, acc2;
    reg rdy_p0, rdy_p1, rdy;
    reg tfault;
    reg [15:0] oh;
    reg [23:0] sel1, sel2;
    integer q;
    wire [4:0] cmut = (MUT == 1 && s_c > 5'd1) ? s_c - 5'd1 : (MUT == 3) ? n_q : s_c;
    wire [4:0] cidx = cmut - 5'd1;
    always @* begin
        oh = 16'd0; oh[cidx[3:0]] = 1'b1;
        sel1 = 24'd0; sel2 = 24'd0;
        for (q = 0; q < 16; q = q + 1) begin
            sel1 = sel1 | (oh[q] ? d1[q] : 24'd0);
            sel2 = sel2 | (oh[q] ? d2[q] : 24'd0);
        end
    end
    // ---------------------------------------------------------------- metadata SRAM (1R1W)
    reg         m_we; reg [9:0] m_waddr; reg [255:0] m_wd;
    reg         m_re; reg [9:0] m_raddr;
    wire [255:0] m_rd;
    hnx_sram_1r1w_1024x256_r43 u_meta (
        .clk(clk), .r_ce_in(m_re), .r_addr_in(m_raddr), .rd_out(m_rd),
        .w_ce_in(m_we), .w_addr_in(m_waddr), .wd_in(m_wd), .w_mask_in({{187{1'b0}}, {69{1'b1}}}),
        .rr_en(2'b00), .rr_addr(18'd0), .cr_en(2'b00), .cr_sel(16'd0));
    reg [68:0] cap;
    always @(posedge clk) cap <= m_rd[68:0];      // capture rung beside the macro (its only load)
    // ---------------------------------------------------------------- dispatch state
    localparam [2:0] D_IDLE = 0, D_READ = 1, D_CAP = 2, D_FORM = 3, D_WAIT = 4, D_TAIL = 5, D_NEXT = 6;
    reg [2:0] dst;
    reg [1:0] loop_q;
    reg [6:0] di, u_q;
    reg [31:0] age, base2, t2_q, evt;
    reg [15:0] cnt;
    reg [8:0] vage;
    reg [4:0] ev_c;
    wire s_hit  = armed && cnt == 16'd0;                     // the compiled union-done edge S
    wire origin = (MUT == 4) ? s_uv : (s_hit || opend);
    wire dready = ucnt != 7'd0 || rdy;                         // slot-0 metadata written (or table closed)
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            e1_v <= 1'b0; m_we <= 1'b0; m_re <= 1'b0; rdy <= 1'b0; rdy_p0 <= 1'b0; rdy_p1 <= 1'b0; tfault <= 1'b0;
            nslot <= 7'd0; ucnt <= 7'd0; acc1 <= 32'd0; acc2 <= 32'd0; busy <= 1'b0; fault <= 1'b0; abort <= 1'b0;
            done <= 1'b0; launch_v <= 1'b0; dst <= D_IDLE; age <= 32'd0; armed <= 1'b0; vpend <= 1'b0; opend <= 1'b0;
            cnt <= 16'd0; vage <= 9'd0;
        end else begin
            fault <= 1'b0; abort <= 1'b0; done <= 1'b0; launch_v <= 1'b0; m_we <= 1'b0; m_re <= 1'b0;
            if (busy) age <= age + 32'd1;
            if (armed) cnt <= cnt - 16'd1;
            if (vpend) vage <= vage + 9'd1;
            // -------- descriptor (stream go): reset the prefix, arm the compiled origin
            if (s_go) begin
                if (busy || armed || opend) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end
                opend <= 1'b0;
                rdy <= 1'b0; tfault <= 1'b0; nslot <= 7'd0; ucnt <= 7'd0; acc1 <= 32'd0; acc2 <= 32'd0; n_q <= s_n;
                if ({16'd0, s_off} < {24'd0, lq_q} + 32'd2) begin armed <= 1'b0; fault <= 1'b1; end
                else begin armed <= (MUT != 4); cnt <= s_off - {8'd0, lq_q} - 16'd1; end
            end
            // -------- E1: slot order check + registered one-hot duration select
            e1_v <= 1'b0;
            if (s_tv) begin
                if (s_slot != nslot || s_cbad) tfault <= 1'b1;
                nslot <= nslot + 7'd1;
                if (s_m && !s_cbad) begin
                    e1_v <= 1'b1; e1_slot <= s_slot; e1_c <= cmut; e1_d1 <= sel1; e1_d2 <= sel2;
                end
            end
            // -------- E2: accumulate + one masked metadata write
            if (e1_v) begin
                if (e1_slot != ucnt) tfault <= 1'b1;
                ucnt <= ucnt + 7'd1;
                m_we <= 1'b1; m_waddr <= {3'd0, e1_slot};
                m_wd <= {187'd0, e1_c, (MUT == 2) ? acc2 + 32'(e1_d2) : acc2, (MUT == 2) ? acc1 + 32'(e1_d1) : acc1};
                acc1 <= acc1 + 32'(e1_d1); acc2 <= acc2 + 32'(e1_d2);
            end
            rdy_p0 <= s_td; rdy_p1 <= rdy_p0;
            if (rdy_p1) rdy <= 1'b1;
            // -------- dispatch
            case (dst)
                D_IDLE: begin
                    if (s_hit) begin armed <= 1'b0; vpend <= 1'b1; vage <= 9'd1; end     // verify window starts at S
                    if (origin && (tfault || cfg_bad)) begin fault <= 1'b1; opend <= 1'b0; end
                    else if (origin && !dready) opend <= 1'b1;                          // static hold of the start
                    else if (origin) begin
                        opend <= 1'b0; busy <= 1'b1; age <= 32'd1; di <= 7'd0; loop_q <= 2'd1;
                        if (ucnt != 7'd0) begin m_re <= 1'b1; m_raddr <= 10'd0; dst <= D_READ; end
                        else dst <= D_NEXT;
                    end
                end
                D_NEXT: begin                                         // loop 1: wait for slot di's metadata / table close
                    if (rdy && di == ucnt) begin
                        if (ucnt == 7'd0) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end
                        else begin
                            loop_q <= 2'd2; di <= 7'd0; u_q <= ucnt; base2 <= b1_q + acc1 + g_q; t2_q <= acc2;
                            m_re <= 1'b1; m_raddr <= 10'd0; dst <= D_READ;
                        end
                    end else if (di < ucnt) begin m_re <= 1'b1; m_raddr <= {3'd0, di}; dst <= D_READ; end
                end
                D_READ: dst <= D_CAP;
                D_CAP: dst <= D_FORM;
                D_FORM: begin
                    ev_c <= cap[68:64];
                    evt <= (loop_q == 2'd1) ? b1_q + cap[31:0] : base2 + cap[63:32];
                    dst <= D_WAIT;
                end
                D_WAIT: if (evt < age) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end
                else if (evt == age) begin
                    launch_v <= 1'b1; launch_loop <= loop_q; launch_slot <= di; launch_c <= ev_c;
                    launch_kref <= ((loop_q == 2'd1) ? kb1_q : kb2_q) + 12'(ev_c) - 12'd1;
                    if (loop_q == 2'd1) begin
                        if (rdy && di + 7'd1 == ucnt) begin
                            loop_q <= 2'd2; di <= 7'd0; u_q <= ucnt; base2 <= b1_q + acc1 + g_q; t2_q <= acc2;
                            m_re <= 1'b1; m_raddr <= 10'd0; dst <= D_READ;
                        end else if (di + 7'd1 < ucnt) begin
                            di <= di + 7'd1; m_re <= 1'b1; m_raddr <= {3'd0, di + 7'd1}; dst <= D_READ;
                        end else begin di <= di + 7'd1; dst <= D_NEXT; end
                    end else if (di + 7'd1 == u_q) begin
                        di <= 7'd0; evt <= base2 + t2_q; dst <= D_TAIL;
                    end else begin
                        di <= di + 7'd1; m_re <= 1'b1; m_raddr <= {3'd0, di + 7'd1}; dst <= D_READ;
                    end
                end
                D_TAIL: if (evt < age) begin busy <= 1'b0; fault <= 1'b1; dst <= D_IDLE; end
                else if (evt == age) begin
                    launch_v <= 1'b1; launch_loop <= 2'd3; launch_slot <= u_q; launch_c <= 5'd0; launch_kref <= kbt_q;
                    busy <= 1'b0; done <= 1'b1; dst <= D_IDLE;
                end
                default: begin dst <= D_IDLE; busy <= 1'b0; fault <= 1'b1; end
            endcase
            // -------- verify: forwarded union_v exactly LQ + 1 edges after S, count == U, table closed
            if (s_uv && MUT != 4) begin
                vpend <= 1'b0;
                if (!vpend || vage != {1'b0, lq_q} + 9'd1 || s_uc != {3'd0, ucnt} || !(rdy || rdy_p1)) begin
                    fault <= 1'b1; busy <= 1'b0; armed <= 1'b0; opend <= 1'b0; dst <= D_IDLE;
                end
            end else if (vpend && vage > {1'b0, lq_q} + 9'd1) begin
                vpend <= 1'b0; fault <= 1'b1; busy <= 1'b0; dst <= D_IDLE;
            end
            // -------- forwarded IDX fault: abort this record (no further launch)
            if (s_uf) begin
                rdy <= 1'b0;
                if (armed || busy || vpend || opend) abort <= 1'b1;
                armed <= 1'b0; vpend <= 1'b0; opend <= 1'b0; busy <= 1'b0; dst <= D_IDLE;
            end
        end
    end
endmodule
`default_nettype wire
