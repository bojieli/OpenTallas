`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA row mover, F6 full-rate version (hgi-takeover 2026-10-09; hgi-e2e F6: the element-serial mover ran one
// element every 4 edges plus a lane round trip per sector: +113k cycles on Qwen L0, +26k on DS L0).
// Same ports / ABI / semantics as hgi-adapters' mover (the peer of ot_hgi_dma_record's move / fence ports):
// Move word (227 b, LSB first): {src space 2, src fmt 3, src base 40, src stride 32, src istride 16, dst space 2,
//   dst fmt 3, dst base 40, dst stride 32, dst istride 16, m 20, n 21}.  Element (o, i), o < m, i < n, row-major:
//   HBM byte  base + o stride + i istride esize      (esize: FP32 / U32 4, BF16 2, FP8E4M3 / INT8 1)
//   VM word   base + o stride + i istride
// LOAD (HBM -> VM): FP32 / U32 the word; BF16 the half << 16; INT8 the integer as FP32 (exact); FP8E4M3 the E4M3 value
//   (NaN code -> 0x7FC00000).  VM -> VM copies the word.  STORE (VM -> HBM): FP32 / U32 the word; BF16 = to_bf16 (RNE);
//   FP8E4M3 = to_fp8 (RNE, saturating at 448) then its code.  Faults: an element not naturally aligned, FP4 / UE8M0, a
//   space other than HBM / VM, a lane fault.  done = every write of the move acknowledged; fence_done when idle.
//
// SECTOR ENGINE (every move whose element strides are 1 on both sides -- rows of contiguous elements; the strided rest
// runs on the element-serial engine ot_hgi_dma_mover_serial, unchanged):
//   R  reader: issues each row's source sectors in order, up to KOUT on the HBM lane / 4 on the VM client (the fast
//      path, in-order responses), never more than the landing FIFO (SFD sectors) can hold;
//   U  unpack (registered): up to 8 elements a cycle from the head source sector -- as many as are left in that sector,
//      in the row and in the destination sector -- with each lane's destination byte offset and a flush mark at a
//      destination sector end / row end;
//   D  decode (registered): source format -> binary32 (or the raw word on a VM source);
//   E  encode + merge (registered): -> the destination format, merged into the destination sector buffer with byte
//      strobes; a flush pushes the sector into a 4-deep write queue;
//   W  writer: the write queue drains first on its port (VM client / HBM lane), reads use the rest.
// Rate: one destination sector a cycle in the pipe; in practice the VM client (4 requests in flight over ~6-8 edges,
// ~4.5 words a cycle) or the HBM lane's request rate bounds it.  Exactness = the serial engine's arithmetic, per element.
// MUT (bench): 1 BF16 store truncates (no RNE; both engines); 2 the sector engine drops a row's last partial sector.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_mover #(
    parameter integer MUT_RNE = 0,        // mutant: BF16 store truncates (no round to nearest even)
    parameter integer MUT = 0,
    parameter integer KOUT = 8,           // HBM lane requests in flight (the lane answers in order)
    parameter integer SFD = 8             // landing FIFO, source sectors
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          mv_v,
    output wire          mv_rdy,
    input  wire [226:0]  mv,
    output reg           mv_done,
    output reg           mv_fault,
    input  wire          fence_v,
    output wire          fence_rdy,
    output reg           fence_done,
    // kport lane (HBM)
    output wire          k_req_v,
    input  wire          k_req_rdy,
    output wire          k_req_we,
    output wire [36:0]   k_req_addr,
    output wire [255:0]  k_req_wdata,
    output wire [31:0]   k_req_wstrb,
    output wire [15:0]   k_req_tag,
    input  wire          k_rsp_v,
    output wire          k_rsp_rdy,
    input  wire          k_rsp_we,
    input  wire [255:0]  k_rsp_data,
    input  wire          k_fault,
    // VM packet client
    output wire [337:0]  vmq,
    input  wire [273:0]  vmr
);
    // the sector engine's port registers (the serial engine has its own; sel_s picks)
    reg f_kv, f_kwe; reg [36:0] f_ka; reg [255:0] f_kd; reg [31:0] f_ks; reg [337:0] f_vmq;
    assign k_req_tag = 16'h4D56;
    assign k_rsp_rdy = 1'b1;
    // ================================================================ dispatch: sector engine or serial engine
    // registered boundary (submit lint: input -> register <= 16 levels): a command station, pin flops on the lane and
    // VM responses (+1 cycle each), and the lane request issues only from an empty request register (k_req_rdy only
    // clears it)
    reg cv_q; reg [226:0] cm_q;
    reg kr_v, kr_we; reg [255:0] kr_d; reg [273:0] vr_q;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin kr_v <= 1'b0; vr_q <= 274'd0; end
        else begin kr_v <= k_rsp_v; vr_q <= vmr; end
    always @(posedge clk) begin kr_we <= k_rsp_we; kr_d <= k_rsp_data; end
    wire fast_cmd = (cm_q[92:77] == 16'd1) && (cm_q[185:170] == 16'd1);     // src istride 1 and dst istride 1
    reg  busy_f;                                                        // the sector engine owns the ports
    reg  sel_s;                                                         // the serial engine owns the ports
    wire s_mv_rdy, s_mv_done, s_mv_fault, s_fence_rdy, s_fence_done;
    wire s_kv, s_kwe; wire [36:0] s_ka; wire [255:0] s_kd; wire [31:0] s_ks; wire [15:0] s_kt; wire s_krr; wire [337:0] s_vmq;
    reg  f_fault;
    assign mv_rdy = !busy_f && !cv_q && !sel_s && s_mv_rdy && !f_fault;
    ot_hgi_dma_mover_serial #(.MUT_RNE(MUT_RNE)) u_ser (.clk(clk), .rst_n(rst_n), .mv_v(cv_q && !fast_cmd),
        .mv_rdy(s_mv_rdy), .mv(cm_q), .mv_done(s_mv_done), .mv_fault(s_mv_fault), .fence_v(1'b0), .fence_rdy(s_fence_rdy),
        .fence_done(s_fence_done), .k_req_v(s_kv), .k_req_rdy(k_req_rdy && sel_s), .k_req_we(s_kwe), .k_req_addr(s_ka),
        .k_req_wdata(s_kd), .k_req_wstrb(s_ks), .k_req_tag(s_kt), .k_rsp_v(kr_v && sel_s), .k_rsp_rdy(s_krr),
        .k_rsp_we(kr_we), .k_rsp_data(kr_d), .k_fault(k_fault && sel_s), .vmq(s_vmq), .vmr(sel_s ? vr_q : 274'd0));
    assign fence_rdy = !busy_f && s_mv_rdy && s_fence_rdy;
    // ================================================================ sector engine
    function automatic [2:0] esz(input [2:0] f);
        esz = (f == 3'd0 || f == 3'd5) ? 3'd4 : (f == 3'd1) ? 3'd2 : 3'd1;
    endfunction
    function automatic [31:0] i8_f(input [7:0] c);               // INT8 -> binary32 (exact)
        reg [7:0] a; reg [2:0] p; integer k;
        begin
            a = c[7] ? (~c + 8'd1) : c; p = 3'd0;
            for (k = 0; k < 8; k = k + 1) if (a[k]) p = k[2:0];
            i8_f = (a == 8'd0) ? 32'd0 : {c[7], 8'd127 + {5'd0, p}, ({15'd0, a} << (5'd23 - {2'd0, p})) & 23'h7FFFFF};
        end
    endfunction
    function automatic [31:0] e4m3_f(input [7:0] c);             // FP8 E4M3 -> binary32 (exact; NaN code -> qNaN)
        reg [3:0] e; reg [2:0] m; reg [1:0] p;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 4'hF && m == 3'h7) e4m3_f = 32'h7FC00000;
            else if (e == 4'd0) begin
                if (m == 3'd0) e4m3_f = {c[7], 31'd0};
                else begin
                    p = m[2] ? 2'd2 : m[1] ? 2'd1 : 2'd0;
                    e4m3_f = {c[7], 8'd127 - 8'd9 + {6'd0, p}, ({20'd0, m} << (5'd23 - {3'd0, p})) & 23'h7FFFFF};
                end
            end else e4m3_f = {c[7], 8'd120 + {4'd0, e}, m, 20'd0};
        end
    endfunction
    function automatic [15:0] to_bf16(input [31:0] x);           // RNE (hdc_golden to_bf16), NaN kept quiet
        reg [31:0] r;
        begin
            if (x[30:23] == 8'hFF && x[22:0] != 0) to_bf16 = {x[31:16]} | 16'h0040;
            else if (MUT_RNE) to_bf16 = x[31:16];
            else begin r = x + 32'h7FFF + {31'd0, x[16]}; to_bf16 = r[31:16]; end
        end
    endfunction
    function automatic [7:0] to_e4m3(input [31:0] x);            // to_fp8 (RNE, binade quantum, saturate 448) -> code
        reg [7:0] ex; reg [23:0] mant; integer sh; reg [24:0] q; reg [7:0] code; reg [4:0] e4; reg [3:0] mq;
        begin
            ex = x[30:23];
            if (ex == 8'hFF) to_e4m3 = {x[31], 7'h7E};
            else if (ex >= 8'd136) to_e4m3 = {x[31], 7'h7E};
            else begin
                mant = (ex == 8'd0) ? 24'd0 : {1'b1, x[22:0]};
                sh = (ex >= 8'd121) ? 20 : (20 + 121 - ex);
                if (sh > 24) begin q = 25'd0; end
                else begin
                    q = {1'b0, mant} >> sh;
                    if (sh > 0 && mant[sh - 1] && ((mant & ((24'd1 << (sh - 1)) - 24'd1)) != 0 || q[0])) q = q + 25'd1;
                end
                if (ex >= 8'd121) begin
                    e4 = ex - 8'd120; mq = q[4] ? 4'd8 : q[3:0];
                    if (q[4]) e4 = e4 + 5'd1;
                    code = (e4 > 5'd15) ? 8'h7F : {e4[3:0], mq[2:0]};
                end else code = {1'b0, 4'd0, q[2:0]} + (q[3] ? 8'd8 : 8'd0);
                if (code > 8'h7E) code = 8'h7E;
                to_e4m3 = (code == 8'd0) ? 8'd0 : {x[31], code[6:0]};
            end
        end
    endfunction
    // ---- command
    reg        go_f;
    reg [1:0]  ssp, dsp; reg [2:0] sf, df; reg [31:0] sst, dst; reg [33:0] sstb, dstb; reg [19:0] mm; reg [20:0] nn;   // sstb / dstb: row strides in bytes
    reg [2:0]  ses, des;                                    // element bytes (VM: 4)
    reg [41:0] sbase, dbase;                                // byte addresses (VM: word x 4)
    // ---- reader state
    reg [19:0] r_o; reg [41:0] r_row; reg [36:0] r_sec, r_last; reg r_done;
    // ---- unpack state
    reg [19:0] u_o; reg [20:0] u_left; reg [4:0] u_sp; reg u_rowstart; reg [41:0] u_srow, u_drow;
    reg [36:0] u_dsec; reg [5:0] u_dp; reg u_done;
    // ---- landing FIFO (source sectors in order)
    reg [255:0] sfd [0:SFD-1]; reg [3:0] sf_h, sf_t; reg [4:0] sf_n;
    // ---- port in-flight accounting: per port a kind FIFO (0 read, 1 write) for the in-order responses
    reg [3:0] k_in; reg [2:0] v_in; reg [15:0] k_kind; reg [7:0] v_kind;    // shift registers of kinds, oldest at [0]
    reg [4:0] rd_in;                                          // source reads in flight (landing room)
    // ---- write queue
    reg [255:0] wq_d [0:3]; reg [31:0] wq_s [0:3]; reg [36:0] wq_a [0:3]; reg [1:0] wq_h, wq_t; reg [2:0] wq_n;
    reg [4:0] wr_in;                                          // writes issued, not acknowledged
    // ---- pipeline registers
    reg        p1_v; reg [3:0] p1_k; reg [255:0] p1_sec; reg [4:0] p1_sp; reg [5:0] p1_dp; reg [36:0] p1_dsec; reg p1_fl;
    reg        p2_v; reg [3:0] p2_k; reg [255:0] p2_w; reg [5:0] p2_dp; reg [36:0] p2_dsec; reg p2_fl;
    reg [255:0] db_dat; reg [31:0] db_strb; reg db_dirty;
    // ---- source sector issue
    wire src_hbm = (ssp == 2'd0), dst_hbm = (dsp == 2'd0);
    wire [41:0] r_end = r_row + {21'd0, nn} * ses - 42'd1;            // last byte of row r_o
    // ---- unpack decision (combinational on registered state)
    reg [3:0] u_k; reg u_fl; reg u_pop; reg u_go;
    always @* begin : unp
        reg [5:0] s_room; reg [5:0] d_room; reg [21:0] kk;
        s_room = (6'd32 - {1'b0, u_sp}) / ses;                        // elements left in the head source sector
        d_room = (6'd32 - u_dp) / des;                                // elements left in the destination sector
        kk = {1'b0, u_left};
        if (kk > 22'd8) kk = 22'd8;
        if (kk > {16'd0, s_room}) kk = {16'd0, s_room};
        if (kk > {16'd0, d_room}) kk = {16'd0, d_room};
        u_k = kk[3:0];
        u_go = busy_f && !u_done && go_q2 && sf_n != 5'd0 && wq_room;
        u_fl = (u_dp + {2'd0, u_k} * des == 6'd32) || ({1'b0, u_left} == {18'd0, u_k});
        u_pop = ({1'b0, u_sp} + {2'd0, u_k} * ses == 6'd32) || ({1'b0, u_left} == {18'd0, u_k});   // sector used up / row ends
    end
    reg go_q2;                                                         // the command fields are settled
    // the write queue must hold the flushes the pipe may still produce (p1 + p2 + this): keep 3 slots free
    wire wq_room = (wq_n + {2'd0, p1_v & p1_fl} + {2'd0, p2_v & p2_fl}) < 3'd3;
    // ---- decode (p1 -> p2) / encode + merge (p2)
    reg [255:0] dec_w; integer j;
    always @* begin
        dec_w = 256'd0;
        for (j = 0; j < 8; j = j + 1) begin : dl
            reg [7:0] b; reg [4:0] off; reg [31:0] w; reg [15:0] h;
            off = p1_sp + 5'(j) * ses;
            w = p1_sec[{off[4:2], 5'd0} +: 32];
            h = off[1] ? w[31:16] : w[15:0];
            b = w[{off[1:0], 3'd0} +: 8];
            if (ssp == 2'd1) dec_w[32*j +: 32] = w;
            else case (sf)
                3'd1: dec_w[32*j +: 32] = {h, 16'd0};
                3'd2: dec_w[32*j +: 32] = e4m3_f(b);
                3'd4: dec_w[32*j +: 32] = i8_f(b);
                default: dec_w[32*j +: 32] = w;
            endcase
        end
    end
    reg [255:0] put_d; reg [31:0] put_s, put_mk;
    always @* begin
        put_d = 256'd0; put_s = 32'd0;
        for (j = 0; j < 8; j = j + 1) if (j < p2_k) begin : el
            reg [5:0] o_; reg [31:0] x;
            o_ = p2_dp + 6'(j) * des; x = p2_w[32*j +: 32];
            if (dsp == 2'd1 || df == 3'd0 || df == 3'd5) begin put_d[{o_[4:0], 3'd0} +: 32] = x; put_s[o_[4:0] +: 4] = 4'hF; end
            else if (df == 3'd1) begin put_d[{o_[4:0], 3'd0} +: 16] = to_bf16(x); put_s[o_[4:0] +: 2] = 2'b11; end
            else begin put_d[{o_[4:0], 3'd0} +: 8] = to_e4m3(x); put_s[o_[4:0]] = 1'b1; end
        end
    end
    // ---- port issue selection
    reg iss_kw, iss_kr, iss_vw, iss_vr;
    always @* begin
        iss_kw = 1'b0; iss_kr = 1'b0; iss_vw = 1'b0; iss_vr = 1'b0;
        if (busy_f && go_q2 && !f_fault) begin
            if (wq_n != 3'd0 && dst_hbm && k_in < 4'(KOUT) && !f_kv) iss_kw = 1'b1;
            else if (!r_done && src_hbm && k_in < 4'(KOUT) && !f_kv && ({1'b0, sf_n} + rd_in) < 6'(SFD)) iss_kr = 1'b1;
            if (wq_n != 3'd0 && !dst_hbm && v_in < 3'd4) iss_vw = 1'b1;
            else if (!r_done && !src_hbm && v_in < 3'd4 && ({1'b0, sf_n} + rd_in) < 6'(SFD)) iss_vr = 1'b1;
        end
    end
    // ---- response routing (in order per port)
    wire k_rv = kr_v && busy_f, v_rv = vr_q[273] && busy_f;
    wire k_rd_land = k_rv && !k_kind[0], k_wr_ack = k_rv && k_kind[0];
    wire v_rd_land = v_rv && !v_kind[0], v_wr_ack = v_rv && v_kind[0];
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            busy_f <= 1'b0; sel_s <= 1'b0; go_f <= 1'b0; go_q2 <= 1'b0; f_fault <= 1'b0;
            mv_done <= 1'b0; mv_fault <= 1'b0; fence_done <= 1'b0; f_kv <= 1'b0; f_vmq <= 338'd0;
            k_in <= 4'd0; v_in <= 3'd0; k_kind <= 16'd0; v_kind <= 8'd0; rd_in <= 5'd0; wr_in <= 5'd0;
            sf_h <= 4'd0; sf_t <= 4'd0; sf_n <= 5'd0; wq_h <= 2'd0; wq_t <= 2'd0; wq_n <= 3'd0;
            p1_v <= 1'b0; p2_v <= 1'b0; db_dirty <= 1'b0; r_done <= 1'b1; u_done <= 1'b1;
            f_kwe <= 1'b0; f_ka <= 37'd0; f_kd <= 256'd0; f_ks <= 32'd0;
        end else begin
            mv_done <= 1'b0; fence_done <= 1'b0;
            if (fence_v && fence_rdy) fence_done <= 1'b1;
            // ---- the serial engine's completion and ports
            if (s_mv_done) begin mv_done <= 1'b1; sel_s <= 1'b0; end
            if (s_mv_fault) mv_fault <= 1'b1;
            cv_q <= 1'b0;
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
            if (cv_q && !fast_cmd) sel_s <= 1'b1;
            // ---- accept a sector-engine command
            go_f <= 1'b0; go_q2 <= go_f | (go_q2 && busy_f);           // go_q2: the command fields have settled (level while busy)
            if (cv_q && fast_cmd) begin
                busy_f <= 1'b1; go_f <= 1'b1;
                ssp <= cm_q[1:0]; sf <= cm_q[4:2]; sst <= cm_q[76:45]; dsp <= cm_q[94:93]; df <= cm_q[97:95]; dst <= cm_q[169:138];
                sstb <= (cm_q[1:0] == 2'd1) ? {cm_q[76:45], 2'b00} : {2'd0, cm_q[76:45]};
                dstb <= (cm_q[94:93] == 2'd1) ? {cm_q[169:138], 2'b00} : {2'd0, cm_q[169:138]};
                mm <= cm_q[205:186]; nn <= cm_q[226:206];
                ses <= (cm_q[1:0] == 2'd1) ? 3'd4 : esz(cm_q[4:2]); des <= (cm_q[94:93] == 2'd1) ? 3'd4 : esz(cm_q[97:95]);
                sbase <= (cm_q[1:0] == 2'd1) ? {cm_q[44:5], 2'b00} : {2'd0, cm_q[44:5]};
                dbase <= (cm_q[94:93] == 2'd1) ? {cm_q[137:98], 2'b00} : {2'd0, cm_q[137:98]};
                if ((cm_q[1:0] > 2'd1) || (cm_q[94:93] > 2'd1) || cm_q[4:2] == 3'd3 || cm_q[4:2] == 3'd6 || cm_q[97:95] == 3'd3 ||
                    cm_q[97:95] == 3'd6 || cm_q[97:95] == 3'd4 || cm_q[205:186] == 20'd0 || cm_q[226:206] == 21'd0) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
            end
            if (go_f) begin
                r_o <= 20'd0; r_row <= sbase; r_sec <= sbase[41:5]; r_done <= 1'b0;
                u_o <= 20'd0; u_left <= nn; u_sp <= sbase[4:0]; u_srow <= sbase; u_drow <= dbase;
                u_dsec <= dbase[41:5]; u_dp <= {1'b0, dbase[4:0]}; u_done <= 1'b0; db_dirty <= 1'b0;
                // natural alignment of every row start (elements are contiguous within a row)
                if ((ses == 3'd4 && (sbase[1:0] != 2'd0 || sstb[1:0] != 2'd0)) || (ses == 3'd2 && (sbase[0] || sstb[0])) ||
                    (des == 3'd4 && (dbase[1:0] != 2'd0 || dstb[1:0] != 2'd0)) || (des == 3'd2 && (dbase[0] || dstb[0]))) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
            end
            // ---- issue: lane / client requests
            if (f_kv && k_req_rdy) f_kv <= 1'b0;
            f_vmq[337] <= 1'b0;
            begin : issue
                reg kpush, kkind, vpush, vkind;
                kpush = 1'b0; kkind = 1'b0; vpush = 1'b0; vkind = 1'b0;
                if (iss_kw) begin
                    f_kv <= 1'b1; f_kwe <= 1'b1; f_ka <= {wq_a[wq_h][31:0], 5'd0}; f_kd <= wq_d[wq_h];
                    f_ks <= wq_s[wq_h]; kpush = 1'b1; kkind = 1'b1;
                end else if (iss_kr) begin
                    f_kv <= 1'b1; f_kwe <= 1'b0; f_ka <= {r_sec[31:0], 5'd0}; kpush = 1'b1;
                end
                if (iss_vw) begin
                    f_vmq <= {1'b1, 1'b1, wq_a[wq_h][26:0], 5'd0, wq_d[wq_h], wq_s[wq_h], 16'h4D57}; vpush = 1'b1; vkind = 1'b1;
                end else if (iss_vr) begin
                    f_vmq <= {1'b1, 1'b0, r_sec[26:0], 5'd0, 256'd0, 32'd0, 16'h4D52}; vpush = 1'b1;
                end
                // write queue pop
                if (iss_kw || iss_vw) begin wq_h <= wq_h + 2'd1; end
                // reader advance
                if (iss_kr || iss_vr) begin
                    if (r_sec == r_end[41:5]) begin
                        if (r_o + 20'd1 == mm) r_done <= 1'b1;
                        else begin
                            r_o <= r_o + 20'd1; r_row <= r_row + {8'd0, sstb}; r_sec <= (r_row + {8'd0, sstb}) >> 5;
                        end
                    end else r_sec <= r_sec + 37'd1;
                end
                // in-flight accounting (kind shift registers: push at the tail, pop at the head)
                k_in <= k_in + {3'd0, kpush} - {3'd0, k_rv};
                v_in <= v_in + {2'd0, vpush} - {2'd0, v_rv};
                begin : kk
                    reg [15:0] t; t = k_kind;
                    if (k_rv) t = t >> 1;
                    if (kpush) t[k_in - {3'd0, k_rv}] = kkind;
                    k_kind <= t;
                end
                begin : vk
                    reg [7:0] t; t = v_kind;
                    if (v_rv) t = t >> 1;
                    if (vpush) t[v_in - {2'd0, v_rv}] = vkind;
                    v_kind <= t;
                end
                rd_in <= rd_in + {4'd0, iss_kr | iss_vr} - {4'd0, k_rd_land | v_rd_land};
                wr_in <= wr_in + {4'd0, iss_kw | iss_vw} - {4'd0, k_wr_ack | v_wr_ack};
            end
            if (k_fault && busy_f) begin f_fault <= 1'b1; mv_fault <= 1'b1; end
            // ---- landing
            begin : land
                reg push_, pop_;
                push_ = k_rd_land || v_rd_land; pop_ = u_go && u_pop;
                if (push_) begin sfd[sf_t[2:0] % SFD] <= k_rd_land ? kr_d : vr_q[255:0]; sf_t <= sf_t + 4'd1; end
                if (pop_) sf_h <= sf_h + 4'd1;
                sf_n <= sf_n + {4'd0, push_} - {4'd0, pop_};
            end
            // ---- unpack (stage U -> p1)
            p1_v <= 1'b0;
            if (u_go) begin
                p1_v <= 1'b1; p1_k <= u_k; p1_sec <= sfd[sf_h[2:0] % SFD]; p1_sp <= u_sp; p1_dp <= u_dp; p1_dsec <= u_dsec;
                p1_fl <= u_fl;
                if ({1'b0, u_left} == {18'd0, u_k}) begin                    // row end: next row
                    if (u_o + 20'd1 == mm) u_done <= 1'b1;
                    u_o <= u_o + 20'd1; u_left <= nn;
                    u_srow <= u_srow + {8'd0, sstb}; u_sp <= 5'(u_srow + {8'd0, sstb});
                    u_drow <= u_drow + {8'd0, dstb}; u_dsec <= (u_drow + {8'd0, dstb}) >> 5; u_dp <= {1'b0, 5'(u_drow + {8'd0, dstb})};
                end else begin
                    u_left <= u_left - {17'd0, u_k};
                    u_sp <= u_sp + 5'(u_k * ses);
                    if (u_fl) begin u_dsec <= u_dsec + 37'd1; u_dp <= 6'd0; end
                    else u_dp <= u_dp + 6'(u_k * des);
                end
            end
            // ---- decode (p1 -> p2)
            p2_v <= p1_v;
            if (p1_v) begin p2_k <= p1_k; p2_w <= dec_w; p2_dp <= p1_dp; p2_dsec <= p1_dsec; p2_fl <= p1_fl; end
            // ---- encode + merge (p2) and flush into the write queue
            if (p2_v) begin
                if (p2_fl && !(MUT == 2 && p2_dp + 6'(p2_k) * des != 6'd32)) begin
                    wq_d[wq_t] <= ((db_dirty ? db_dat : 256'd0) & ~mk(put_s)) | put_d;
                    wq_s[wq_t] <= (db_dirty ? db_strb : 32'd0) | put_s; wq_a[wq_t] <= p2_dsec; wq_t <= wq_t + 2'd1;
                    db_dirty <= 1'b0;
                end else if (p2_fl) db_dirty <= 1'b0;                          // MUT 2: the partial sector is lost
                else begin
                    db_dat <= ((db_dirty ? db_dat : 256'd0) & ~mk(put_s)) | put_d;
                    db_strb <= (db_dirty ? db_strb : 32'd0) | put_s; db_dirty <= 1'b1;
                end
            end
            wq_n <= wq_n + {2'd0, p2_v && p2_fl && !(MUT == 2 && p2_dp + 6'(p2_k) * des != 6'd32)} - {2'd0, iss_kw | iss_vw};
            // ---- completion: everything unpacked, the pipe empty, the queue drained and every write acknowledged
            if (busy_f && go_q2 && !f_fault && u_done && r_done && !p1_v && !p2_v && wq_n == 3'd0 && wr_in == 5'd0 &&
                !(iss_kw | iss_vw) && rd_in == 5'd0 && sf_n == 5'd0) begin
                busy_f <= 1'b0; mv_done <= 1'b1;
            end
            if (f_fault && busy_f && k_in == 4'd0 && v_in == 3'd0) busy_f <= 1'b0;
        end
    end
    function automatic [255:0] mk(input [31:0] s);
        integer t; begin mk = 256'd0; for (t = 0; t < 32; t = t + 1) if (s[t]) mk[8*t +: 8] = 8'hFF; end
    endfunction
    // ---- port muxing with the serial engine (it drives the ports while it owns them)
    assign k_req_v = sel_s ? s_kv : f_kv;   assign k_req_we = sel_s ? s_kwe : f_kwe;
    assign k_req_addr = sel_s ? s_ka : f_ka; assign k_req_wdata = sel_s ? s_kd : f_kd;
    assign k_req_wstrb = sel_s ? s_ks : f_ks; assign vmq = sel_s ? s_vmq : f_vmq;
    wire unused_ok = &{1'b0, s_kt, s_krr, s_fence_done};
endmodule
`default_nettype wire
