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
//   R  reader (hgi-1010/c 2026-10-10, HC weight prefetch: lead + hbm-phys svc_dma_hc_sizing): a row is cut into CHUNKS of
//      up to 8 source sectors ending on an 8-sector boundary or the row end.  HBM source: a chunk is ONE native burst on the
//      kport read lane of its stack (r_req_*, lanes 0..3 = stacks 0..3, len 1..8, tag = its first landing slot; the lane
//      answers in order, up to the kport's NO requests outstanding a lane), so every stack the move touches streams at the
//      svc's in-flight limit.  VM source: a chunk is one sector, one VM packet read (4 in flight, in order).  Each chunk
//      allocates its landing slots at issue and pushes a descriptor {elements, first byte, destination sector / byte,
//      row end} into the chunk FIFO (64), in issue order.
//      STRIPE4 (source HBM, base bits [39:37] = 1, spec 6.4): row o reads stack (base[36:35] + o) mod 4 at the local byte
//      address base[34:0] + o x stride: four reader slots (slot k = rows k, k + 4, ..., all on one stack) issue chunks in
//      rotation, so one move keeps the four stacks busy (an HC weight row = 4 quarter rows, one a stack, stride 0).  Rows
//      and their destinations must start 32 B aligned (whole destination sectors a chunk: chunks of different rows never
//      share a destination sector), the destination must be VM; else the move faults.  Other codes than 0 / 1 fault.
//   L  landing: one response sector a cycle (a registered rotating grant over the four read lanes, rsp_rdy) is written
//      into its slot (tag + beat) of the 256-sector landing RAM (ot_sram_1r1w_256x256, slot valid bits in flops);
//   U  unpack (registered): the head chunk's descriptor, up to 8 elements a cycle from the head slot (when it has
//      landed) -- as many as are left in that sector, in the chunk and in the destination sector -- with each lane's
//      destination byte offset and a flush mark at a destination sector end / row end;
//   D  decode (registered): source format -> binary32 (or the raw word on a VM source);
//   E  encode + merge (registered): -> the destination format, merged into the destination sector buffer with byte
//      strobes; a flush pushes the sector into a 4-deep write queue;
//   W  writer: the write queue drains first on its port (VM client / HBM lane), reads use the rest.
// Rate: one destination sector a cycle in the pipe (FP32 / U32 source: 32 B a cycle); an HBM source stack streams at the
// kport's in-flight limit (NO x 4 sectors a round trip), a STRIPE4 move at four times that.  Exactness = the serial
// engine's arithmetic, per element.
// MUT (bench): 1 BF16 store truncates (no RNE; both engines); 2 the sector engine drops a row's last partial sector;
//   3 a burst's beats all land in its first slot (beat ignored); 4 STRIPE4 reads / writes every row on stack base[36:35].
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_mover #(
    parameter integer MUT_RNE = 0,        // mutant: BF16 store truncates (no round to nearest even)
    parameter integer MUT = 0,
    parameter integer KOUT = 64,          // HBM writes in flight (the per-stack lanes)
    parameter integer VR2 = 0             // 1: VM-source sectors on the VM's DMA wide READ group (vr2q / vr2r), else the packet client
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
    // HBM lanes (hgi-1010/c): kport lane of stack l.  Reads: bursts {addr 37, len 1..8, tag 16 = the first landing slot},
    // answered in request order (rsp_tag = the request's tag, rsp_last on its last sector); rsp_rdy = this lane's
    // registered landing grant.  Writes (STORE): one full sector a request, many outstanding; rsp_we = its acknowledgement
    // (always accepted)
    output wire [3:0]     r_req_v,
    input  wire [3:0]     r_req_rdy,
    output wire [4*37-1:0] r_req_addr,
    output wire [4*4-1:0] r_req_len,
    output wire [4*16-1:0] r_req_tag,
    output wire [3:0]     r_req_we,                     // a write (STORE to HBM): one full sector, acknowledged by rsp_we
    output wire [4*256-1:0] r_req_wdata,
    output wire [4*32-1:0] r_req_wstrb,
    input  wire [3:0]     r_rsp_v,
    input  wire [3:0]     r_rsp_we,
    output wire [3:0]     r_rsp_rdy,
    input  wire [4*16-1:0] r_rsp_tag,
    input  wire [3:0]     r_rsp_last,
    input  wire [4*256-1:0] r_rsp_data,
    // VM wide READ group 2 = DMA (VR2 = 1; b's ot_hgi_vm_die contract): up {c_req, 32 lanes x {v, sector 15}}; down
    // {c_gnt, credits 32, 32 lanes x {v, data 256}}; lane b serves sectors s[4:0] = b, in order a lane, LQ credits a lane;
    // c_req is held until every credit is home (burst ownership).  The mover keeps one sector in flight a lane.
    output reg  [512:0]  vr2q,
    input  wire [8256:0] vr2r,
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
    wire f_kv = 1'b0, f_kwe = 1'b0; wire [36:0] f_ka = 37'd0; wire [255:0] f_kd = 256'd0; wire [31:0] f_ks = 32'd0; reg [337:0] f_vmq;
    // hgi-1010/c: the sector engine's HBM reads and writes use the per-stack lanes (r_*); kport lane 2 is the serial engine's
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
    reg wld_q; always @(posedge clk) wld_q <= wl_done;     // wide-port done pin flop (hgi-1010/c: wl_done -> wr_in was 17 levels)
    always @(posedge clk or negedge rn)
        if (!rn) begin kr_v <= 1'b0; vr_q <= 274'd0; end
        else begin kr_v <= k_rsp_v; vr_q <= vmr; end
    always @(posedge clk) begin kr_we <= k_rsp_we; kr_d <= k_rsp_data; end
    wire fast_cmd = (cm_q[92:77] == 16'd1) && (cm_q[185:170] == 16'd1);     // src istride 1 and dst istride 1
    reg  busy_f; reg src_sent;
    wire ko_ld;                                                         // the lane output register takes a request                                                        // the sector engine owns the ports
    reg  sel_s;                                                         // the serial engine owns the ports
    wire s_mv_rdy, s_mv_done, s_mv_fault, s_fence_rdy, s_fence_done;
    wire s_kv, s_kwe; wire [36:0] s_ka; wire [255:0] s_kd; wire [31:0] s_ks; wire [15:0] s_kt; wire s_krr; wire [337:0] s_vmq;
    reg  f_fault;
    assign mv_rdy = !busy_f && !cv_q && !sel_s && s_mv_rdy && !f_fault;
    ot_hgi_dma_mover_serial #(.MUT_RNE(MUT_RNE)) u_ser (.clk(clk), .rst_n(rn), .mv_v(cv_q && !fast_cmd && cm_q[94:93] != 2'd0),
        .mv_rdy(s_mv_rdy), .mv(cm_q), .mv_done(s_mv_done), .mv_fault(s_mv_fault), .fence_v(1'b0), .fence_rdy(s_fence_rdy),
        .fence_done(s_fence_done), .k_req_v(s_kv), .k_req_rdy(ko_ld && sel_s), .k_req_we(s_kwe), .k_req_addr(s_ka),
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
    // ---- reader: up to four slots (STRIPE4: slot k = rows k, k + 4, ...; else slot 0 = every row)
    reg        stp, stpd;                                   // STRIPE4 source / destination
    reg [1:0]  s0, d0;                                      // STRIPE4: row 0's source / destination stack
    reg [41:0] sstw, dstw;                                  // a slot's row step (STRIPE4: 4 strides)
    reg [3:0]  ract;                                        // slot active (rows left to issue)
    reg [19:0] ro [0:3];                                    // slot's row index
    reg [41:0] rsa [0:3], rnsa [0:3];                       // next chunk's source byte (STRIPE4: stack-local), next row's start
    reg [41:0] rdd [0:3], rndd [0:3];                       // next chunk's destination byte, next row's start
    reg [23:0] rrl [0:3];                                   // source bytes left in the slot's row
    reg [1:0]  rrr;                                         // rotation
    wire       r_done = ract == 4'd0;                       // every chunk issued
    // ---- read lanes (one a stack): request registers, landing grant, beat counters
    reg [3:0] lq_v; reg [36:0] lq_a [0:3]; reg [3:0] lq_n [0:3]; reg [7:0] lq_t [0:3];
    reg [3:0] lq_we; reg [255:0] lq_d [0:3]; reg [31:0] lq_s [0:3];
    wire [1:0] w_l = wq_a[wq_h][31:30];                     // the write queue head's stack (its lane)
    // ---- VM read group (VR2): per lane a sector in flight, its landing slot, the held response, the credits
    localparam integer GLQ = 32;
    reg [31:0] g_busy, g_hv; reg [7:0] g_slot [0:31]; reg [255:0] g_d [0:31]; reg [5:0] g_cr [0:31]; reg [4:0] g_rr;
    // pin flops (registered boundary: route lint 98f8152b3 counted 96 levels from c_gnt through the reader issue)
    reg g_gnt; reg [31:0] g_crp;
    always @(posedge clk or negedge rn) if (!rn) begin g_gnt <= 1'b0; g_crp <= 32'd0; end
                                        else begin g_gnt <= vr2r[8256]; g_crp <= vr2r[8255:8224]; end
    reg g_dv; reg [4:0] g_di;                               // the held response drained into the landing RAM this cycle
    always @* begin g_dv = 1'b0; g_di = 5'd0;
        for (integer t = 31; t >= 0; t = t - 1) if (g_hv[5'(g_rr + 5'(t))]) begin g_dv = 1'b1; g_di = 5'(g_rr + 5'(t)); end end
    reg g_home; always @* begin g_home = 1'b1; for (integer b = 0; b < 32; b = b + 1) if (g_cr[b] != 6'(GLQ)) g_home = 1'b0; end
    reg [3:0] lg; reg [1:0] lgi; reg [2:0] lbc [0:3];
    // ---- chunk FIFO (issue order) and the staged head descriptor {slot 2, rend, dp 6, dsec 37, sp 5, elements 9}
    localparam integer CF = 64;
    reg [59:0] cf [0:CF-1]; reg [5:0] cf_h, cf_t; reg [6:0] cf_n; reg cd_v; reg [59:0] cd;   // + {slot 2} at [59:58]
    // ---- unpack state (the current chunk)
    // (route 51ae5ce55: the elements left in the head source sector (s_room) and in the destination sector (d_room) are
    //  registers that count down)
    reg u_cv; reg [8:0] u_left; reg [4:0] u_sp; reg [36:0] u_dsec; reg [5:0] u_dp; reg u_rend; reg [5:0] s_room, d_room;
    // ---- landing RAM (slots allocated at issue in order, filled in any order, consumed in order)
    localparam integer SFD = 256;
    localparam integer SB = 8;
    reg [SB-1:0] sf_h, sf_a, v_ptr; reg [8:0] sf_n; reg [SFD-1:0] lv;
    reg lw_v; reg [SB-1:0] lw_a; reg [255:0] lw_d;          // landing write stage
    wire [255:0] lr_d;                                      // the landing RAM's read register (PR stage)
    // ---- port in-flight accounting
    reg [7:0] k_in; reg [2:0] v_in; reg [7:0] v_kind;      // lane 2 (writes) / VM client (reads), kinds oldest at [0]
    reg [8:0] rd_in;                                        // source sectors issued, not landed
    // ---- write queue
    reg [255:0] wq_d [0:15]; reg [31:0] wq_s [0:15]; reg [36:0] wq_a [0:15]; reg [3:0] wq_h, wq_t; reg [4:0] wq_n;   // 16: the 8-stage pipe
    reg [8:0] wr_in;                                          // writes issued, not acknowledged
    // ---- pipeline registers
    // hgi-1010/c (route f628d5015: sf_h -> p1_sec, the 64-entry landing read under the unpack enable, 18 levels): p1 keeps
    // the slot address, the PR stage reads the slot from that register (+1 cycle); the reader stops 2 slots short of
    // full, so a popped slot is not rewritten before PR has read it
    reg        p1_v; reg [3:0] p1_k; reg [SB-1:0] p1_h; reg [4:0] p1_sp; reg [5:0] p1_dp; reg [36:0] p1_dsec; reg p1_fl;
    reg        pr_v; reg [3:0] pr_k; wire [255:0] p1_sec = lr_d; reg [4:0] pr_sp; reg [5:0] pr_dp; reg [36:0] pr_dsec; reg pr_fl;
    // extract (px) and convert (p2) are separate stages; encode (pe) and byte placement (p3) are separate stages
    // (route 51ae5ce55: p2_w / des -> p3_d, 31 levels: the encoders and the variable placement in one cycle)
    reg        px_v; reg [3:0] px_k; reg [255:0] px_r; reg [5:0] px_dp; reg [36:0] px_dsec; reg px_fl;
    reg        p2_v; reg [3:0] p2_k; reg [255:0] p2_w; reg [5:0] p2_dp; reg [36:0] p2_dsec; reg p2_fl;
    reg        pe_v; reg [7:0] pe_lv; reg [255:0] pe_e; reg [5:0] pe_dp; reg [36:0] pe_dsec; reg pe_fl, pe_keep;
    reg        p3_v; reg [255:0] p3_d; reg [31:0] p3_s; reg [36:0] p3_dsec; reg p3_fl, p3_keep;
    // hgi-1010/c (route bf6565982 TT -107 / -168, SS -570: dl2 / pe_dp -> p3_d, 23-25 levels = per-element variable
    // placement): PACK (pe -> pk, registered: the k encoded elements contiguous from byte 0, by dl2) then SHIFT (pk -> p3:
    // one 32-byte barrel shift by pe_dp and the byte mask with it).  +1 cycle in the pipe.
    reg        pk_v; reg [255:0] pk_d; reg [31:0] pk_s; reg [5:0] pk_dp; reg [36:0] pk_dsec; reg pk_fl, pk_keep;
    reg [255:0] db_dat [0:3]; reg [31:0] db_strb [0:3]; reg [3:0] db_dirty;   // a merge buffer a reader slot (rows interleave)
    reg [1:0] p1_sl, pr_sl, px_sl, p2_sl, pa_sl, pe_sl, pk_sl, p3_sl, u_sl;
    // ---- source sector issue
    wire src_hbm = (ssp == 2'd0), dst_hbm = (dsp == 2'd0);
    // ---- unpack decision (combinational on registered state)
    reg [3:0] u_k; reg u_fl; reg u_pop; reg u_go; reg u_end;
    always @* begin : unp
        reg [5:0] l8, m1;
        l8 = (u_left > 9'd8) ? 6'd8 : {2'd0, u_left[3:0]};            // elements left in the chunk, at most 8
        m1 = (s_room < d_room) ? s_room : d_room;
        u_k = 4'((l8 < m1) ? l8 : m1);
        u_end = u_left <= 9'({5'd0, u_k});                             // the chunk ends with this step
        u_go = busy_f && u_cv && go_q3 && lv[sf_h] && wq_room;
        u_fl = ({2'd0, u_k} == d_room) || (u_end && u_rend);          // the destination sector is full / row end
        u_pop = ({2'd0, u_k} == s_room) || u_end;                     // the source sector is used up / chunk end
    end
    // ---- reader: each slot's next chunk (combinational on registered slot state)
    reg [3:0] c_ok; reg [36:0] c_ea [0:3]; reg [3:0] c_ns [0:3]; reg [8:0] c_by [0:3]; reg [3:0] c_rend; reg [3:0] c_bad;
    reg [36:0] c_ds [0:3];                                  // the chunk's first destination sector (STRIPE4: its stack)
    always @* begin : chk
        for (integer k = 0; k < 4; k = k + 1) begin : ck
            reg [3:0] lm; reg [8:0] bav; reg [1:0] st;
            lm = src_hbm ? (4'd8 - {1'b0, rsa[k][7:5]}) : 4'd1;       // sectors to the 8-sector boundary (VM: one)
            bav = {lm, 5'd0} - {4'd0, rsa[k][4:0]};
            c_by[k] = ({15'd0, bav} < rrl[k]) ? bav : rrl[k][8:0];
            c_rend[k] = {15'd0, bav} >= rrl[k];
            c_ns[k] = 4'(({4'd0, rsa[k][4:0]} + c_by[k] + 9'd31) >> 5);
            st = (MUT == 4) ? s0 : s0 + 2'(k);
            c_ea[k] = stp ? {st, rsa[k][34:0]} : rsa[k][36:0];
            c_bad[k] = (stp && rsa[k][41:35] != 7'd0) || (stpd && rdd[k][41:35] != 7'd0);   // STRIPE4: beyond the stack-local space
            c_ds[k] = stpd ? {5'd0, (MUT == 4) ? d0 : 2'(d0 + 2'(k)), rdd[k][34:5]} : rdd[k][41:5];
            c_ok[k] = ract[k] && (src_hbm ? !lq_v[c_ea[k][36:35]] && !(iss_kw && w_l == c_ea[k][36:35]) :
                                  (VR2 != 0) ? g_gnt && !g_busy[rsa[k][9:5]] && g_cr[rsa[k][9:5]] != 6'd0 : v_in < 3'd4);
        end
    end
    reg r_go; reg [1:0] r_k;
    always @* begin : rpick
        r_go = 1'b0; r_k = 2'd0;
        for (integer t = 3; t >= 0; t = t - 1) if (c_ok[2'(rrr + 2'(t))]) begin r_go = 1'b1; r_k = 2'(rrr + 2'(t)); end
        r_go = r_go && busy_f && go_q4 && !f_fault && sf_n <= 9'(SFD - 10) && cf_n < 7'(CF - 2);
    end
    reg go_q3;                                                         // one more setup edge: the row-end registers settle
    reg go_q4;                                                         // the reader slots are set up
    reg go_q2;                                                         // the command fields are settled
    // the write queue (16) must hold the flushes the pipe may still produce (p1, px, p2, pe, p3 + this one)
    // slots reserved = queued + flushes in the pipe, kept as a register (a popcount over the 8 stages sat in u_go)
    reg [4:0] wq_res;
    wire wq_room = wq_res < 5'd15;
    // ---- extract (p1 -> px): lane j's raw element, right-aligned (word / half / byte at offset sp + j << sl2)
    reg [255:0] ext_r;
    always @* begin
        ext_r = 256'd0;
        for (integer j = 0; j < 8; j = j + 1) begin : xl
            reg [4:0] off; reg [31:0] w;
            off = pr_sp + (5'(j) << sl2);
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
    // ---- encode, two stages (hgi-1010/c, route f628d5015: p2_w -> pe_e 20 levels = E4M3 variable shift + sticky + round +
    //      code assembly in one edge).  ENC A (p2 -> pa): BF16 complete (one 32-bit add); E4M3 to the pre-round quotient,
    //      its round-up bit and the exponent class.  ENC B (pa -> pe): E4M3 round add + code.  +1 cycle in the pipe.
    reg [255:0] enc_a; reg [8*25-1:0] ea_q; reg [7:0] ea_inc, ea_big, ea_sat, ea_sign; reg [8*8-1:0] ea_ex;
    always @* begin
        enc_a = 256'd0; ea_q = '0; ea_inc = 8'd0; ea_big = 8'd0; ea_sat = 8'd0; ea_sign = 8'd0; ea_ex = '0;
        for (integer j = 0; j < 8; j = j + 1) begin : en
            reg [31:0] x; reg [7:0] ex; reg [23:0] mant; integer sh; reg [24:0] q;
            x = p2_w[32*j +: 32];
            if (dsp == 2'd1 || df == 3'd0 || df == 3'd5) enc_a[32*j +: 32] = x;
            else if (df == 3'd1) enc_a[32*j +: 32] = {16'd0, to_bf16(x)};
            else begin
                ex = x[30:23]; ea_ex[8*j +: 8] = ex; ea_sign[j] = x[31];
                ea_sat[j] = (ex == 8'hFF) || (ex >= 8'd136);
                ea_big[j] = ex >= 8'd121;
                mant = (ex == 8'd0) ? 24'd0 : {1'b1, x[22:0]};
                sh = (ex >= 8'd121) ? 20 : (20 + 121 - ex);
                if (sh > 24) q = 25'd0;
                else begin
                    q = {1'b0, mant} >> sh;
                    ea_inc[j] = sh > 0 && mant[sh - 1] && ((mant & ((24'd1 << (sh - 1)) - 24'd1)) != 0 || q[0]);
                end
                ea_q[25*j +: 25] = q;
            end
        end
    end
    reg        pa_v; reg [3:0] pa_k; reg [255:0] pa_e; reg [8*25-1:0] pa_q; reg [7:0] pa_inc, pa_big, pa_sat, pa_sign;
    reg [8*8-1:0] pa_ex; reg [5:0] pa_dp; reg [36:0] pa_dsec; reg pa_fl, pa_e4;
    reg [255:0] enc_e;
    always @* begin
        enc_e = pa_e;
        if (pa_e4) for (integer j = 0; j < 8; j = j + 1) begin : eb
            reg [24:0] q; reg [7:0] code; reg [4:0] e4; reg [3:0] mq;
            q = pa_q[25*j +: 25] + {24'd0, pa_inc[j]};
            if (pa_big[j]) begin
                e4 = 5'(pa_ex[8*j +: 8] - 8'd120); mq = q[4] ? 4'd8 : q[3:0];
                if (q[4]) e4 = e4 + 5'd1;
                code = (e4 > 5'd15) ? 8'h7F : {e4[3:0], mq[2:0]};
            end else code = {1'b0, 4'd0, q[2:0]} + (q[3] ? 8'd8 : 8'd0);
            if (code > 8'h7E) code = 8'h7E;
            enc_e[32*j +: 32] = {24'd0, pa_sat[j] ? {pa_sign[j], 7'h7E} : (code == 8'd0) ? 8'd0 : {pa_sign[j], code[6:0]}};
        end
    end
    // ---- place (pe -> p3): lane j at byte dp + j << dl2 of the destination sector
    // pack: element j of the k at byte j << dl2 (contiguous from byte 0)
    reg [255:0] pack_d; reg [31:0] pack_s;
    always @* begin
        pack_d = 256'd0; pack_s = 32'd0;
        for (integer j = 0; j < 8; j = j + 1) if (pe_lv[j]) begin
            if (dl2 == 2'd2) begin pack_d[32*j +: 32] = pe_e[32*j +: 32]; pack_s[4*j +: 4] = 4'hF; end
            else if (dl2 == 2'd1) begin pack_d[16*j +: 16] = pe_e[32*j +: 16]; pack_s[2*j +: 2] = 2'b11; end
            else begin pack_d[8*j +: 8] = pe_e[32*j +: 8]; pack_s[j] = 1'b1; end
        end
    end
    // shift: the packed elements to the destination byte offset (a run never crosses the sector: d_room bounds k)
    wire [255:0] put_d = pk_d << {pk_dp[4:0], 3'd0};
    wire [31:0]  put_s = pk_s << pk_dp[4:0];
    // ---- port issue selection
    reg iss_kw, iss_kr, iss_vw, iss_vr;
    always @* begin
        iss_kw = 1'b0; iss_kr = 1'b0; iss_vw = 1'b0; iss_vr = 1'b0;
        if (busy_f && go_q3 && !f_fault) begin
            if (wq_n != 5'd0 && dst_hbm && !lq_v[w_l] && wr_in < 9'(KOUT)) iss_kw = 1'b1;   // a full sector to its stack's lane
            if (wq_n != 5'd0 && !dst_hbm) iss_vw = 1'b1;                      // the wide port: no client slot
        end
        iss_vr = r_go && !src_hbm && VR2 == 0; iss_kr = r_go && src_hbm;
    end
    // ---- response routing (in order per port)
    wire k_rv = kr_v && busy_f, v_rv = vr_q[273] && busy_f;
    wire k_wr_ack = k_rv;                                               // lane 2 carries the sector engine's writes only
    wire v_rd_land = v_rv && !v_kind[0], v_wr_ack = v_rv && v_kind[0];
    // ---- read lanes: requests, the registered landing grant (one sector a cycle), the landing RAM
    wire [3:0] l_take = r_rsp_v & lg & ~r_rsp_we;               // read sectors on the landing grant
    wire [3:0] w_ack = r_rsp_v & r_rsp_we & l_wo;                // write acknowledgements (taken on a lane with writes in flight)
    genvar gl;
    for (gl = 0; gl < 4; gl = gl + 1) begin : g_rl
        assign r_req_v[gl] = lq_v[gl]; assign r_req_addr[gl*37 +: 37] = lq_a[gl]; assign r_req_len[gl*4 +: 4] = lq_n[gl];
        assign r_req_tag[gl*16 +: 16] = {8'h52, lq_t[gl]};
        assign r_req_we[gl] = lq_we[gl]; assign r_req_wdata[gl*256 +: 256] = lq_d[gl]; assign r_req_wstrb[gl*32 +: 32] = lq_s[gl];
    end
    reg [3:0] l_wo;                                        // lanes with writes in flight (their responses are all write acks)
    reg [5:0] l_wn [0:3];
    reg [3:0] w_acc_q, w_ack_q;                            // write accepted / acknowledged a lane (pin flops of the handshakes)
    always @* for (integer l = 0; l < 4; l = l + 1) l_wo[l] = l_wn[l] != 6'd0 || w_acc_q[l];
    assign r_rsp_rdy = lg | l_wo;
    // the taken sector is registered first (the grant is one-hot: an AND-OR pick), its slot computed from the register
    // (registered boundary: r_rsp_v -> lt_i -> tag[lt_i] + beat -> lw_a was 49 levels)
    reg lt_v; reg [7:0] lt_tag; reg [2:0] lt_bt; reg [255:0] lt_d;
    always @(posedge clk) begin : ltk
        reg [7:0] tg; reg [2:0] bt; reg [255:0] dd;
        tg = 8'd0; bt = 3'd0; dd = 256'd0;
        for (integer l = 0; l < 4; l = l + 1) if (l_take[l]) begin
            tg = tg | r_rsp_tag[l*16 +: 8]; bt = bt | lbc[l]; dd = dd | r_rsp_data[l*256 +: 256];
        end
        lt_tag <= tg; lt_bt <= bt; lt_d <= dd;
    end
    always @(posedge clk or negedge rn) if (!rn) lt_v <= 1'b0; else lt_v <= |l_take;
    ot_sram_1r1w_256x256_m2_r2c2 u_land (.clk(clk), .r_ce_in(p1_v), .r_addr_in(p1_h), .rd_out(lr_d),
        .w_ce_in(lw_v), .w_addr_in(lw_a), .wd_in(lw_d), .w_mask_in({256{1'b1}}),
        .rr_en(2'b00), .rr_addr(14'd0), .cr_en(2'b00), .cr_sel(16'd0));
    always @(posedge clk) begin : lwd
        lw_a <= lt_v ? lt_tag + ((MUT == 3) ? 8'd0 : {5'd0, lt_bt}) : (VR2 != 0) ? g_slot[g_di] : v_ptr;
        lw_d <= lt_v ? lt_d : (VR2 != 0) ? g_d[g_di] : vr_q[255:0];
        for (integer b = 0; b < 32; b = b + 1) if (vr2r[b*257 + 256]) g_d[b] <= vr2r[b*257 +: 256];   // the lane's response (pin flop)
    end
    always @(posedge clk or negedge rn) begin
        if (!rn) begin
            busy_f <= 1'b0; sel_s <= 1'b0; go_f <= 1'b0; go_q2 <= 1'b0; f_fault <= 1'b0;
            mv_done <= 1'b0; mv_fault <= 1'b0; fence_done <= 1'b0; f_vmq <= 338'd0; wl <= 280'd0; mv_src <= 1'b0; src_sent <= 1'b0;
            k_in <= 8'd0; v_in <= 3'd0; v_kind <= 8'd0; rd_in <= 9'd0; wr_in <= 9'd0;
            sf_h <= '0; sf_a <= '0; v_ptr <= '0; sf_n <= 9'd0; lv <= '0; lw_v <= 1'b0; lq_v <= 4'd0; lg <= 4'd0; lgi <= 2'd0; ract <= 4'd0; rrr <= 2'd0;
            cf_h <= 6'd0; cf_t <= 6'd0; cf_n <= 7'd0; cd_v <= 1'b0; u_cv <= 1'b0; go_q4 <= 1'b0; stp <= 1'b0; stpd <= 1'b0;
            g_busy <= 32'd0; g_hv <= 32'd0; g_rr <= 5'd0; vr2q <= '0; for (integer b = 0; b < 32; b = b + 1) g_cr[b] <= 6'(GLQ);
            w_acc_q <= 4'd0; w_ack_q <= 4'd0; for (integer l = 0; l < 4; l = l + 1) l_wn[l] <= 6'd0;
            for (integer l = 0; l < 4; l = l + 1) lbc[l] <= 3'd0;
            wq_h <= 4'd0; wq_t <= 4'd0; wq_n <= 5'd0; wq_res <= 5'd0; go_q3 <= 1'b0;
            p1_v <= 1'b0; pr_v <= 1'b0; px_v <= 1'b0; p2_v <= 1'b0; pa_v <= 1'b0; pe_v <= 1'b0; pk_v <= 1'b0; p3_v <= 1'b0; db_dirty <= 4'd0;
        end else begin
            mv_done <= 1'b0; fence_done <= 1'b0; mv_src <= 1'b0;
            if (fence_v && fence_rdy) fence_done <= 1'b1;
            // ---- the serial engine's completion and ports
            if (s_mv_done) begin mv_done <= 1'b1; mv_src <= 1'b1; sel_s <= 1'b0; end   // serial engine: source = done
            if (s_mv_fault) mv_fault <= 1'b1;
            cv_q <= 1'b0;
            if (mv_v && mv_rdy) begin cv_q <= 1'b1; cm_q <= mv; end
            if (cv_q && !fast_cmd && cm_q[94:93] == 2'd0) begin mv_fault <= 1'b1; f_fault <= 1'b1; end   // strided HBM writes: partial sectors
            else if (cv_q && !fast_cmd) sel_s <= 1'b1;
            // ---- accept a sector-engine command
            go_f <= 1'b0; go_q2 <= go_f | (go_q2 && busy_f);           // go_q2: the command fields have settled (level while busy)
            go_q3 <= go_q2 && busy_f && !go_f;                         // go_q3: the row registers have settled
            go_q4 <= go_q3 && busy_f && !go_f;                         // go_q4: the reader slots' next-row registers have settled
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
                    cm_q[97:95] == 3'd6 || cm_q[97:95] == 3'd4 || cm_q[205:186] == 20'd0 || cm_q[226:206] == 21'd0 ||
                    (cm_q[1:0] == 2'd0 && cm_q[44:42] > 3'd1) ||                       // HBM source: stripe code 0 / 1 only
                    (cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1 &&                       // STRIPE4 source: 32 B row starts, VM destination
                     (cm_q[9:5] != 5'd0 || cm_q[49:45] != 5'd0 || cm_q[94:93] != 2'd1 || cm_q[100:98] != 3'd0 || cm_q[140:138] != 3'd0)) ||
                    (cm_q[94:93] == 2'd0 && cm_q[137:135] > 3'd1) ||                   // HBM destination: stripe code 0 / 1 only
                    (cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1 && cm_q[1:0] == 2'd0) ||   // STRIPE4 destination: VM source
                    // HBM destination (STORE): whole sectors only (the kport writes full sectors): row start, stride and row
                    // bytes multiples of 32
                    (cm_q[94:93] == 2'd0 && (cm_q[102:98] != 5'd0 || cm_q[142:138] != 5'd0 ||
                     ((cm_q[226:206] << l2(esz(cm_q[97:95]))) & 21'h1F) != 21'd0))) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
                // STRIPE4: the base is stack-local (bits [34:0]), row 0's stack is base[36:35]
                stp <= cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1; s0 <= cm_q[41:40];
                if (cm_q[1:0] == 2'd0 && cm_q[44:42] == 3'd1) sbase <= {7'd0, cm_q[39:5]};
                stpd <= cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1; d0 <= cm_q[134:133];
                if (cm_q[94:93] == 2'd0 && cm_q[137:135] == 3'd1) dbase <= {7'd0, cm_q[132:98]};
            end
            if (go_f) src_sent <= 1'b0;
            if (busy_f && go_q4 && !f_fault && r_done && rd_in == 9'd0 && !src_sent) begin mv_src <= 1'b1; src_sent <= 1'b1; end
            if (go_f) begin
                // reader slots: slot k starts at row k (STRIPE4: rows k, k + 4, ...; else slot 0 takes every row)
                db_dirty <= 4'd0; u_cv <= 1'b0; rrr <= 2'd0; v_ptr <= sf_a;
                sstw <= (stp || stpd) ? {6'd0, sstb, 2'b00} : {8'd0, sstb}; dstw <= (stp || stpd) ? {6'd0, dstb, 2'b00} : {8'd0, dstb};
                rsa[0] <= sbase; rsa[1] <= sbase + {8'd0, sstb}; rsa[2] <= sbase + {7'd0, sstb, 1'b0};
                rsa[3] <= sbase + {7'd0, sstb, 1'b0} + {8'd0, sstb};
                rdd[0] <= dbase; rdd[1] <= dbase + {8'd0, dstb}; rdd[2] <= dbase + {7'd0, dstb, 1'b0};
                rdd[3] <= dbase + {7'd0, dstb, 1'b0} + {8'd0, dstb};
                for (integer k = 0; k < 4; k = k + 1) begin
                    ro[k] <= 20'(k); rrl[k] <= nnb;
                    ract[k] <= (k == 0 || stp || stpd) && 20'(k) < mm;
                end
                // natural alignment of every row start (elements are contiguous within a row)
                if ((ses == 3'd4 && (sbase[1:0] != 2'd0 || sstb[1:0] != 2'd0)) || (ses == 3'd2 && (sbase[0] || sstb[0])) ||
                    (des == 3'd4 && (dbase[1:0] != 2'd0 || dstb[1:0] != 2'd0)) || (des == 3'd2 && (dbase[0] || dstb[0]))) begin
                    f_fault <= 1'b1; mv_fault <= 1'b1; busy_f <= 1'b0;
                end
            end
            if (go_q2 && !go_q3) for (integer k = 0; k < 4; k = k + 1) begin   // the settle edge: each slot's next row
                rnsa[k] <= rsa[k] + sstw; rndd[k] <= rdd[k] + dstw;
            end
            // ---- issue: lane / client requests
            f_vmq[337] <= 1'b0;
            begin : issue
                reg kpush, kkind, vpush, vkind;
                kpush = 1'b0; kkind = 1'b0; vpush = 1'b0; vkind = 1'b0;
                // lane requests enter a 2-entry skid (its head drives k_req; k_req_rdy only pops it)
                if (iss_kw) begin
                    lq_v[w_l] <= 1'b1; lq_we[w_l] <= 1'b1; lq_a[w_l] <= {wq_a[wq_h][31:0], 5'd0}; lq_n[w_l] <= 4'd1;
                    lq_d[w_l] <= wq_d[wq_h]; lq_s[w_l] <= wq_s[wq_h]; lq_t[w_l] <= 8'd0;
                end
                wl[279] <= 1'b0;
                if (iss_vw) begin : wide
                    reg [7:0] wm; integer t;
                    for (t = 0; t < 8; t = t + 1) wm[t] = &wq_s[wq_h][4*t +: 4];
                    wl <= {1'b1, wq_a[wq_h][14:0], wq_d[wq_h], wm};
                end
                if (iss_vr) begin
                    f_vmq <= {1'b1, 1'b0, rsa[r_k][31:5], 5'd0, 256'd0, 32'd0, 16'h4D52}; vpush = 1'b1;
                end
                // write queue pop
                if (iss_kw || iss_vw) begin wq_h <= wq_h + 4'd1; end
                // read lane requests leave their registers when the lane takes them
                for (integer l = 0; l < 4; l = l + 1) begin
                    if (lq_v[l] && r_req_rdy[l]) lq_v[l] <= 1'b0;
                    w_acc_q[l] <= lq_v[l] && r_req_rdy[l] && lq_we[l]; w_ack_q[l] <= w_ack[l];
                    l_wn[l] <= l_wn[l] + 6'(w_acc_q[l] ? 1 : 0) - 6'(w_ack_q[l] ? 1 : 0);
                end
                // reader: the chunk of slot r_k -> its lane request (HBM) / VM read, its descriptor, its landing slots
                if (r_go) begin : radv
                    reg [41:0] w;
                    cf[cf_t] <= {r_k, c_rend[r_k], 1'b0, rdd[r_k][4:0], c_ds[r_k], rsa[r_k][4:0], c_by[r_k] >> sl2};
                    cf_t <= cf_t + 6'd1;
                    sf_a <= sf_a + 8'(c_ns[r_k]);
                    if (src_hbm) begin
                        lq_v[c_ea[r_k][36:35]] <= 1'b1; lq_we[c_ea[r_k][36:35]] <= 1'b0; lq_a[c_ea[r_k][36:35]] <= {c_ea[r_k][36:5], 5'd0};
                        lq_n[c_ea[r_k][36:35]] <= c_ns[r_k]; lq_t[c_ea[r_k][36:35]] <= sf_a;
                    end
                    if (c_bad[r_k]) begin f_fault <= 1'b1; mv_fault <= 1'b1; end
                    rrr <= r_k + 2'd1;
                    if (c_rend[r_k]) begin                                       // the slot's next row (precomputed)
                        if (ro[r_k] + ((stp || stpd) ? 20'd4 : 20'd1) >= mm) ract[r_k] <= 1'b0;
                        ro[r_k] <= ro[r_k] + ((stp || stpd) ? 20'd4 : 20'd1); rrl[r_k] <= nnb;
                        rsa[r_k] <= rnsa[r_k]; rnsa[r_k] <= rnsa[r_k] + sstw; rdd[r_k] <= rndd[r_k]; rndd[r_k] <= rndd[r_k] + dstw;
                    end else begin
                        rsa[r_k] <= rsa[r_k] + {33'd0, c_by[r_k]}; rrl[r_k] <= rrl[r_k] - {15'd0, c_by[r_k]};
                        w = {33'd0, c_by[r_k] >> sl2}; rdd[r_k] <= rdd[r_k] + (w << dl2);
                    end
                end
                // in-flight accounting (kind shift registers: push at the tail, pop at the head)
                k_in <= k_in + {7'd0, kpush} - {7'd0, k_rv};
                v_in <= v_in + {2'd0, vpush} - {2'd0, v_rv};
                begin : vk
                    reg [7:0] t; t = v_kind;
                    if (v_rv) t = t >> 1;
                    if (vpush) t[v_in - {2'd0, v_rv}] = vkind;
                    v_kind <= t;
                end
                rd_in <= rd_in + (r_go ? {5'd0, c_ns[r_k]} : 9'd0) - {8'd0, lw_v};
                wr_in <= wr_in + {8'd0, iss_kw | iss_vw} - {8'd0, v_wr_ack | (wld_q & busy_f & !dst_hbm)}
                         - {6'd0, 3'(w_ack_q[0]) + 3'(w_ack_q[1]) + 3'(w_ack_q[2]) + 3'(w_ack_q[3])};
            end
            if (k_fault && busy_f) begin f_fault <= 1'b1; mv_fault <= 1'b1; end
            // ---- landing
            // ---- landing: a lane's response sector (registered grant) or the VM read, into its slot of the landing RAM
            begin : land
                reg pop_; reg [1:0] nx; reg nf;
                pop_ = u_go && u_pop;
                lw_v <= lt_v || v_rd_land || (VR2 != 0 && g_dv);
                // VM read group: responses held a lane, drained one a cycle; credits; burst ownership
                for (integer b = 0; b < 32; b = b + 1) begin
                    if (vr2r[b*257 + 256]) g_hv[b] <= 1'b1;
                    g_cr[b] <= g_cr[b] + 6'(g_crp[b]) - 6'((r_go && !src_hbm && VR2 != 0 && rsa[r_k][9:5] == 5'(b)) ? 1 : 0);
                end
                if (VR2 != 0 && g_dv) begin g_hv[g_di] <= 1'b0; g_busy[g_di] <= 1'b0; g_rr <= g_di + 5'd1; end
                vr2q[511:0] <= '0;
                if (r_go && !src_hbm && VR2 != 0) begin
                    g_busy[rsa[r_k][9:5]] <= 1'b1; g_slot[rsa[r_k][9:5]] <= sf_a;
                    vr2q[rsa[r_k][9:5]*16 +: 16] <= {1'b1, rsa[r_k][19:5]};
                end
                vr2q[512] <= VR2 != 0 && ((busy_f && !src_hbm && go_q4 && !r_done) || g_busy != 32'd0 || !g_home);
                if (v_rd_land) v_ptr <= v_ptr + 8'd1;
                for (integer l = 0; l < 4; l = l + 1) if (l_take[l]) lbc[l] <= r_rsp_last[l] ? 3'd0 : lbc[l] + 3'd1;
                // next grant: rotating from the lane after the current grant, among the lanes with a sector waiting
                nf = 1'b0; nx = 2'd0;
                for (integer t = 4; t >= 1; t = t - 1) begin : gp
                    reg [1:0] c; c = 2'(lgi + 2'(t));
                    if (r_rsp_v[c] && !r_rsp_we[c]) begin nf = 1'b1; nx = c; end
                end
                lg <= nf ? (4'd1 << nx) : 4'd0; if (nf) lgi <= nx;
                if (lw_v) lv[lw_a] <= 1'b1;
                if (pop_) begin lv[sf_h] <= 1'b0; sf_h <= sf_h + 8'd1; end
                sf_n <= sf_n + (r_go ? {5'd0, c_ns[r_k]} : 9'd0) - {8'd0, pop_};
            end
            // ---- unpack (stage U -> p1): the current chunk; the staged descriptor becomes current at the chunk end
            p1_v <= 1'b0;
            begin : unpk
                reg take_cd;
                take_cd = cd_v && (!u_cv || (u_go && u_end));
                if (u_go) begin
                    p1_v <= 1'b1; p1_k <= u_k; p1_h <= sf_h; p1_sp <= u_sp; p1_dp <= u_dp; p1_dsec <= u_dsec;
                    p1_fl <= u_fl; p1_sl <= u_sl;
                    if (u_end) u_cv <= 1'b0;
                    else begin
                        u_left <= u_left - {5'd0, u_k};
                        u_sp <= u_sp + (5'(u_k) << sl2);
                        s_room <= u_pop ? (6'd32 >> sl2) : s_room - {2'd0, u_k};
                        if (u_fl) begin u_dsec <= u_dsec + 37'd1; u_dp <= 6'd0; d_room <= 6'd32 >> dl2; end
                        else begin u_dp <= u_dp + (6'(u_k) << dl2); d_room <= d_room - {2'd0, u_k}; end
                    end
                end
                if (take_cd) begin
                    u_cv <= 1'b1; u_left <= cd[8:0]; u_sp <= cd[13:9]; u_dsec <= cd[50:14]; u_dp <= cd[56:51]; u_rend <= cd[57]; u_sl <= cd[59:58];
                    s_room <= room(cd[13:9], sl2); d_room <= room(cd[55:51], dl2);
                end
                if (cf_n != 7'd0 && (!cd_v || take_cd)) begin cd <= cf[cf_h]; cd_v <= 1'b1; cf_h <= cf_h + 6'd1; end
                else if (take_cd) cd_v <= 1'b0;
                cf_n <= cf_n + {6'd0, r_go} - {6'd0, cf_n != 7'd0 && (!cd_v || take_cd)};
            end
            // ---- extract (p1 -> px), convert (px -> p2), encode (p2 -> pe), place (pe -> p3), merge (p3)
            pr_v <= p1_v;
            if (p1_v) begin pr_k <= p1_k; pr_sp <= p1_sp; pr_dp <= p1_dp; pr_dsec <= p1_dsec; pr_fl <= p1_fl; pr_sl <= p1_sl; end
            px_v <= pr_v;
            if (pr_v) begin px_k <= pr_k; px_r <= ext_r; px_dp <= pr_dp; px_dsec <= pr_dsec; px_fl <= pr_fl; px_sl <= pr_sl; end
            p2_v <= px_v;
            if (px_v) begin p2_k <= px_k; p2_w <= dec_w; p2_dp <= px_dp; p2_dsec <= px_dsec; p2_fl <= px_fl; p2_sl <= px_sl; end
            pa_v <= p2_v;
            if (p2_v) begin
                pa_k <= p2_k; pa_e <= enc_a; pa_q <= ea_q; pa_inc <= ea_inc; pa_big <= ea_big; pa_sat <= ea_sat; pa_sign <= ea_sign;
                pa_ex <= ea_ex; pa_dp <= p2_dp; pa_dsec <= p2_dsec; pa_fl <= p2_fl; pa_sl <= p2_sl; pa_e4 <= !(dsp == 2'd1 || df == 3'd0 || df == 3'd5 || df == 3'd1);
            end
            pe_v <= pa_v;
            if (pa_v) begin
                pe_e <= enc_e; pe_dp <= pa_dp; pe_dsec <= pa_dsec; pe_fl <= pa_fl; pe_sl <= pa_sl;
                for (integer q = 0; q < 8; q = q + 1) pe_lv[q] <= q < pa_k;
                pe_keep <= !(MUT == 2 && pa_dp + (6'(pa_k) << dl2) != 6'd32);
            end
            pk_v <= pe_v;
            if (pe_v) begin pk_d <= pack_d; pk_s <= pack_s; pk_dp <= pe_dp; pk_dsec <= pe_dsec; pk_fl <= pe_fl; pk_keep <= pe_keep; pk_sl <= pe_sl; end
            p3_v <= pk_v;
            if (pk_v) begin p3_d <= put_d; p3_s <= put_s; p3_dsec <= pk_dsec; p3_fl <= pk_fl; p3_keep <= pk_keep; p3_sl <= pk_sl; end
            if (p3_v) begin
                if (p3_fl && p3_keep) begin
                    wq_d[wq_t] <= ((db_dirty[p3_sl] ? db_dat[p3_sl] : 256'd0) & ~mk(p3_s)) | p3_d;
                    wq_s[wq_t] <= (db_dirty[p3_sl] ? db_strb[p3_sl] : 32'd0) | p3_s; wq_a[wq_t] <= p3_dsec; wq_t <= wq_t + 4'd1;
                    db_dirty[p3_sl] <= 1'b0;
                end else if (p3_fl) db_dirty[p3_sl] <= 1'b0;                  // MUT 2: the partial sector is lost
                else begin
                    db_dat[p3_sl] <= ((db_dirty[p3_sl] ? db_dat[p3_sl] : 256'd0) & ~mk(p3_s)) | p3_d;
                    db_strb[p3_sl] <= (db_dirty[p3_sl] ? db_strb[p3_sl] : 32'd0) | p3_s; db_dirty[p3_sl] <= 1'b1;
                end
            end
            wq_n <= wq_n + {4'd0, p3_v && p3_fl && p3_keep} - {4'd0, iss_kw | iss_vw};
            wq_res <= wq_res + {4'd0, u_go && u_fl} - {4'd0, iss_kw | iss_vw} - {4'd0, p3_v && p3_fl && !p3_keep};
            // ---- completion: everything unpacked, the pipe empty, the queue drained and every write acknowledged
            if (busy_f && go_q4 && !f_fault && r_done && !u_cv && !cd_v && cf_n == 7'd0 && !lw_v && lq_v == 4'd0 && !p1_v && !pr_v && !px_v && !p2_v && !pa_v && !pe_v && !pk_v && !p3_v && wq_n == 5'd0 && wr_in == 9'd0 &&
                !(iss_kw | iss_vw) && rd_in == 9'd0 && sf_n == 9'd0) begin
                busy_f <= 1'b0; mv_done <= 1'b1;
            end
            if (f_fault && busy_f && k_in == 8'd0 && v_in == 3'd0 && rd_in == 9'd0 && lq_v == 4'd0) busy_f <= 1'b0;
        end
    end
    function automatic [1:0] l2(input [2:0] e);
        l2 = (e == 3'd4) ? 2'd2 : (e == 3'd2) ? 2'd1 : 2'd0;
    endfunction
    function automatic [5:0] room(input [4:0] off, input [1:0] lgs);  // elements from byte off to the sector end
        room = (6'd32 - {1'b0, off}) >> lgs;
    endfunction
    function automatic [255:0] mk(input [31:0] s);
        integer t; begin mk = 256'd0; for (t = 0; t < 32; t = t + 1) if (s[t]) mk[8*t +: 8] = 8'hFF; end
    endfunction
    // ---- port muxing with the serial engine (it drives the ports while it owns them)
    assign ko_ld = !ko_v || k_req_rdy;
    // hgi-1010/c: the lane request leaves an OUTPUT REGISTER (route bf6565982: sel_s / kq_h -> k_req_wdata / k_req_addr
    // through the engine mux to the pins, -352 ps): the register loads the selected engine's request whenever it is
    // empty or the lane takes its content (bubble-free); an engine's request counts as taken when the register loads it
    reg ko_v, ko_we; reg [36:0] ko_a; reg [255:0] ko_d; reg [31:0] ko_s;
    always @(posedge clk or negedge rn)
        if (!rn) ko_v <= 1'b0;
        else if (ko_ld) begin
            ko_v <= sel_s ? s_kv : f_kv;
            ko_we <= sel_s ? s_kwe : f_kwe; ko_a <= sel_s ? s_ka : f_ka;
            ko_d <= sel_s ? s_kd : f_kd; ko_s <= sel_s ? s_ks : f_ks;
        end
    assign k_req_v = ko_v; assign k_req_we = ko_we; assign k_req_addr = ko_a; assign k_req_wdata = ko_d; assign k_req_wstrb = ko_s;
    assign vmq = sel_s ? s_vmq : f_vmq;
    wire unused_ok = &{1'b0, s_kt, s_krr, s_fence_done};
`ifndef SYNTHESIS
    // a refused move names itself (bench / e2e debugging)
    always @(posedge clk) if (rn && cv_q && (fast_cmd ? 1'b1 : cm_q[94:93] == 2'd0)) begin : flt
        reg x; x = (cm_q[94:93] == 2'd0) && (!fast_cmd || cm_q[102:98] != 5'd0 || cm_q[142:138] != 5'd0 ||
                    ((cm_q[226:206] << l2(esz(cm_q[97:95]))) & 21'h1F) != 21'd0);
        if (x) $display("MOVER refuses a partial-sector HBM write: src sp %0d fmt %0d dst base %h stride %0d fmt %0d m %0d n %0d istride %0d/%0d",
                        cm_q[1:0], cm_q[4:2], cm_q[137:98], cm_q[169:138], cm_q[97:95], cm_q[205:186], cm_q[226:206], cm_q[92:77], cm_q[185:170]);
    end
`endif
endmodule
`default_nettype wire
