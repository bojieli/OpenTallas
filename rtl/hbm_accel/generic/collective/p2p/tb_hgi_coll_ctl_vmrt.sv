`timescale 1ns/1ps
`default_nettype none
// HBM-BANKLAT-COLL 10-19: COLL parent VM read path at a VM_RT budget. DUT = the protocol leaf the v8 parent binds at
// VM_RT > 0 (ot_hgi_coll_ctl_v5r_q2 #(VM_RT)) + the unchanged 16 assembly slices (ot_hgi_coll_vmasm_sliced_v7), wired
// exactly as ot_hfd_coll_q_hard_v8g_body (vm_sel = VM_RT ? vm_sel_d : the uop-pipe d3 select; bit-interleaved faces).
// VM model = the d4g faces bank (pin flop +1 on rq, bank read n+6 after its own sample -> answer n+7 at the bank pins)
// behind UNEQUAL per-bank die lanes (rq lane LQ[b], rr lane LR[b]) padded on the 17-bit request side to the budget:
// round trip at the client = n+8+LAT with LAT = 1 + LQ[b] + LR[b] + PAD[b] for every bank.
// Programme: random full 8-bank reads (random pairings, random sectors / metadata) and idle edges.
// PASS: no protocol fault; every assembled pair = {bank hi word, bank lo word} of the request, in order, with its
// metadata, on edge E + 10 + VM_RT (E = the edge the instruction is sampled by the leaf: "VM capture P+10").
// Mutants (must FAIL): MUT 1 VM_RT = LAT-1 (one short), MUT 2 VM_RT = 0 (the closed v5 leaf / today), MUT 3 lanes NOT
// padded (VM_RT = LAT but each bank answers at its raw lane latency).
module tb_hgi_coll_ctl_vmrt;
 parameter integer LAT = 74, MUT = 0;
 localparam integer VM_RT = (MUT == 1) ? LAT - 1 : (MUT == 2) ? 0 : LAT;
 localparam integer NOPS = 600;
 reg clk = 0; always #0.5 clk = ~clk;
 reg rst_n = 0;
 integer cyc = 0; always @(posedge clk) cyc <= cyc + 1;
 // per-bank raw die lanes (GEN2c-like spread), padded on the request side to LAT
 integer LQ [0:7] = '{2, 5, 9, 14, 20, 26, 31, 35};
 integer LR [0:7] = '{1, 4, 6, 12, 17, 22, 27, 37};
 function automatic integer dly(input integer b);   // bank answer edge after the client's request edge, minus 7
  return (MUT == 3) ? 1 + LQ[b] + LR[b] : LAT;
 endfunction
 reg [1535:0] inst = 0;          // the uop pipe d2 word (sampled by the leaf's inst_q = the parent's d3)
 reg [1535:0] inst_d3 = 0; always @(posedge clk) inst_d3 <= inst;
 wire [135:0] vm_rq; wire [7:0] vm_rv; wire [2055:0] vm_rr;
 wire [131:0] vm_meta; wire [3:0] vm_av; wire protocol_fault; wire [23:0] vm_sel_d;
 wire [1:0] inj_req; wire [31:0] inj_idx; wire [159:0] inj_addr, del_obase, rgx_addr; wire [1:0] inj_v; wire [65:0] inj_meta;
 wire [23:0] held; wire [47:0] wseq, rseq, xseq; wire [31:0] cycles;
 // HBM-ARGMAX 10-19: +define+CTL_Q3 benches the q3 leaf (kit hcoll_v5r_ctl3_v74); default = the q2 leaf
`ifdef CTL_Q3
 ot_hgi_coll_ctl_v5r_q3
`else
 ot_hgi_coll_ctl_v5r_q2
`endif
  #(.VM_RT(VM_RT)) dut(.clk_control(clk), .rst_n(rst_n), .inst(inst), .tap_iteration(32'd0),
  .tap_steps(88'd0), .hgi_start(1'b0), .hgi_busy(1'b0), .issue_done(1'b0), .tkm_done(1'b0), .tkm_busy(1'b0),
  .dest_v(15'd0), .rc_v(1'b0), .rc_tag(3'd0), .vm_rv(vm_rv), .vm_req_pin(vm_rq), .inj_req_pin(inj_req),
  .inj_idx_pin(inj_idx), .inj_addr_pin(inj_addr), .delivery_obase_pin(del_obase), .rgx_addr_pin(rgx_addr),
  .inj_source_v(inj_v), .inj_source_meta(inj_meta), .vm_source_meta(vm_meta), .vm_assembled_v(vm_av),
  .held_epoch(held), .wr_sequence_pin(wseq), .rd_sequence_pin(rseq), .rx_sequence_pin(xseq),
  .protocol_fault(protocol_fault), .cycles(cycles), .vm_sel_d(vm_sel_d));
 // the v8 body's VM wiring
 wire [23:0] vm_sel = (VM_RT == 0) ? inst_d3[1383 +: 24] : vm_sel_d;
 wire [2047:0] rd_il, as_il, vm_assembled;
 for (genvar b = 0; b < 8; b = b + 1) begin : g_split
  assign vm_rv[b] = vm_rr[b*257+256];
  for (genvar i = 0; i < 256; i = i + 1) begin : g_bit assign rd_il[i*8+b] = vm_rr[b*257+i]; end
 end
 for (genvar j = 0; j < 4; j = j + 1) begin : g_out
  for (genvar i = 0; i < 256; i = i + 1) begin : g_bit
   assign vm_assembled[j*512+i] = as_il[i*8+2*j]; assign vm_assembled[j*512+256+i] = as_il[i*8+2*j+1];
  end
 end
 ot_hgi_coll_vmasm_sliced_v7 u_vmasm(.clk({16{clk}}), .sel(vm_sel), .rd_il(rd_il), .as_il(as_il));
 // VM model: bank b answers 7 + dly(b) edges after the request edge (request visible after edge n -> answer after n+7+dly)
 function automatic [255:0] word(input integer b, input [15:0] s);
  reg [255:0] w; for (integer k = 0; k < 8; k = k + 1) w[k*32 +: 32] = 32'h9e3779b9 * (32'(s) * 16 + 32'(b) * 2 + 32'(k) + 1) ^ 32'h5bd1e995;
  return w;
 endfunction
 localparam integer DMAX = 8 + 2 * 128;
 reg [256:0] line [0:7][0:DMAX-1];
 reg [256:0] rr_q [0:7];
 for (genvar b = 0; b < 8; b = b + 1) begin : g_rr assign vm_rr[b*257 +: 257] = rr_q[b]; end
 always @(posedge clk) for (integer b = 0; b < 8; b = b + 1) begin
  for (integer d = DMAX - 1; d > 0; d = d - 1) line[b][d] <= line[b][d-1];
  line[b][0] <= vm_rq[b*17+16] ? {1'b1, word(b, vm_rq[b*17 +: 16])} : 257'd0;
  rr_q[b] <= line[b][7 + dly(b) - 2];
 end
 // expected outputs (by issue order) and their edge
 reg [511:0] exp_d [0:4*NOPS-1]; reg [131:0] exp_m [0:4*NOPS-1]; integer exp_e [0:4*NOPS-1]; reg [1:0] exp_j [0:4*NOPS-1];
 integer nexp = 0, ngot = 0, errors = 0, faults = 0;
 always @(posedge clk) if (rst_n) begin
  if (protocol_fault) faults = faults + 1;
  for (integer j = 0; j < 4; j = j + 1) if (vm_av[j]) begin
   if (ngot >= nexp || exp_j[ngot] != 2'(j) || exp_e[ngot] != cyc || vm_assembled[j*512 +: 512] !== exp_d[ngot] ||
       vm_meta[j*33 +: 33] !== exp_m[ngot][j*33 +: 33]) begin
    if (errors < 10) $display("COLL_VMRT mismatch out%0d pair%0d cyc%0d exp_cyc%0d", ngot, j, cyc, ngot < nexp ? exp_e[ngot] : -1);
    errors = errors + 1;
   end
   ngot = ngot + 1;
  end
 end
 initial begin
  for (integer b = 0; b < 8; b = b + 1) begin rr_q[b] = 0; for (integer d = 0; d < DMAX; d = d + 1) line[b][d] = 0;
   if (1 + LQ[b] + LR[b] > LAT) $fatal(1, "lane budget");
  end
  repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
  for (integer t = 0; t < NOPS; t = t + 1) begin
   inst = 0;
   if ($urandom % 4 != 0) begin
    integer perm [0:7]; reg [131:0] m;
    for (integer b = 0; b < 8; b = b + 1) perm[b] = b;
    for (integer b = 7; b > 0; b = b - 1) begin integer r, x; r = $urandom % (b + 1); x = perm[b]; perm[b] = perm[r]; perm[r] = x; end
    m = {$urandom, $urandom, $urandom, $urandom, $urandom};
    for (integer b = 0; b < 8; b = b + 1) inst[1034 + b*17 +: 17] = {1'b1, 16'($urandom)};
    for (integer j = 0; j < 4; j = j + 1) inst[1383 + j*6 +: 6] = {3'(perm[2*j+1]), 3'(perm[2*j])};
    inst[1170 +: 132] = m;
    // the leaf samples inst at the next posedge (cyc + 1 there): request pin after it, assembled on E + 10 + VM_RT
    for (integer j = 0; j < 4; j = j + 1) begin
     exp_d[nexp] = {word(perm[2*j+1], inst[1034 + perm[2*j+1]*17 +: 16]), word(perm[2*j], inst[1034 + perm[2*j]*17 +: 16])};
     exp_m[nexp] = m; exp_j[nexp] = 2'(j); exp_e[nexp] = cyc + 1 + 10 + LAT; nexp = nexp + 1;
    end
   end
   @(negedge clk);
  end
  inst = 0; repeat (LAT + 40) @(negedge clk);
  if (errors == 0 && faults == 0 && ngot == nexp)
   $display("COLL_VMRT PASS LAT%0d VM_RT%0d pairs%0d lanes_padded_to_budget", LAT, VM_RT, ngot);
  else begin
   $display("COLL_VMRT FAIL MUT%0d LAT%0d VM_RT%0d errors%0d protocol_fault_edges%0d got%0d exp%0d", MUT, LAT, VM_RT, errors, faults, ngot, nexp);
   $fatal(1, "COLL VM_RT");
  end
  $finish;
 end
endmodule
`default_nettype wire
