`timescale 1ns/1ps
// r19 VM quadrant tiles joined vs the monolithic hfd_vm (views agent, 2026-10-07).
//   `MODE 1 (transaction): one reactive environment per design, indexed by transaction count: writes (f_su_NW request +
//     f_su_SW data), reads of written rows (f_su_SE), the tap ACKs forced on the root's cfg register (the die feeds them
//     from the static cfg chain), one wrong-owner ACK at op KF (sticky fault).  Compared (hash + count): every write ACK
//     owner, every publish (tap owners + the row at all four x faces), final fault / drained.
//   `MODE 2 (structure): random die inputs with the root idle (wr_v / rd_v held 0); every output bit of both designs is
//     dumped each cycle (trace_ref.hex / trace_dut.hex) for check_vm_tiles.py (one constant latency per output bit).
//   `MUT_XBUS: SW -> SE write bus bits 10/11 swapped in the joined design (SE slice data) -- must FAIL mode 1.
`ifndef MODE
`define MODE 1
`endif
`ifndef SEED
`define SEED 1
`endif
`ifndef NOPS
`define NOPS 60
`endif
`ifndef VM_DBG
`define VM_DBG 0
`endif
`ifndef KF
`define KF 50
`endif
module vm_joined (input wire [0:0] ck, input wire [0:0] rst,
    input wire [2047:0] f_su_SW, f_su_NW, f_su_SE, f_su_NE, input wire [511:0] iSW, iNW, iSE, iNE,
    output wire [2047:0] t_su_SW, t_su_NW, t_su_SE, t_su_NE, output wire [581:0] qSW, qNW, qSE, qNE,
    output wire [2067:0] xSW, xNW, xSE, xNE, output wire [1023:0] t_quant, output wire [511:0] t_router);
    wire [2263:0] sw_n_wr, nw_s_wr, sw_e_wr, se_w_wr, nw_e_wr, ne_w_wr, se_n_wr, ne_s_wr;
    wire [2255:0] sw_n_row, nw_s_row, sw_e_row, se_w_row, nw_e_row, ne_w_row, se_n_row, ne_s_row;
    wire [255:0] sw_n_ctl, nw_s_ctl, sw_e_ctl, se_w_ctl, nw_e_ctl, ne_w_ctl, se_n_ctl, ne_s_ctl;
`ifdef MUT_XBUS
    wire [2263:0] sw_e_wr_x = {sw_e_wr[2263:12], sw_e_wr[10], sw_e_wr[11], sw_e_wr[9:0]};
`else
    wire [2263:0] sw_e_wr_x = sw_e_wr;
`endif
    hfd_vm_sw u_sw (.ck(ck), .rst(rst), .f_su_SW(f_su_SW), .iSW(iSW), .qSW(qSW), .xSW(xSW), .t_su_SW(t_su_SW), .t_router(t_router),
        .f_n_wr(nw_s_wr), .f_n_row(nw_s_row), .f_n_ctl(nw_s_ctl), .t_n_wr(sw_n_wr), .t_n_row(sw_n_row), .t_n_ctl(sw_n_ctl),
        .f_e_wr(se_w_wr), .f_e_row(se_w_row), .f_e_ctl(se_w_ctl), .t_e_wr(sw_e_wr), .t_e_row(sw_e_row), .t_e_ctl(sw_e_ctl));
    hfd_vm_nw u_nw (.ck(ck), .rst(rst), .f_su_NW(f_su_NW), .iNW(iNW), .qNW(qNW), .xNW(xNW), .t_su_NW(t_su_NW), .t_quant(t_quant),
        .f_s_wr(sw_n_wr), .f_s_row(sw_n_row), .f_s_ctl(sw_n_ctl), .t_s_wr(nw_s_wr), .t_s_row(nw_s_row), .t_s_ctl(nw_s_ctl),
        .f_e_wr(ne_w_wr), .f_e_row(ne_w_row), .f_e_ctl(ne_w_ctl), .t_e_wr(nw_e_wr), .t_e_row(nw_e_row), .t_e_ctl(nw_e_ctl));
    hfd_vm_se u_se (.ck(ck), .rst(rst), .f_su_SE(f_su_SE), .iSE(iSE), .qSE(qSE), .xSE(xSE), .t_su_SE(t_su_SE),
        .f_w_wr(sw_e_wr_x), .f_w_row(sw_e_row), .f_w_ctl(sw_e_ctl), .t_w_wr(se_w_wr), .t_w_row(se_w_row), .t_w_ctl(se_w_ctl),
        .f_n_wr(ne_s_wr), .f_n_row(ne_s_row), .f_n_ctl(ne_s_ctl), .t_n_wr(se_n_wr), .t_n_row(se_n_row), .t_n_ctl(se_n_ctl));
    hfd_vm_ne u_ne (.ck(ck), .rst(rst), .f_su_NE(f_su_NE), .iNE(iNE), .qNE(qNE), .xNE(xNE), .t_su_NE(t_su_NE),
        .f_s_wr(se_n_wr), .f_s_row(se_n_row), .f_s_ctl(se_n_ctl), .t_s_wr(ne_s_wr), .t_s_row(ne_s_row), .t_s_ctl(ne_s_ctl),
        .f_w_wr(nw_e_wr), .f_w_row(nw_e_row), .f_w_ctl(nw_e_ctl), .t_w_wr(ne_w_wr), .t_w_row(ne_w_row), .t_w_ctl(ne_w_ctl));
endmodule

`define VM_ENV_NAME vm_env_m
`define VM_DUT hfd_vm
`define VM_CFG u.cfg
`define VM_TRACE "trace_ref.hex"
`define VM_ROOT u.u_mr.on
`include "vm_env_body.svh"
`undef VM_ENV_NAME
`undef VM_DUT
`undef VM_CFG
`undef VM_TRACE
`undef VM_ROOT
`define VM_ENV_NAME vm_env_t
`define VM_DUT vm_joined
`define VM_CFG u.u_sw.cfg
`define VM_TRACE "trace_dut.hex"
`define VM_ROOT u.u_sw.u_mr.on
`include "vm_env_body.svh"

module tb_vm_tiles;
    reg clk = 0; always #0.5 clk = ~clk;
    wire [63:0] ha, hb; integer na, nb; wire da, db, fa, fb;
    vm_env_m a (.clk(clk), .h(ha), .nev(na), .done(da), .fault_end(fa));
    vm_env_t b (.clk(clk), .h(hb), .nev(nb), .done(db), .fault_end(fb));
    integer t = 0;
    always @(posedge clk) begin
        t <= t + 1;
        if ((da && db) || t > 2000000) begin
            $display("VM_TILES mode=%0d seed=%0d events=%0d/%0d fault=%0d/%0d hash=%s", `MODE, `SEED, na, nb, fa, fb,
                     (ha === hb) ? "MATCH" : "DIFF");
            if (`MODE == 1 && (!(da && db) || ha !== hb || na != nb || fa != fb || na < 10)) $fatal(1, "VM_TILES FAIL");
            $finish;
        end
    end
endmodule
