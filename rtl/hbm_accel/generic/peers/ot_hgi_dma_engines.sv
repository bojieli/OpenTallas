`timescale 1ns/1ps
`default_nettype none
// ---------------------------------------------------------------------------------------------------------------------
// HGI-1 DMA engines (hgi-takeover 2026-10-10): the DMA unit's move port (ot_hgi_dma_record, one move outstanding)
// dispatched to
//   ot_hgi_dma_front  every HBM -> VM LOAD with element strides 1, 32 B aligned source rows of whole sectors, VM rows of
//                     whole sectors (base / stride multiples of 8 words), formats FP32 / U32 / BF16 / FP8E4M3 / INT8:
//                     the svc DMA stream (per-stack requests, 4 x 8 data lanes) -> the 32 VM wide write lanes;
//   ot_hgi_dma_mover  the rest (STORE, VM -> VM, strided, unaligned, KV ops) on its kport lane + VM client; its one
//                     VM wide lane goes out on its bank's lane (the engines never run together: one move outstanding).
// FRONT = 0 sends every move to the mover (the comparison point).  Fence: the mover's (the front is idle at a fence).
// INDEXED ROW STREAM (hgi-1010/c, spec 3.3): is_cmd {ilist 32, ix_cmd 176} from the DMA record adapter (the stream form:
// A indexed + n_sel N_FROM_VM).  The I-list reader reads the cnt ids U32(VM[ilist + e]) through the mover's VM packet
// client (taken only while the mover is idle: a posted STORE may still own it), up to 4 sector reads in flight (responses
// into a 4-entry FIFO: VM answers are not back-pressured), into a 32-entry id FIFO.  FRONT = 1: the front runs the stream
// (ix_cmd + the id list).  FRONT = 0: a row sequencer issues one mover LOAD per row (row e: source abase + (id_e - id_0)
// x dyn_mul with rebase, m 1, n, destination dbase + e x dstride), so the stream form also runs without the svc stream.
// Completion: mv_done / mv_fdone (front), or the last row move's mv_done / mv_pdone (mover); row moves before it are
// internal.  MUT_IL (bench): the reader skips the id at list position 1 (duplicates id 2): must FAIL.
// ---------------------------------------------------------------------------------------------------------------------
module ot_hgi_dma_engines #(
    parameter integer FRONT = 1,
    parameter integer VR2 = 0,            // 1: the mover's VM-source reads on the VM DMA wide read group (vr2q / vr2r)
    parameter integer MUT_IL = 0,
    parameter integer SBIT = 35,
    parameter [35:0] STACK_BYTES = 36'd22500000000
) (
    input  wire                clk,
    input  wire                rst_n,
    input  wire                mv_v,
    output wire                mv_rdy,
    input  wire [226:0]        mv,
    output wire                mv_done,
    output wire                mv_fault,
    output wire                mv_src,      // the mover's source-consumed pulse (posted STORE / KVWB retire)
    output wire                mv_pdone,    // the mover's done
    output wire                mv_fdone,    // the front's done
    // indexed row stream command (hgi-1010/c)
    input  wire                is_v,
    output wire                is_rdy,
    input  wire [207:0]        is_cmd,
    input  wire                fence_v,
    output wire                fence_rdy,
    output wire                fence_done,
    // the mover's kport lane
    output wire                k_req_v,
    input  wire                k_req_rdy,
    output wire                k_req_we,
    output wire [36:0]         k_req_addr,
    output wire [255:0]        k_req_wdata,
    output wire [31:0]         k_req_wstrb,
    output wire [15:0]         k_req_tag,
    input  wire                k_rsp_v,
    output wire                k_rsp_rdy,
    input  wire                k_rsp_we,
    input  wire [255:0]        k_rsp_data,
    // the mover's HBM lanes (one kport lane a stack: burst reads, full-sector writes; hgi-1010/c)
    output wire [3:0]          r_req_v,
    input  wire [3:0]          r_req_rdy,
    output wire [4*37-1:0]     r_req_addr,
    output wire [4*4-1:0]      r_req_len,
    output wire [4*16-1:0]     r_req_tag,
    output wire [3:0]          r_req_we,
    output wire [4*256-1:0]    r_req_wdata,
    output wire [4*32-1:0]     r_req_wstrb,
    input  wire [3:0]          r_rsp_v,
    input  wire [3:0]          r_rsp_we,
    output wire [3:0]          r_rsp_rdy,
    input  wire [4*16-1:0]     r_rsp_tag,
    input  wire [3:0]          r_rsp_last,
    input  wire [4*256-1:0]    r_rsp_data,
    // the mover's VM wide READ group 2 (VR2 = 1; b's ot_hgi_vm_die DMA group)
    output wire [512:0]        vr2q,
    input  wire [8256:0]       vr2r,
    // the mover's VM packet client
    output wire [337:0]        vmq,
    input  wire [273:0]        vmr,
    // the svc DMA stream (hgi-takeover.log "SPEC for hbm-forks")
    output wire [4*51-1:0]     dq,
    input  wire [3:0]          dq_rdy,
    input  wire [32*270-1:0]   dd,
    output wire [31:0]         dd_cr,
    // the VM wide write port
    output wire [32*280-1:0]   wl,
    input  wire [31:0]         wl_done
);
    wire [2:0] sf = mv[4:2];
    wire elig = mv[1:0] == 2'd0 && mv[94:93] == 2'd1 && mv[92:77] == 16'd1 && mv[185:170] == 16'd1 &&
                (sf == 3'd0 || sf == 3'd1 || sf == 3'd2 || sf == 3'd4 || sf == 3'd5) &&
                mv[9:5] == 5'd0 && mv[49:45] == 5'd0 && mv[100:98] == 3'd0 && mv[140:138] == 3'd0 &&
                ((sf == 3'd0 || sf == 3'd5) ? mv[208:206] == 3'd0 : (sf == 3'd1) ? mv[209:206] == 4'd0 : mv[210:206] == 5'd0) &&
                mv[205:186] != 20'd0 && mv[226:206] != 21'd0;
    wire to_f = (FRONT != 0) && elig;
    // ---------------------------------------------------------------- I-list reader state
    reg rd_act; reg [31:0] rd_w; reg [19:0] rd_left;           // next id word to request, ids not yet requested
    reg [2:0] rd_out; reg [5:0] rd_fl;                         // sector reads in flight, ids in flight + buffered
    reg [2:0] ro_off [0:3]; reg [3:0] ro_k [0:3]; reg [1:0] ro_h, ro_t;    // per read: first word, ids in it
    reg [255:0] rb_d [0:3]; reg [1:0] rb_h, rb_t; reg [2:0] rb_n;          // response FIFO
    reg [2:0] u_off; reg [3:0] u_k; reg [19:0] u_e;            // unpack position in the head response, list position
    reg [31:0] idf [0:31]; reg [4:0] idf_h, idf_t; reg [5:0] idf_n;
    reg [337:0] r_vmq;
    wire [337:0] m_vmq;
    wire ix_rdy_f, id_rdy_f; reg ixf_v; reg [175:0] ixf_cmd;
    wire s_id_v = idf_n != 6'd0;
    wire s_id_take;
    reg [3:0] iss_k; reg iss_go;
    always @* begin
        iss_k = 4'd8 - {1'b0, rd_w[2:0]};
        if ({16'd0, iss_k} > rd_left) iss_k = rd_left[3:0];
        iss_go = rd_act && rd_left != 20'd0 && rd_out < 3'd4 && ({2'd0, iss_k} <= 6'd32 - rd_fl);
    end
    // row sequencer (FRONT 0)
    reg [175:0] sc; reg sq_act, sq_last, sq_mv_v, sq_wait; reg [226:0] sq_mv; reg [19:0] sq_e;
    reg sq_p0v; reg [59:0] sq_p0; reg [1:0] sq_ph; reg [59:0] sq_p; reg [42:0] sq_lo, sq_hi; reg [31:0] sq_id;
    assign vmq = rd_act ? r_vmq : m_vmq;
    wire f_rdy, f_done, f_fault, m_rdy, m_done, m_fault, m_src; wire [279:0] m_wl; wire [32*280-1:0] f_wl;
    assign mv_rdy = !rd_act && !sq_act && (to_f ? f_rdy : m_rdy);
    assign mv_done = f_done | (m_done && (!sq_act || sq_last));
    assign mv_fault = f_fault | m_fault;
    assign mv_src = m_src && !sq_act; assign mv_pdone = m_done && (!sq_act || sq_last); assign mv_fdone = f_done;
    generate if (FRONT != 0) begin : g_front
        ot_hgi_dma_front #(.SBIT(SBIT), .STACK_BYTES(STACK_BYTES)) u_front (.clk(clk), .rst_n(rst_n), .mv_v(mv_v && to_f),
            .mv_rdy(f_rdy), .mv(mv), .mv_done(f_done), .mv_fault(f_fault),
            .ix_v(ixf_v), .ix_rdy(ix_rdy_f), .ix_cmd(ixf_cmd), .id_v(s_id_v), .id_rdy(id_rdy_f), .id(idf[idf_h]),
            .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
            .wl(f_wl), .wl_done(wl_done));
    end else begin : g_nofront
        assign f_rdy = 1'b0; assign f_done = 1'b0; assign f_fault = 1'b0; assign dq = '0; assign dd_cr = '0; assign f_wl = '0;
        assign ix_rdy_f = 1'b0; assign id_rdy_f = 1'b0;
    end endgenerate
    // the mover's lane goes out on the lane of its sector's bank (the VM takes lane b into bank b); its done pulses come
    // one a cycle at most, so any lane's done is the mover's while the front is idle
    reg [32*280-1:0] m_wlx;
    always @* begin m_wlx = '0; if (m_wl[279]) m_wlx[m_wl[268:264]*280 +: 280] = m_wl; end
    // per lane: the front's lane when it is valid (its data bits are not cleared between writes), else the mover's
    genvar gl;
    generate for (gl = 0; gl < 32; gl = gl + 1) begin : g_wl
        assign wl[gl*280 +: 280] = f_wl[gl*280 + 279] ? f_wl[gl*280 +: 280] : m_wlx[gl*280 +: 280];
    end endgenerate
    ot_hgi_dma_mover #(.VR2(VR2)) u_mover (.clk(clk), .rst_n(rst_n), .mv_v(sq_act ? sq_mv_v : (mv_v && !to_f && !rd_act)), .mv_rdy(m_rdy),
        .mv(sq_act ? sq_mv : mv), .mv_done(m_done),
        .mv_fault(m_fault), .mv_src(m_src), .fence_v(fence_v), .fence_rdy(fence_rdy), .fence_done(fence_done),
        .k_req_v(k_req_v), .k_req_rdy(k_req_rdy), .k_req_we(k_req_we), .k_req_addr(k_req_addr), .k_req_wdata(k_req_wdata),
        .k_req_wstrb(k_req_wstrb), .k_req_tag(k_req_tag), .k_rsp_v(k_rsp_v), .k_rsp_rdy(k_rsp_rdy), .k_rsp_we(k_rsp_we),
        .k_rsp_data(k_rsp_data), .k_fault(1'b0),
        .r_req_v(r_req_v), .r_req_rdy(r_req_rdy), .r_req_addr(r_req_addr), .r_req_len(r_req_len), .r_req_tag(r_req_tag), .r_req_we(r_req_we), .r_req_wdata(r_req_wdata), .r_req_wstrb(r_req_wstrb),
        .r_rsp_v(r_rsp_v), .r_rsp_we(r_rsp_we), .r_rsp_rdy(r_rsp_rdy), .r_rsp_tag(r_rsp_tag), .r_rsp_last(r_rsp_last), .r_rsp_data(r_rsp_data), .vr2q(vr2q), .vr2r(vr2r),
        .vmq(m_vmq), .vmr(rd_act ? 274'd0 : vmr), .wl(m_wl), .wl_done(|wl_done));
    // ---------------------------------------------------------------- stream command, I-list reader, row sequencer
    assign is_rdy = !rd_act && !sq_act && m_rdy && ((FRONT != 0) ? (ix_rdy_f && f_rdy) : 1'b1) && !ixf_v;
    assign s_id_take = (FRONT != 0) ? (s_id_v && id_rdy_f) : (sq_act && !sq_wait && sq_ph == 2'd0 && s_id_v);
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_act <= 1'b0; rd_out <= 3'd0; rd_fl <= 6'd0; ro_h <= 2'd0; ro_t <= 2'd0; idf_h <= 5'd0; idf_t <= 5'd0;
            idf_n <= 6'd0; r_vmq <= 338'd0; rb_h <= 2'd0; rb_t <= 2'd0; rb_n <= 3'd0; u_k <= 4'd0; u_e <= 20'd0; ixf_v <= 1'b0;
            sq_act <= 1'b0; sq_mv_v <= 1'b0; sq_wait <= 1'b0; sq_last <= 1'b0; sq_ph <= 2'd0;
        end else begin : rdr
            reg push, rsp_in, upop;
            ixf_v <= 1'b0; r_vmq[337] <= 1'b0; push = 1'b0;
            if (is_v && is_rdy) begin
                sc <= is_cmd[175:0]; rd_act <= is_cmd[174:155] != 20'd0; rd_w <= is_cmd[207:176]; rd_left <= is_cmd[174:155]; u_e <= 20'd0;
                if (FRONT != 0) begin ixf_v <= 1'b1; ixf_cmd <= is_cmd[175:0]; end
                else begin
                    sq_act <= is_cmd[174:155] != 20'd0; sq_e <= 20'd0; sq_p0v <= 1'b0; sq_wait <= 1'b0; sq_ph <= 2'd0; sq_last <= 1'b0;
                end
            end
            if (iss_go) begin
                r_vmq <= {1'b1, 1'b0, rd_w[29:3], 5'd0, 256'd0, 32'd0, 16'h4944};   // byte address = sector x 32
                ro_off[ro_t] <= rd_w[2:0]; ro_k[ro_t] <= iss_k; ro_t <= ro_t + 2'd1;
                rd_w <= rd_w + {28'd0, iss_k}; rd_left <= rd_left - {16'd0, iss_k};
            end
            rsp_in = rd_act && vmr[273];
            if (rsp_in) begin rb_d[rb_t] <= vmr[255:0]; rb_t <= rb_t + 2'd1; end
            upop = 1'b0;
            if (rb_n != 3'd0) begin : unp
                reg [2:0] o; reg [3:0] kk;
                o = (u_k == 4'd0) ? ro_off[ro_h] : u_off; kk = (u_k == 4'd0) ? ro_k[ro_h] : u_k;
                idf[idf_t] <= rb_d[rb_h][{((MUT_IL != 0 && u_e == 20'd1) ? o + 3'd1 : o), 5'd0} +: 32];
                idf_t <= idf_t + 5'd1; push = 1'b1; u_e <= u_e + 20'd1;
                u_off <= o + 3'd1; u_k <= kk - 4'd1;
                if (kk == 4'd1) begin upop = 1'b1; rb_h <= rb_h + 2'd1; ro_h <= ro_h + 2'd1; u_k <= 4'd0; end
            end
            rb_n <= rb_n + {2'd0, rsp_in} - {2'd0, upop};
            rd_out <= rd_out + {2'd0, iss_go} - {2'd0, rsp_in};
            if (s_id_take) idf_h <= idf_h + 5'd1;
            idf_n <= idf_n + {5'd0, push} - {5'd0, s_id_take};
            rd_fl <= rd_fl + (iss_go ? {2'd0, iss_k} : 6'd0) - {5'd0, s_id_take};
            if (rd_act && rd_left == 20'd0 && rd_out == 3'd0 && !iss_go && !rsp_in && rb_n == 3'd0) rd_act <= 1'b0;
            // row sequencer (FRONT 0): id -> partial products -> address -> one mover LOAD, wait for its done
            sq_mv_v <= sq_mv_v && !m_rdy;
            if (sq_act) begin
                if (sq_ph == 2'd0 && !sq_wait && s_id_v) begin sq_id <= idf[idf_h]; sq_ph <= 2'd1; end
                if (sq_ph == 2'd1) begin
                    sq_lo <= {16'd0, sq_id[15:0]} * {16'd0, sc[69:43]}; sq_hi <= {16'd0, sq_id[31:16]} * {16'd0, sc[69:43]};
                    sq_ph <= 2'd2;
                end
                if (sq_ph == 2'd2) begin : ps
                    reg [59:0] p;
                    p = {17'd0, sq_lo} + ({17'd0, sq_hi} << 16);
                    if (!sq_p0v) begin sq_p0 <= p; sq_p0v <= 1'b1; end
                    sq_p <= p - (sc[175] ? (sq_p0v ? sq_p0 : p) : 60'd0);
                    sq_ph <= 2'd3;
                end
                if (sq_ph == 2'd3) begin : mvw
                    reg [59:0] a; reg [31:0] dw;
                    a = {20'd0, sc[42:3]} + sq_p; dw = sc[122:91] + sq_e * sc[154:123];
                    // move word {n 21, m 20, dst istride 16, dst stride 32, dst base 40, dst fmt 3, dst space 2,
                    //            src istride 16, src stride 32, src base 40, src fmt 3, src space 2}
                    sq_mv <= {sc[90:70], 20'd1, 16'd1, 32'd0, {8'd0, dw}, (sc[2:0] == 3'd5) ? 3'd5 : 3'd0, 2'd1,
                              16'd1, 32'd0, a[39:0], sc[2:0], 2'd0};
                    sq_mv_v <= 1'b1; sq_wait <= 1'b1; sq_ph <= 2'd0;
                    sq_last <= sq_e + 20'd1 == sc[174:155];
                    sq_e <= sq_e + 20'd1;
                end
                if (sq_wait && m_done) begin
                    sq_wait <= 1'b0;
                    if (sq_last) sq_act <= 1'b0;
                end
                if (m_fault) begin sq_act <= 1'b0; sq_wait <= 1'b0; end
            end
        end
    end
`ifndef SYNTHESIS
    reg trc; initial trc = $test$plusargs("DMA_TRACE");
    always @(posedge clk) if (trc && rst_n && mv_v && mv_rdy)
        $display("ENGINES move -> %s ssp %0d sf %0d src %h sst %0d sis %0d dsp %0d df %0d dst %h dstr %0d dis %0d m %0d n %0d",
                 to_f ? "front" : "mover", mv[1:0], mv[4:2], mv[44:5], mv[76:45], mv[92:77], mv[94:93], mv[97:95], mv[137:98],
                 mv[169:138], mv[185:170], mv[205:186], mv[226:206]);
`endif
endmodule
`default_nettype wire
