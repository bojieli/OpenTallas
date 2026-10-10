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
    parameter integer KOUT = 64,          // HBM lane requests in flight (the lane answers in order; >= the lane latency)
    parameter integer SFD = 64            // landing FIFO, source sectors (a power of 2, >= KOUT; a 1R1W macro in the view)
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire          mv_v,
    output wire          mv_rdy,
    input  wire [226:0]  mv,
    output reg           mv_done,
    output reg           mv_fault,
    output reg           mv_src,      // pulse: every source sector of the move has been read and landed (posted
                                      // STORE / KVWB retire here; the VM / HBM source may be overwritten from now on)
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
    input  wire [273:0]  vmr,
    // VM WIDE WRITE PORT lane (hgi-takeover 2026-10-10, coordinator decision): the sector engine writes its VM
    // destination sectors here, one a cycle, never back-pressured, {v, sector 15, wdata 256, word mask 8}; wl_done
    // returns when the write is in the macro (ot_hgi_vm_unit wq / wq_done)
    output reg  [279:0]  wl,
    input  wire          wl_done
);
    // the sector engine's port registers (the serial engine has its own; sel_s picks)
    reg f_kv, f_kwe; reg [36:0] f_ka; reg [255:0] f_kd; reg [31:0] f_ks; reg [337:0] f_vmq;
    reg [1:0] kq_n; reg kq_h, kq_t; reg kq_we [0:1]; reg [36:0] kq_a [0:1]; reg [255:0] kq_d [0:1]; reg [31:0] kq_s [0:1];
    always @* begin f_kv = kq_n != 2'd0; f_kwe = kq_we[kq_h]; f_ka = kq_a[kq_h]; f_kd = kq_d[kq_h]; f_ks = kq_s[kq_h]; end
    assign k_req_tag = 16'h4D56;
    assign k_rsp_rdy = 1'b1;
    // ================================================================ dispatch: sector engine or serial engine
    // registered reset (async assert, release two edges after rst_n): the port reset no longer reaches the D / recovery
    // pins of the whole mover (route 00007e219 IO paths rst_n -> f_vmq / u_ser.i)
    reg [1:0] rq; always @(posedge clk or negedge rst_n) if (!rst_n) rq <= 2'b00; else rq <= {rq[0], 1'b1};
    wire rn = rq[1];
    // registered boundary (submit lint: input -> register <= 16 levels): a command station, pin flops on the lane and
    // VM responses (+1 cycle each), and the lane request issues only from an empty request register (k_req_rdy only
    // clears it)
    reg cv_q; reg [226:0] cm_q;
    reg kr_v, kr_we; reg [255:0] kr_d; reg [273:0] vr_q;
    always @(posedge clk or negedge rn)
        if (!rn) begin kr_v <= 1'b0; vr_q <= 274'd0; end
        else begin kr_v <= k_rsp_v; vr_q <= vmr; end
    always @(posedge clk) begin kr_we <= k_rsp_we; kr_d <= k_rsp_data; end
    wire fast_cmd = (cm_q[92:77] == 16'd1) && (cm_q[185:170] == 16'd1);     // src istride 1 and dst istride 1
    reg  busy_f; reg src_sent;                                                        // the sector engine owns the ports
    reg  sel_s;                                                         // the serial engine owns the ports
    wire s_mv_rdy, s_mv_done, s_mv_fault, s_fence_rdy, s_fence_done;
    wire s_kv, s_kwe; wire [36:0] s_ka; wire [255:0] s_kd; wire [31:0] s_ks; wire [15:0] s_kt; wire s_krr; wire [337:0] s_vmq;
    reg  f_fault;
    assign mv_rdy = !busy_f && !cv_q && !sel_s && s_mv_rdy && !f_fault;
    ot_hgi_dma_mover_serial #(.MUT_RNE(MUT_RNE)) u_ser (.clk(clk), .rst_n(rn), .mv_v(cv_q && !fast_cmd),
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
    reg [1:0]  sl2, dl2;                                    // log2 of the element bytes: every size product is a shift
    reg [23:0] nnb;                                         // row bytes on the source side = nn << sl2
    reg [41:0] sbase, dbase;                                // byte addresses (VM: word x 4)
    // ---- reader state
    // (route 51ae5ce55 TT -212 / -270: r_end = r_row + nn * ses - 1 was a multiply + add into the row compare; now the
    //  current / next row start and last byte are registers, a row change is a register move)
    reg [19:0] r_o; reg [41:0] r_nrow, r_end, r_nend; reg [36:0] r_sec; reg r_done;
    // ---- unpack state
    // (route 51ae5ce55: the unpack decision divided by the element size, (32 - u_sp) / ses and (32 - u_dp) / des, then
    //  multiplied u_k back -- the ses / u_dp -> u_dsec / sf_n / sf_h classes, 28-30 levels.  Now the elements left in the
    //  head source sector (s_room) and in the destination sector (d_room) are registers that count down; the next row's
    //  addresses are precomputed registers)
    reg [19:0] u_o; reg [20:0] u_left; reg [4:0] u_sp; reg [41:0] u_nsrow, u_ndrow;
    reg [36:0] u_dsec; reg [5:0] u_dp; reg u_done; reg [5:0] s_room, d_room;
    // ---- landing FIFO (source sectors in order)
    localparam integer SB = $clog2(SFD);
    reg [255:0] sfd [0:SFD-1]; reg [SB-1:0] sf_h, sf_t; reg [8:0] sf_n;
    // ---- port in-flight accounting: per port a kind FIFO (0 read, 1 write) for the in-order responses
    reg [7:0] k_in; reg [2:0] v_in; reg [255:0] k_kind; reg [7:0] v_kind;    // shift registers of kinds, oldest at [0]
    reg [8:0] rd_in;                                          // source reads in flight (landing room)
    // ---- write queue
    reg [255:0] wq_d [0:7]; reg [31:0] wq_s [0:7]; reg [36:0] wq_a [0:7]; reg [2:0] wq_h, wq_t; reg [3:0] wq_n;
    reg [8:0] wr_in;                                          // writes issued, not acknowledged
    // ---- pipeline registers
    reg        p1_v; reg [3:0] p1_k; reg [255:0] p1_sec; reg [4:0] p1_sp; reg [5:0] p1_dp; reg [36:0] p1_dsec; reg p1_fl;
    // extract (px) and convert (p2) are separate stages; encode (pe) and byte placement (p3) are separate stages
    // (route 51ae5ce55: p2_w / des -> p3_d, 31 levels: the encoders and the variable placement in one cycle)
    reg        px_v; reg [3:0] px_k; reg [255:0] px_r; reg [5:0] px_dp; reg [36:0] px_dsec; reg px_fl;
    reg        p2_v; reg [3:0] p2_k; reg [255:0] p2_w; reg [5:0] p2_dp; reg [36:0] p2_dsec; reg p2_fl;
    reg        pe_v; reg [7:0] pe_lv; reg [255:0] pe_e; reg [5:0] pe_dp; reg [36:0] pe_dsec; reg pe_fl, pe_keep;
    reg        p3_v; reg [255:0] p3_d; reg [31:0] p3_s; reg [36:0] p3_dsec; reg p3_fl, p3_keep;
    reg [255:0] db_dat; reg [31:0] db_strb; reg db_dirty;
    // ---- source sector issue
    wire src_hbm = (ssp == 2'd0), dst_hbm = (dsp == 2'd0);
    // ---- unpack decision (combinational on registered state)
    reg [3:0] u_k; reg u_fl; reg u_pop; reg u_go;
    always @* begin : unp
        reg [5:0] l8, m1; reg lfit;
        l8 = (u_left > 21'd8) ? 6'd8 : {2'd0, u_left[3:0]};          // elements left in the row, at most 8
        m1 = (s_room < d_room) ? s_room : d_room;
        u_k = 4'((l8 < m1) ? l8 : m1);
        lfit = u_left <= 21'({2'd0, u_k});                             // the row ends with this step
        u_go = busy_f && !u_done && go_q3 && sf_n != 9'd0 && wq_room;
        u_fl = ({2'd0, u_k} == d_room) || lfit;                       // the destination sector is full / row end
        u_pop = ({2'd0, u_k} == s_room) || lfit;                      // the source sector is used up / row end
    end
    reg go_q3;                                                         // one more setup edge: the row-end registers settle
    reg go_q2;                                                         // the command fields are settled
    // the write queue (8) must hold the flushes the pipe may still produce (p1, px, p2, pe, p3 + this one)
    wire wq_room = (wq_n + {3'd0, p1_v & p1_fl} + {3'd0, px_v & px_fl} + {3'd0, p2_v & p2_fl} + {3'd0, pe_v & pe_fl} +
                    {3'd0, p3_v & p3_fl}) < 4'd7;
    // ---- extract (p1 -> px): lane j's raw element, right-aligned (word / half / byte at offset sp + j << sl2)
    reg [255:0] ext_r;
    always @* begin
        ext_r = 256'd0;
        for (integer j = 0; j < 8; j = j + 1) begin : xl
            reg [4:0] off; reg [31:0] w;
            off = p1_sp + (5'(j) << sl2);
            w = p1_sec[{off[4:2], 5'd0} +: 32];
            ext_r[32*j +: 32] = (sl2 == 2'd2) ? w : (sl2 == 2'd1) ? {16'd0, off[1] ? w[31:16] : w[15:0]}
                                                             : {24'd0, w[{off[1:0], 3'd0} +: 8]};
        end
    end
    // ---- convert (px -> p2): source format -> binary32 (VM source: the word)
    reg [255:0] dec_w;
    always @* begin
        dec_w = 256'd0;
        for (integer j = 0; j < 8; j = j + 1) begin : dl
            reg [31:0] r; r = px_r[32*j +: 32];
            if (ssp == 2'd1) dec_w[32*j +: 32] = r;
            else case (sf)
                3'd1: dec_w[32*j +: 32] = {r[15:0], 16'd0};
                3'd2: dec_w[32*j +: 32] = e4m3_f(r[7:0]);
                3'd4: dec_w[32*j +: 32] = i8_f(r[7:0]);
                default: dec_w[32*j +: 32] = r;
            endcase
        end
    end
    // ---- encode (p2 -> pe): binary32 -> the destination format, right-aligned per lane
    reg [255:0] enc_e;
    always @* begin
        enc_e = 256'd0;
        for (integer j = 0; j < 8; j = j + 1) begin : en
            reg [31:0] x; x = p2_w[32*j +: 32];
            if (dsp == 2'd1 || df == 3'd0 || df == 3'd5) enc_e[32*j +: 32] = x;
            else if (df == 3'd1) enc_e[32*j +: 32] = {16'd0, to_bf16(x)};
            else enc_e[32*j +: 32] = {24'd0, to_e4m3(x)};
        end
    end
    // ---- place (pe -> p3): lane j at byte dp + j << dl2 of the destination sector
    reg [255:0] put_d; reg [31:0] put_s;
    always @* begin
        put_d = 256'd0; put_s = 32'd0;
        for (integer j = 0; j < 8; j = j + 1) if (pe_lv[j]) begin : el
            reg [5:0] o_; reg [31:0] x;
            o_ = pe_dp + (6'(j) << dl2); x = pe_e[32*j +: 32];
            if (dl2 == 2'd2) begin put_d[{o_[4:0], 3'd0} +: 32] = x; put_s[o_[4:0] +: 4] = 4'hF; end
            else if (dl2 == 2'd1) begin put_d[{o_[4:0], 3'd0} +: 16] = x[15:0]; put_s[o_[4:0] +: 2] = 2'b11; end
            else begin put_d[{o_[4:0], 3'd0} +: 8] = x[7:0]; put_s[o_[4:0]] = 1'b1; end
        end
    end
    // ---- port issue selection
    reg iss_kw, iss_kr, iss_vw, iss_vr;
    always @* begin
        iss_kw = 1'b0; iss_kr = 1'b0; iss_vw = 1'b0; iss_vr = 1'b0;
        if (busy_f && go_q3 && !f_fault) begin
            if (wq_n != 4'd0 && dst_hbm && k_in < 8'(KOUT) && kq_n < 2'd2) iss_kw = 1'b1;
            else if (!r_done && src_hbm && k_in < 8'(KOUT) && kq_n < 2'd2 && ({1'b0, sf_n} + {1'b0, rd_in}) < 10'(SFD)) iss_kr = 1'b1;
            if (wq_n != 4'd0 && !dst_hbm) iss_vw = 1'b1;                      // the wide port: no client slot
            if (!r_done && !src_hbm && v_in < 3'd4 && ({1'b0, sf_n} + {1'b0, rd_in}) < 10'(SFD)) iss_vr = 1'b1;
        end
    end
    // ---- response routing (in order per port)
    wire k_rv = kr_v && busy_f, v_rv = vr_q[273] && busy_f;
    wire k_rd_land = k_rv && !k_kind[0], k_wr_ack = k_rv && k_kind[0];
    wire v_rd_land = v_rv && !v_kind[0], v_wr_ack = v_rv && v_kind[0];
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            busy_f <= 1'b0; sel_s <= 1'b0; go_f <= 1'b0; go_q2 <= 1'b0; f_fault <= 1'b0;
            mv_done <= 1'b0; mv_fault <= 1'b0; fence_done <= 1'b0; f_vmq <= 338'd0; wl <= 280'd0; mv_src <= 1'b0; src_sent <= 1'b0;
            k_in <= 8'd0; v_in <= 3'd0; k_kind <= 256'd0; v_kind <= 8'd0; rd_in <= 9'd0; wr_in <= 9'd0; kq_n <= 2'd0; kq_h <= 1'b0; kq_t <= 1'b0;
            sf_h <= '0; sf_t <= '0; sf_n <= 9'd0; wq_h <= 3'd0; wq_t <= 3'd0; wq_n <= 4'd0; go_q3 <= 1'b0;
            p1_v <= 1'b0; px_v <= 1'b0; p2_v <= 1'b0; pe_v <= 1'b0; p3_v <= 1'b0; db_dirty <= 1'b0; r_done <= 1'b1; u_done <= 1'b1;
        end else begin
            mv_done <= 1'b0; fence_done <= 1'b0; mv_src <= 1'b0;
            if (fence_v && fence_rdy) fence_done <= 1'b1;
            // ---- the serial engine's completion and ports
            if (s_mv_done) begin mv_done <= 1'b1; mv_src <= 1'b1; sel_s <= 1'b0; end   // serial engine: source = done
            if (s_mv_fault) mv_fault <= 1'b1;
            cv_q <= 1'b0;
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
            if (cv_q && !fast_cmd) sel_s <= 1'b1;
            // ---- accept a sector-engine command
            go_f <= 1'b0; go_q2 <= go_f | (go_q2 && busy_f);           // go_q2: the command fields have settled (level while busy)
            go_q3 <= go_q2 && busy_f && !go_f;                         // go_q3: the row registers have settled
            if (cv_q && fast_cmd) begin
                busy_f <= 1'b1; go_f <= 1'b1;
                ssp <= cm_q[1:0]; sf <= cm_q[4:2]; sst <= cm_q[76:45]; dsp <= cm_q[94:93]; df <= cm_q[97:95]; dst <= cm_q[169:138];
                sstb <= (cm_q[1:0] == 2'd1) ? {cm_q[76:45], 2'b00} : {2'd0, cm_q[76:45]};
                dstb <= (cm_q[94:93] == 2'd1) ? {cm_q[169:138], 2'b00} : {2'd0, cm_q[169:138]};
                mm <= cm_q[205:186]; nn <= cm_q[226:206];
                ses <= (cm_q[1:0] == 2'd1) ? 3'd4 : esz(cm_q[4:2]); des <= (cm_q[94:93] == 2'd1) ? 3'd4 : esz(cm_q[97:95]);
                sl2 <= (cm_q[1:0] == 2'd1) ? 2'd2 : l2(esz(cm_q[4:2])); dl2 <= (cm_q[94:93] == 2'd1) ? 2'd2 : l2(esz(cm_q[97:95]));
                nnb <= {3'd0, cm_q[226:206]} << ((cm_q[1:0] == 2'd1) ? 2'd2 : l2(esz(cm_q[4:2])));
                sbase <= (cm_q[1:0] == 2'd1) ? {cm_q[44:5], 2'b00} : {2'd0, cm_q[44:5]};
                dbase <= (cm_q[94:93] == 2'd1) ? {cm_q[137:98], 2'b00} : {2'd0, cm_q[137:98]};
                if ((cm_q[1:0] > 2'd1) || (cm_q[94:93] > 2'd1) || cm_q[4:2] == 3'd3 || cm_q[4:2] == 3'd6 || cm_q[97:95] == 3'd3 ||
                    cm_q[97:95] == 3'd6 || cm_q[97:95] == 3'd4 || cm_q[205:186] == 20'd0 || cm_q[226:206] == 21'd0) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
            end
            if (go_f) src_sent <= 1'b0;
            if (busy_f && go_q3 && !f_fault && r_done && rd_in == 9'd0 && !src_sent) begin mv_src <= 1'b1; src_sent <= 1'b1; end
            if (go_f) begin
                r_o <= 20'd0; r_sec <= sbase[41:5]; r_done <= 1'b0;
                r_nrow <= sbase + {8'd0, sstb}; r_end <= sbase + {18'd0, nnb} - 42'd1;
                u_o <= 20'd0; u_left <= nn; u_sp <= sbase[4:0]; u_nsrow <= sbase + {8'd0, sstb}; u_ndrow <= dbase + {8'd0, dstb};
                u_dsec <= dbase[41:5]; u_dp <= {1'b0, dbase[4:0]}; u_done <= 1'b0; db_dirty <= 1'b0;
                s_room <= room(sbase[4:0], sl2); d_room <= room(dbase[4:0], dl2);
                // natural alignment of every row start (elements are contiguous within a row)
                if ((ses == 3'd4 && (sbase[1:0] != 2'd0 || sstb[1:0] != 2'd0)) || (ses == 3'd2 && (sbase[0] || sstb[0])) ||
                    (des == 3'd4 && (dbase[1:0] != 2'd0 || dstb[1:0] != 2'd0)) || (des == 3'd2 && (dbase[0] || dstb[0]))) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
            end
            if (go_q2 && !go_q3) r_nend <= r_end + {8'd0, sstb};            // the settle edge
            // ---- issue: lane / client requests
            f_vmq[337] <= 1'b0;
            begin : issue
                reg kpush, kkind, vpush, vkind;
                kpush = 1'b0; kkind = 1'b0; vpush = 1'b0; vkind = 1'b0;
                // lane requests enter a 2-entry skid (its head drives k_req; k_req_rdy only pops it)
                if (iss_kw) begin
                    kq_we[kq_t] <= 1'b1; kq_a[kq_t] <= {wq_a[wq_h][31:0], 5'd0}; kq_d[kq_t] <= wq_d[wq_h];
                    kq_s[kq_t] <= wq_s[wq_h]; kpush = 1'b1; kkind = 1'b1;
                end else if (iss_kr) begin
                    kq_we[kq_t] <= 1'b0; kq_a[kq_t] <= {r_sec[31:0], 5'd0}; kpush = 1'b1;
                end
                if (kpush) kq_t <= ~kq_t;
                if (kq_n != 2'd0 && k_req_rdy && !sel_s) kq_h <= ~kq_h;
                kq_n <= kq_n + {1'b0, kpush} - {1'b0, kq_n != 2'd0 && k_req_rdy && !sel_s};
                wl[279] <= 1'b0;
                if (iss_vw) begin : wide
                    reg [7:0] wm; integer t;
                    for (t = 0; t < 8; t = t + 1) wm[t] = &wq_s[wq_h][4*t +: 4];
                    wl <= {1'b1, wq_a[wq_h][14:0], wq_d[wq_h], wm};
                end
                if (iss_vr) begin
                    f_vmq <= {1'b1, 1'b0, r_sec[26:0], 5'd0, 256'd0, 32'd0, 16'h4D52}; vpush = 1'b1;
                end
                // write queue pop
                if (iss_kw || iss_vw) begin wq_h <= wq_h + 3'd1; end
                // reader advance
                if (iss_kr || iss_vr) begin
                    if (r_sec == r_end[41:5]) begin
                        if (r_o + 20'd1 == mm) r_done <= 1'b1;
                        else begin
                            r_o <= r_o + 20'd1; r_sec <= r_nrow[41:5]; r_nrow <= r_nrow + {8'd0, sstb};
                            r_end <= r_nend; r_nend <= r_nend + {8'd0, sstb};
                        end
                    end else r_sec <= r_sec + 37'd1;
                end
                // in-flight accounting (kind shift registers: push at the tail, pop at the head)
                k_in <= k_in + {7'd0, kpush} - {7'd0, k_rv};
                v_in <= v_in + {2'd0, vpush} - {2'd0, v_rv};
                begin : kk
                    reg [255:0] t; t = k_kind;
                    if (k_rv) t = t >> 1;
                    if (kpush) t[k_in - {7'd0, k_rv}] = kkind;
                    k_kind <= t;
                end
                begin : vk
                    reg [7:0] t; t = v_kind;
                    if (v_rv) t = t >> 1;
                    if (vpush) t[v_in - {2'd0, v_rv}] = vkind;
                    v_kind <= t;
                end
                rd_in <= rd_in + {8'd0, iss_kr | iss_vr} - {8'd0, k_rd_land | v_rd_land};
                wr_in <= wr_in + {8'd0, iss_kw | iss_vw} - {8'd0, k_wr_ack | v_wr_ack | (wl_done & busy_f & !dst_hbm)};
            end
            if (k_fault && busy_f) begin f_fault <= 1'b1; mv_fault <= 1'b1; end
            // ---- landing
            begin : land
                reg push_, pop_;
                push_ = k_rd_land || v_rd_land; pop_ = u_go && u_pop;
                if (push_) begin sfd[sf_t] <= k_rd_land ? kr_d : vr_q[255:0]; sf_t <= sf_t + 1'b1; end
                if (pop_) sf_h <= sf_h + 1'b1;
                sf_n <= sf_n + {8'd0, push_} - {8'd0, pop_};
            end
            // ---- unpack (stage U -> p1)
            p1_v <= 1'b0;
            if (u_go) begin
                p1_v <= 1'b1; p1_k <= u_k; p1_sec <= sfd[sf_h]; p1_sp <= u_sp; p1_dp <= u_dp; p1_dsec <= u_dsec;
                p1_fl <= u_fl;
                if (u_left <= 21'({2'd0, u_k})) begin                         // row end: next row (precomputed)
                    if (u_o + 20'd1 == mm) u_done <= 1'b1;
                    u_o <= u_o + 20'd1; u_left <= nn;
                    u_sp <= u_nsrow[4:0]; u_nsrow <= u_nsrow + {8'd0, sstb}; s_room <= room(u_nsrow[4:0], sl2);
                    u_dsec <= u_ndrow[41:5]; u_dp <= {1'b0, u_ndrow[4:0]}; u_ndrow <= u_ndrow + {8'd0, dstb};
                    d_room <= room(u_ndrow[4:0], dl2);
                end else begin
                    u_left <= u_left - {17'd0, u_k};
                    u_sp <= u_sp + (5'(u_k) << sl2);
                    s_room <= u_pop ? (6'd32 >> sl2) : s_room - {2'd0, u_k};
                    if (u_fl) begin u_dsec <= u_dsec + 37'd1; u_dp <= 6'd0; d_room <= 6'd32 >> dl2; end
                    else begin u_dp <= u_dp + (6'(u_k) << dl2); d_room <= d_room - {2'd0, u_k}; end
                end
            end
            // ---- extract (p1 -> px), convert (px -> p2), encode (p2 -> pe), place (pe -> p3), merge (p3)
            px_v <= p1_v;
            if (p1_v) begin px_k <= p1_k; px_r <= ext_r; px_dp <= p1_dp; px_dsec <= p1_dsec; px_fl <= p1_fl; end
            p2_v <= px_v;
            if (px_v) begin p2_k <= px_k; p2_w <= dec_w; p2_dp <= px_dp; p2_dsec <= px_dsec; p2_fl <= px_fl; end
            pe_v <= p2_v;
            if (p2_v) begin
                pe_e <= enc_e; pe_dp <= p2_dp; pe_dsec <= p2_dsec; pe_fl <= p2_fl;
                for (integer q = 0; q < 8; q = q + 1) pe_lv[q] <= q < p2_k;
                pe_keep <= !(MUT == 2 && p2_dp + (6'(p2_k) << dl2) != 6'd32);
            end
            p3_v <= pe_v;
            if (pe_v) begin p3_d <= put_d; p3_s <= put_s; p3_dsec <= pe_dsec; p3_fl <= pe_fl; p3_keep <= pe_keep; end
            if (p3_v) begin
                if (p3_fl && p3_keep) begin
                    wq_d[wq_t] <= ((db_dirty ? db_dat : 256'd0) & ~mk(p3_s)) | p3_d;
                    wq_s[wq_t] <= (db_dirty ? db_strb : 32'd0) | p3_s; wq_a[wq_t] <= p3_dsec; wq_t <= wq_t + 3'd1;
                    db_dirty <= 1'b0;
                end else if (p3_fl) db_dirty <= 1'b0;                          // MUT 2: the partial sector is lost
                else begin
                    db_dat <= ((db_dirty ? db_dat : 256'd0) & ~mk(p3_s)) | p3_d;
                    db_strb <= (db_dirty ? db_strb : 32'd0) | p3_s; db_dirty <= 1'b1;
                end
            end
            wq_n <= wq_n + {3'd0, p3_v && p3_fl && p3_keep} - {3'd0, iss_kw | iss_vw};
            // ---- completion: everything unpacked, the pipe empty, the queue drained and every write acknowledged
            if (busy_f && go_q3 && !f_fault && u_done && r_done && !p1_v && !px_v && !p2_v && !pe_v && !p3_v && wq_n == 4'd0 && wr_in == 9'd0 &&
                !(iss_kw | iss_vw) && rd_in == 9'd0 && sf_n == 9'd0 && kq_n == 2'd0) begin
                busy_f <= 1'b0; mv_done <= 1'b1;
            end
            if (f_fault && busy_f && k_in == 8'd0 && v_in == 3'd0) busy_f <= 1'b0;
        end
    end
    function automatic [1:0] l2(input [2:0] e);
        l2 = (e == 3'd4) ? 2'd2 : (e == 3'd2) ? 2'd1 : 2'd0;
    endfunction
    function automatic [5:0] room(input [4:0] off, input [1:0] lg);   // elements from byte off to the sector end
        room = (6'd32 - {1'b0, off}) >> lg;
    endfunction
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
