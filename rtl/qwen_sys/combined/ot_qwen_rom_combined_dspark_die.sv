// SOURCE-ONLY opt-in DSpark join: existing VPOS/KVmp/accept and near arithmetic.
// Optional STREAM4 uses owner tagged controller and multi-position service; no gain claim.
// OWNER mandatory nearHBM baseline: fenced 7960 + pipelined 6256; one-stream AR.
`timescale 1ns/1ps
// Fullshape successor of the pinned W12 REAL_MEM runtime die. All code/scale,
// descriptor/constant/VM arithmetic and tile interfaces retain the baseline.
// Independent hclk crosses only the tagged HBM ports, with actual WR_ACK.
// No ideal-memory bypass. Optional near descriptor is OFF by default.
// No async collective. DSPARK is opt-in; this successor reuses owner KVmp.
// HBM_STREAM4=1 selects the actual owner multi-position STREAM4 service.
module ot_qwen_rom_combined_dspark_die #(
    parameter integer HBM_STREAM4=0, NSTK=4, WBW=4,
    parameter integer DSPARK=0, ACCEPT_COMMIT=0, VPMAX=4, VWA=16, NPROG=1024, NDESC=64,
    parameter integer NEAR_HBM=1,
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
    parameter integer ENABLE_AR256 = 1,
    parameter integer D = 4,
    // REAL_MEM
    parameter integer REAL_MEM = 1,
    parameter integer SCALE_BANKS = 13,      // 4096-word macros per scale port (>= scale words / 4096)
    parameter integer CROM_WORDS = 1048576,
    parameter integer VM_ELEMS = 1048576,
    parameter integer NPC = 32,
    parameter integer HBM_LAYERS = 36,
    parameter integer FILL_LAT = 8,
    parameter integer NRD = 256,
    parameter integer LKA = 512,
    parameter integer EMBED_ROM = 1         // the token's X from the INT8 embedding ROM (stage E); 0: X preloaded
) (
    input  wire              clk,
    input wire rst_n,hclk,hrst_n,
    output wire core_start_o,core_done_o,kv_layer_start_o,kv_arm_o,row_drained_o,nhb_active_o,
    output wire [3:0] h_req_v,h_req_we,input wire [3:0] h_req_ready,
    output wire [95:0] h_req_addr,output wire [19:0] h_req_len,
    output wire [51:0] h_req_tag,output wire [1023:0] h_req_wdata,
    input wire [127:0] h_pc_room,h_rsp_v,h_rsp_wr,
    output wire [127:0] h_rsp_ready,
    input wire [1663:0] h_rsp_tag,input wire [511:0] h_rsp_beat,
    input wire [32767:0] h_rsp_data,
    // Claude STREAM4 core-domain service boundary (4 stacks x 32 PCs).
    input wire [7:0] rm_next_layer,
    input wire rm_early_go,rm_posted_wb,rm_kv_free,
    output wire wb_busy_o,kv_free_o,
    output wire [31:0] st_fill_exposed,
    output wire stream_d_v,stream_go,input wire stream_d_rdy,
    output wire [18:0] stream_d_row,output wire [10:0] stream_d_n,
    input wire [127:0] stream_l_v,stream_w_room,stream_wd_v,
    input wire [2175:0] stream_l_sec,input wire [1023:0] stream_l_row,
    input wire [32767:0] stream_l_data,
    output wire [127:0] stream_l_pop,stream_w_v,
    output wire [3071:0] stream_w_sec,output wire [32767:0] stream_w_data,
    output wire [1151:0] stream_w_tag,input wire [1151:0] stream_wd_tag,
    input wire stream_fault,
    output wire              rt_rst_n,
    output reg  [31:0]       cyc,
    output wire              start,
    input  wire [SNW-1:0]    tp_token,
    input  wire [SNW-1:0]    tp_pos,
    input  wire              rm_kv_ideal,       // must be zero; baseline has no ideal bypass
    input  wire [7:0]        rm_layer,          // the stage's layer (its HBM KV region); 255: no KV (embedding stage)
    input wire [3:0] rm_npos, h_commit_n,
    input wire h_commit_v, acc_start_v, acc_tokx_v, acc_arm, acc_commit_en,
    input wire [SNW-1:0] acc_start_tok, acc_tokx_tok,
    input wire [2:0] acc_tokx_slot,
    output wire acc_done,output wire [2:0] acc_a,
    output wire [3:0] acc_n_emit,output wire [SNW-1:0] acc_bonus,
    output wire [NW-1:0] kv_committed_len,output wire kv_committed_v,
    output wire [8*SNW-1:0] seq_tok_vec,output wire [8*32-1:0] seq_val_vec,
    output wire [3:0] seq_n_tok,
    // Actual verify-program vm_map_p bases, held for the entire decoder stage.
    input wire [8*24-1:0] rm_near_qbases,rm_near_obases,
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
    output wire [43:0]       c_tag,
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
    output wire [31:0]       st_kvok_low_desc, st_drain_low, st_wr_lat_max,
    output reg  [31:0]       st_stall_kv, st_stall_drain, st_stall_bridge, st_stall_retire, st_stall_mem
);
    localparam integer W=16, AW=24, PAW=12, DAW=6, FW=512, NPORT = G >> SMIN, NXC = 1 << SMAX;
    // Explicit external reset/start: no automatic launch at simulator cycle 7.
    assign rt_rst_n=rst_n;assign start=h_start;
    always @(posedge clk or negedge rst_n)if(!rst_n)cyc<=0;else cyc<=cyc+1;
    initial if(NEAR_HBM!=1||G!=6144||SW!=64||NW!=18||SNW!=18||D!=4||REAL_MEM!=1||NPC!=32)
        $fatal(1,"Selected combined die is TP4/G6144/SW64/NW18/REAL_MEM");
    // rm_kv_ideal is retained as an ABI input but no bypass is selectable here.
    wire core_start, core_done;
    wire [SNW-1:0] core_tok, core_pos, core_ntok;
    wire [31:0] core_nval;
    wire coll_busy;
    wire [NW-1:0] core_ntok_c;
    assign core_ntok = core_ntok_c;
    // core memory ports
    wire prog_re; wire [11:0] prog_addr; reg [1023:0] prog_q;
    wire desc_re; wire [5:0] desc_addr; reg [63:0] desc_q;
    wire s_vre; wire [VWA-1:0] s_vraddr; reg [511:0] s_vrq; wire s_vwe; wire [VWA-1:0] s_vwaddr; wire [511:0] s_vwdata;
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
        .FAST_ISSUE(FAST_ISSUE),.KV_PREP(KV_PREP),.VPOS(DSPARK)) core (
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
    ot_qwen_tp_seq_combined_vp #(.ENABLE_ARP(DSPARK),.NTOK(8),.NEAR_HBM(NEAR_HBM),.N(D),.NW(SNW),.PAW(PAW),.VWA(VWA),.DAW(DAW),.FW(FW),.TAGW(44),
                    .QWEN_FULLSHAPE(QWEN_FULLSHAPE), .ENABLE_AR256(ENABLE_AR256)) seq (
        .clk(clk),.rst_n(rst_n),.start(start | h_start),.token(tp_token),.pos(tp_pos),
        .done(s_done),.next_token(seq_ntok),.next_val(seq_nval),
        .tok_vec(seq_tok_vec),.val_vec(seq_val_vec),.n_tok(seq_n_tok),.near_decoder(rm_layer!=8'hff),
        .fault(s_fault),.coll_busy(coll_busy),
        .core_start(core_start),.core_token(core_tok),.core_pos(core_pos),
        .core_done(core_done),.core_next_token(core_ntok),.core_next_val(core_nval),
        .core_fault(core_fault),.prog_base(prog_base),
        .desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
        .nhb_request(nhb_request),.nhb_qbase(nhb_qbase),.nhb_obase(nhb_obase),.nhb_done(nhb_done),.nhb_fault(nhb_protocol_fault|near_fault|near_sys_fault),
        .vm_re(s_vre),.vm_raddr(s_vraddr),.vm_rq(s_vrq),
        .vm_we(s_vwe),.vm_waddr(s_vwaddr),.vm_wdata(s_vwdata),
        .c_valid(c_valid),.c_ready(c_ready),.c_data(c_data),
        .c_last(c_last),.c_mode(c_mode),.c_tag(c_tag),
        .r_valid(r_valid),.r_data(r_data),.r_last(r_last),
        .r_rank(r_rank),.r_err(r_err));

    // ---- program ROM, segment descriptors, constant ROM (host-preloaded arrays) -----------
    reg [1023:0] prog_mem [0:NPROG-1]      /*verilator public_flat_rw*/;
    reg [63:0]   desc_mem [0:NDESC-1]       /*verilator public_flat_rw*/;
    reg [63:0]   crom_mem [0:CROM_WORDS-1] /*verilator public_flat_rw*/;
    reg [31:0]   crom_words           /*verilator public_flat_rw*/;
    reg          rom_fault;
    wire [11:0]  prog_a = prog_base + prog_addr;
    integer li;
    always @(posedge clk) begin
        if (prog_re) prog_q <= (prog_a < NPROG) ? prog_mem[prog_a[$clog2(NPROG)-1:0]] : 1024'd0;
        if (desc_re) desc_q <= (desc_addr < NDESC) ? desc_mem[desc_addr[$clog2(NDESC)-1:0]] : 64'd0;
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

    // Actual service stays in the core/tile clock domain. Only the tagged
    // memory transport crosses to independent HBM hclk. This preserves all
    // original scalar-write/descriptor/capture handshakes without an unsafe
    // multi-bit direct crossing or a fabricated drain.
    wire [3:0] m_req_v,m_req_ready,m_req_we;wire [95:0] m_req_addr;wire [19:0] m_req_len;
    wire [51:0] m_req_tag;wire [1023:0] m_req_wdata;
    wire [127:0] m_pc_room,m_rsp_v,m_rsp_ready,m_rsp_wr;wire [1663:0] m_rsp_tag;
    wire [511:0] m_rsp_beat;wire [32767:0] m_rsp_data;
    wire [31:0] row_valid,row_v,row_g,row_rsp_valid;wire [415:0] row_t;wire [32767:0] row_rsp_data;
    wire kv_fault,cdc_fault,h_cdc_fault,row_drained;
    reg ideal_forbidden;
    always @(posedge clk or negedge rst_n)if(!rst_n)ideal_forbidden<=0;else if(h_start&&rm_kv_ideal)ideal_forbidden<=1;
    wire nhb_request,nhb_done,nhb_protocol_fault,near_fault,near_sys_fault;
    wire [23:0] nhb_qbase,nhb_obase;
    reg kv_arm;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)kv_arm<=0;else if(h_start)kv_arm<=1;else if(core_start)kv_arm<=0;
    wire kv_layer_start=core_start&&kv_arm&&rm_layer!=8'hff;
    assign core_start_o=core_start;assign core_done_o=core_done;assign kv_layer_start_o=kv_layer_start;
    assign nhb_active_o=nhb_request;assign kv_arm_o=kv_arm;assign row_drained_o=row_drained;
    wire [3:0] stage_npos=(DSPARK!=0)?rm_npos:4'd1;
    wire kv_commit_v;wire [3:0] kv_commit_n;
    ot_qwen_combined_dspark_accept #(.SNW(SNW),.ACCEPT_COMMIT(ACCEPT_COMMIT)) accept_join(
        .clk(clk),.rst_n(rst_n),.s_done(s_done),.seq_tok_vec(seq_tok_vec),.seq_n_tok(seq_n_tok),
        .h_commit_v((DSPARK!=0)&&h_commit_v),.h_commit_n(h_commit_n),
        .acc_start_v((DSPARK!=0)&&acc_start_v),.acc_start_tok(acc_start_tok),
        .acc_tokx_v((DSPARK!=0)&&acc_tokx_v),.acc_tokx_slot(acc_tokx_slot),.acc_tokx_tok(acc_tokx_tok),
        .acc_arm((DSPARK!=0)&&acc_arm),.acc_commit_en((DSPARK!=0)&&acc_commit_en),
        .acc_done(acc_done),.a(acc_a),.n_emit(acc_n_emit),.bonus(acc_bonus),
        .kv_commit_v(kv_commit_v),.kv_commit_n(kv_commit_n));
    generate if(HBM_STREAM4!=0)begin:g_stream4
    // Descriptor3 splits near attention from O/AR. The runtime pulses rm_kv_free
    // ONLY at the actual post-O/all-reduce MLP boundary, not every core_start.
    // Request/response drains and row visibility must precede slice reuse.
    wire release_ok=rm_kv_free && !nhb_request && row_drained && !kv_layer_start;
    reg release_fault;
    always @(posedge clk or negedge rst_n)
        if(!rst_n)release_fault<=0;
        else if(rm_kv_free && !release_ok)release_fault<=1;
    assign kv_free_o=release_ok;
    wire stream_svc_fault,row_fault;
    wire [15:0] stream_svc_code;
    ot_qwen_rt_kv_stream4_mp_service #(.VPMAX((DSPARK!=0)?VPMAX:1),.G(G),.SW(SW),.AW(AW),.NW(NW),.NSTK(4),.NPC(128),.FILL_LAT(FILL_LAT),.KV_IDEAL(0),.WBW(WBW)) u_kv(
        .clk(clk),.rst_n(rst_n),.start(kv_layer_start),.ideal_in(1'b0),.pos(core_pos[NW-1:0]),.layer(rm_layer),
        .npos(stage_npos),.commit_v(kv_commit_v),.commit_n(kv_commit_n),.committed_len(kv_committed_len),.committed_v(kv_committed_v),
        .nx_layer(rm_next_layer),.pos_hint(tp_pos[NW-1:0]),.kv_free(release_ok),.early_go_in(rm_early_go),.posted_wb_in(rm_posted_wb),.wb_busy(wb_busy_o),
        .kvd_v(kvd_v),.kvd_pos(kvd_pos),.kvd_kindk(kvd_kindk),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_ok(kv_ok),.kv_write_drained(kv_write_drained),.kvw_ce(kvw_ce),.kvw_addr(kvw_addr),.kvw_data(kvw_data),.kvw_mask(kvw_mask),
        .d_v(stream_d_v),.d_rdy(stream_d_rdy),.d_row(stream_d_row),.d_n(stream_d_n),.go(stream_go),
        .l_v(stream_l_v),.l_sec(stream_l_sec),.l_row(stream_l_row),.l_data(stream_l_data),.l_pop(stream_l_pop),
        .w_v(stream_w_v),.w_sec(stream_w_sec),.w_data(stream_w_data),.w_tag(stream_w_tag),.w_room(stream_w_room),.wd_v(stream_wd_v),.wd_tag(stream_wd_tag),
        .fault(stream_svc_fault),.fault_code(stream_svc_code),
        .st_fill_cycles(st_fill_cycles),.st_fill_sectors(st_fill_sectors),.st_wr_sectors(st_wr_sectors),.st_rsp_stall(st_rsp_stall),
        .st_kvok_low_desc(st_kvok_low_desc),.st_drain_low(st_drain_low),.st_wr_lat_max(st_wr_lat_max),.st_fill_exposed(st_fill_exposed));
    assign kv_fault=stream_svc_fault|row_fault|release_fault|stream_fault;
    assign kv_fault_code=stream_svc_code|((row_fault|release_fault|stream_fault)?16'h8000:16'h0);
    // Same canonical near-row engines; stream write ACK debt is required before
    // reading token K/V from HBM even when posted_wb bypasses the core drain gate.
    ot_qwen_combined_stream4_rows #(.R(8)) u_rows(
        .clk(clk),.rst_n(rst_n),.start(kv_layer_start),.pos(core_pos[NW-1:0]+NW'(stage_npos)-NW'(1)),.layer(rm_layer),
        .memory_ready(kv_ok&&kv_write_drained&&!wb_busy_o&&!kv_fault&&!mem_fault),
        .row_valid(row_valid),.row_v(row_v),.row_g(row_g),.row_t(row_t),.row_rsp_valid(row_rsp_valid),.row_rsp_data(row_rsp_data),
        .m_req_v(m_req_v),.m_req_ready(m_req_ready),.m_req_we(m_req_we),.m_req_addr(m_req_addr),.m_req_len(m_req_len),.m_req_tag(m_req_tag),.m_req_wdata(m_req_wdata),
        .m_pc_room(m_pc_room),.m_rsp_v(m_rsp_v),.m_rsp_ready(m_rsp_ready),.m_rsp_wr(m_rsp_wr),.m_rsp_tag(m_rsp_tag),.m_rsp_beat(m_rsp_beat),.m_rsp_data(m_rsp_data),
        .fault(row_fault),.row_drained(row_drained));
    end else begin:g_canonical_kvmp
    assign wb_busy_o=0;assign kv_free_o=0;assign st_fill_exposed=0;
    assign stream_d_v=0;assign stream_go=0;assign stream_d_row=0;assign stream_d_n=0;
    assign stream_l_pop=0;assign stream_w_v=0;assign stream_w_sec=0;assign stream_w_data=0;assign stream_w_tag=0;
    ot_qwen_combined_nearhbm_mp_service #(.VPMAX((DSPARK!=0)?VPMAX:1),.ENABLE(1),.G(G),.SW(SW),.NW(NW),.NPC(32),.NRD(NRD),.LKA(LKA),.FILL_LAT(FILL_LAT)) u_kv(
        .clk(clk),.rst_n(rst_n),.start(kv_layer_start),.pos(core_pos[NW-1:0]),.layer(rm_layer),
        .npos(stage_npos),.commit_v(kv_commit_v),.commit_n(kv_commit_n),.committed_len(kv_committed_len),.committed_v(kv_committed_v),
        .kvd_v(kvd_v),.kvd_pos(kvd_pos),.kvd_kindk(kvd_kindk),.kv_we(kv_we),.kv_waddr(kv_waddr),.kv_wdata(kv_wdata),
        .kv_ok(kv_ok),.kv_write_drained(kv_write_drained),.kvw_ce(kvw_ce),.kvw_addr(kvw_addr),.kvw_data(kvw_data),.kvw_mask(kvw_mask),
        .row_valid(row_valid),.row_v(row_v),.row_g(row_g),.row_t(row_t),.row_rsp_valid(row_rsp_valid),.row_rsp_data(row_rsp_data),
        .m_req_v(m_req_v),.m_req_ready(m_req_ready),.m_req_we(m_req_we),.m_req_addr(m_req_addr),.m_req_len(m_req_len),.m_req_tag(m_req_tag),.m_req_wdata(m_req_wdata),
        .m_pc_room(m_pc_room),.m_rsp_v(m_rsp_v),.m_rsp_ready(m_rsp_ready),.m_rsp_wr(m_rsp_wr),.m_rsp_tag(m_rsp_tag),.m_rsp_beat(m_rsp_beat),.m_rsp_data(m_rsp_data),
        .fault(kv_fault),.kv_fault_code(kv_fault_code),.row_drained(row_drained),.rows_retired(),.read_bursts(),
        .st_fill_cycles(st_fill_cycles),.st_fill_sectors(st_fill_sectors),.st_wr_sectors(st_wr_sectors),.st_rsp_stall(st_rsp_stall),
        .st_kvok_low_desc(st_kvok_low_desc),.st_drain_low(st_drain_low),.st_wr_lat_max(st_wr_lat_max));
    end endgenerate
    ot_qwen_combined_hbm_cdc transport(
        .clk(clk),.rst_n(rst_n),.hclk(hclk),.hrst_n(hrst_n),
        .s_req_v(m_req_v),.s_req_ready(m_req_ready),.s_req_we(m_req_we),.s_req_addr(m_req_addr),.s_req_len(m_req_len),.s_req_tag(m_req_tag),.s_req_wdata(m_req_wdata),
        .s_pc_room(m_pc_room),.s_rsp_v(m_rsp_v),.s_rsp_ready(m_rsp_ready),.s_rsp_wr(m_rsp_wr),.s_rsp_tag(m_rsp_tag),.s_rsp_beat(m_rsp_beat),.s_rsp_data(m_rsp_data),
        .h_req_v(h_req_v),.h_req_ready(h_req_ready),.h_req_we(h_req_we),.h_req_addr(h_req_addr),.h_req_len(h_req_len),.h_req_tag(h_req_tag),.h_req_wdata(h_req_wdata),
        .h_pc_room(h_pc_room),.h_rsp_v(h_rsp_v),.h_rsp_ready(h_rsp_ready),.h_rsp_wr(h_rsp_wr),.h_rsp_tag(h_rsp_tag),.h_rsp_beat(h_rsp_beat),.h_rsp_data(h_rsp_data),.fault(cdc_fault),.h_fault(h_cdc_fault));

    generate if(NEAR_HBM)begin:g_near
        reg n_started,n_bad,n_done,q_valid;reg [5:0] q_beat;reg [511:0] q_data;
        reg [5:0] feed;reg [63:0] seen;reg [1:0] state;
        reg [2:0] n_slot;reg [3:0] n_count;
        reg [NW-1:0] n_pos;
        reg [23:0] slot_qbase,slot_obase;
        wire [23:0] selected_qbase=(DSPARK!=0)?rm_near_qbases[n_slot*24 +:24]:nhb_qbase;
        wire [23:0] selected_obase=(DSPARK!=0)?rm_near_obases[n_slot*24 +:24]:nhb_obase;
        reg n_start;wire links_up,out_valid,out_g;wire [5:0] out_beat;wire [511:0] out_data;
        wire [4:0] n_fault;wire sys_fault;
        function automatic [15:0] bf16(input [31:0] u);
            reg [31:0] rounded;
            begin rounded=u+32'h00007fff+u[16];bf16=rounded[31:16];end
        endfunction
        ot_qwen_combined_nearbaseline_subsystem #(.HD(128),.R(8),.LAYER_START_FENCE(1)) near_unit(
            .clk(clk),.hclk(clk),.rst_n(rst_n),.hrst_n(rst_n),.start(n_start),.T({1'b0,n_pos[12:0]}+14'd1),
            .q_valid(q_valid),.q_beat(q_beat),.q_data(q_data),.req_valid(row_valid),.req_v(row_v),.req_g(row_g),.req_t(row_t),
            .rsp_valid(row_rsp_valid),.rsp_data(row_rsp_data),.out_valid(out_valid),.out_g(out_g),.out_beat(out_beat),.out_data(out_data),
            .fault(n_fault),.sys_fault(sys_fault),.links_up(links_up),.flip_period(32'd0),.crc_errors(),.replays(),.ev_stack(),.ev_hub());
        assign nhb_done=n_done;assign nhb_protocol_fault=n_bad;assign near_fault=|n_fault;assign near_sys_fault=sys_fault;
        integer x,index,address;
        always @(posedge clk or negedge rst_n)begin
            if(!rst_n)begin n_slot<=0;n_count<=1;n_pos<=0;slot_qbase<=0;slot_obase<=0;state<=0;n_started<=0;n_bad<=0;n_done<=0;n_start<=0;q_valid<=0;q_beat<=0;feed<=0;seen<=0;q_data<=0;end
            else begin
                n_start<=0;n_done<=0;q_valid<=0;
                if(!nhb_request)begin n_started<=0;n_slot<=0;end
                if(nhb_request&&!n_started&&(state==0||state==3)&&row_drained&&kv_ok&&kv_write_drained&&links_up&&!mem_fault)begin
                    if(stage_npos==0||stage_npos>VPMAX||({1'b0,core_pos}+stage_npos)>8192||selected_qbase>VM_ELEMS-1024||selected_obase>VM_ELEMS-1024)n_bad<=1;
                    else begin n_pos<=core_pos+NW'(n_slot);n_count<=stage_npos;slot_qbase<=selected_qbase;slot_obase<=selected_obase;n_start<=1;n_started<=1;state<=1;feed<=0;seen<=0;end
                end
                if(state==1)begin
                    q_valid<=1;q_beat<=feed;
                    for(x=0;x<32;x=x+1)begin
                        q_data[x*16 +:16]<=bf16(vm[slot_qbase+feed*32+x]);
                        if(vm[slot_qbase+feed*32+x][30:23]==8'hff)n_bad<=1;
                    end
                    if(feed==31)state<=2;else feed<=feed+1'b1;
                end
                if(out_valid)begin
                    index=out_g*32+out_beat;address=slot_obase+index*16;
                    if(state==0||out_beat>=32||seen[index]||address+15>=VM_ELEMS)n_bad<=1;
                    else begin
                        for(x=0;x<16;x=x+1)vm[address+x]<=out_data[x*32 +:32];
                        seen[index]<=1;
                        if((seen|(64'd1<<index))==64'hffffffffffffffff)begin
                            if({1'b0,n_slot}+4'd1==n_count)begin n_done<=1;state<=0;end
                            else begin n_slot<=n_slot+1'b1;n_started<=0;state<=3;end
                        end
                    end
                end
            end
        end
    end else begin:g_no_near
        assign row_valid=0;assign row_v=0;assign row_g=0;assign row_t=0;
        assign nhb_done=0;assign nhb_protocol_fault=0;assign near_fault=0;assign near_sys_fault=0;
    end endgenerate
    assign mem_fault=ideal_forbidden|kv_fault|cdc_fault|rom_fault|(|sc_fault)|emb_fault|nhb_protocol_fault|near_fault|near_sys_fault;

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
