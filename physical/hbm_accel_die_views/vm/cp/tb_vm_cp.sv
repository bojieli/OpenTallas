`timescale 1ns/1ps
// [vm8cp] channel-plan VM (hfd_vm_cp: logic tiles + relay tiles) vs the monolithic hfd_vm; modes as the r19 tiles bench.
//   MUT_XBUS: SE slice write-data bits 10/11 swapped; MUT_RELAY: xSE tap bits 10/11 swapped in the E fork.
//   `MODE 1 (transaction): one reactive environment per design, indexed by transaction count: writes (f_su_NW request +
//     f_su_SW data), reads of written rows (f_su_SE), the tap ACKs forced on the root's cfg register (the die feeds them
//     from the static cfg chain), one wrong-owner ACK at op KF (sticky fault).  Compared (hash + count): every write ACK
//     owner, every publish (tap owners + the row at all four x faces), final fault / drained.
//   `MODE 2 (structure): random die inputs with the root idle (wr_v / rd_v held 0); every output bit of both designs is
//     dumped each cycle (trace_ref.hex / trace_dut.hex) for check_vm_tiles.py (one constant latency per output bit).
//   `MODE 3 (port depth): every field of the root's write / read port matched against the die-pin history (vm_env_body).
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

`define VM_ENV_NAME vm_env_m
`define VM_DUT hfd_vm
`define VM_CFG u.cfg
`define VM_TRACE "trace_ref.hex"
`define VM_ROOT u.u_mr.on
`define VM_RT u.u_mr
`include "vm_env_body_cp.svh"
`undef VM_ENV_NAME
`undef VM_DUT
`undef VM_CFG
`undef VM_TRACE
`undef VM_ROOT
`undef VM_RT
`define VM_ENV_NAME vm_env_t
`define VM_DUT hfd_vm_cp
`define VM_CFG u.u_root.cfg
`define VM_TRACE "trace_dut.hex"
`define VM_ROOT u.u_root.u_mr.on
`define VM_RT u.u_root.u_mr
`include "vm_env_body_cp.svh"

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
