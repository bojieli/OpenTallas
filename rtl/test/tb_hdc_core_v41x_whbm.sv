`timescale 1ns/1ps
// Token-level HBM-weight integration top of the adopted V4.1 decode core.
// Quantized QE weights are fetched by ot_hdc_qstream from a physical HBM model;
// qrom is retained only as an independent byte-for-byte delivered-word oracle.
// the as-built bench (rtl/test/tb_hdc_core_v41.sv) with the new engines' memories in
// their own layouts (tools/hdc_images_v41x.py).  Behavioural synchronous-read memories
// loaded from tools/hdc_program_v41.py and tools/hdc_images_v41x.py images.
// Driven by Verilator (rtl/test/hdc_core_v41x_harness.cpp).  Bring-up switches:
// +define+HDC_X_HE=0|1 (default 1) etc. select the re-specified unit or the as-built one.
//
// Default: one decode step at +POS for +TOKEN from the golden-prefilled state
// (KV image, persistent vector memory, Engram hash history primed with the
// preceding tokens), then a bit-exact check of every logit, the whole vector
// memory and the whole KV cache against the ISA-level model.
// +MULTI: start from an EMPTY state, run the +NPROMPT prompt tokens through
// the core, then generate +NGEN tokens feeding each output back; compare the
// generated ids with the ISA model's, and the final vector memory and KV cache
// with its final state.
// +TRACE prints every issue (cycle, pc, unit) for the per-op breakdown.
`ifndef HDC_SW
`define HDC_SW 8
`endif
`ifndef HDC_X_HE
`define HDC_X_HE 1
`endif
`ifndef HDC_X_ME
`define HDC_X_ME 0
`endif
`ifndef HDC_X_ATT
`define HDC_X_ATT 0
`endif
`ifndef HDC_X_IDX
`define HDC_X_IDX 0
`endif
`ifndef HDC_X_SEL
`define HDC_X_SEL 0
`endif
`ifndef HDC_X_EG
`define HDC_X_EG 0
`endif
`ifndef HDC_MG
`define HDC_MG 8
`endif
`ifndef HDC_X_SU
`define HDC_X_SU 0
`endif
`ifndef HDC_SUN
`define HDC_SUN 16
`endif
`ifndef HDC_SUM
`define HDC_SUM 8
`endif
`ifndef HDC_HHW
`define HDC_HHW 8
`endif
`ifndef HDC_ME0_HBM
`define HDC_ME0_HBM 0
`endif
module tb_hdc_core_v41x_whbm #(
    parameter integer NPC = 8,
    parameter integer LWIN = 10,
    parameter integer CLK_PS = 1000
) (input wire clk);
    localparam integer INSTR_BITS = 1536;
    localparam integer W = 16, G = 4, BL = 16, QLB = 272, AW = 24, NW = 16, PAW = 14, HNL = 3;
    localparam integer SW = `HDC_SW;          // stream-unit lanes
    localparam integer HS = 8;                // HE K chunks
    localparam integer HROM_WORDS = 1 << 16;
    localparam integer WROM_WORDS = 1 << 19, QROM_WORDS = 1 << 16, EROM_WORDS = 1 << 19, CROM_WORDS = 1 << 15;
    localparam integer HHW = `HDC_HHW, HBAW = 16;
    localparam integer XSQ = 4, XSW = 16;       // X_SEL: select quarters x lanes
    localparam integer MG = `HDC_MG, MBAW = 17, ML = 2;   // ME weight tile: read latency ML (RL)
    localparam integer SUN = `HDC_SUN, SUM = `HDC_SUM;     // vector-unit lanes (X_SU)
    localparam integer KV_WORDS = 32768, VM_ELEMS = 65536, VOCAB = 4040, PROG_WORDS = 1 << PAW;

    reg [G*W*16-1:0]    wrom [0:WROM_WORDS-1];
    reg [HS*HNL*32-1:0] hrom [0:HROM_WORDS-1];
    reg [BL*QLB-1:0]    qrom [0:QROM_WORDS-1]; // independent oracle only
    localparam integer SPW = BL * QLB / 256, HMEM = 1 << 20, LAW = 12;
    reg [127:0] qlist [0:(1 << LAW)-1];
    reg [255:0] qwin [0:SPW-1][0:(1 << LWIN)-1];
    reg [HHW*32-1:0]    hbank [0:8*(1<<HBAW)-1];     // HCP weight banks: line a*8 + k
    reg [31:0]          mbank [0:8*MG*(1<<MBAW)-1];  // ME weight-tile banks: line a*8*MG + b
    reg [263:0]         erom [0:EROM_WORDS-1];
    reg [63:0]          crom [0:CROM_WORDS-1];
    reg [W*32-1:0]      kv   [0:KV_WORDS-1];
    reg [INSTR_BITS-1:0] prog [0:PROG_WORDS-1];
    reg [31:0]          vm   [0:VM_ELEMS-1];
    reg [31:0]          e_vm [0:VM_ELEMS-1];
    reg [31:0]          e_kv [0:KV_WORDS*W-1];
    reg [31:0]          e_lg [0:VOCAB-1];
    reg [31:0]          lg   [0:VOCAB-1];
    reg [31:0]          kvimg [0:KV_WORDS*W-1];

    reg rst_n = 1'b0, start = 1'b0;
    reg [NW-1:0] token, pos, expect_tok;
    wire done, fault;
    wire [NW-1:0] next_token;
    wire [31:0] next_val, cycles;
    reg prime_v = 1'b0, prime_first = 1'b0;
    reg [11:0] prime_cid = 0;

    wire prog_re; wire [PAW-1:0] prog_addr; reg [INSTR_BITS-1:0] prog_q;
    wire wrom_re; wire [AW-1:0] wrom_addr; reg [G*W*16-1:0] wrom_q;
    wire [SW-1:0] ewrom_re; wire [SW*AW-1:0] ewrom_addr; reg [SW*G*W*16-1:0] ewrom_q;
    wire qrom_re; wire [AW-1:0] qrom_addr; wire [BL*QLB-1:0] qrom_q;
    wire qd_v, q_ok, wrel_v; wire [AW-1:0] qd_wbase; wire [7:0] qd_nb; wire [NW-1:0] qd_tiles;
    wire hrom_re; wire [AW-1:0] hrom_addr; reg [HS*HNL*32-1:0] hrom_q;
    wire [XSQ-1:0] vsl_re; wire [XSQ*AW-1:0] vsl_addr; reg [XSQ*XSW*32-1:0] vsl_q;
    wire [7:0] mb_re; wire [8*MBAW-1:0] mb_addr; reg [8*MG*32-1:0] mb_p [0:ML-1];
    localparam integer M0_BASE = 10100, M0_WORDS = 36; // L0.router in this reduced program
    wire m0d_v, m0_select, m0_ok;
    wire [AW-1:0] m0d_wbase, m0d_xjs;
    wire [NW-1:0] m0d_nout, m0d_tiles, m0d_k;
    wire [1:0] m0d_split;
    wire [MG*32-1:0] m0_q;
    wire m0_fault;
    wire [3:0] m0_fault_why;
    wire [31:0] m0_sectors;
    reg m0_active = 0, m0_issued = 0, m0_busy_seen = 0;
    wire m0_begin = m0d_v && m0_select;
    wire m0_release = m0_active && m0_busy_seen && !unit_busy[0];
    assign m0_select = `HDC_ME0_HBM && m0d_wbase == M0_BASE &&
                       m0d_nout == 12 && m0d_tiles == 1 && m0d_k == 40 &&
                       m0d_xjs == 0 && m0d_split == 2;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            m0_active <= 0; m0_issued <= 0; m0_busy_seen <= 0;
        end else begin
            if (m0_begin) begin
                m0_active <= 1; m0_issued <= 0; m0_busy_seen <= 0;
            end else if (m0_release) m0_active <= 0;
            if (m0_active && issue_unit == 1) m0_issued <= 1;
            if (m0_issued && unit_busy[0]) m0_busy_seen <= 1;
        end
    end
    wire [7:0] hb_re; wire [8*HBAW-1:0] hb_addr; reg [8*HHW*32-1:0] hb_q;
    wire [HS-1:0] vh_re; wire [HS*AW-1:0] vh_addr; reg [HS*32-1:0] vh_q;
    wire ww_h_we; wire [AW-1:0] ww_h_addr; wire [31:0] ww_h_mask; wire [1023:0] ww_h_data;
    wire erom_re; wire [AW-1:0] erom_addr; reg [263:0] erom_q;
    wire [4*SW-1:0] crom_re; wire [4*SW*AW-1:0] crom_addr; reg [4*SW*64-1:0] crom_q;
    wire xcrom_re; wire [AW-1:0] xcrom_addr; reg [63:0] xcrom_q;
    wire kv_re; wire [G*AW-1:0] kv_raddr; reg [G*W*32-1:0] kv_q;
    wire [SW-1:0] kv_we; wire [SW*AW-1:0] kv_waddr; wire [SW*32-1:0] kv_wdata;
    wire [G-1:0] vx_re; wire [G*AW-1:0] vx_addr; reg [G*32-1:0] vx_q;
    wire [4*SW-1:0] vs_re; wire [4*SW*AW-1:0] vs_addr; reg [4*SW*32-1:0] vs_q;
    wire [SW-1:0] vi_re; wire [SW*AW-1:0] vi_addr; reg [SW*32-1:0] vi_q;
    wire vq_re, vr_re, wqr_re, wxr_re;
    wire [AW-1:0] vq_addr, vr_addr, wqr_addr, wxr_addr;
    reg [31:0] vq_q, vr_q;
    reg [1023:0] wqr_q, wxr_q;
    wire [G-1:0] vw_me_we; wire [G*AW-1:0] vw_me_addr; wire [G*W-1:0] vw_me_mask; wire [G*W*32-1:0] vw_me_data;
    wire [SUN-1:0] xs_vi_re, xs_vm_we, xs_kv_we; wire [SUN*AW-1:0] xs_vi_addr, xs_vm_waddr, xs_kv_waddr;
    reg  [SUN*32-1:0] xs_vi_q; wire [4*SUN-1:0] xs_rd_re; wire [4*SUN*AW-1:0] xs_rd_addr; wire [8*SUN-1:0] xs_rd_src;
    reg  [4*SUN*32-1:0] xs_rd_q; wire [SUN*32-1:0] xs_vm_wdata, xs_kv_wdata;
    wire [SUN/8-1:0] xs_res_we; wire [SUN/8*AW-1:0] xs_res_addr; wire [SUN/8*32-1:0] xs_res_data;
    wire [SW-1:0] vw_su_we, vw_rd_we; wire [SW*AW-1:0] vw_su_addr, vw_rd_addr; wire [SW*32-1:0] vw_su_data, vw_rd_data;
    wire vw_xe_we, ww_q_we, ww_x_we;
    wire [AW-1:0] vw_xe_addr, ww_q_addr, ww_x_addr;
    wire [31:0] vw_xe_data, ww_q_mask, ww_x_mask;
    wire [1023:0] ww_q_data, ww_x_data;
    wire me_ov; wire [G*AW-1:0] me_oaddr; wire [G*W-1:0] me_omask; wire [G*W*32-1:0] me_odata;
    wire [4:0] unit_busy; wire [2:0] issue_unit;

    // Index-key HBM: X_IDX=1 retains the legacy backdoor. X_IDX=2 sends each
    // replicated key through bounded request arbitration and the timed WR
    // queues of four HBM3E stack models.
    localparam integer IKH_WORDS = 1 << 18;          // 32-B sectors (8 MB)
    wire [31:0] ikh_req_v, ikh_req_rdy, ikh_rsp_v, ikh_rsp_rdy;
    wire [32*28-1:0] ikh_req_addr; wire [32*4-1:0] ikh_req_len, ikh_rsp_beat;
    wire [32*16-1:0] ikh_req_tag, ikh_rsp_tag; wire [32*256-1:0] ikh_rsp_data;
    wire ikw_v; wire [27:0] ikw_csec, ikw_ssec; wire [127:0] ikw_codes; wire [2:0] ikw_sslot; wire [7:0] ikw_scale;
    wire [127:0] pikh_req_v,pikh_req_rdy,pikh_rsp_v,pikh_rsp_rdy;
    wire [128*28-1:0] pikh_req_addr;
    wire [128*4-1:0] pikh_req_len,pikh_rsp_beat;
    wire [128*16-1:0] pikh_req_tag,pikh_rsp_tag;
    wire [128*256-1:0] pikh_rsp_data;
    wire pikw_v,pikw_rdy; wire [3:0] pikw_stack_mask;
    wire [27:0] pikw_csec,pikw_ssec; wire [511:0] pikw_codes;
    wire [2:0] pikw_sslot; wire [31:0] pikw_scales;
    wire [31:0] idxwr_records,idxwr_writes,idxwr_highwater,idxwr_read_stalls,idxwr_writer_stalls;
    wire [63:0] idxwr_refreshes;
    generate if (`HDC_X_IDX == 1) begin : g_ikh
        assign idxwr_records=0;assign idxwr_writes=0;assign idxwr_highwater=0;
        assign idxwr_read_stalls=0;assign idxwr_writer_stalls=0;assign idxwr_refreshes=0;
        ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28), .DW(256), .MEM_WORDS(IKH_WORDS), .TAGW(16), .LENW(4), .BEATW(4),
                              .QD(64), .REFPB(3), .MEM_MODE(0)) u_ikh (
            .clk(clk), .rst_n(rst_n), .req_v(ikh_req_v), .req_rdy(ikh_req_rdy), .req_addr(ikh_req_addr),
            .req_len(ikh_req_len), .req_tag(ikh_req_tag), .rsp_v(ikh_rsp_v), .rsp_rdy(ikh_rsp_rdy),
            .rsp_tag(ikh_rsp_tag), .rsp_beat(ikh_rsp_beat), .rsp_data(ikh_rsp_data));
        reg [255:0] ikimg [0:IKH_WORDS-1];
        integer ii;
        reg ik_multi;
        reg [8*512-1:0] ikdir;
        initial begin
            ik_multi = $test$plusargs("MULTI");
            if (!$value$plusargs("DIR=%s", ikdir)) ikdir = ".";
            for (ii = 0; ii < IKH_WORDS; ii = ii + 1) ikimg[ii] = 256'd0;
            if (!ik_multi) $readmemh({ikdir, "/ikhbm.hex"}, ikimg);
        end
        reg ik_loaded = 1'b0;
        always @(posedge clk) begin
            if (!ik_loaded) begin
                for (ii = 0; ii < IKH_WORDS; ii = ii + 1) u_ikh.mem[ii] = ikimg[ii];
                ik_loaded = 1'b1;
            end
            if (ikw_v) begin
                u_ikh.mem[ikw_csec] = {128'd0, ikw_codes};
                u_ikh.mem[ikw_ssec][32*ikw_sslot +: 32] = {24'd0, ikw_scale};
            end
        end
        assign pikh_req_rdy = 0; assign pikh_rsp_v = 0; assign pikh_rsp_tag = 0;
        assign pikh_rsp_beat = 0; assign pikh_rsp_data = 0;
    end else if (`HDC_X_IDX == 2) begin : g_pikh
        assign ikh_req_rdy = 0; assign ikh_rsp_v = 0; assign ikh_rsp_tag = 0;
        assign ikh_rsp_beat = 0; assign ikh_rsp_data = 0;
        reg [255:0] ikimg [0:IKH_WORDS-1];
        reg ik_multi;
        reg [8*512-1:0] ikdir;
        initial begin
            ik_multi = $test$plusargs("MULTI");
            if (!$value$plusargs("DIR=%s", ikdir)) ikdir = ".";
            for (integer i=0; i<IKH_WORDS; i=i+1) ikimg[i] = 256'd0;
            if (!ik_multi) $readmemh({ikdir, "/ikhbm.hex"}, ikimg);
        end
        wire [127:0] h_v,h_rdy,h_we,h_wr_done;
        wire [128*28-1:0] h_addr;
        wire [128*4-1:0] h_len;
        wire [128*16-1:0] h_tag;
        wire [128*256-1:0] h_wdata;
        wire [128*32-1:0] h_wstrb;
        wire bridge_busy;
        wire [31:0] bridge_records,bridge_writes,bridge_highwater,bridge_read_stalls,bridge_writer_stalls;
        wire [4*64-1:0] stack_refs;
        assign idxwr_records=bridge_records;assign idxwr_writes=bridge_writes;
        assign idxwr_highwater=bridge_highwater;assign idxwr_read_stalls=bridge_read_stalls;
        assign idxwr_writer_stalls=bridge_writer_stalls;
        assign idxwr_refreshes=stack_refs[0 +: 64]+stack_refs[64 +: 64]+
                               stack_refs[128 +: 64]+stack_refs[192 +: 64];
        ot_hdc_v41x_idx_pool_hbm_bridge u_bridge (
            .clk(clk),.rst_n(rst_n),.w_v(pikw_v),.w_rdy(pikw_rdy),.w_stack_mask(pikw_stack_mask),
            .w_csec(pikw_csec),.w_codes(pikw_codes),.w_ssec(pikw_ssec),.w_sslot(pikw_sslot),
            .w_scales(pikw_scales),.r_v(pikh_req_v),.r_rdy(pikh_req_rdy),.r_addr(pikh_req_addr),
            .r_len(pikh_req_len),.r_tag(pikh_req_tag),.h_v(h_v),.h_rdy(h_rdy),.h_addr(h_addr),
            .h_len(h_len),.h_tag(h_tag),.h_we(h_we),.h_wdata(h_wdata),.h_wstrb(h_wstrb),
            .h_wr_done(h_wr_done),.busy(bridge_busy),.dbg_records(bridge_records),
            .dbg_writes(bridge_writes),.dbg_fifo_highwater(bridge_highwater),
            .dbg_read_stalls(bridge_read_stalls),.dbg_writer_stalls(bridge_writer_stalls));
        for (genvar s=0; s<4; s=s+1) begin : g_stack
            ot_hdc_v41x_idx_hbm #(.NPC(32), .AW(28), .DW(256), .MEM_WORDS(IKH_WORDS),
                .TAGW(16), .LENW(4), .BEATW(4), .QD(64), .REFPB(3), .MEM_MODE(0)) hm (
                .clk(clk), .rst_n(rst_n), .req_v(h_v[s*32 +: 32]),
                .req_rdy(h_rdy[s*32 +: 32]), .req_addr(h_addr[s*32*28 +: 32*28]),
                .req_len(h_len[s*32*4 +: 32*4]), .req_tag(h_tag[s*32*16 +: 32*16]),
                .req_we(h_we[s*32 +: 32]),.req_wdata(h_wdata[s*32*256 +: 32*256]),
                .req_wstrb(h_wstrb[s*32*32 +: 32*32]),.wr_done(h_wr_done[s*32 +: 32]),
                .rsp_v(pikh_rsp_v[s*32 +: 32]), .rsp_rdy(pikh_rsp_rdy[s*32 +: 32]),
                .rsp_tag(pikh_rsp_tag[s*32*16 +: 32*16]), .rsp_beat(pikh_rsp_beat[s*32*4 +: 32*4]),
                .rsp_data(pikh_rsp_data[s*32*256 +: 32*256]));
            reg loaded=0;
            reg [63:0] refresh_count;
            integer pp;
            always @* begin
                refresh_count=0;
                for(pp=0;pp<32;pp=pp+1) refresh_count=refresh_count+hm.st_ref[pp];
            end
            assign stack_refs[s*64 +: 64]=refresh_count;
            always @(posedge clk) begin
                if (!loaded) begin
                    for (integer i=0; i<IKH_WORDS; i=i+1) hm.mem[i]=ikimg[i];
                    loaded<=1;
                end
            end
        end
    end else begin : g_ikh_n
        assign idxwr_records=0;assign idxwr_writes=0;assign idxwr_highwater=0;
        assign idxwr_read_stalls=0;assign idxwr_writer_stalls=0;assign idxwr_refreshes=0;
        assign ikh_req_rdy = 0; assign ikh_rsp_v = 0; assign ikh_rsp_tag = 0; assign ikh_rsp_beat = 0;
        assign ikh_rsp_data = 0;
        assign pikh_req_rdy = 0; assign pikh_rsp_v = 0; assign pikh_rsp_tag = 0;
        assign pikh_rsp_beat = 0; assign pikh_rsp_data = 0;
    end endgenerate
    reg [AW-1:0] cfg [0:15];                   // tools/hdc_images_v41x.py cfg.hex: [0] the index keys' KV word base
    ot_hdc_core_v41x #(.SW(SW), .HS(HS), .W_HBM(1), .ME0_HBM(`HDC_ME0_HBM), .X_HE(`HDC_X_HE), .X_ME(`HDC_X_ME), .X_ATT(`HDC_X_ATT), .X_IDX(`HDC_X_IDX),
                       .X_SEL(`HDC_X_SEL), .X_EG(`HDC_X_EG), .XSQ(XSQ), .XSW(XSW),
                       .X_SU(`HDC_X_SU), .SUN(SUN), .SUM(SUM),
                       .HHW(HHW), .HBAW(HBAW), .MG(MG), .MBAW(MBAW)) dut (
        .cfg_ik_base(cfg[0]), .cfg_me_xs(cfg[1][3:0]),
        .ikh_req_v(ikh_req_v), .ikh_req_rdy(ikh_req_rdy), .ikh_req_addr(ikh_req_addr), .ikh_req_len(ikh_req_len),
        .ikh_req_tag(ikh_req_tag), .ikh_rsp_v(ikh_rsp_v), .ikh_rsp_rdy(ikh_rsp_rdy), .ikh_rsp_tag(ikh_rsp_tag),
        .ikh_rsp_beat(ikh_rsp_beat), .ikh_rsp_data(ikh_rsp_data), .ikw_v(ikw_v), .ikw_csec(ikw_csec),
        .ikw_codes(ikw_codes), .ikw_ssec(ikw_ssec), .ikw_sslot(ikw_sslot), .ikw_scale(ikw_scale),
        .pikh_req_v(pikh_req_v), .pikh_req_rdy(pikh_req_rdy), .pikh_req_addr(pikh_req_addr),
        .pikh_req_len(pikh_req_len), .pikh_req_tag(pikh_req_tag), .pikh_rsp_v(pikh_rsp_v),
        .pikh_rsp_rdy(pikh_rsp_rdy), .pikh_rsp_tag(pikh_rsp_tag), .pikh_rsp_beat(pikh_rsp_beat),
        .pikh_rsp_data(pikh_rsp_data), .pikw_v(pikw_v), .pikw_rdy(pikw_rdy),
        .pikw_stack_mask(pikw_stack_mask),
        .pikw_csec(pikw_csec), .pikw_codes(pikw_codes), .pikw_ssec(pikw_ssec),
        .pikw_sslot(pikw_sslot), .pikw_scales(pikw_scales),
        .mb_re(mb_re), .mb_addr(mb_addr), .mb_q(mb_p[ML-1]),
        .m0d_v(m0d_v), .m0d_wbase(m0d_wbase), .m0d_nout(m0d_nout),
        .m0d_tiles(m0d_tiles), .m0d_k(m0d_k), .m0d_xjs(m0d_xjs),
        .m0d_split(m0d_split), .m0_select(m0_select), .m0_ok(m0_ok),
        .xs_vi_re(xs_vi_re), .xs_vi_addr(xs_vi_addr), .xs_vi_q(xs_vi_q), .xs_rd_re(xs_rd_re),
        .xs_rd_addr(xs_rd_addr), .xs_rd_src(xs_rd_src), .xs_rd_q(xs_rd_q), .xs_vm_we(xs_vm_we),
        .xs_vm_waddr(xs_vm_waddr), .xs_vm_wdata(xs_vm_wdata), .xs_kv_we(xs_kv_we), .xs_kv_waddr(xs_kv_waddr),
        .xs_kv_wdata(xs_kv_wdata), .xs_res_we(xs_res_we), .xs_res_addr(xs_res_addr), .xs_res_data(xs_res_data),
        .clk(clk), .rst_n(rst_n), .start(start), .token(token), .pos(pos), .entry({PAW{1'b0}}), .acc_n(), .acc_tok(),
        .done(done), .next_token(next_token), .next_val(next_val), .cycles(cycles), .fault(fault),
        .prime_v(prime_v), .prime_first(prime_first), .prime_cid(prime_cid),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .wrom_re(wrom_re), .wrom_addr(wrom_addr), .wrom_q(wrom_q),
        .ewrom_re(ewrom_re), .ewrom_addr(ewrom_addr), .ewrom_q(ewrom_q),
        .qrom_re(qrom_re), .qrom_addr(qrom_addr), .qrom_q(qrom_q),
        .hrom_re(hrom_re), .hrom_addr(hrom_addr), .hrom_q(hrom_q),
        .hb_re(hb_re), .hb_addr(hb_addr), .hb_q(hb_q), .vh_re(vh_re), .vh_addr(vh_addr), .vh_q(vh_q),
        .ww_h_we(ww_h_we), .ww_h_addr(ww_h_addr), .ww_h_mask(ww_h_mask), .ww_h_data(ww_h_data),
        .erom_re(erom_re), .erom_addr(erom_addr), .erom_q(erom_q),
        .crom_re(crom_re), .crom_addr(crom_addr), .crom_q(crom_q),
        .xcrom_re(xcrom_re), .xcrom_addr(xcrom_addr), .xcrom_q(xcrom_q),
        .kv_re(kv_re), .kv_raddr(kv_raddr), .kv_q(kv_q), .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata),
        .vx_re(vx_re), .vx_addr(vx_addr), .vx_q(vx_q), .vs_re(vs_re), .vs_addr(vs_addr), .vs_q(vs_q),
        .vi_re(vi_re), .vi_addr(vi_addr), .vi_q(vi_q), .vq_re(vq_re), .vq_addr(vq_addr), .vq_q(vq_q),
        .vr_re(vr_re), .vr_addr(vr_addr), .vr_q(vr_q), .wqr_re(wqr_re), .wqr_addr(wqr_addr), .wqr_q(wqr_q),
        .wxr_re(wxr_re), .wxr_addr(wxr_addr), .wxr_q(wxr_q),
        .vsl_re(vsl_re), .vsl_addr(vsl_addr), .vsl_q(vsl_q),
        .vw_me_we(vw_me_we), .vw_me_addr(vw_me_addr), .vw_me_mask(vw_me_mask), .vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we), .vw_su_addr(vw_su_addr), .vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we), .vw_rd_addr(vw_rd_addr), .vw_rd_data(vw_rd_data),
        .vw_xe_we(vw_xe_we), .vw_xe_addr(vw_xe_addr), .vw_xe_data(vw_xe_data),
        .ww_q_we(ww_q_we), .ww_q_addr(ww_q_addr), .ww_q_mask(ww_q_mask), .ww_q_data(ww_q_data),
        .ww_x_we(ww_x_we), .ww_x_addr(ww_x_addr), .ww_x_mask(ww_x_mask), .ww_x_data(ww_x_data),
        .me_ov(me_ov), .me_oaddr(me_oaddr), .me_omask(me_omask), .me_odata(me_odata),
        .unit_busy(unit_busy), .issue_unit(issue_unit),
        .qd_v(qd_v), .qd_wbase(qd_wbase), .qd_nb(qd_nb), .qd_tiles(qd_tiles),
        .q_ok(q_ok), .wrel_v(wrel_v));

    // First non-QE comparator path: bank 0 of the reduced L0.router ME op.
    // The other seven ME banks remain on the independent ROM image in this
    // incremental exact gate. A complete comparator must place every weight
    // family on shared, bounded HBM ports with the KV and index traffic.
    reg [31:0] m0_reads = 0, m0_bad = 0;
    generate if (`HDC_ME0_HBM) begin : g_m0_hbm
        wire hq_v, hq_rdy;
        wire [23:0] hq_addr;
        wire [3:0] hq_len;
        wire [5:0] hq_tag;
        wire [3:0] hr_v, hr_rdy;
        wire [4*6-1:0] hr_tag;
        wire [3:0] hr_beat;
        wire [4*256-1:0] hr_data;
        wire [6:0] fetched;
        wire rd = m0_active && mb_re[0];
        ot_hdc_v41x_weight_window #(.WB(MG*32), .SB(256), .WORDS(64),
            .AW(MBAW), .HAW(24), .NPC(4), .LENW(4)) u_win (
            .clk(clk), .rst_n(rst_n), .start(m0_begin), .release_window(m0_release),
            .rom_base(MBAW'(M0_BASE)), .hbm_base(24'd0), .nwords(7'(M0_WORDS)),
            .ready(m0_ok), .hq_v(hq_v), .hq_rdy(hq_rdy),
            .hq_addr(hq_addr), .hq_len(hq_len), .hq_tag(hq_tag),
            .hr_v(hr_v), .hr_rdy(hr_rdy), .hr_tag(hr_tag), .hr_beat(hr_beat),
            .hr_data(hr_data), .rom_re(rd), .rom_addr(mb_addr[0 +: MBAW]),
            .rom_q(m0_q), .fault(m0_fault), .fault_why(m0_fault_why),
            .fetched_words(fetched), .received_sectors(m0_sectors));
        ot_hdc_hbm_model #(.NPC(4), .AW(24), .DW(256), .MEM_WORDS(64),
            .TAGW(6), .LENW(4), .BEATW(1), .QD(32), .RQD(16),
            .CLK_PS(CLK_PS), .PC_RDY(0)) u_hbm (
            .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy),
            .pc_room(), .req_we(1'b0), .req_addr(hq_addr), .req_len(hq_len),
            .req_tag(hq_tag), .req_wdata(256'd0),
            .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag),
            .rsp_beat(hr_beat), .rsp_data(hr_data));
        // Match the banked image's address map exactly: line a*8*MG+8*u is
        // bank 0 lane u. This image is an oracle, never the delivered port.
        reg loaded = 0;
        always @(posedge clk) if (rst_n && !loaded) begin
            for (integer a = 0; a < 64; a = a + 1)
                for (integer u = 0; u < MG; u = u + 1)
                    u_hbm.mem[a][32*u +: 32] = mbank[(M0_BASE+a)*8*MG + 8*u];
            loaded <= 1;
        end
        reg check_v = 0;
        reg [MG*32-1:0] expected;
        always @(posedge clk) begin
            if (check_v && m0_q !== expected) begin
                if (m0_bad < 3) $display("M0_BAD addr=%0d got=%h expected=%h",
                                         mb_addr[0 +: MBAW], m0_q, expected);
                m0_bad <= m0_bad + 1;
            end
            check_v <= rd;
            if (rd) begin
                m0_reads <= m0_reads + 1;
                for (integer u = 0; u < MG; u = u + 1)
                    expected[32*u +: 32] <= mbank[32'(mb_addr[0 +: MBAW])*8*MG + 8*u];
            end
        end
    end else begin : g_m0_rom
        assign m0_ok = 1'b1;
        assign m0_q = '0;
        assign m0_fault = 1'b0;
        assign m0_fault_why = '0;
        assign m0_sectors = 0;
    end endgenerate

    // The streamer's fetch-list and weight HBM are distinct from the index-key HBM.
    reg [15:0] qlead, qrate;
    wire l_re; wire [LAW-1:0] l_addr; reg [127:0] l_q;
    wire xi_re; wire [AW-1:0] xi_addr; reg [31:0] xi_q;
    wire [SPW-1:0] qw_we; wire [SPW*LWIN-1:0] qw_waddr; wire [BL*QLB-1:0] qw_wdata;
    wire qw_re; wire [LWIN-1:0] qw_raddr; reg [BL*QLB-1:0] qw_q;
    wire hq_v, hq_rdy; wire [23:0] hq_addr; wire [5:0] hq_len; wire [LWIN-1:0] hq_tag;
    wire [NPC-1:0] hr_v, hr_rdy, pc_room; wire [NPC*LWIN-1:0] hr_tag;
    wire [NPC*5-1:0] hr_beat; wire [NPC*256-1:0] hr_data;
    wire qs_fault; wire [3:0] qs_why; wire [31:0] qs_fetched, qs_consumed;
    ot_hdc_qstream #(.BL(BL), .QLB(QLB), .AW(AW), .HAW(24), .NW(NW), .LWIN(LWIN),
                     .NPC(NPC), .LENW(6), .BEATW(5), .LAW(LAW)) u_qs (
        .clk(clk), .rst_n(rst_n), .cfg_base(24'd0), .cfg_lbase({LAW{1'b0}}),
        .cfg_lead(qlead), .cfg_rate(qrate), .tok_start(start), .pos(pos),
        .l_re(l_re), .l_addr(l_addr), .l_q(l_q), .vi_re(xi_re), .vi_addr(xi_addr),
        .vi_q(xi_q), .wrel_v(wrel_v), .qd_v(qd_v), .qd_nb(qd_nb),
        .qd_tiles(qd_tiles), .q_ok(q_ok), .qr_re(qrom_re), .qr_addr(qrom_addr),
        .qr_q(qrom_q), .win_we(qw_we), .win_waddr(qw_waddr), .win_wdata(qw_wdata),
        .win_re(qw_re), .win_raddr(qw_raddr), .win_q(qw_q),
        .hq_v(hq_v), .hq_rdy(hq_rdy), .hq_addr(hq_addr), .hq_len(hq_len),
        .hq_tag(hq_tag), .hq_room(pc_room), .hr_v(hr_v), .hr_rdy(hr_rdy),
        .hr_tag(hr_tag), .hr_beat(hr_beat), .hr_data(hr_data),
        .fault(qs_fault), .fault_why(qs_why), .st_fetched(qs_fetched),
        .st_consumed(qs_consumed));
    ot_hdc_hbm_model #(.NPC(NPC), .AW(24), .DW(256), .MEM_WORDS(HMEM),
                       .TAGW(LWIN), .LENW(6), .BEATW(5), .CLK_PS(CLK_PS),
                       .PC_RDY(1), .PC_ROOM(16)) u_hbm (
        .clk(clk), .rst_n(rst_n), .req_v(hq_v), .req_rdy(hq_rdy),
        .pc_room(pc_room), .req_we(1'b0), .req_addr(hq_addr),
        .req_len(hq_len), .req_tag(hq_tag), .req_wdata(256'd0),
        .rsp_v(hr_v), .rsp_rdy(hr_rdy), .rsp_tag(hr_tag),
        .rsp_beat(hr_beat), .rsp_data(hr_data));
    assign qrom_q = qw_q;
    integer qb;
    always @(posedge clk) begin
        if (l_re) l_q <= qlist[l_addr];
        if (xi_re) xi_q <= vm[xi_addr[15:0]];
        for (qb = 0; qb < SPW; qb = qb + 1) begin
            if (qw_re) qw_q[qb*256 +: 256] <= qwin[qb][qw_raddr];
            if (qw_we[qb]) qwin[qb][qw_waddr[qb*LWIN +: LWIN]] <= qw_wdata[qb*256 +: 256];
        end
    end
    reg qchk_v; reg [AW-1:0] qchk_a;
    integer q_bad = 0, q_words = 0, q_ops = 0;
    always @(posedge clk) begin
        qchk_v <= qrom_re; qchk_a <= qrom_addr;
        if (qchk_v) begin
            q_words <= q_words + 1;
            if (qrom_q !== qrom[qchk_a[15:0]]) begin
                if (q_bad < 3) $display("QBAD addr=%0d got=%h expected=%h", qchk_a, qrom_q, qrom[qchk_a[15:0]]);
                q_bad = q_bad + 1;
            end
        end
        if (qd_v) q_ops <= q_ops + 1;
    end
    task qstats;
        integer p, reads;
        begin
            reads = 0;
            for (p = 0; p < NPC; p = p + 1) reads = reads + u_hbm.st_rd[p];
            $display("QSTREAM q_ops=%0d q_words=%0d q_bad=%0d qs_fault=%0d qs_why=%0d fetched=%0d consumed=%0d hbm_reads=%0d",
                     q_ops, q_words, q_bad, qs_fault, qs_why, qs_fetched, qs_consumed, reads);
        end
    endtask
    task m0stats;
        begin
            if (`HDC_ME0_HBM)
                $display("M0_HBM reads=%0d sectors=%0d bad=%0d fault=%0d why=%0d",
                         m0_reads, m0_sectors, m0_bad, m0_fault, m0_fault_why);
        end
    endtask

    // synchronous-read memories
    integer l, q;
    reg [AW:0] xa;
    always @(posedge clk) begin
        if (prog_re) prog_q <= prog[prog_addr];
        if (wrom_re) wrom_q <= wrom[wrom_addr[18:0]];
        for (q = 0; q < SW; q = q + 1) if (ewrom_re[q]) ewrom_q[q*G*W*16 +: G*W*16] <= wrom[ewrom_addr[q*AW +: 19]];
        if (hrom_re) hrom_q <= hrom[hrom_addr[15:0]];
        // ME weight-tile banks: bank b = 8u + c answers chain position c's address ML cycles later
        for (q = 0; q < 8 * MG; q = q + 1)
            mb_p[0][32*q +: 32] <= mbank[32'(mb_addr[(q % 8)*MBAW +: MBAW]) * (8 * MG) + q];
        for (l = 1; l < ML; l = l + 1)
            for (q = 0; q < 8*MG; q = q + 1)
                mb_p[l][32*q +: 32] <= (`HDC_ME0_HBM && m0_active && (q % 8 == 0)) ?
                    m0_q[32*(q/8) +: 32] : mb_p[l-1][32*q +: 32];
        for (q = 0; q < 8; q = q + 1) if (hb_re[q]) hb_q[q*HHW*32 +: HHW*32] <= hbank[{hb_addr[q*HBAW +: HBAW], 3'(q)}];
        for (q = 0; q < HS; q = q + 1) if (vh_re[q]) vh_q[32*q +: 32] <= vm[vh_addr[q*AW +: 16]];
        if (ww_h_we) for (q = 0; q < 32; q = q + 1) if (ww_h_mask[q]) vm[ww_h_addr[15:0] + q] <= ww_h_data[32*q +: 32];
        if (erom_re) erom_q <= erom[erom_addr[18:0]];
        for (q = 0; q < 4*SW; q = q + 1) if (crom_re[q]) crom_q[64*q +: 64] <= crom[crom_addr[q*AW +: 15]];
        if (xcrom_re) xcrom_q <= crom[xcrom_addr[14:0]];
        for (q = 0; q < G; q = q + 1) if (kv_re) kv_q[q*W*32 +: W*32] <= kv[kv_raddr[q*AW +: 15]];
        for (q = 0; q < G; q = q + 1) if (vx_re[q]) vx_q[32*q +: 32] <= vm[vx_addr[q*AW +: 16]];
        for (q = 0; q < 4*SW; q = q + 1) if (vs_re[q]) vs_q[32*q +: 32] <= vm[vs_addr[q*AW +: 16]];
        for (q = 0; q < SW; q = q + 1) if (vi_re[q]) vi_q[32*q +: 32] <= vm[vi_addr[q*AW +: 16]];
        if (vq_re) vq_q <= vm[vq_addr[15:0]];
        if (vr_re) vr_q <= vm[vr_addr[15:0]];
        if (wqr_re) for (q = 0; q < 32; q = q + 1) wqr_q[32*q +: 32] <= vm[wqr_addr[15:0] + q];
        if (wxr_re) for (q = 0; q < 32; q = q + 1) wxr_q[32*q +: 32] <= vm[wxr_addr[15:0] + q];
        for (q = 0; q < XSQ; q = q + 1)
            if (vsl_re[q]) for (l = 0; l < XSW; l = l + 1) vsl_q[32*(q*XSW + l) +: 32] <= vm[vsl_addr[q*AW +: 16] + l];
        for (q = 0; q < SW; q = q + 1)
            if (kv_we[q]) kv[kv_waddr[q*AW+4 +: 15]][32*kv_waddr[q*AW +: 4] +: 32] <= kv_wdata[32*q +: 32];
        for (q = 0; q < G; q = q + 1)
            if (vw_me_we[q])
                for (l = 0; l < W; l = l + 1)
                    if (vw_me_mask[q*W + l]) vm[{vw_me_addr[q*AW +: 12], 4'b0} + l] <= vw_me_data[32*(q*W + l) +: 32];
        for (q = 0; q < SW; q = q + 1) if (vw_su_we[q]) vm[vw_su_addr[q*AW +: 16]] <= vw_su_data[32*q +: 32];
        for (q = 0; q < SW; q = q + 1) if (vw_rd_we[q]) vm[vw_rd_addr[q*AW +: 16]] <= vw_rd_data[32*q +: 32];
        // the vector unit (X_SU): reads by source, element and KV writes, reducer results
        for (q = 0; q < SUN; q = q + 1) if (xs_vi_re[q]) xs_vi_q[32*q +: 32] <= vm[xs_vi_addr[q*AW +: 16]];
        for (q = 0; q < 4*SUN; q = q + 1) if (xs_rd_re[q]) begin
            xa = xs_rd_addr[q*AW +: AW];
            case (xs_rd_src[2*q +: 2])
                2'd0: xs_rd_q[32*q +: 32] <= vm[xa[15:0]];
                2'd1: xs_rd_q[32*q +: 32] <= crom[xa[14:0]][31:0];
                2'd2: xs_rd_q[32*q +: 32] <= crom[xa[14:0]][63:32];
                default: xs_rd_q[32*q +: 32] <= {wrom[xa[24:6]][16*xa[5:0] +: 16], 16'h0000};
            endcase
        end
        for (q = 0; q < SUN; q = q + 1) begin
            if (xs_vm_we[q]) vm[xs_vm_waddr[q*AW +: 16]] <= xs_vm_wdata[32*q +: 32];
            if (xs_kv_we[q]) kv[xs_kv_waddr[q*AW+4 +: 15]][32*xs_kv_waddr[q*AW +: 4] +: 32] <= xs_kv_wdata[32*q +: 32];
        end
        for (q = 0; q < SUN/8; q = q + 1) if (xs_res_we[q]) vm[xs_res_addr[q*AW +: 16]] <= xs_res_data[32*q +: 32];
        if (vw_xe_we) vm[vw_xe_addr[15:0]] <= vw_xe_data;
        if (ww_q_we) for (q = 0; q < 32; q = q + 1) if (ww_q_mask[q]) vm[ww_q_addr[15:0] + q] <= ww_q_data[32*q +: 32];
        if (ww_x_we) for (q = 0; q < 32; q = q + 1) if (ww_x_mask[q]) vm[ww_x_addr[15:0] + q] <= ww_x_data[32*q +: 32];
        // the result words of the one unwritten matrix-vector op are the logits
        if (me_ov && vw_me_we == 0)
            for (q = 0; q < G; q = q + 1)
                for (l = 0; l < W; l = l + 1)
                    if (me_omask[q*W + l] && ({me_oaddr[q*AW +: 12], 4'b0} + l) < VOCAB)
                        lg[{me_oaddr[q*AW +: 12], 4'b0} + l] <= me_odata[32*(q*W + l) +: 32];
    end

    wire [63:0] x_cnt_he, x_cnt_me, x_cnt_att, x_cnt_idx, x_cnt_su;
    wire [47:0] x_idx_ks, x_idx_hb, x_idx_sc, x_idx_hs;
    wire [31:0] x_idx_kw;
`ifdef HDC_ME0_HBM_GATE
    // The local simulator resolves hierarchical references in inactive generate
    // branches. These optional debug counters do not enter the exact gate.
    assign x_cnt_idx = 0;
    assign x_cnt_he = 0; assign x_cnt_me = 0;
    assign x_cnt_att = 0; assign x_cnt_su = 0;
    assign x_idx_ks = 0; assign x_idx_hb = 0; assign x_idx_sc = 0;
    assign x_idx_hs = 0; assign x_idx_kw = 0;
`else
    generate
        if (`HDC_X_IDX == 2) begin : g_cnt_idx_pool
            assign x_cnt_idx = {dut.g_idx_x.g_pool.u_idx.dbg_ops, dut.g_idx_x.g_pool.u_idx.dbg_elems};
            assign x_idx_ks = dut.g_idx_x.g_pool.u_idx.dbg_keys_streamed;
            assign x_idx_hb = dut.g_idx_x.g_pool.u_idx.dbg_hbm_beats;
            assign x_idx_sc = dut.g_idx_x.g_pool.u_idx.dbg_keys_scored;
            assign x_idx_hs = dut.g_idx_x.g_pool.u_idx.dbg_headsums_fused;
            assign x_idx_kw = dut.g_idx_x.g_pool.u_kwr.dbg_keys;
        end else if (`HDC_X_IDX == 1) begin : g_cnt_idx
            assign x_cnt_idx = {dut.g_idx_x.g_legacy.u_idx.dbg_ops, dut.g_idx_x.g_legacy.u_idx.dbg_elems};
            assign x_idx_ks = dut.g_idx_x.g_legacy.u_idx.dbg_keys_streamed;
            assign x_idx_hb = dut.g_idx_x.g_legacy.u_idx.dbg_hbm_beats;
            assign x_idx_sc = dut.g_idx_x.g_legacy.u_idx.dbg_keys_scored;
            assign x_idx_hs = dut.g_idx_x.g_legacy.u_idx.dbg_headsums_fused;
            assign x_idx_kw = dut.g_idx_x.g_legacy.u_kwr.dbg_keys;
        end else begin : g_cnt_idx_n
            assign x_cnt_idx = 64'd0; assign x_idx_ks = 0; assign x_idx_hb = 0; assign x_idx_sc = 0;
            assign x_idx_hs = 0; assign x_idx_kw = 0;
        end
        if (`HDC_X_HE) begin : g_cnt_he
            assign x_cnt_he = {dut.g_he_x.u_he.dbg_ops, dut.g_he_x.u_he.dbg_elems};
        end else begin : g_cnt_he_n
            assign x_cnt_he = 64'd0;
        end
        if (`HDC_X_ME) begin : g_cnt_me
            assign x_cnt_me = {dut.g_me_x.u_mw.dbg_ops, dut.g_me_x.u_mw.dbg_elems};
        end else begin : g_cnt_me_n
            assign x_cnt_me = 64'd0;
        end
        if (`HDC_X_ATT) begin : g_cnt_att
            assign x_cnt_att = {dut.g_att_x.u_att.dbg_ops, dut.g_att_x.u_att.dbg_elems};
        end else begin : g_cnt_att_n
            assign x_cnt_att = 64'd0;
        end
        if (`HDC_X_SU) begin : g_cnt_su
            assign x_cnt_su = {dut.g_su_x.u_su.dbg_ops, dut.g_su_x.u_su.dbg_elems};
        end else begin : g_cnt_su_n
            assign x_cnt_su = 64'd0;
        end
    endgenerate
`endif
    wire [63:0] x_cnt_sel, x_cnt_eg;
    wire [31:0] x_sel_reps;
    generate
        if (`HDC_X_SEL || `HDC_X_EG) begin : g_cnt_xu
            assign x_cnt_sel = {dut.g_xu_x.u_xu.dbg_sel_ops, dut.g_xu_x.u_xu.dbg_sel_elems};
            assign x_sel_reps = dut.g_xu_x.u_xu.dbg_sel_reps;
            assign x_cnt_eg = {dut.g_xu_x.u_xu.dbg_eg_ops, dut.g_xu_x.u_xu.dbg_eg_elems};
        end else begin : g_cnt_xu_n
            assign x_cnt_sel = 64'd0; assign x_sel_reps = 32'd0; assign x_cnt_eg = 64'd0;
        end
    endgenerate
    reg [8*512-1:0] dir;
    integer cyc = 0, i, bad_lg, bad_vm, bad_kv, n_prime = 0, pfirst = 0, prime_i = 0;
    reg trace = 1'b0, multi = 1'b0, running = 1'b0, dbg = 1'b0;
    reg [NW-1:0] prompt [0:255];
    reg [NW-1:0] gold_gen [0:255];
    reg [NW-1:0] prime [0:7];
    integer n_prompt = 0, n_gen = 0, step = 0, gen_bad = 0;
    reg [63:0] total_cycles = 0;
    integer busy_me = 0, busy_su = 0, busy_qe = 0, busy_xu = 0, busy_he = 0, all_idle = 0;
    always @(posedge clk) if (dut.st != 0) begin
        if (unit_busy[0]) busy_me <= busy_me + 1;
        if (unit_busy[1]) busy_su <= busy_su + 1;
        if (unit_busy[2]) busy_qe <= busy_qe + 1;
        if (unit_busy[3]) busy_xu <= busy_xu + 1;
        if (unit_busy[4]) busy_he <= busy_he + 1;
        if (unit_busy == 0) all_idle <= all_idle + 1;
    end
    reg [31:0] kv_e;
    reg [4:0] busy_q = 5'd0;
    initial begin
        if (!$value$plusargs("DIR=%s", dir)) dir = ".";
        if ($test$plusargs("TRACE")) trace = 1'b1;
        if ($test$plusargs("DBG")) dbg = 1'b1;
        if (!$value$plusargs("TOKEN=%d", token)) token = 0;
        if (!$value$plusargs("POS=%d", pos)) pos = 0;
        if (!$value$plusargs("EXPECT=%d", expect_tok)) expect_tok = 0;
        if (!$value$plusargs("NPRIME=%d", n_prime)) n_prime = 0;
        if (!$value$plusargs("PFIRST=%d", pfirst)) pfirst = 0;
        $readmemh({dir, "/wrom.hex"}, wrom);
        $readmemh({dir, "/qrom.hex"}, qrom);
        $readmemh({dir, "/qlist.hex"}, qlist);
        for (i = 0; i < HMEM; i = i + 1) u_hbm.mem[i] = 256'd0;
        $readmemh({dir, "/hbm_q.hex"}, u_hbm.mem);
        if (!$value$plusargs("QLEAD=%d", qlead)) qlead = 512;
        if (!$value$plusargs("QRATE=%d", qrate)) qrate = 0;
        $readmemh({dir, "/hrom.hex"}, hrom);
        if (`HDC_X_HE) $readmemh({dir, "/hbank.hex"}, hbank);
        $readmemh({dir, "/cfg.hex"}, cfg);
        if (`HDC_X_ME) $readmemh({dir, "/mbank.hex"}, mbank);
        $readmemh({dir, "/erom.hex"}, erom);
        $readmemh({dir, "/crom.hex"}, crom);
        $readmemh({dir, "/prog.hex"}, prog);
        if ($test$plusargs("MULTI")) multi = 1'b1;
        if (!$value$plusargs("NPROMPT=%d", n_prompt)) n_prompt = 0;
        if (!$value$plusargs("NGEN=%d", n_gen)) n_gen = 0;
        for (i = 0; i < VM_ELEMS; i = i + 1) vm[i] = 32'd0;
        for (i = 0; i < KV_WORDS; i = i + 1) kv[i] = {(W*32){1'b0}};
        if (multi) begin
            $readmemh({dir, "/prompt.hex"}, prompt);
            $readmemh({dir, "/generated.hex"}, gold_gen);
            $readmemh({dir, "/expect_multi_vm.hex"}, e_vm);
            $readmemh({dir, "/expect_multi_kv.hex"}, e_kv);
        end else begin
            $readmemh({dir, "/kv.hex"}, kvimg);
            for (i = 0; i < KV_WORDS * W; i = i + 1) kv[i / W][32*(i % W) +: 32] = kvimg[i];
            $readmemh({dir, "/vm_init.hex"}, vm);
            $readmemh({dir, "/prime.hex"}, prime);
            $readmemh({dir, "/expect_vm.hex"}, e_vm);
            $readmemh({dir, "/expect_kv.hex"}, e_kv);
            $readmemh({dir, "/expect_logits.hex"}, e_lg);
        end
        for (i = 0; i < VOCAB; i = i + 1) lg[i] = 32'hFFFFFFFF;
    end

    // activation counters of the re-specified units: "XCNT unit=<u> ops=<n> elems=<n>" (the campaign asserts them)
    task print_counters;
        begin
            if (`HDC_X_HE) $display("XCNT unit=he ops=%0d elems=%0d", x_cnt_he[63:32], x_cnt_he[31:0]);
            if (`HDC_X_ME) $display("XCNT unit=me ops=%0d elems=%0d", x_cnt_me[63:32], x_cnt_me[31:0]);
            if (`HDC_X_ATT) $display("XCNT unit=att ops=%0d elems=%0d", x_cnt_att[63:32], x_cnt_att[31:0]);
            if (`HDC_X_SU) $display("XCNT unit=su ops=%0d elems=%0d", x_cnt_su[63:32], x_cnt_su[31:0]);
            if (`HDC_X_SEL) $display("XCNT unit=sel ops=%0d elems=%0d reps=%0d", x_cnt_sel[63:32], x_cnt_sel[31:0],
                                     x_sel_reps);
            if (`HDC_X_EG) $display("XCNT unit=eg ops=%0d elems=%0d", x_cnt_eg[63:32], x_cnt_eg[31:0]);
            if (`HDC_X_IDX) begin
                $display("XCNT unit=idx ops=%0d elems=%0d", x_cnt_idx[63:32], x_cnt_idx[31:0]);
                // ops = keys the HBM key stream delivered, elems = HBM beats; keys scored / head terms fused
                // inside the engine; index keys written to the HBM image
                $display("XCNT unit=idx_hbm ops=%0d elems=%0d", x_idx_ks, x_idx_hb);
                $display("XCNT unit=idx_fused ops=%0d elems=%0d", x_idx_sc, x_idx_hs);
                $display("XCNT unit=idx_kwr ops=%0d elems=%0d", x_idx_kw, x_idx_kw);
            end
            if (`HDC_X_IDX == 2)
                $display("IDXHBMWR records=%0d writes=%0d highwater=%0d read_stalls=%0d writer_stalls=%0d refreshes=%0d refpb=3",
                    idxwr_records,idxwr_writes,idxwr_highwater,idxwr_read_stalls,
                    idxwr_writer_stalls,idxwr_refreshes);
        end
    endtask

    task check_state(input integer check_logits);
        begin
            print_counters();
            bad_lg = 0; bad_vm = 0; bad_kv = 0;
            if ($test$plusargs("DUMP")) $writememh({dir, "/rtl_vm.hex"}, vm);
            if (check_logits)
                for (i = 0; i < VOCAB; i = i + 1) if (lg[i] !== e_lg[i]) begin
                    if (bad_lg < 5) $display("logit %0d rtl %h expect %h", i, lg[i], e_lg[i]);
                    bad_lg = bad_lg + 1;
                end
            for (i = 0; i < VM_ELEMS; i = i + 1) if (vm[i] !== e_vm[i]) begin
                if (bad_vm < 10) $display("vm %0d rtl %h expect %h", i, vm[i], e_vm[i]);
                bad_vm = bad_vm + 1;
            end
            for (i = 0; i < KV_WORDS * W; i = i + 1) begin
                kv_e = kv[i / W][32*(i % W) +: 32];
                if (kv_e !== e_kv[i]) begin
                    if (bad_kv < 10) $display("kv %0d rtl %h expect %h", i, kv_e, e_kv[i]);
                    bad_kv = bad_kv + 1;
                end
            end
        end
    endtask

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 5) rst_n <= 1'b1;
        // prime the Engram hash history with the tokens before POS (single step)
        prime_v <= 1'b0;
        if (!multi && cyc >= 8 && prime_i < n_prime) begin
            prime_v <= 1'b1; prime_cid <= prime[prime_i][11:0]; prime_first <= (prime_i == 0) && pfirst;
            prime_i <= prime_i + 1;
        end
        start <= (cyc == 30);
        if (cyc == 29 && multi) begin token <= prompt[0]; pos <= 0; step <= 0; end
        if (multi && cyc > 32 && done && !start) begin
            total_cycles = total_cycles + cycles;
            $display("STEP pos=%0d in=%0d out=%0d gold=%0d cycles=%0d fault=%0d", pos, token, next_token,
                     (step >= n_prompt - 1) ? gold_gen[step - (n_prompt - 1)] : 0, cycles, fault);
            if (step >= n_prompt - 1 && (next_token != gold_gen[step - (n_prompt - 1)])) gen_bad = gen_bad + 1;
            if (fault) gen_bad = gen_bad + 1;
            if (step + 1 == n_prompt + n_gen - 1) begin
                check_state(0);
                $display("HDC41_MULTI steps=%0d generated=%0d mismatches=%0d total_cycles=%0d vm_mismatch=%0d kv_mismatch=%0d",
                         step + 1, n_gen, gen_bad, total_cycles, bad_vm, bad_kv);
                qstats();
                m0stats();
                if (gen_bad == 0 && bad_vm == 0 && bad_kv == 0 && !qs_fault && q_bad == 0 &&
                    (!`HDC_ME0_HBM || (m0_reads > 0 && m0_sectors == M0_WORDS &&
                                      m0_bad == 0 && !m0_fault)))
                    $display("PASS"); else $display("FAIL");
                $finish;
            end
            step <= step + 1;
            token <= (step + 1 < n_prompt) ? prompt[step + 1] : next_token;
            pos <= pos + 1;
            start <= 1'b1;
        end
        if (!multi && cyc > 32 && done) begin
            check_state(1);
            $display("HDC41 token=%0d pos=%0d next_token=%0d expect=%0d cycles=%0d fault=%0d logit_mismatch=%0d vm_mismatch=%0d kv_mismatch=%0d",
                     token, pos, next_token, expect_tok, cycles, fault, bad_lg, bad_vm, bad_kv);
            $display("UTIL me_busy=%0d su_busy=%0d qe_busy=%0d xu_busy=%0d he_busy=%0d all_idle=%0d", busy_me,
                     busy_su, busy_qe, busy_xu, busy_he, all_idle);
                qstats();
                m0stats();
                if (next_token == expect_tok && !fault && bad_lg == 0 && bad_vm == 0 && bad_kv == 0 &&
                    !qs_fault && q_bad == 0 &&
                    (!`HDC_ME0_HBM || (m0_reads > 0 && m0_sectors == M0_WORDS &&
                                      m0_bad == 0 && !m0_fault)))
                $display("PASS");
            else
                $display("FAIL");
            $finish;
        end
        if (dbg && (vw_su_we[0] || vw_rd_we[0] || kv_we[0]))
            $display("DBG cyc=%0d su_we=%0d a=%0d d=%h rd_we=%0d a=%0d d=%h kv_we=%0d a=%0d d=%h", cycles, vw_su_we[0],
                     vw_su_addr[AW-1:0], vw_su_data[31:0], vw_rd_we[0], vw_rd_addr[AW-1:0], vw_rd_data[31:0], kv_we[0],
                     kv_waddr[AW-1:0], kv_wdata[31:0]);
        if (dbg && (unit_busy != busy_q))
            $display("BUSY cyc=%0d units=%b", cycles, unit_busy);
        busy_q <= unit_busy;
        if (trace && issue_unit != 0)
            $display("ISSUE cyc=%0d pc=%0d unit=%0d", cycles, dut.pc, issue_unit);
        if (cyc > 50000000) begin
            $display("TIMEOUT pc=%0d st=%0d idles=%b", dut.pc, dut.st, dut.idles);
            $finish;
        end
    end
endmodule
