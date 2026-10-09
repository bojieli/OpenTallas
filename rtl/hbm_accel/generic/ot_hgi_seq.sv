`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// hbm-forks 2026-10-09: the HGI-1 command-processor SEQUENCER (C2 of docs/HBM_GENERIC_INTERFACE.md section 6, owner
// Claude per the REVIEW_20261009 HGI-1 work split).  It replaces the LAUNCH/END list walk of ot_ds_hbm_cmdproc20 with the
// record stream of section 3:
//   * fetch: records are read from the program image in HBM (image_base 4 KiB pages + entry offset in 16 B units, MD
//     section D) through one 32 B-sector read port (in order; the die binds it to the loader's memory side), into a
//     ring of RW 16 B words; credits keep at most the ring's free space requested;
//   * decode: a record = header (16 B) + [SUT 32 B] + one MDESC (32 B) per opnd bit (A, B, C, O);
//   * predicate (ALWAYS / POS0 / NOT_POS0 / LAST_ITER), one LOOP level (ENDLOOP re-fetches the body from its HBM
//     address: no replay storage), CTL.FENCE (all units drained), CTL.END (completion with the posted result token,
//     range-checked against cp_vocab: status 0 / 2 no result / 3 out of range, as today's cmdproc);
//   * effective addresses BEFORE the wait: base + L*lstride + DYN[dyn_sel]*dyn_mul (40 b) and n = DYN[n_sel], by one
//     radix-16 iterative multiplier (early exit on a zero multiplier), so address arithmetic hides behind the drain;
//   * the `wait` mask: dispatch only when every unit in the mask has nothing outstanding; per-unit outstanding counts
//     (+1 on dispatch, -1 on the unit's retire pulse);
//   * dispatch: one unit port valid/ready at a time, payload {header, SUT, 4 effective MDESCs}.
// DYN codes 0..7 (ZERO, POS, POS1, TOKEN, L, RANK, SLOT, POS_SLOT) per slot; codes 8..31 (DS window counters) and units
// with no target on this die (SIMT: no r25 block runs kernels, hbm-forks.log 03:29) end the step with status 3.
// A unit fault ends the step with status 1.  No protection beyond the existing interfaces (REVIEW_20261009).
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_seq #(
    parameter integer RW  = 64,          // ring words (16 B each); a record is at most 11 words
    parameter integer NOS = 8            // fetch sectors outstanding
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [159:0]  md_d,           // {image_pages, image_base, entry_draft, entry_verify, entry_ar} (cfg master)
    input  wire [17:0]   cfg_vocab,
    input  wire [7:0]    rank,
    input  wire          hold,           // config commit / settle: doorbells refused
    // doorbell {token 18, pos 20, job 32, gen 4, entry 2, ncol 4}
    input  wire          db_v,
    output wire          db_rdy,
    input  wire [17:0]   db_token,
    input  wire [19:0]   db_pos,
    input  wire [31:0]   db_job,
    input  wire [3:0]    db_gen,
    input  wire [1:0]    db_entry,
    // record fetch: 32 B sectors, in-order responses
    output reg           f_req_v,
    input  wire          f_req_rdy,
    output reg  [39:0]   f_req_addr,
    input  wire          f_rsp_v,
    input  wire [255:0]  f_rsp_data,
    // unit dispatch (index = HGI unit code; CTL = 0 is internal)
    output reg  [11:0]   u_v,
    input  wire [11:0]   u_rdy,
    output reg  [127:0]  d_hdr,
    output reg  [255:0]  d_sut,
    output reg  [1023:0] d_desc,         // {O, C, B, A}, each with its effective base and n
    input  wire [11:0]   u_done,         // retire pulses (one per dispatched record)
    input  wire [11:0]   u_fault,
    input  wire          res_v,          // the step's result token (ARGMAX / COLL ARGMAX_MERGE posts it)
    input  wire [31:0]   res_data,
    // completion {token, pos, job, gen, status, cycles}
    output wire          cpl_v,
    input  wire          cpl_rdy,
    output reg  [17:0]   cpl_token,
    output reg  [19:0]   cpl_pos,
    output reg  [31:0]   cpl_job,
    output reg  [3:0]    cpl_gen,
    output reg  [3:0]    cpl_status,
    output reg  [31:0]   cpl_cycles
);
    localparam integer RB = $clog2(RW);
    // ------------------------------------------------------------------ step state
    localparam [3:0] S_IDLE = 4'd0, S_DEC = 4'd1, S_ADDR = 4'd2, S_WAIT = 4'd3, S_DISP = 4'd4, S_CPL = 4'd5,
                     S_DRAIN = 4'd6;
    reg [3:0]  st;
    reg [17:0] token; reg [19:0] pos;
    reg [15:0] L, lcnt; reg loop_on; reg [39:0] loop_addr;
    reg        have_res; reg [31:0] res_q;
    // ------------------------------------------------------------------ ring + fetch
    reg [127:0] ring [0:RW-1];
    reg [RB:0]  rcount;                  // valid words
    reg [RB-1:0] rp, wp;
    reg [39:0]  rec_addr;                // byte address of the record word at rp
    reg [39:0]  faddr;                   // next sector to request
    reg [4:0]   inflight;                // sectors requested (accepted), not yet returned
    reg [4:0]   drop;                    // responses to discard (requested before a jump / a new step)
    reg         skip_lo;                 // the next kept sector starts mid-sector: drop its low word
    reg         fetching;
    wire signed [RB+7:0] space = RW - $signed({1'b0, rcount}) - 2 * $signed({1'b0, inflight}) - (f_req_v ? 2 : 0);
    // ------------------------------------------------------------------ record fields at rp
    wire [127:0] h = ring[rp];
    wire [3:0]  h_unit = h[127:124];
    wire [5:0]  h_op   = h[123:118];
    wire [11:0] h_wait = h[117:106];
    wire [1:0]  h_pred = h[105:104];
    wire [3:0]  h_opnd = h[103:100];
    wire        h_tmpl = h[99];
    wire [31:0] h_param = h[95:64];
    wire [3:0]  rlen = 4'd1 + {2'd0, h_tmpl, 1'b0} + {2'd0, h_opnd[0], 1'b0} + {2'd0, h_opnd[1], 1'b0} +
                       {2'd0, h_opnd[2], 1'b0} + {2'd0, h_opnd[3], 1'b0};
    wire        have_rec = (rcount != 0) && (rcount >= {{(RB-3){1'b0}}, rlen});
    function automatic [127:0] rw(input [RB-1:0] base, input [3:0] k);
        rw = ring[base + k];
    endfunction
    wire last_iter = loop_on && (L + 16'd1 == lcnt);
    reg  pred_ok;
    always @* case (h_pred) 2'd0: pred_ok = 1'b1; 2'd1: pred_ok = (pos == 0); 2'd2: pred_ok = (pos != 0);
                            default: pred_ok = last_iter; endcase
    // ------------------------------------------------------------------ outstanding per unit
    reg [7:0] outst [0:11];
    reg [11:0] busy_u;
    integer u;
    always @* for (u = 0; u < 12; u = u + 1) busy_u[u] = (outst[u] != 8'd0);
    function automatic waitok(input [11:0] w, input [11:0] b);
`ifdef OT_HGI_SEQ_MUT_WAIT
        waitok = 1'b1;                                     // NEGATIVE CONTROL: the drain mask ignored
`else
        waitok = (w & b) == 12'd0;
`endif
    endfunction
    // ------------------------------------------------------------------ DYN
    function automatic [31:0] dynv(input [4:0] sel, input [2:0] slot);
        case (sel)
            5'd0: dynv = 32'd0;
            5'd1: dynv = {12'd0, pos};
            5'd2: dynv = {12'd0, pos} + 32'd1;
            5'd3: dynv = {14'd0, token};
            5'd4: dynv = {16'd0, L};
            5'd5: dynv = {24'd0, rank};
            5'd6: dynv = {29'd0, slot};
            5'd7: dynv = {12'd0, pos} + {29'd0, slot};
            default: dynv = 32'd0;
        endcase
    endfunction
    // ------------------------------------------------------------------ address unit: radix-16 iterative multiply
    localparam [2:0] A_LOAD = 3'd0, A_ML = 3'd1, A_DYN = 3'd2, A_MD = 3'd3, A_WR = 3'd4;
    reg [2:0]  as;
    reg [1:0]  aj;                       // descriptor (A, B, C, O)
    reg [47:0] acc, mcand;
    reg [31:0] mplier;
    reg [5:0]  ash;                      // shift of the current digit (bits)
    reg [3:0]  dk;                       // word offset of the next present descriptor
    reg        bad;
    wire [255:0] dcur = {rw(rp, dk + 4'd1), rw(rp, dk)};
    wire [31:0]  n_dyn32 = dynv(dcur[204:200], d_hdr[98:96]);
    wire [19:0]  n_dyn = n_dyn32[19:0];
    // ------------------------------------------------------------------ main FSM
    integer k;
    wire [11:0] u_acc = u_v & u_rdy;
    assign db_rdy = (st == S_IDLE) && !hold;
    assign cpl_v = (st == S_CPL);
    wire [39:0] entry_off = {4'd0, (db_entry == 2'd0) ? md_d[31:0] : (db_entry == 2'd1) ? md_d[63:32] : md_d[95:64], 4'd0};
    wire [39:0] img = {md_d[139:128], 12'd0} + entry_off;
    wire is_ctl = (h_unit == 4'd0);
`ifdef OT_HGI_SEQ_MUT_LOOP
    wire more = loop_on && (L + 16'd2 < lcnt);             // NEGATIVE CONTROL: one iteration short
`else
    wire more = loop_on && (L + 16'd1 < lcnt);
`endif
    wire jump = (st == S_DEC) && have_rec && pred_ok && is_ctl && h_op == 6'd2 && more;
    wire consume = (st == S_DEC && have_rec && !jump && (!pred_ok || (is_ctl && h_op <= 6'd2))) ||
                   (st == S_DRAIN && busy_u == 12'd0) || (st == S_DISP && |u_acc);
    wire [4:0] fl_after = inflight + ((f_req_v && f_req_rdy) ? 5'd1 : 5'd0) - (f_rsp_v ? 5'd1 : 5'd0);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            st <= S_IDLE; rcount <= 0; rp <= 0; wp <= 0; inflight <= 0; drop <= 0; fetching <= 1'b0; f_req_v <= 1'b0;
            L <= 0; lcnt <= 0; loop_on <= 1'b0; have_res <= 1'b0; res_q <= 0; u_v <= 12'd0; skip_lo <= 1'b0;
            cpl_status <= 0; cpl_token <= 0; cpl_cycles <= 0; bad <= 1'b0; as <= A_LOAD; faddr <= 0; rec_addr <= 0;
            for (k = 0; k < 12; k = k + 1) outst[k] <= 8'd0;
        end else begin
            for (k = 0; k < 12; k = k + 1) outst[k] <= outst[k] + {7'd0, u_acc[k]} - {7'd0, u_done[k]};
            if (res_v) begin have_res <= 1'b1; res_q <= res_data; end
            if (st != S_IDLE && st != S_CPL) cpl_cycles <= cpl_cycles + 32'd1;
            inflight <= fl_after;
            // ---- fetch requests (valid held until ready)
            if (f_req_v && f_req_rdy) begin f_req_v <= 1'b0; faddr <= faddr + 40'd32; end
            else if (fetching && !f_req_v && inflight < NOS && space >= 2) begin f_req_v <= 1'b1; f_req_addr <= faddr; end
            // ---- fetch responses -> ring (the case below may restart the ring; its assignments win)
            begin : rsp
                reg [RB:0] add; add = 0;
                if (f_rsp_v) begin
                    if (drop != 0) drop <= drop - 5'd1;
                    else if (skip_lo) begin ring[wp] <= f_rsp_data[255:128]; wp <= wp + 1'd1; add = 1; skip_lo <= 1'b0; end
                    else begin ring[wp] <= f_rsp_data[127:0]; ring[wp + 1'd1] <= f_rsp_data[255:128]; wp <= wp + 2'd2; add = 2; end
                end
                rcount <= rcount + add - (consume ? {{(RB-3){1'b0}}, rlen} : {(RB+1){1'b0}});
            end
            if (consume) begin rp <= rp + rlen; rec_addr <= rec_addr + {32'd0, rlen, 4'd0}; end
            if ((|u_fault) && st != S_IDLE && st != S_CPL) begin
                st <= S_CPL; cpl_status <= 4'd1; cpl_token <= 0; u_v <= 0; fetching <= 1'b0; f_req_v <= 1'b0;
            end else case (st)
                S_IDLE: if (db_v && !hold) begin
                    token <= db_token; pos <= db_pos; cpl_job <= db_job; cpl_gen <= db_gen; cpl_pos <= db_pos;
                    cpl_cycles <= 0; have_res <= 1'b0; L <= 0; loop_on <= 1'b0;
                    faddr <= {img[39:5], 5'd0}; skip_lo <= img[4]; rec_addr <= img; fetching <= 1'b1; f_req_v <= 1'b0;
                    rp <= 0; wp <= 0; rcount <= 0; drop <= fl_after;
                    st <= S_DEC;
                end
                S_DEC: if (have_rec) begin
                    if (jump) begin                                   // ENDLOOP with iterations left: re-fetch the body
                        L <= L + 16'd1;
                        faddr <= {loop_addr[39:5], 5'd0}; skip_lo <= loop_addr[4]; rec_addr <= loop_addr;
                        rp <= 0; wp <= 0; rcount <= 0; f_req_v <= 1'b0; drop <= fl_after;
                    end else if (!pred_ok) ;                          // skipped
                    else if (is_ctl) begin
                        case (h_op)
                            6'd0: ;                                   // NOP
                            6'd1: begin loop_on <= 1'b1; lcnt <= h_param[15:0]; L <= 0;
                                        loop_addr <= rec_addr + {32'd0, rlen, 4'd0}; end
                            6'd2: begin loop_on <= 1'b0; L <= 0; end  // ENDLOOP, last iteration
                            6'd3: if (waitok(h_wait, busy_u)) begin   // END
                                st <= S_CPL; fetching <= 1'b0; f_req_v <= 1'b0;
                                cpl_status <= !have_res ? 4'd2 :
                                              ((res_q >> 18) != 0 || res_q >= {14'd0, cfg_vocab}) ? 4'd3 : 4'd0;
                                cpl_token <= res_q[17:0];
                            end
                            6'd4: st <= S_DRAIN;                      // FENCE
                            default: begin st <= S_CPL; cpl_status <= 4'd3; cpl_token <= 0; fetching <= 1'b0; f_req_v <= 1'b0; end
                        endcase
                    end else if (h_unit >= 4'd11) begin               // SIMT / undefined: no target on this die
                        st <= S_CPL; cpl_status <= 4'd3; cpl_token <= 0; fetching <= 1'b0; f_req_v <= 1'b0;
                    end else begin
                        d_hdr <= h; d_sut <= h_tmpl ? {rw(rp, 4'd2), rw(rp, 4'd1)} : 256'd0; d_desc <= 1024'd0;
                        aj <= 2'd0; as <= A_LOAD; dk <= h_tmpl ? 4'd3 : 4'd1; bad <= 1'b0; st <= S_ADDR;
                    end
                end
                S_ADDR: if (!d_hdr[100 + aj]) begin                  // operand absent
                        if (aj == 2'd3) st <= S_WAIT; else aj <= aj + 2'd1;
                    end else case (as)
                        A_LOAD: begin
                            acc <= {8'd0, dcur[47:8]}; mcand <= {16'd0, dcur[167:136]}; mplier <= {16'd0, L}; ash <= 6'd0;
                            if (dcur[172:168] > 5'd7 || dcur[204:200] > 5'd7) bad <= 1'b1;   // DS-only DYN codes
                            as <= A_ML;
                        end
                        A_ML, A_MD: if (mplier != 32'd0) begin
                                acc <= acc + ((mcand * {44'd0, mplier[3:0]}) << ash);
                                mplier <= mplier >> 4; ash <= ash + 6'd4;
                            end else if (as == A_ML) as <= A_DYN;
                            else as <= A_WR;
                        A_DYN: begin
                            mcand <= {21'd0, dcur[199:173]}; mplier <= dynv(dcur[172:168], d_hdr[98:96]); ash <= 6'd0;
                            as <= A_MD;
                        end
                        default: begin                                // A_WR: the effective descriptor
                            d_desc[aj*256 +: 256] <= {dcur[255:68],
                                                      (dcur[204:200] != 5'd0) ? n_dyn : dcur[67:48],
                                                      acc[39:0], dcur[7:0]};
                            dk <= dk + 4'd2; as <= A_LOAD;
                            if (aj == 2'd3) st <= S_WAIT; else aj <= aj + 2'd1;
                        end
                    endcase
                S_WAIT: if (bad) begin st <= S_CPL; cpl_status <= 4'd3; cpl_token <= 0; fetching <= 1'b0; f_req_v <= 1'b0; end
                        else if (waitok(d_hdr[117:106], busy_u)) begin st <= S_DISP; u_v <= 12'd1 << d_hdr[127:124]; end
                S_DISP: if (|u_acc) begin u_v <= 12'd0; st <= S_DEC; end
                S_DRAIN: if (busy_u == 12'd0) st <= S_DEC;
                S_CPL: if (cpl_rdy) st <= S_IDLE;
                default: st <= S_IDLE;
            endcase
        end
    end
endmodule
`default_nettype wire
