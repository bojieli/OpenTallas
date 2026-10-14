`timescale 1ns/1ps
// Qwen3-8B ROM TP8 die, IO-band CDC slot qfd_io_xfifo as a leaf partition (el1013-qwen-small-masters r3b, 2026-10-13).
// The flat master ot_qwen_die_io_xfifo (62,971 flops + 4 x 4,096 receive-buffer bits on four clock roots, 11 failed flat
// routes) is nothing but independent credit CDC channels (ot_qwen_die_cdc_ch) and four fault OR flops.  The slot is
// therefore built as:
//   qfd_xf_ch    ONE hardened leaf = one 1,024-bit channel, ot_qwen_die_cdc_ch #(W 1024, PIPE 2) unchanged:
//                kept pin relay on i_v / i_d, registered credit i_cr, output pin station on o_v / o_d, o_cr captured
//                at the pin, sticky flop-launched faults.  Two clock roots (wck: the writer's clock, rck: the
//                reader's), 19,569 sinks in all (yosys bit level: 15,473 flops + the 4 x 1,024 receive buffer).
//                The same master serves both directions: ck -> cku / cks (TX) and cku / cks -> ck (RX).
//   qfd_io_xfifo wires-only parent (no flop, no tree of its own): 8 x qfd_xf_ch (UCIe TX / RX, 3 x SerDes TX / RX) + the
//                collective local port leaf; every channel fault leaves on its own pin (registered in the leaf): the
//                per-domain OR of the flat master (f_ck / f_cku / f_cks / f_ckd, one flop each) is not built here, the
//                consumer (qfd_io_collective fault collection) ORs registered bits.
// OT_XF_MUT (bench only): two data bits of the output word are swapped.
module qfd_xf_ch (
    input  wire          wck,
    input  wire          rck,
    input  wire          rst_n,
    input  wire          i_v,
    input  wire [1023:0] i_d,
    output wire          i_cr,
    output wire          w_fault,
    output wire          o_v,
    output wire [1023:0] o_d,
    input  wire          o_cr,
    output wire          r_fault
);
    wire [1023:0] od;
    ot_qwen_die_cdc_ch #(.W(1024), .PIPE(2)) u_ch (
        .wclk(wck), .wrst_n(rst_n), .i_v(i_v), .i_d(i_d), .i_cr(i_cr), .w_fault(w_fault),
        .rclk(rck), .rrst_n(rst_n), .o_v(o_v), .o_d(od), .o_cr(o_cr), .r_fault(r_fault));
`ifdef OT_XF_MUT
    assign o_d = {od[1023:518], od[5], od[516:6], od[517], od[4:0]};
`else
    assign o_d = od;
`endif
endmodule
