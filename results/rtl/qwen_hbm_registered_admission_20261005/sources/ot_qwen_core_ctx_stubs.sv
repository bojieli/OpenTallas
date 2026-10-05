`timescale 1ns/1ps
// ---------------------------------------------------------------------------
// PHYSICAL-CONTEXT STUBS (fmax closure, 2026-10-04): registered-boundary stand-ins for the two units of the generated
// Qwen core ot_qwen_rom_core, so the sequencer can be routed in context without the units' bodies:
//   ot_qwen_me_spine_w12  (agent qwen-me; routed separately): every output the core's logic reads is a flop output, as in
//                         the real spine (ready = !active && !pend, idle, wrom_re / wrom_addr, progress, am_*, fault are
//                         registered in ot_qwen_w12_matvec_part); the go-latched instruction fields are captured into
//                         flops enabled by go && ready, the real spine's issue load.  Clocked by the core's gated
//                         engine clock me_clk exactly as the real unit.
//   ot_hdc_vstream_rt     (the stream unit, hardened separately): ready = !active && ((i_sfu == cls) || inflight == 0),
//                         combinational from the core's decoded sfu field exactly as ot_hdc_vstream; the accept load is
//                         the field capture plus SW lanes x TAPV valid flops cleared on accept && i_sfu != cls (the
//                         lanes' tap-line valid reset).  idle / progress / progress_rows / fault / kv_we are flops.
// Pass-through buses (memory data and address ports the core only forwards) are tied off: they carry no core logic.
// NOT simulation models: they exist only to give the physical flow realistic launch/capture points and loads.
// ---------------------------------------------------------------------------
module ot_qwen_me_spine_w12 #(
    parameter integer W = 16, IL = 8, AW = 24, NW = 16, INT8_SCALE_WCS_BASE = 1, GT = 6144, TG = 4,
    parameter integer SMIN = 7, SMAX = 11, TCUT = 7, BD = 41, XVM = 1, NWS = 5, TWS = 38, ORD = 7, SCALE_LOCAL = 0,
    parameter integer MEM_EXTRA = 1, ACC_LAT = 5, TREE_LAT = 3, MUL_LAT = 5, FAST_ISSUE = 0, KV_PREP = 0
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout, i_tiles, i_k,
    input  wire              i_wsrc,
    input  wire [AW-1:0]     i_wbase, i_ts, i_ks, i_js,
    input  wire [AW-1:0]     i_xbase, i_xks, i_xjs, i_xcs,
    input  wire [2:0]        i_jsh,
    input  wire [3:0]        i_split,
    input  wire [AW-1:0]     i_wcs,
    input  wire              i_round,
    input  wire [AW-1:0]     i_obase, i_ots, i_ojs,
    input  wire              i_mmode, i_oen, i_amax, i_rmax,
    input  wire [AW-1:0]     i_mbase,
    output wire              scale_re,
    output wire [(GT >> SMIN)-1:0]     scale_gre,
    output wire [(GT >> SMIN)*AW-1:0]  scale_addr,
    input  wire [(GT >> SMIN)*W*16-1:0] scale_q,
    output wire [(1<<SMAX)-1:0]    x_re,
    output wire [(1<<SMAX)*AW-1:0] x_addr,
    input  wire [(1<<SMAX)*32-1:0] x_q,
    output reg               wrom_re,
    output reg  [AW-1:0]     wrom_addr,
    output reg               kv_re,
    output wire              tgo,
    output wire [3*NW+13*AW+13-1:0] tb,
    output wire [(1<<SMAX)*32-1:0] xl_d,
    input  wire [(GT >> TCUT)*W*32-1:0] t_lvl,
    input  wire              fab_fault,
    output reg               ov,
    output reg  [(GT >> SMIN)-1:0]     o_we,
    output wire [(GT >> SMIN)*AW-1:0]  o_addr,
    output wire [(GT >> SMIN)*W-1:0]   o_mask,
    output wire [(GT >> SMIN)*W*32-1:0] o_data,
    output reg  [NW-1:0]     am_idx,
    output reg  [31:0]       am_val,
    output reg               am_any,
    output reg               mx_we,
    output wire [AW-1:0]     mx_addr,
    output wire [W-1:0]      mx_mask,
    output wire [W*32-1:0]   mx_data,
    output reg  [15:0]       progress,
    output reg               fault
);
    localparam integer IBW = 3 * NW + 13 * AW + 13;
    wire [IBW-1:0] fields = {i_nout, i_tiles, i_k, i_wsrc, i_wbase, i_ts, i_ks, i_js, i_xbase, i_xks, i_xjs, i_xcs,
                             i_jsh, i_split, i_wcs, i_round, i_obase, i_ots, i_ojs, i_mmode, i_oen, i_amax, i_rmax, i_mbase};
    reg [IBW-1:0] f;
    reg           active, pend;
    reg [15:0]    left;
    reg [31:0]    lfsr;
    assign ready = !active && !pend;
    wire acc = go && ready;
    reg [31:0] fold;
    integer b;
    always @* begin fold = 0; for (b = 0; b < IBW; b = b + 1) fold[b % 32] = fold[b % 32] ^ f[b]; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0; pend <= 0; left <= 0; lfsr <= 32'h1; idle <= 1; wrom_re <= 0; kv_re <= 0; ov <= 0; o_we <= 0;
            am_any <= 0; mx_we <= 0; progress <= 0; fault <= 0;
        end else begin
            lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
            pend <= acc && lfsr[3];
            if (acc) begin active <= 1; left <= {lfsr[11:4], 2'b11}; end
            else if (active) begin left <= left - 1; if (left == 0) active <= 0; end
            idle <= !active && !acc && !pend;
            wrom_re <= active && !f[IBW - 3*NW - 1] && lfsr[5];
            kv_re <= active && f[IBW - 3*NW - 1];
            ov <= active && lfsr[7];
            o_we <= {(GT >> SMIN){active}} & {(GT >> SMIN){lfsr[9]}} ^ fold[(GT >> SMIN)-1 > 31 ? 31 : (GT >> SMIN)-1:0];
            am_any <= fold[0] ^ lfsr[13];
            mx_we <= active && lfsr[15];
            progress <= acc ? 16'd0 : progress + {15'd0, active & lfsr[17]};
            fault <= fault | (fold[1] & fold[2] & fab_fault);
        end
    end
    always @(posedge clk) begin
        if (acc) f <= fields;
        wrom_addr <= f[AW-1:0] ^ lfsr[AW-1:0];
        am_idx <= fold[NW-1:0] ^ lfsr[NW-1:0];
        am_val <= fold ^ lfsr;
    end
    assign scale_re = 1'b0; assign scale_gre = 0; assign scale_addr = 0; assign x_re = 0; assign x_addr = 0;
    assign tgo = 1'b0; assign tb = 0; assign xl_d = 0; assign o_addr = 0; assign o_mask = 0; assign o_data = 0;
    assign mx_addr = 0; assign mx_mask = 0; assign mx_data = 0;
endmodule

module ot_hdc_vstream_rt #(
    parameter integer SW = 8, LV = 4, WR = 64, AW = 24, NW = 16, KV_FP8 = 1,
    parameter integer TAPV = 64          // per-lane tap-line valid flops reset on a class switch (ot_hdc_vstream_lane tlv)
) (
    output wire              rt_active,
    output wire [7:0]        rt_inflight,
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output reg               idle,
    input  wire [NW-1:0]     i_nout,
    input  wire [NW-1:0]     i_nin,
    input  wire              i_asrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi,
    input  wire              i_bsrc,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_csrc,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire [1:0]        i_ma,
    input  wire [1:0]        i_mb,
    input  wire [2:0]        i_ad,
    input  wire [2:0]        i_sfu,
    input  wire              i_mc,
    input  wire              i_md,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire [1:0]        i_red,
    input  wire              i_redsq,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2,
    output wire [SW-1:0]     va_re,
    output wire [SW*AW-1:0]  va_addr,
    input  wire [SW*32-1:0]  va_q,
    output wire [SW-1:0]     vb_re,
    output wire [SW*AW-1:0]  vb_addr,
    input  wire [SW*32-1:0]  vb_q,
    output wire [SW-1:0]     vc_re,
    output wire [SW*AW-1:0]  vc_addr,
    input  wire [SW*32-1:0]  vc_q,
    output reg               wrom_re,
    output wire [AW-1:0]     wrom_addr,
    input  wire [WR*16-1:0]  wrom_q,
    output wire [SW-1:0]     crom_re,
    output wire [SW*AW-1:0]  crom_addr,
    input  wire [SW*64-1:0]  crom_q,
    output wire [SW-1:0]     vm_we,
    output wire [SW*AW-1:0]  vm_waddr,
    output wire [SW*32-1:0]  vm_wdata,
    output reg  [SW-1:0]     kv_we,
    output wire [SW*AW-1:0]  kv_waddr,
    output wire [SW*32-1:0]  kv_wdata,
    output wire              red_we,
    output wire [AW-1:0]     red_addr,
    output wire [31:0]       red_data,
    output reg  [15:0]       progress,
    output reg  [15:0]       progress_rows,
    output reg               fault
);
    localparam integer FB = 2*NW + 3 + 13*AW + 2+2+3+3+1+1+2+2+1 + 64;
    wire [FB-1:0] fields = {i_nout, i_nin, i_asrc, i_abase, i_aso, i_asi, i_bsrc, i_bbase, i_bso, i_bsi, i_csrc, i_cbase,
                            i_cso, i_csi, i_ma, i_mb, i_ad, i_sfu, i_mc, i_md, i_dst, i_dbase, i_dso, i_dsi, i_red,
                            i_redsq, i_rbase, i_rso, i_imm1, i_imm2};
    reg [FB-1:0] f;
    reg          active;
    reg [2:0]    cls;
    reg [7:0]    inflight;
    reg [15:0]   left;
    reg [31:0]   lfsr;
    reg [TAPV-1:0] tlv [0:SW-1];
    assign ready = !active && ((i_sfu == cls) || (inflight == 0));
    wire accept = go && ready;
    reg [31:0] fold;
    integer b;
    always @* begin fold = 0; for (b = 0; b < FB; b = b + 1) fold[b % 32] = fold[b % 32] ^ f[b]; end
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            active <= 0; cls <= 0; inflight <= 0; left <= 0; lfsr <= 32'h5; idle <= 1; wrom_re <= 0; kv_we <= 0;
            progress <= 0; progress_rows <= 0; fault <= 0;
        end else begin
            lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]};
            inflight <= inflight + {7'd0, active} - {7'd0, inflight != 0 && lfsr[2]};
            if (accept) begin active <= 1; cls <= i_sfu; left <= {lfsr[9:4], 2'b11}; end
            else if (active) begin left <= left - 1; if (left == 0) active <= 0; end
            idle <= !active && inflight == 0 && !accept;
            wrom_re <= active && f[FB - 2*NW - 1];
            kv_we <= {SW{active && lfsr[6]}} & fold[SW-1 > 31 ? 31 : SW-1:0];
            progress <= accept ? 16'd0 : progress + {15'd0, inflight != 0 && lfsr[2]};
            progress_rows <= accept ? 16'd0 : progress_rows + {15'd0, lfsr[8] & lfsr[2]};
            fault <= fault | (&fold[3:0]);
        end
    end
    always @(posedge clk) if (accept) f <= fields;
    // the lanes' tap-line valid bits: cleared on accept of another class, else shifted (ot_hdc_vstream_lane tlv)
    reg [SW-1:0] tl_top;
    genvar gl;
    for (gl = 0; gl < SW; gl = gl + 1) begin : g_lane
        always @(posedge clk or negedge rst_n)
            if (!rst_n) tlv[gl] <= 0;
            else if (accept && i_sfu != cls) tlv[gl] <= 0;
            else tlv[gl] <= {tlv[gl][TAPV-2:0], active & lfsr[gl % 32]};
        always @(posedge clk) tl_top[gl] <= tlv[gl][TAPV-1];
    end
    assign rt_active = active;
    assign rt_inflight = inflight;
    assign va_re = 0; assign va_addr = 0; assign vb_re = 0; assign vb_addr = 0; assign vc_re = 0; assign vc_addr = 0;
    assign wrom_addr = f[AW-1:0];
    assign crom_re = 0; assign crom_addr = 0;
    assign vm_we = tl_top; assign vm_waddr = 0; assign vm_wdata = 0; assign kv_waddr = 0; assign kv_wdata = 0;
    assign red_we = 1'b0; assign red_addr = 0; assign red_data = 0;
endmodule
