// Full36+head consumer source connection; runtime is not exercised here.
// Derived from the existing additive P0 root, SHA256 7c1312ebcb748df8ddd150aafa5263080668b11f511d46cf1cd40aed21bf89b9.
// All compute, rounding, actual ROM/SRAM ports, stage controls and KV owners
// are retained. Only the embedded simulation provider is removed and its real
// typed boundary exported. Same priced model851.8086996; no new hardware,
// storage or latency. Physical adapter/transport and final token gates remain
// with the owners; no constant producer returns or unprotected runtime path.
// Additive full-shape original-AR consumer join. NEAR_HBM=0, DSpark OFF.
// Existing core/program/ROM/vector/tile/collective semantics retained.
// SOURCE CONNECTION ONLY: protected provider numerical/physical gates and
// missing real full-width transport are NOT qualified by this module.
// SOURCE-ONLY donor rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12_stream4.sv @14dbc8e20 SHA256 d052c15b427eb88a63134edf1646c68ad32554c7b019d5d2c906d6c3754b0f9d
`timescale 1ns/1ps
// Required geometry and owner clock policy remain explicit below.
module ot_qwen_p0_full_consumer_exports #(
    parameter integer PROTECTED_STREAM4 = 0, // source candidate, opt-in until owner gates pass
    parameter integer BASELINE_AR = 0, // explicit owner selection; off by default
    parameter integer CORE_FS = 833333, CTL_FS = 1024000,
    parameter integer G = 6144,
    parameter integer NW = 18,
    parameter integer SNW = 18,
    parameter integer QWEN_FULLSHAPE = 1,
    parameter integer ME_IDLE_GATE = 1,
    parameter integer SW = 64,
    parameter integer LV = 7,
    parameter integer SMIN = 7,
    parameter integer SMAX = 11,
    parameter integer TCUT = 7,
    parameter integer BD = 1,
    parameter integer XVM = 0,
    parameter integer NWS = 0,
    parameter integer TWS = 0,
    parameter integer ORD = 0,
    parameter integer SCALE_LOCAL = 0,
    parameter integer MEM_EXTRA = 0,
    parameter integer ACC_LAT = 5,
    parameter integer TREE_LAT = 3,
    parameter integer MUL_LAT = 5,
    parameter integer FAST_ISSUE = 0,
    parameter integer KV_PREP = 0,
    parameter integer ENABLE_AR256 = 0,
    parameter integer D = 4,
    // REAL_MEM
    parameter integer REAL_MEM = 1,
    parameter integer SCALE_BANKS = 13,      // 4096-word macros per scale port (>= scale words / 4096)
    parameter integer CROM_WORDS = 1048576,
    parameter integer VM_ELEMS = 177808,
    parameter integer NSTK = 4,                // HBM3E stacks a die
    parameter integer NPC = 32 * NSTK,
    parameter integer HBM_LAYERS = 3,
    parameter integer FILL_LAT = 8,
    parameter integer NRD = 256,
    parameter integer LKA = 512,              // unused (fill-service parameter, kept for the driver)
    parameter integer WBW = 1,                // token write-backs a cycle (distinct PCs)
    parameter integer HBM_PHASE = 0,          // refresh phase of the stack's REFpb schedule
    parameter integer HBM_PULLIN = 0,         // controller refresh pull-in (ot_hbm_r14_stream_pc PULLIN)
    parameter integer EMBED_ROM = 1         // the token's X from the INT8 embedding ROM (stage E); 0: X preloaded
) (
    // Actual protected producer boundary. Owner stack/transport adapter must
    // supply these returns; there is no simulation backend or fake PHY here.
    output wire producer_clk, producer_hclk, producer_por_n, producer_warm_rst_n,
    output wire stream_d_v, stream_go,
    input wire stream_d_rdy,
    output wire [18:0] stream_d_row,
    output wire [10:0] stream_d_n,
    input wire [NPC-1:0] stream_l_v, stream_w_room, stream_wd_v,
    output wire [NPC-1:0] stream_l_pop, stream_w_v,
    input wire [NPC*17-1:0] stream_l_sec,
    input wire [NPC*8-1:0] stream_l_row,
    input wire [NPC*256-1:0] stream_l_data,
    output wire [NPC*24-1:0] stream_w_sec,
    output wire [NPC*256-1:0] stream_w_data,
    output wire [NPC*9-1:0] stream_w_tag,
    input wire [NPC*9-1:0] stream_wd_tag,
    input wire producer_fault,
    input wire [15:0] producer_fault_code,
    input  wire              clk,
    input  wire              hclk, // independent periodic 1024ps controller root
    input  wire              warm_rst_n, // admission pause only; cold POR is rt_rst_n
    output reg               rt_rst_n,
    output reg  [31:0]       cyc,
    output reg               start,
    input  wire [SNW-1:0]    tp_token,
    input  wire [SNW-1:0]    tp_pos,
    input  wire              rm_kv_ideal,       // A/B reference: KV service HBM bypassed (run-time strap)
    input  wire [7:0]        rm_layer,          // the stage's layer (its HBM KV region); 255: no KV (embedding stage)
    input  wire [7:0]        rm_next_layer,     // the layer of the next stage (notice); 255: none
    input  wire              rm_early_go,       // strap: release the next layer's stream at this layer's kv_free
    input  wire              rm_posted_wb,      // strap: posted token write-back
    output wire              kv_wb_busy,        // write-backs outstanding (the host drains before reading HBM)
    input  wire              h_start,
    output wire              me_clk_en,
    output wire              s_done,
    output wire              s_fault,
    output wire              core_fault,
    output wire [SNW-1:0]    seq_ntok,
    output wire [31:0]       seq_nval,
    output wire [31:0]       core_cycles,
    output wire              c_valid,
    input  wire              c_ready,
    output wire [511:0]      c_data,
    output wire              c_last,
    output wire              c_mode,
    output wire [31:0]       c_tag,
    input  wire              r_valid,
    input  wire [511:0]      r_data,
    input  wire              r_last,
    input  wire [((D > 2) ? 2 : 1)-1:0] r_rank,
    input  wire              r_err,
    output wire [11:0]       prog_base,
    // array spine: tile fabric
    output wire              tgo,
    output wire [3*NW+13*24+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(G >> TCUT)*16*32-1:0] t_lvl,
    input  wire              fab_fault,
    // tile KV slice write ports (to ot_qwen_rom_tile_w12 kvw_*)
    output wire [G/4-1:0]     kvw_ce,
    output wire [G/4*7-1:0]   kvw_addr,
    output wire [G/4*512-1:0] kvw_data,
    output wire [G/4*512-1:0] kvw_mask,
    // memory-service status
    output wire              mem_fault,
    output wire [15:0]       kv_fault_code,
    output wire              kv_ok_o,
    output wire              kv_drained_o,
    output wire [31:0]       st_fill_cycles, st_fill_sectors, st_wr_sectors, st_rsp_stall,
    output wire [31:0]       st_kvok_low_desc, st_drain_low, st_wr_lat_max, st_fill_exposed,
    output reg  [31:0]       st_stall_kv, st_stall_drain, st_stall_bridge, st_stall_retire, st_stall_mem
);
    localparam integer W=16, AW=24, PAW=12, DAW=6, FW=512, NPORT = G >> SMIN, NXC = 1 << SMAX;
    initial begin
        // No raw mutable path is runnable through this successor. The default
        // remains off; the source recipe must explicitly select the candidate.
        if (PROTECTED_STREAM4 != 1 || HBM_PULLIN != 0 || CORE_FS != 833333 || CTL_FS != 1024000)
            $fatal(1,"P0 requires protected STREAM4, PULLIN0 and independent owner clocks");
        if(BASELINE_AR!=1 || G!=6144 || SW!=64 || D!=4 || NW!=18 || SNW!=18 ||
           HBM_LAYERS!=36 || NSTK!=4 || NPC!=128 || WBW!=4 || ENABLE_AR256!=1 || REAL_MEM!=1)
            $fatal(1,"owner-selected plain AR STREAM4 full36 geometry required");
        rt_rst_n = 0; start = 0; cyc = 0;
    end
    always @(posedge clk) begin
        cyc <= cyc+1;
        if (cyc==5) rt_rst_n <= 1;
        if (cyc==7) start <= 1;
        if (cyc==8) start <= 0;
    end
    wire rst_n = rt_rst_n;
    wire core_start, core_done;
    wire [SNW-1:0] core_tok, core_pos, core_ntok;
    wire [31:0] core_nval;
    wire coll_busy;
    wire [NW-1:0] core_ntok_c;
    assign core_ntok = core_ntok_c;
    // core memory ports
    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q;
    wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;
    wire s_vre; wire [7:0] s_vraddr; reg [511:0] s_vrq; wire s_vwe; wire [7:0] s_vwaddr; wire [511:0] s_vwdata;
    wire wrom_re, int8_wrom_re; wire [23:0] int8_wrom_addr;
    wire scale_re; wire [NPORT-1:0] scale_gre; wire [NPORT*24-1:0] scale_addr; wire [NPORT*256-1:0] scale_q;
    wire [SW-1:0] crom_re; wire [SW*24-1:0] crom_addr; reg [SW*64-1:0] crom_q;
    wire kv_re; wire [SW-1:0] kv_we; wire [SW*24-1:0] kv_waddr; wire [SW*32-1:0] kv_wdata;
    wire [SW-1:0] va_re, vb_re, vc_re; wire [SW*24-1:0] va_addr, vb_addr, vc_addr; reg [SW*32-1:0] va_q, vb_q, vc_q;
    wire [SW-1:0] vw_su_we; wire [SW*24-1:0] vw_su_addr; wire [SW*32-1:0] vw_su_data;
    wire vw_rd_we; wire [23:0] vw_rd_addr; wire [31:0] vw_rd_data;
    wire vw_mx_we; wire [23:0] vw_mx_addr; wire [15:0] vw_mx_mask; wire [511:0] vw_mx_data;
    wire [NPORT-1:0] vw_me_we; wire [NPORT*24-1:0] vw_me_addr; wire [NPORT*16-1:0] vw_me_mask; wire [NPORT*512-1:0] vw_me_data;
    wire [NXC-1:0] vx_re; wire [NXC*24-1:0] vx_addr; reg [NXC*32-1:0] vx_q;
    wire kvd_v, kvd_kindk; wire [NW-1:0] kvd_pos;
    wire kv_ok, kv_write_drained, kv_write_flush;
    wire scale_ready, w_ok_svc, emb_ok_svc, me_mem_ok_svc;
    wire embed_code_re, embed_scale_re; wire [23:0] embed_code_addr; wire [NW-1:0] embed_scale_addr;
    wire [511:0] embed_code_q; wire [15:0] embed_scale_q; wire emb_fault;
    ot_qwen_rom_core #(.W(W),.G(G),.AW(AW),.NW(NW),.PAW(PAW),
        .SU_VEC(1),.SW(SW),.LV(LV),.KV_FP8(1),
        .INT8_WEIGHT(1),.INT8_SCALE_WCS_BASE(1),.INT8_EMBED(EMBED_ROM),.QWEN_FULLSHAPE(QWEN_FULLSHAPE),
        //: the Qwen3-8B DYN constants (tools/hdc_program.py dyn_values: token*H, pos*half, K/V write offsets
        //: with head_dim 128).  ot_qwen_rom_rt_die_w12 leaves the core defaults HID 128 / HALF 8 / HD 16 (the
        //: reduced model's): every DYN offset is 0 at position 0, so the retained position-0 token is
        //: unaffected, but at any other position the RoPE row and the K/V write addresses would be wrong.
        .HID(4096),.HALF(64),.HD(128),.EMB_CODE_LANES(64),.EMB_ADDR_BASE(0),
        .KV_HBM(1),.KV_VEC_WRITE_BRIDGE(1),
        .ME_STALL(1),.ME_IDLE_GATE(ME_IDLE_GATE),
        .SMIN(SMIN),.SMAX(SMAX),.TCUT(TCUT),.BD(BD),.XVM(XVM),.NWS(NWS),.TWS(TWS),.ORD(ORD),.SCALE_LOCAL(SCALE_LOCAL),.MEM_EXTRA(MEM_EXTRA),
        .ACC_LAT(ACC_LAT),.TREE_LAT(TREE_LAT),.MUL_LAT(MUL_LAT),
        .FAST_ISSUE(FAST_ISSUE),.KV_PREP(KV_PREP)) core (
        .clk(clk),.rst_n(rst_n),.start(core_start),.token(core_tok[NW-1:0]),.pos(core_pos[NW-1:0]),
        .done(core_done),.next_token(core_ntok_c),.next_val(core_nval),
        .cycles(core_cycles),.fault(core_fault),
        .prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),
        .wrom_re(wrom_re),.wrom_addr(),.wrom_q({(G*W*16){1'b0}}),
        .int8_wrom_re(int8_wrom_re),.int8_wrom_addr(int8_wrom_addr),
        .scale_re(scale_re),.scale_gre(scale_gre),.scale_addr(scale_addr),.scale_q(scale_q),
        .embed_code_re(embed_code_re),.embed_code_addr(embed_code_addr),.embed_code_q(embed_code_q),
        .embed_scale_re(embed_scale_re),.embed_scale_addr(embed_scale_addr),.embed_scale_q(embed_scale_q),
        .crom_re(crom_re),.crom_addr(crom_addr),.crom_q(crom_q),
        .kv_re(kv_re),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_write_drained(kv_write_drained),.kv_write_flush(kv_write_flush),
        .va_re(va_re),.va_addr(va_addr),.va_q(va_q),
        .vb_re(vb_re),.vb_addr(vb_addr),.vb_q(vb_q),
        .vc_re(vc_re),.vc_addr(vc_addr),.vc_q(vc_q),
        .vw_me_we(vw_me_we),.vw_me_addr(vw_me_addr),.vw_me_mask(vw_me_mask),.vw_me_data(vw_me_data),
        .vw_su_we(vw_su_we),.vw_su_addr(vw_su_addr),.vw_su_data(vw_su_data),
        .vw_rd_we(vw_rd_we),.vw_rd_addr(vw_rd_addr),.vw_rd_data(vw_rd_data),
        .vw_mx_we(vw_mx_we),.vw_mx_addr(vw_mx_addr),.vw_mx_mask(vw_mx_mask),.vw_mx_data(vw_mx_data),
        .me_ov(),
        .kvd_v(kvd_v),.kvd_wbase(),.kvd_ts(),.kvd_ks(),.kvd_js(),.kvd_wcs(),.kvd_split(),.kvd_jsh(),
        .kvd_tiles(),.kvd_k(),.kvd_nout(),.kvd_kindk(kvd_kindk),.kvd_pos(kvd_pos),.kv_ok(kv_ok),
        .wrom_su(),.wd_v(),.wd_wbase(),.wd_sbase(),.wd_tiles(),.wd_k(),.wd_nout(),
        .vx_re(vx_re),.vx_addr(vx_addr),.vx_q(vx_q),
        .tgo(tgo),.tb(tb),.xl_d(xl_d),.t_lvl(t_lvl),.fab_fault(fab_fault),
        .w_ok(w_ok_svc),.emb_ok(emb_ok_svc),.me_mem_ok(me_mem_ok_svc),.me_clk_en(me_clk_en));
    ot_qwen_tp_seq_w12 #(.N(D),.NW(SNW),.PAW(PAW),.VWA(8),.DAW(DAW),.FW(FW),.TAGW(32),
                    .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .ENABLE_AR256(ENABLE_AR256)) seq (
        .clk(clk),.rst_n(rst_n),.start(start | h_start),.token(tp_token),.pos(tp_pos),
        .done(s_done),.next_token(seq_ntok),.next_val(seq_nval),
        .fault(s_fault),.coll_busy(coll_busy),
        .core_start(core_start),.core_token(core_tok),.core_pos(core_pos),
        .core_done(core_done),.core_next_token(core_ntok),.core_next_val(core_nval),
        .core_fault(core_fault),.prog_base(prog_base),
        .desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
        .vm_re(s_vre),.vm_raddr(s_vraddr),.vm_rq(s_vrq),
        .vm_we(s_vwe),.vm_waddr(s_vwaddr),.vm_wdata(s_vwdata),
        .c_valid(c_valid),.c_ready(c_ready),.c_data(c_data),
        .c_last(c_last),.c_mode(c_mode),.c_tag(c_tag),
        .r_valid(r_valid),.r_data(r_data),.r_last(r_last),
        .r_rank(r_rank),.r_err(r_err));

    // ---- program ROM, segment descriptors, constant ROM (host-preloaded arrays) -----------
    reg [1023:0] prog_mem [0:63]      /*verilator public_flat_rw*/;
    reg [63:0]   desc_mem [0:7]       /*verilator public_flat_rw*/;
    reg [63:0]   crom_mem [0:CROM_WORDS-1] /*verilator public_flat_rw*/;
    reg [31:0]   crom_words           /*verilator public_flat_rw*/;
    reg          rom_fault;
    wire [11:0]  prog_a = prog_base + prog_addr;
    integer li;
    always @(posedge clk) begin
        if (prog_re) prog_q <= (prog_a < 64) ? prog_mem[prog_a[5:0]] : 1024'd0;
        if (desc_re) desc_q <= (desc_addr < 8) ? desc_mem[desc_addr[2:0]] : 64'd0;
        for (li = 0; li < SW; li = li + 1)
            if (crom_re[li]) crom_q[li*64 +: 64] <= crom_mem[crom_addr[li*24 +: 20]];
    end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) rom_fault <= 1'b0;
        else begin
            for (li = 0; li < SW; li = li + 1)
                if (crom_re[li] && crom_addr[li*24 +: 24] >= crom_words) rom_fault <= 1'b1;
            if (wrom_re) rom_fault <= 1'b1;            // the stream unit's BF16 weight-ROM port is never used
        end
    end

    // ---- scale ROM: one macro bank per result port ------------------------------------
    wire [NPORT-1:0] sc_fault;
    genvar gp;
    generate
        for (gp = 0; gp < NPORT; gp = gp + 1) begin : g_sc
            ot_qwen_rt_rom_bank #(.NB(SCALE_BANKS), .AW(24), .DW(256)) u_bank (
                .clk(clk), .rst_n(rst_n), .re(scale_gre[gp] && me_clk_en), .addr(scale_addr[gp*24 +: 24]),
                .q(scale_q[gp*256 +: 256]), .addr_fault(sc_fault[gp]));
        end
    endgenerate
    //: the ROM services are fixed-latency synchronous macros (no back-pressure): ready out of reset
    reg rom_ready;
    always @(posedge clk or negedge rst_n) if (!rst_n) rom_ready <= 1'b0; else rom_ready <= 1'b1;
    assign scale_ready = rom_ready && !(|sc_fault);
    assign w_ok_svc = scale_ready;            // code ROM macros are in the tiles, same readiness
    generate if (EMBED_ROM != 0) begin : g_emb
        ot_qwen_rt_embed_rom #(.AW(24), .NW(NW)) u_emb (.clk(clk), .rst_n(rst_n),
            .code_re(embed_code_re), .code_addr(embed_code_addr), .code_q(embed_code_q),
            .scale_re(embed_scale_re), .scale_addr(embed_scale_addr), .scale_q(embed_scale_q), .fault(emb_fault));
    end else begin : g_noemb
        assign embed_code_q = 0; assign embed_scale_q = 0; assign emb_fault = 1'b0;
    end endgenerate
    assign emb_ok_svc = rom_ready && !emb_fault;
    assign me_mem_ok_svc = !rst_n || scale_ready;

    // ---- vector memory (host-preloaded; the host's port semantics) ---------------------
    reg [31:0] vm [0:VM_ELEMS-1] /*verilator public_flat_rw*/;
    reg [NXC*32-1:0] xp_q [0:(XVM > 0 ? XVM : 1)-1];
    reg [NXC-1:0]    xp_v [0:(XVM > 0 ? XVM : 1)-1];
    integer vi, vl, xs;
    always @(posedge clk) begin
        reg [31:0] a; reg [NXC*32-1:0] rq;
        // reads (registered responses, held when not read)
        for (vi = 0; vi < SW; vi = vi + 1) begin
            if (va_re[vi]) begin a = va_addr[vi*24 +: 24]; va_q[vi*32 +: 32] <= (a < VM_ELEMS) ? vm[a] : 32'd0; end
            if (vb_re[vi]) begin a = vb_addr[vi*24 +: 24]; vb_q[vi*32 +: 32] <= (a < VM_ELEMS) ? vm[a] : 32'd0; end
            if (vc_re[vi]) begin a = vc_addr[vi*24 +: 24]; vc_q[vi*32 +: 32] <= (a < VM_ELEMS) ? vm[a] : 32'd0; end
        end
        if (s_vre)
            for (vl = 0; vl < W; vl = vl + 1) begin
                a = ({24'd0, s_vraddr} << 4) + vl;
                s_vrq[vl*32 +: 32] <= (a < VM_ELEMS) ? vm[a] : 32'd0;
            end
        if (me_clk_en) begin
            rq = 0;
            for (vi = 0; vi < NXC; vi = vi + 1)
                if (vx_re[vi]) begin a = vx_addr[vi*24 +: 24]; rq[vi*32 +: 32] = (a < VM_ELEMS) ? vm[a] : 32'd0; end
            if (XVM == 0) begin
                for (vi = 0; vi < NXC; vi = vi + 1) if (vx_re[vi]) vx_q[vi*32 +: 32] <= rq[vi*32 +: 32];
            end else begin
                for (vi = 0; vi < NXC; vi = vi + 1) if (xp_v[XVM-1][vi]) vx_q[vi*32 +: 32] <= xp_q[XVM-1][vi*32 +: 32];
                for (xs = XVM - 1; xs > 0; xs = xs - 1) begin xp_q[xs] <= xp_q[xs-1]; xp_v[xs] <= xp_v[xs-1]; end
                xp_q[0] <= rq; xp_v[0] <= vx_re;
            end
        end
        // writes, in the host's commit order (the last writer of an element wins)
        if (me_clk_en)
            for (vi = 0; vi < NPORT; vi = vi + 1)
                if (vw_me_we[vi])
                    for (vl = 0; vl < W; vl = vl + 1)
                        if (vw_me_mask[vi*16 + vl]) begin
                            a = ({8'd0, vw_me_addr[vi*24 +: 24]} << 4) + vl;
                            if (a < VM_ELEMS) vm[a] <= vw_me_data[(vi*16 + vl)*32 +: 32];
                        end
        if (vw_mx_we)
            for (vl = 0; vl < W; vl = vl + 1)
                if (vw_mx_mask[vl]) begin a = ({8'd0, vw_mx_addr} << 4) + vl; if (a < VM_ELEMS) vm[a] <= vw_mx_data[vl*32 +: 32]; end
        for (vi = 0; vi < SW; vi = vi + 1)
            if (vw_su_we[vi]) begin a = vw_su_addr[vi*24 +: 24]; if (a < VM_ELEMS) vm[a] <= vw_su_data[vi*32 +: 32]; end
        if (vw_rd_we && vw_rd_addr < VM_ELEMS) vm[vw_rd_addr] <= vw_rd_data;
        if (s_vwe)
            for (vl = 0; vl < W; vl = vl + 1) begin
                a = ({24'd0, s_vwaddr} << 4) + vl;
                if (a < VM_ELEMS) vm[a] <= s_vwdata[vl*32 +: 32];
            end
    end

    // ---- KV service and streaming HBM ---------------------------------------------------------
    localparam integer TGWK = 3 + 6;           // NWR = 64
    wire hd_v, hd_rdy, h_go; wire [18:0] hd_row; wire [10:0] hd_n;
    wire [NPC-1:0] hl_v, hl_pop, hw_v, hw_room, hwd_v;
    wire [NPC*17-1:0] hl_sec; wire [NPC*8-1:0] hl_row; wire [NPC*256-1:0] hl_data, hw_data;
    wire [NPC*24-1:0] hw_sec; wire [NPC*TGWK-1:0] hw_tag, hwd_tag;
    wire kv_fault, svc_fault, hbm_fault; wire [15:0] svc_code, hbm_code;
    //: a LAYER starts at the stage's first core start (the sequencer starts the core once per program
    //: segment, i.e. again after each collective, within the same layer)
    reg kv_arm;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) kv_arm <= 1'b0;
        else if (start | h_start) kv_arm <= 1'b1;
        else if (core_start) kv_arm <= 1'b0;
    wire kv_layer_start = core_start && kv_arm && rm_layer != 8'hff;
    //: a later segment of the same layer starts: the previous segment (QK/PV, the O projection and its
    //: all-reduce) is complete, so the core is done with this layer's KV slices
    wire kv_free = core_start && !kv_arm && rm_layer != 8'hff;
    //: the notice names the layer that runs AFTER the current one: before the first KV layer of a run has
    //: started, the next layer to run is that stage's own layer, so no notice is given then (a non-KV
    //: stage, e.g. the embedding, may announce the first KV layer)
    reg kv_started;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) kv_started <= 1'b0;
        else if (kv_layer_start) kv_started <= 1'b1;
    wire [7:0] kv_notice = (kv_started || rm_layer == 8'hff) ? rm_next_layer : 8'hff;
    ot_qwen_rt_kv_stream4_service #(.G(G), .SW(SW), .AW(AW), .NW(NW), .NSTK(NSTK), .NPC(NPC), .FILL_LAT(FILL_LAT), .KV_IDEAL(0),
                                   .WBW(WBW)) u_kv (
        .clk(clk), .rst_n(rst_n), .start(kv_layer_start), .ideal_in(rm_kv_ideal), .pos(core_pos[NW-1:0]), .layer(rm_layer),
        .nx_layer(kv_notice), .pos_hint(tp_pos[NW-1:0]),
        .kv_free(kv_free), .early_go_in(rm_early_go), .posted_wb_in(rm_posted_wb), .wb_busy(kv_wb_busy),
        .kvd_v(kvd_v), .kvd_pos(kvd_pos), .kvd_kindk(kvd_kindk), .kv_ok(kv_ok),
        .kv_we(kv_we), .kv_waddr(kv_waddr), .kv_wdata(kv_wdata), .kv_write_drained(kv_write_drained),
        .kvw_ce(kvw_ce), .kvw_addr(kvw_addr), .kvw_data(kvw_data), .kvw_mask(kvw_mask),
        .d_v(hd_v), .d_rdy(hd_rdy), .d_row(hd_row), .d_n(hd_n), .go(h_go),
        .l_v(hl_v), .l_sec(hl_sec), .l_row(hl_row), .l_data(hl_data), .l_pop(hl_pop),
        .w_v(hw_v), .w_sec(hw_sec), .w_data(hw_data), .w_tag(hw_tag), .w_room(hw_room), .wd_v(hwd_v), .wd_tag(hwd_tag),
        .fault(svc_fault), .fault_code(svc_code), .st_fill_cycles(st_fill_cycles), .st_fill_sectors(st_fill_sectors),
        .st_wr_sectors(st_wr_sectors), .st_rsp_stall(st_rsp_stall), .st_kvok_low_desc(st_kvok_low_desc),
        .st_drain_low(st_drain_low), .st_wr_lat_max(st_wr_lat_max), .st_fill_exposed(st_fill_exposed));
    // Source connection only: the same service transaction owners, finite
    // grants, row identities and checked ACK tags cross this literal boundary.
    // All producer returns are required inputs. Bind only the owner successor;
    // this file makes no claim that its physical stack adapter is ready.
    assign producer_clk=clk;
    assign producer_hclk=hclk;
    assign producer_por_n=rst_n;
    assign producer_warm_rst_n=warm_rst_n;
    assign stream_d_v=hd_v;
    assign hd_rdy=stream_d_rdy;
    assign stream_d_row=hd_row;
    assign stream_d_n=hd_n;
    assign stream_go=h_go;
    assign hl_v=stream_l_v;
    assign hl_sec=stream_l_sec;
    assign hl_row=stream_l_row;
    assign hl_data=stream_l_data;
    assign stream_l_pop=hl_pop;
    assign stream_w_v=hw_v;
    assign stream_w_sec=hw_sec;
    assign stream_w_data=hw_data;
    assign stream_w_tag=hw_tag;
    assign hw_room=stream_w_room;
    assign hwd_v=stream_wd_v;
    assign hwd_tag=stream_wd_tag;
    assign hbm_fault=producer_fault;
    assign hbm_code=producer_fault_code;
    assign kv_fault = svc_fault | hbm_fault;
    assign kv_fault_code = svc_code | (hbm_fault ? 16'h8000 : 16'h0);

    assign mem_fault = kv_fault | rom_fault | (|sc_fault) | emb_fault;
    assign kv_ok_o = kv_ok;
    assign kv_drained_o = kv_write_drained;

    // ---- issue-stall attribution (cycles an op waited at NEXT while a memory gate was low) --
    wire run_nx = (core.st == 2'd2) && core.nx_v;
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin st_stall_kv <= 0; st_stall_drain <= 0; st_stall_bridge <= 0; st_stall_retire <= 0; st_stall_mem <= 0; end
        else begin
            if (run_nx && core.d_unit == 2'd1 && core.me_wsrc && !core.kv_gate) st_stall_kv <= st_stall_kv + 1;
            if (run_nx && core.d_unit == 2'd2 && core.su_ready && core.su_idle && !kv_write_drained) st_stall_drain <= st_stall_drain + 1;
            if (run_nx && core.d_unit == 2'd2 && core.su_ready && !core.su_idle) st_stall_bridge <= st_stall_bridge + 1;
            if (run_nx && (core.d_unit == 2'd0 || core.d_barrier) && core.me_idle && core.su_idle && !kv_write_drained)
                st_stall_retire <= st_stall_retire + 1;
            if (run_nx && !me_mem_ok_svc) st_stall_mem <= st_stall_mem + 1;
        end
    end
endmodule
