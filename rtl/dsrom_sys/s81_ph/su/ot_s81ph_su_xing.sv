`timescale 1ns/1ps
// CLAUDE S81-PH su (2026-10-06): the SU slab's die crossing around ot_s81ph_su_adapt (REMOTE-READ split, contracts_hub.json
// kinds.su.decision.chosen).  The whole stream unit sits in the SU slab; the VM and the sequencer stay in the hub slab.
//   VM -> SU, DF cycles: the issue (go + every op field), the read words rd_q / vi_q.
//   SU -> VM, DR cycles: the read requests (rd_addr/re/src, vi_re/addr), ready / idle / fault, and the writes (inside the
//                        unit: RET_STAGES + DR, so the unit's chaining credits count when a write LANDS in the VM).
// The lanes therefore see a read answered RX = GX = DR + DF cycles late (ot_s81ph_vec_lane).  The sequencer's view of
// ready / idle is the unit's, DR late, and false for DF + DR cycles after every go (the go is still in flight), so a
// wait on SU idle never passes an op that has not reached the unit.  DF = DR = 0 is ot_hdc_v41x_su_adapt exactly.
// In silicon the DF / DR pipes are the slab pin flops plus the die bus stations; here they are plain register stages.
module ot_s81ph_su_xing #(
    parameter integer DF = 0,
    parameter integer DR = 0,
    parameter integer NEG = 0,          // bench negative controls only: 1 lane read delay one short, 2 idle/ready not held while a go
                                        // is in flight, 3 writes' credits counted before they land (RET_STAGES not + DR)

    parameter integer N  = 16,          // vector-unit light lanes
    parameter integer M  = 8,           // SFU lanes
    parameter integer LV = 7,           // reducer time levels (a reduced segment spans <= 2^LV vectors), 1..7
    parameter integer AW = 24,
    parameter integer NW = 16,
    parameter integer CLS_DRAIN = 0,
    parameter integer KVT_SH = 9,
    parameter integer BCAST_STAGES = 0, // ot_hdc_v41x_vec: controller -> lane broadcast tree stages
    parameter integer RET_STAGES = 0,   // ot_hdc_v41x_vec: lane / reducer -> vector-memory write stages
    parameter integer MLAT = 3,         // ot_hdc_v41x_vec: multiplier latency (3, 4 or 5: W11 serial domain)
    parameter integer ALAT = 3          // ot_hdc_v41x_vec: FP add latency (3, or 4)
) (
    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire              idle,
    input  wire [NW-1:0]     i_nout, i_nin, i_chase,
    input  wire [1:0]        i_asrc, i_bsrc, i_csrc, i_dsrc,
    input  wire [AW-1:0]     i_abase, i_aso, i_asi, i_aibase,
    input  wire [1:0]        i_aind,
    input  wire [AW-1:0]     i_bbase, i_bso, i_bsi,
    input  wire              i_bhalf,
    input  wire [AW-1:0]     i_cbase, i_cso, i_csi,
    input  wire              i_cpair,
    input  wire [AW-1:0]     i_dbase, i_dso, i_dsi,
    input  wire              i_arnd, i_arelu, i_amin, i_cclip,
    input  wire [2:0]        i_m1,
    input  wire [1:0]        i_m2,
    input  wire [2:0]        i_qm, i_ad, i_sfu, i_e1,
    input  wire [1:0]        i_e2,
    input  wire              i_rnd,
    input  wire [1:0]        i_dst,
    input  wire [AW-1:0]     i_obase, i_oso, i_osi, i_orow,
    input  wire [1:0]        i_red,
    input  wire              i_redsq, i_redwhole, i_redtree, i_redrnd,
    input  wire [AW-1:0]     i_rbase, i_rso,
    input  wire [31:0]       i_imm1, i_imm2, i_imm3,
    input  wire [2:0]        i_m,
    input  wire [AW-1:0]     i_xps, i_ops,
    // the vector unit's memory ports
    output wire [N-1:0]      vi_re,
    output wire [N*AW-1:0]   vi_addr,
    input  wire [N*32-1:0]   vi_q,
    output wire [4*N*AW-1:0] rd_addr,
    output wire [4*N-1:0]    rd_re,
    output wire [8*N-1:0]    rd_src,
    input  wire [4*N*32-1:0] rd_q,
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    output reg               fault,
    output wire [31:0]       dbg_ops, dbg_elems
);
    localparam integer FW = $bits(i_nout) + $bits(i_nin) + $bits(i_chase) + $bits(i_asrc) + $bits(i_bsrc) + $bits(i_csrc) + $bits(i_dsrc) + $bits(i_abase) + $bits(i_aso) + $bits(i_asi) + $bits(i_aibase) + $bits(i_aind) + $bits(i_bbase) + $bits(i_bso) + $bits(i_bsi) + $bits(i_bhalf) + $bits(i_cbase) + $bits(i_cso) + $bits(i_csi) + $bits(i_cpair) + $bits(i_dbase) + $bits(i_dso) + $bits(i_dsi) + $bits(i_arnd) + $bits(i_arelu) + $bits(i_amin) + $bits(i_cclip) + $bits(i_m1) + $bits(i_m2) + $bits(i_qm) + $bits(i_ad) + $bits(i_sfu) + $bits(i_e1) + $bits(i_e2) + $bits(i_rnd) + $bits(i_dst) + $bits(i_obase) + $bits(i_oso) + $bits(i_osi) + $bits(i_orow) + $bits(i_red) + $bits(i_redsq) + $bits(i_redwhole) + $bits(i_redtree) + $bits(i_redrnd) + $bits(i_rbase) + $bits(i_rso) + $bits(i_imm1) + $bits(i_imm2) + $bits(i_imm3) + $bits(i_m) + $bits(i_xps) + $bits(i_ops);
    localparam integer WIN = DF + DR;
    wire [NW-1:0] d_nout;
    wire [NW-1:0] d_nin;
    wire [NW-1:0] d_chase;
    wire [1:0] d_asrc;
    wire [1:0] d_bsrc;
    wire [1:0] d_csrc;
    wire [1:0] d_dsrc;
    wire [AW-1:0] d_abase;
    wire [AW-1:0] d_aso;
    wire [AW-1:0] d_asi;
    wire [AW-1:0] d_aibase;
    wire [1:0] d_aind;
    wire [AW-1:0] d_bbase;
    wire [AW-1:0] d_bso;
    wire [AW-1:0] d_bsi;
    wire  d_bhalf;
    wire [AW-1:0] d_cbase;
    wire [AW-1:0] d_cso;
    wire [AW-1:0] d_csi;
    wire  d_cpair;
    wire [AW-1:0] d_dbase;
    wire [AW-1:0] d_dso;
    wire [AW-1:0] d_dsi;
    wire  d_arnd;
    wire  d_arelu;
    wire  d_amin;
    wire  d_cclip;
    wire [2:0] d_m1;
    wire [1:0] d_m2;
    wire [2:0] d_qm;
    wire [2:0] d_ad;
    wire [2:0] d_sfu;
    wire [2:0] d_e1;
    wire [1:0] d_e2;
    wire  d_rnd;
    wire [1:0] d_dst;
    wire [AW-1:0] d_obase;
    wire [AW-1:0] d_oso;
    wire [AW-1:0] d_osi;
    wire [AW-1:0] d_orow;
    wire [1:0] d_red;
    wire  d_redsq;
    wire  d_redwhole;
    wire  d_redtree;
    wire  d_redrnd;
    wire [AW-1:0] d_rbase;
    wire [AW-1:0] d_rso;
    wire [31:0] d_imm1;
    wire [31:0] d_imm2;
    wire [31:0] d_imm3;
    wire [2:0] d_m;
    wire [AW-1:0] d_xps;
    wire [AW-1:0] d_ops;
    wire d_go;
    ot_hdc_delay #(.W(1), .D(DF), .RESET(1)) u_dgo (.clk(clk), .rst_n(rst_n), .d(go), .q(d_go));
    ot_hdc_delay #(.W(FW), .D(DF)) u_dfld (.clk(clk), .rst_n(rst_n), .d({i_nout, i_nin, i_chase, i_asrc, i_bsrc, i_csrc, i_dsrc, i_abase, i_aso, i_asi, i_aibase, i_aind, i_bbase, i_bso, i_bsi, i_bhalf, i_cbase, i_cso, i_csi, i_cpair, i_dbase, i_dso, i_dsi, i_arnd, i_arelu, i_amin, i_cclip, i_m1, i_m2, i_qm, i_ad, i_sfu, i_e1, i_e2, i_rnd, i_dst, i_obase, i_oso, i_osi, i_orow, i_red, i_redsq, i_redwhole, i_redtree, i_redrnd, i_rbase, i_rso, i_imm1, i_imm2, i_imm3, i_m, i_xps, i_ops}), .q({d_nout, d_nin, d_chase, d_asrc, d_bsrc, d_csrc, d_dsrc, d_abase, d_aso, d_asi, d_aibase, d_aind, d_bbase, d_bso, d_bsi, d_bhalf, d_cbase, d_cso, d_csi, d_cpair, d_dbase, d_dso, d_dsi, d_arnd, d_arelu, d_amin, d_cclip, d_m1, d_m2, d_qm, d_ad, d_sfu, d_e1, d_e2, d_rnd, d_dst, d_obase, d_oso, d_osi, d_orow, d_red, d_redsq, d_redwhole, d_redtree, d_redrnd, d_rbase, d_rso, d_imm1, d_imm2, d_imm3, d_m, d_xps, d_ops}));
    // go in flight: any go in the last DF + DR cycles
    wire inflight;
    generate if (WIN == 0) begin : g_w0
        assign inflight = 1'b0;
    end else begin : g_w
        reg [WIN-1:0] gw;
        always @(posedge clk or negedge rst_n) if (!rst_n) gw <= {WIN{1'b0}}; else gw <= {gw, go};
        assign inflight = |gw;
    end endgenerate
    wire u_ready, u_idle, u_fault, r_ready, r_idle;
    ot_hdc_delay #(.W(2), .D(DR), .RESET(1)) u_rst (.clk(clk), .rst_n(rst_n), .d({u_ready, u_idle}), .q({r_ready, r_idle}));
    assign ready = r_ready && (!inflight || NEG == 2);
    assign idle = r_idle && (!inflight || NEG == 2);
    wire r_fault;
    ot_hdc_delay #(.W(1), .D(DR), .RESET(1)) u_rf (.clk(clk), .rst_n(rst_n), .d(u_fault), .q(r_fault));
    always @(*) fault = r_fault;
    // read requests SU -> VM (DR), answers VM -> SU (DF)
    wire [N-1:0]      u_vi_re;  wire [N*AW-1:0]   u_vi_addr;  wire [N*32-1:0]   u_vi_q;
    wire [4*N*AW-1:0] u_rd_addr; wire [4*N-1:0]   u_rd_re;    wire [8*N-1:0]    u_rd_src; wire [4*N*32-1:0] u_rd_q;
    ot_hdc_delay #(.W(N), .D(DR), .RESET(1)) u_dvr (.clk(clk), .rst_n(rst_n), .d(u_vi_re), .q(vi_re));
    ot_hdc_delay #(.W(N*AW), .D(DR)) u_dva (.clk(clk), .rst_n(rst_n), .d(u_vi_addr), .q(vi_addr));
    ot_hdc_delay #(.W(4*N), .D(DR), .RESET(1)) u_drr (.clk(clk), .rst_n(rst_n), .d(u_rd_re), .q(rd_re));
    ot_hdc_delay #(.W(4*N*AW + 8*N), .D(DR)) u_dra (.clk(clk), .rst_n(rst_n), .d({u_rd_addr, u_rd_src}), .q({rd_addr, rd_src}));
    ot_hdc_delay #(.W(N*32), .D(DF)) u_dvq (.clk(clk), .rst_n(rst_n), .d(vi_q), .q(u_vi_q));
    ot_hdc_delay #(.W(4*N*32), .D(DF)) u_drq (.clk(clk), .rst_n(rst_n), .d(rd_q), .q(u_rd_q));
    // writes: DR is inside the unit (RET_STAGES + DR); NEG 3 moves it outside, so credits count before the landing
    localparam integer XD = (NEG == 3) ? DR : 0;
    wire [N-1:0] w_vm_we, w_kv_we; wire [N*AW-1:0] w_vm_waddr, w_kv_waddr; wire [N*32-1:0] w_vm_wdata, w_kv_wdata;
    wire [N/8-1:0] w_res_we; wire [N/8*AW-1:0] w_res_addr; wire [N/8*32-1:0] w_res_data;
    ot_hdc_delay #(.W(2*N + N/8), .D(XD), .RESET(1)) u_xwe (.clk(clk), .rst_n(rst_n), .d({w_vm_we, w_kv_we, w_res_we}), .q({vm_we, kv_we, res_we}));
    ot_hdc_delay #(.W(2*N*(AW+32) + N/8*(AW+32)), .D(XD)) u_xwd (.clk(clk), .rst_n(rst_n),
        .d({w_vm_waddr, w_vm_wdata, w_kv_waddr, w_kv_wdata, w_res_addr, w_res_data}), .q({vm_waddr, vm_wdata, kv_waddr, kv_wdata, res_addr, res_data}));
    ot_s81ph_su_adapt #(.RX(DF + DR - (NEG == 1 ? 1 : 0)), .GX(DF + DR - (NEG == 1 ? 1 : 0)), .N(N), .M(M), .LV(LV), .AW(AW), .NW(NW), .CLS_DRAIN(CLS_DRAIN),
                        .KVT_SH(KVT_SH), .BCAST_STAGES(BCAST_STAGES), .RET_STAGES(RET_STAGES + (NEG == 3 ? 0 : DR)), .MLAT(MLAT), .ALAT(ALAT)) u_su (
        .clk(clk), .rst_n(rst_n), .go(d_go), .ready(u_ready), .idle(u_idle),
        .i_nout(d_nout),
        .i_nin(d_nin),
        .i_chase(d_chase),
        .i_asrc(d_asrc),
        .i_bsrc(d_bsrc),
        .i_csrc(d_csrc),
        .i_dsrc(d_dsrc),
        .i_abase(d_abase),
        .i_aso(d_aso),
        .i_asi(d_asi),
        .i_aibase(d_aibase),
        .i_aind(d_aind),
        .i_bbase(d_bbase),
        .i_bso(d_bso),
        .i_bsi(d_bsi),
        .i_bhalf(d_bhalf),
        .i_cbase(d_cbase),
        .i_cso(d_cso),
        .i_csi(d_csi),
        .i_cpair(d_cpair),
        .i_dbase(d_dbase),
        .i_dso(d_dso),
        .i_dsi(d_dsi),
        .i_arnd(d_arnd),
        .i_arelu(d_arelu),
        .i_amin(d_amin),
        .i_cclip(d_cclip),
        .i_m1(d_m1),
        .i_m2(d_m2),
        .i_qm(d_qm),
        .i_ad(d_ad),
        .i_sfu(d_sfu),
        .i_e1(d_e1),
        .i_e2(d_e2),
        .i_rnd(d_rnd),
        .i_dst(d_dst),
        .i_obase(d_obase),
        .i_oso(d_oso),
        .i_osi(d_osi),
        .i_orow(d_orow),
        .i_red(d_red),
        .i_redsq(d_redsq),
        .i_redwhole(d_redwhole),
        .i_redtree(d_redtree),
        .i_redrnd(d_redrnd),
        .i_rbase(d_rbase),
        .i_rso(d_rso),
        .i_imm1(d_imm1),
        .i_imm2(d_imm2),
        .i_imm3(d_imm3),
        .i_m(d_m),
        .i_xps(d_xps),
        .i_ops(d_ops),
        .vi_re(u_vi_re), .vi_addr(u_vi_addr), .vi_q(u_vi_q),
        .rd_addr(u_rd_addr), .rd_re(u_rd_re), .rd_src(u_rd_src), .rd_q(u_rd_q),
        .vm_we(w_vm_we), .vm_waddr(w_vm_waddr), .vm_wdata(w_vm_wdata), .kv_we(w_kv_we), .kv_waddr(w_kv_waddr), .kv_wdata(w_kv_wdata),
        .res_we(w_res_we), .res_addr(w_res_addr), .res_data(w_res_data), .fault(u_fault), .dbg_ops(dbg_ops), .dbg_elems(dbg_elems));
endmodule
