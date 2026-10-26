`timescale 1ps/1ps
(* blackbox *) module q3_body_clock_stub (
    input wire clk_control,
    input wire clk_program,
    input wire [15:0] clk_upipe,
    input wire clk_issue,
    input wire [28:0] clk_qslots,
    input wire clk_reduce
); endmodule
(* blackbox *) module q3_edge_clock_stub (
    input wire arg_clk,
    input wire [4:0] link0_ck,
    input wire [4:0] link1_ck,
    input wire [4:0] link2_ck
); endmodule
(* blackbox *) module q3_vm_clock_stub (
    input wire [15:0] vmasm_clk,
    input wire writer_clk_rgx_data0,
    input wire writer_clk_rgx_data1,
    input wire writer_clk_rgx_data2,
    input wire writer_clk_rgx_data3,
    input wire writer_clk_rgx_ctrl,
    input wire writer_clk_tkw,
    input wire writer_clk_meta,
    input wire writer_clk_body,
    input wire writer_clk_bank0,
    input wire writer_clk_bank1,
    input wire writer_clk_bank2,
    input wire writer_clk_bank3,
    input wire writer_clk_bank4,
    input wire writer_clk_bank5,
    input wire writer_clk_bank6,
    input wire writer_clk_bank7
); endmodule
(* blackbox *) module q3_reduce_clock_stub (
    input wire reduce_clk_control,
    input wire [15:0] reduce_clk_state,
    input wire [15:0] reduce_clk_add
); endmodule
(* blackbox *) module q3_ring_ag_clock_stub (
    input wire ring_clk,
    input wire [7:0] ring_clk_state,
    input wire [7:0] ring_clk_add
); endmodule
module native_clock_alias_probe(input wire clk);
  localparam NLINK=3;
  wire [0:0] clk_program = clk;
  wire [0:0] clk_control = clk;
  wire [0:0] clk_issue = clk;
  wire [0:0] clk_arg = clk;
  wire [15:0] clk_vmasm = {16{clk}};
  wire [15:0] clk_upipe = {16{clk}};
  wire [28:0] clk_qslots = {(NLINK+8+18){clk}};
  wire [16:0] clk_ring = {17{clk}};
  wire [32:0] clk_reduce = {33{clk}};
  wire [15:0] clk_vmwrite = {16{clk}};
  wire [14:0] clk_link = {(5*NLINK){clk}};
  q3_body_clock_stub body (
    .clk_control(clk_control),
    .clk_program(clk_program),
    .clk_upipe({ clk_upipe[15], clk_upipe[14], clk_upipe[13], clk_upipe[12], clk_upipe[11], clk_upipe[10], clk_upipe[9], clk_upipe[8], clk_upipe[7], clk_upipe[6], clk_upipe[5], clk_upipe[4], clk_upipe[3], clk_upipe[2], clk_upipe[1], clk_upipe[0] }),
    .clk_issue(clk_issue),
    .clk_qslots({ clk_qslots[28], clk_qslots[27], clk_qslots[26], clk_qslots[25], clk_qslots[24], clk_qslots[23], clk_qslots[22], clk_qslots[21], clk_qslots[20], clk_qslots[19], clk_qslots[18], clk_qslots[17], clk_qslots[16], clk_qslots[15], clk_qslots[14], clk_qslots[13], clk_qslots[12], clk_qslots[11], clk_qslots[10], clk_qslots[9], clk_qslots[8], clk_qslots[7], clk_qslots[6], clk_qslots[5], clk_qslots[4], clk_qslots[3], clk_qslots[2], clk_qslots[1], clk_qslots[0] }),
    .clk_reduce(clk_reduce[0])
  );
  q3_edge_clock_stub edge (
    .arg_clk(clk_arg),
    .link0_ck({ clk_link[4], clk_link[3], clk_link[2], clk_link[1], clk_link[0] }),
    .link1_ck({ clk_link[9], clk_link[8], clk_link[7], clk_link[6], clk_link[5] }),
    .link2_ck({ clk_link[14], clk_link[13], clk_link[12], clk_link[11], clk_link[10] })
  );
  q3_vm_clock_stub vm (
    .vmasm_clk({ clk_vmasm[15], clk_vmasm[14], clk_vmasm[13], clk_vmasm[12], clk_vmasm[11], clk_vmasm[10], clk_vmasm[9], clk_vmasm[8], clk_vmasm[7], clk_vmasm[6], clk_vmasm[5], clk_vmasm[4], clk_vmasm[3], clk_vmasm[2], clk_vmasm[1], clk_vmasm[0] }),
    .writer_clk_rgx_data0(clk_vmwrite[0]),
    .writer_clk_rgx_data1(clk_vmwrite[1]),
    .writer_clk_rgx_data2(clk_vmwrite[2]),
    .writer_clk_rgx_data3(clk_vmwrite[3]),
    .writer_clk_rgx_ctrl(clk_vmwrite[4]),
    .writer_clk_tkw(clk_vmwrite[5]),
    .writer_clk_meta(clk_vmwrite[6]),
    .writer_clk_body(clk_vmwrite[7]),
    .writer_clk_bank0(clk_vmwrite[8]),
    .writer_clk_bank1(clk_vmwrite[9]),
    .writer_clk_bank2(clk_vmwrite[10]),
    .writer_clk_bank3(clk_vmwrite[11]),
    .writer_clk_bank4(clk_vmwrite[12]),
    .writer_clk_bank5(clk_vmwrite[13]),
    .writer_clk_bank6(clk_vmwrite[14]),
    .writer_clk_bank7(clk_vmwrite[15])
  );
  q3_reduce_clock_stub reduce (
    .reduce_clk_control(clk_reduce[0]),
    .reduce_clk_state({ clk_reduce[16], clk_reduce[15], clk_reduce[14], clk_reduce[13], clk_reduce[12], clk_reduce[11], clk_reduce[10], clk_reduce[9], clk_reduce[8], clk_reduce[7], clk_reduce[6], clk_reduce[5], clk_reduce[4], clk_reduce[3], clk_reduce[2], clk_reduce[1] }),
    .reduce_clk_add({ clk_reduce[32], clk_reduce[31], clk_reduce[30], clk_reduce[29], clk_reduce[28], clk_reduce[27], clk_reduce[26], clk_reduce[25], clk_reduce[24], clk_reduce[23], clk_reduce[22], clk_reduce[21], clk_reduce[20], clk_reduce[19], clk_reduce[18], clk_reduce[17] })
  );
  q3_ring_ag_clock_stub ring_ag (
    .ring_clk(clk_ring[0]),
    .ring_clk_state({ clk_ring[8], clk_ring[7], clk_ring[6], clk_ring[5], clk_ring[4], clk_ring[3], clk_ring[2], clk_ring[1] }),
    .ring_clk_add({ clk_ring[16], clk_ring[15], clk_ring[14], clk_ring[13], clk_ring[12], clk_ring[11], clk_ring[10], clk_ring[9] })
  );
endmodule
