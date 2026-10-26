`timescale 1ns/1ps
// Actual arithmetic/control quarter candidate. Local8 cache/native VM endpoint remains external.
// Clocks must carry the same logical engine edges at phi-R; separate roots are not async CDC.
module ot_hgi_sfu_native_quarter #(parameter integer ENABLE_NATIVE=0, SPLIT_S_PIPE=0)(

    input  wire              clk,
    input  wire              rst_n,
    input  wire              go,
    output wire              ready,
    output wire               idle,
    // ---- instruction (DYN already added to the bases and counts)
    input  wire [NW-1:0]     i_nout, i_nin,
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
    // ---- chaining (see the protocol above)
    input  wire [1:0]        i_ch_src,
    input  wire [7:0]        i_ch_seq,
    input  wire [15:0]       i_ch_lead,
    input  wire [15:0]       i_ch_mul,
    input  wire [7:0]        x_seq, x_dseq,
    input  wire [15:0]       x_cnt,
    output wire  [7:0]        cr_seq, cr_dseq, cr_rseq,
    output wire [15:0]       cr_cnt,
    // ---- per lane: element writes
    output wire [N-1:0]      vm_we,
    output wire [N*AW-1:0]   vm_waddr,
    output wire [N*32-1:0]   vm_wdata,
    output wire [N-1:0]      kv_we,
    output wire [N*AW-1:0]   kv_waddr,
    output wire [N*32-1:0]   kv_wdata,
    // ---- reduction results (to the vector memory)
    output wire [N/8-1:0]    res_we,
    output wire [N/8*AW-1:0] res_addr,
    output wire [N/8*32-1:0] res_data,
    // ---- status
    output wire               fault,          // an arithmetic refusal or a configuration the unit cannot run
    output wire               order_fault,    // an internal ordering violation (never, by construction)
    output wire  [15:0]       emitted,        // vectors emitted since reset (bench)
    output wire               retire_o,       // a vector retired this cycle (bench)
    output wire              dbg_emit,       // this cycle: a vector of op dbg_eseq is emitted
    output wire [7:0]        dbg_eseq,
    output wire              dbg_ret,        // this cycle: a vector of op dbg_rseq retires (writes)
    output wire [7:0]        dbg_rseq,
    output wire              dbg_res,        // this cycle: results of op dbg_sseq are written
    output wire [7:0]        dbg_sseq,
    output wire admission_fault,
    input wire clk_s_ops_lo,clk_s_ops_hi,clk_s_meta_lo,clk_s_meta_hi,
    input wire [15:0] clk_lane, clk_map, rst_lane_n, rst_map_n,
    input wire [511:0] vi_q,
    input wire [2047:0] rd_q,
    output wire [15:0] vi_re,
    output wire [383:0] vi_addr,
    output wire [1535:0] rd_addr,
    output wire [63:0] rd_re,
    output wire [127:0] rd_src,
    output wire [15:0] lane_fault, lane_coll
);
localparam N=16, AW=24, NW=16;
wire [1741:0] control, raw_control;
`ifdef OT_SFU_PHASE_MUTANT
// Genuine negative control: add a physical control register edge without shifting retirement metadata.
reg [1741:0] shifted_control;
always @(posedge clk) shifted_control<=raw_control;
assign control=shifted_control;
`else
assign control=raw_control;
`endif
wire [15:0] l_vm_we,l_kv_we,l_rov;
wire [383:0] l_vm_waddr,l_kv_waddr;
wire [511:0] l_vm_wdata,l_kv_wdata,l_rox;
ot_hgi_sfu_ctl_extract #(.ENABLE_NATIVE(ENABLE_NATIVE),.SPLIT_S_PIPE(SPLIT_S_PIPE)) u_ctl (
.clk(clk),
.rst_n(rst_n),
.go(go),
.ready(ready),
.idle(idle),
.i_nout(i_nout),
.i_nin(i_nin),
.i_asrc(i_asrc),
.i_bsrc(i_bsrc),
.i_csrc(i_csrc),
.i_dsrc(i_dsrc),
.i_abase(i_abase),
.i_aso(i_aso),
.i_asi(i_asi),
.i_aibase(i_aibase),
.i_aind(i_aind),
.i_bbase(i_bbase),
.i_bso(i_bso),
.i_bsi(i_bsi),
.i_bhalf(i_bhalf),
.i_cbase(i_cbase),
.i_cso(i_cso),
.i_csi(i_csi),
.i_cpair(i_cpair),
.i_dbase(i_dbase),
.i_dso(i_dso),
.i_dsi(i_dsi),
.i_arnd(i_arnd),
.i_arelu(i_arelu),
.i_amin(i_amin),
.i_cclip(i_cclip),
.i_m1(i_m1),
.i_m2(i_m2),
.i_qm(i_qm),
.i_ad(i_ad),
.i_sfu(i_sfu),
.i_e1(i_e1),
.i_e2(i_e2),
.i_rnd(i_rnd),
.i_dst(i_dst),
.i_obase(i_obase),
.i_oso(i_oso),
.i_osi(i_osi),
.i_orow(i_orow),
.i_red(i_red),
.i_redsq(i_redsq),
.i_redwhole(i_redwhole),
.i_redtree(i_redtree),
.i_redrnd(i_redrnd),
.i_rbase(i_rbase),
.i_rso(i_rso),
.i_imm1(i_imm1),
.i_imm2(i_imm2),
.i_imm3(i_imm3),
.i_ch_src(i_ch_src),
.i_ch_seq(i_ch_seq),
.i_ch_lead(i_ch_lead),
.i_ch_mul(i_ch_mul),
.x_seq(x_seq),
.x_dseq(x_dseq),
.x_cnt(x_cnt),
.cr_seq(cr_seq),
.cr_dseq(cr_dseq),
.cr_rseq(cr_rseq),
.cr_cnt(cr_cnt),
.vm_we(vm_we),
.vm_waddr(vm_waddr),
.vm_wdata(vm_wdata),
.kv_we(kv_we),
.kv_waddr(kv_waddr),
.kv_wdata(kv_wdata),
.res_we(res_we),
.res_addr(res_addr),
.res_data(res_data),
.fault(fault),
.order_fault(order_fault),
.emitted(emitted),
.retire_o(retire_o),
.dbg_emit(dbg_emit),
.dbg_eseq(dbg_eseq),
.dbg_ret(dbg_ret),
.dbg_rseq(dbg_rseq),
.dbg_res(dbg_res),
.dbg_sseq(dbg_sseq),
.admission_fault(admission_fault),
.clk_s_ops_lo(clk_s_ops_lo),.clk_s_ops_hi(clk_s_ops_hi),.clk_s_meta_lo(clk_s_meta_lo),.clk_s_meta_hi(clk_s_meta_hi),
.grid_control(raw_control),.l_fault(lane_fault),.l_coll(lane_coll),.l_rov(l_rov),
.l_vm_we(l_vm_we),.l_kv_we(l_kv_we),.l_vm_waddr(l_vm_waddr),.l_kv_waddr(l_kv_waddr),
.l_vm_wdata(l_vm_wdata),.l_kv_wdata(l_kv_wdata),.l_rox(l_rox));
ot_hgi_sfu_arithmetic_grid u_grid (
.clk_lane(clk_lane),.clk_map(clk_map),.rst_lane_n(rst_lane_n),.rst_map_n(rst_map_n),
.control(control),.vi_q(vi_q),.rd_q(rd_q),
.vi_re(vi_re),.vi_addr(vi_addr),.rd_addr(rd_addr),.rd_re(rd_re),.rd_src(rd_src),
.vm_we(l_vm_we),.kv_we(l_kv_we),.ro_v(l_rov),.fault(lane_fault),.coll(lane_coll),
.vm_waddr(l_vm_waddr),.kv_waddr(l_kv_waddr),.vm_wdata(l_vm_wdata),.kv_wdata(l_kv_wdata),.ro_x(l_rox));
endmodule
