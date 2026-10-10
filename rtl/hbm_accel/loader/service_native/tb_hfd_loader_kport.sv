`timescale 1ps/1ps
// ot_hfd_loader_kport bench (hgi-takeover): two loader lanes -> four stacks, each an actual ot_hbm_svc_core_native
// (NATIVE, WB, WB_SOURCE_ACK, KVS) + refresh-aware controller model, through the lq / lr die packing.  Both lanes write
// interleaved sectors spread over all four stacks and all PCs, then read them back; every write packet must arrive at
// the svc of the stack that owns its address, and every read must return the written data on the issuing lane.
module tb_hfd_loader_kport;
 parameter integer MUT = 0;
 reg clk=0; always #416 clk=~clk; reg rst_n=0;
 localparam [35:0] SB = 36'd65536;            // per-stack capacity used here (fits the controller model's memory)
 reg [1:0] req_v=0, req_we=0, rsp_rdy=0; reg [73:0] req_addr=0; reg [511:0] req_wdata=0; reg [31:0] req_tag=0;
 wire [1:0] req_rdy, rsp_v, rsp_we; wire [31:0] rsp_tag; wire [511:0] rsp_data; wire fault;
 wire [4*346-1:0] lq; wire [4*293-1:0] lr;
 ot_hfd_loader_kport #(.ENABLE(1),.ND(2),.STACK_BYTES(SB),.MUT(MUT)) dut(.clk(clk),.rst_n(rst_n),.req_v(req_v),
  .req_rdy(req_rdy),.req_we(req_we),.req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb({32'hffffffff,32'hffffffff}),
  .req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_we(rsp_we),.rsp_tag(rsp_tag),.rsp_data(rsp_data),.lq(lq),.lr(lr),
  .fault(fault));
 genvar s;
 integer placed_bad=0;
 for (s=0;s<4;s=s+1) begin : g_st
  wire [345:0] q = lq[s*346 +: 346];
  wire[31:0]k_v,k_rdy,k_we,kr_v,kr_rdy,k_wr_done; wire[959:0]k_addr; wire[127:0]k_len,kr_beat; wire[543:0]k_tag,kr_tag;
  wire[8191:0]k_wdata,kr_data; wire[1023:0]k_wstrb; wire[31:0]wq_source_g,wq_source_busy; wire wq_source_fault,wq_pending,native_fault,phy_rst_n;
  wire n_rdy,n_rsp_v; wire[4:0]n_rsp_pc; wire[15:0]n_rsp_tag; wire[3:0]n_rsp_beat; wire[255:0]n_rsp_data;
  assign lr[s*293 +: 293] = {wq_source_fault, wq_source_g[31:24], native_fault, n_rsp_data, n_rsp_beat, n_rsp_tag, n_rsp_pc, n_rsp_v, n_rdy};
  ot_hbm_svc_core_native #(.NATIVE(1),.WB(1),.WB_SOURCE_ACK(1),.KVS(1),.XST(0),.WQ_ST(1)) service(
   .ck(clk),.rst(rst_n),.q_d(336'b0),.q_v(8'b0),.q_fclk(8'b0),.e_d(128'b0),.e_fclk(1'b0),
   .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
   .kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data),
   .w_rdy(1'b1),.w_room(8'hff),.wr_v(8'b0),.wr_tag(80'b0),.wr_beat(40'b0),.wr_data(2048'b0),
   .wq_d(q[291:0]),.wq_fclk(clk),.wq_source(2'd2),.wq_source_g(wq_source_g),.wq_source_fault(wq_source_fault),
   .wq_source_busy(wq_source_busy),.wq_pending(wq_pending),.k_wr_done(k_wr_done),.phy_rst_n(phy_rst_n),
   .outer_write_pending(q[345]),
   .native_v(q[292]),.native_rdy(n_rdy),.native_pc(q[297:293]),.native_addr(q[327:298]),.native_tag(q[343:328]),.native_len(4'd1),
   .native_rsp_v(n_rsp_v),.native_rsp_rdy(q[344]),.native_rsp_pc(n_rsp_pc),.native_rsp_tag(n_rsp_tag),
   .native_rsp_beat(n_rsp_beat),.native_rsp_data(n_rsp_data),.native_fault(native_fault));
  ot_hdc_v41x_idx_hbm #(.NPC(32),.AW(30),.DW(256),.MEM_WORDS(1024),.TAGW(17),.LENW(4),.BEATW(4),.QD(64),.REFPB(3),.MEM_MODE(0)) phy(
   .clk(clk),.rst_n(phy_rst_n),.req_v(k_v),.req_rdy(k_rdy),.req_addr(k_addr),.req_len(k_len),.req_tag(k_tag),.req_we(k_we),
   .req_wdata(k_wdata),.req_wstrb(k_wstrb),.wr_done(k_wr_done),.rsp_v(kr_v),.rsp_rdy(kr_rdy),.rsp_tag(kr_tag),.rsp_beat(kr_beat),.rsp_data(kr_data));
  // placement: a write packet's data carries its stack in word 1 (the bench's pattern), it must land on stack s
  always @(posedge clk) if (rst_n && q[0] && q[291:260] != 32'(s)) begin
   $display("FATAL: stack %0d received a write for stack %0d", s, q[291:260]); placed_bad = placed_bad + 1;
  end
 end
 function [255:0] pat(input integer stk, input integer lane, input integer j);
  pat = {32'(stk), 32'h5a000000 + 32'(lane*4096 + j), 192'(j * 32'h01010101 + lane)};
 endfunction
 // lane d, transaction j: stack (j + d) % 4, sector 32*j + 4*d (+ stack base) : spreads PCs and stacks
 function [36:0] adr(input integer lane, input integer j);
  adr = {2'((j + lane) % 4), 35'(((j * 8 + lane) * 32) % 65536)};
 endfunction
 integer ph, j, d, done_n=0, cycles=0;
 integer jj [0:1]; reg [1:0] pend, acc;
 initial begin
  repeat(4) @(posedge clk); rst_n=1; repeat(16) @(posedge clk);
  for (ph=0; ph<2; ph=ph+1) begin                       // 0: write all, 1: read all back
   jj[0]=0; jj[1]=0; pend=0;
   while (jj[0] < 64 || jj[1] < 64 || pend != 0 || req_v != 0) begin
    @(posedge clk); cycles=cycles+1; if (cycles > 4000000) $fatal(1, "FATAL: liveness");
    for (d=0; d<2; d=d+1) begin                  // handshakes at this edge (pre-edge values)
     if (rsp_v[d] && rsp_rdy[d]) begin
      if (rsp_tag[d*16 +: 16] !== 16'(jj[d]-1 + d*1024) || rsp_we[d] !== (ph==0) ||
          rsp_data[d*256 +: 256] !== (ph==0 ? 256'd0 : pat((jj[d]-1 + d) % 4, d, jj[d]-1)))
        $fatal(1, "FATAL: lane %0d response mismatch j=%0d tag=%h", d, jj[d]-1, rsp_tag[d*16 +: 16]);
      pend[d]=0; done_n = done_n + 1;
     end
     acc[d] = req_v[d] && req_rdy[d];
    end
    @(negedge clk);
    for (d=0; d<2; d=d+1) begin
     if (acc[d]) begin req_v[d]=0; pend[d]=1; end
     rsp_rdy[d] = pend[d] && ($random & 1);
     if (!req_v[d] && !pend[d] && jj[d] < 64) begin
      req_v[d]=1; req_we[d]=(ph==0); req_addr[d*37 +: 37]=adr(d, jj[d]); req_tag[d*16 +: 16]=16'(jj[d] + d*1024);
      req_wdata[d*256 +: 256]=pat((jj[d] + d) % 4, d, jj[d]); jj[d]=jj[d]+1;
     end
    end
   end
  end
  if (fault || placed_bad) $fatal(1, "FATAL: fault=%0d placement errors=%0d", fault, placed_bad);
  if (done_n != 256) $fatal(1, "FATAL: %0d of 256 transactions completed", done_n);
  $display("PASS HFD-LOADER-KPORT lanes=2 stacks=4 transactions=256 (128 writes / 128 reads) cycles=%0d", cycles);
  $finish;
 end
endmodule
