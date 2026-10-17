// H7 scalar sticky vs additive six registered fault classes; wrapper selects actual endpoints.
`timescale 1ps/1fs
// H-HARDEN 2026-10-16: lockstep miter of the configured PC controller leaf, QREG=0 (H6 exactly) versus QREG=1
// (free-slot queue writes, registered push entry, late identity select, controller PHYS_WACT 2).  Same K requests,
// response back-pressure and in-order DRAM returns drive both; every output is compared on every edge (col_data /
// col_strb only with col_v: the PHY samples them with the command).  Three reset phases, legal traffic over two rows
// with reads of length 1..4 and writes, then a phase that ends with illegal requests (sticky owner fault).
module tb;
  reg clk=0; always #512 clk=~clk;
  reg rst_n=0;
  reg [4:0] pc_id=5'd9; reg [7:0] refresh_reload=8'd151;   // the P=9 PHASE=0 die strap (ot_hbm_svc_pc_ctrl_leaf RELOAD)
  reg k_v=0,k_we=0,kr_rdy=0; reg [29:0] k_addr=0; reg [3:0] k_len=1; reg [16:0] k_tag=0;
  reg [255:0] k_wdata=0; reg [31:0] k_wstrb=0;
  reg dram_rvalid=0; reg [255:0] dram_rdata=0;
  wire [1:0] k_rdy,kr_v,k_wr_done,row_v,col_v,col_we,pc_fault,owner_fault;
  wire [16:0] kr_tag[2]; wire [3:0] kr_beat[2]; wire [255:0] kr_data[2],col_data[2]; wire [31:0] col_strb[2];
  wire [2:0] row_op[2]; wire [4:0] row_bank[2],col_bank[2],col_col[2]; wire [18:0] row_row[2];
  for(genvar g=0;g<2;g=g+1)begin:impl
    ot_hbm_svc_pc_ctrl_leaf_cfg #(.QREG(g)) dut(.clk(clk),.rst_n(rst_n),.pc_id(pc_id),.refresh_reload(refresh_reload),
      .k_v(k_v),.k_rdy(k_rdy[g]),.k_we(k_we),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_wdata(k_wdata),.k_wstrb(k_wstrb),
      .kr_v(kr_v[g]),.kr_rdy(kr_rdy),.kr_tag(kr_tag[g]),.kr_beat(kr_beat[g]),.kr_data(kr_data[g]),.k_wr_done(k_wr_done[g]),
      .row_v(row_v[g]),.row_op(row_op[g]),.row_bank(row_bank[g]),.row_row(row_row[g]),
      .col_v(col_v[g]),.col_we(col_we[g]),.col_bank(col_bank[g]),.col_col(col_col[g]),.col_data(col_data[g]),.col_strb(col_strb[g]),
      .dram_rvalid(dram_rvalid),.dram_rdata(dram_rdata),.pc_fault(pc_fault[g]),.owner_fault(owner_fault[g]));
  end

 integer c,checks=0;
 initial begin
 for(c=0;c<6;c=c+1)begin
 rst_n=0;k_v=0;repeat(6)@(posedge clk);@(negedge clk);#1;rst_n=1;repeat(6)@(posedge clk);@(negedge clk);#1;
 case(c)
0:begin
 force impl[0].dut.g_ref.u.i_v=1'b1;
 force impl[1].dut.g_cand.u.i_v=1'b1;
 force impl[0].dut.g_ref.u.legal=1'b0;
 force impl[1].dut.g_cand.u.legal=1'b0;
end
1:begin
 force impl[0].dut.g_ref.u.cv=1'b1;
 force impl[1].dut.g_cand.u.cv=1'b1;
 force impl[0].dut.g_ref.u.state=2'd0;
 force impl[1].dut.g_cand.u.state=2'd0;
 force impl[0].dut.g_ref.u.count=6'd0;
 force impl[1].dut.g_cand.u.count=6'd0;
end
2:begin
 force impl[0].dut.g_ref.u.cv=1'b1;
 force impl[1].dut.g_cand.u.cv=1'b1;
 force impl[0].dut.g_ref.u.state=2'd3;
 force impl[1].dut.g_cand.u.state=2'd3;
 force impl[0].dut.g_ref.u.count=6'd1;
 force impl[1].dut.g_cand.u.count=6'd1;
 force impl[0].dut.g_ref.u.cwe=1'b1;
 force impl[1].dut.g_cand.u.cwe=1'b1;
 force impl[0].dut.g_ref.u.cb=5'd0;
 force impl[1].dut.g_cand.u.cb=5'd0;
 force impl[0].dut.g_ref.u.cc=5'd0;
 force impl[1].dut.g_cand.u.cc=5'd0;
 force impl[0].dut.g_ref.u.head={1'b1,5'd0,5'd0,309'd0};
 force impl[1].dut.g_cand.u.head={1'b1,5'd0,5'd0,309'd0};
 force impl[0].dut.g_ref.u.fresh_v=1'b1;
 force impl[1].dut.g_cand.u.fresh_v=1'b1;
 force impl[0].dut.g_ref.u.fresh_slot=5'd0;
 force impl[1].dut.g_cand.u.fresh_slot=5'd0;
 force impl[0].dut.g_ref.u.rp=5'd0;
 force impl[1].dut.g_cand.u.rp=5'd0;
end
3:begin
 force impl[0].dut.g_ref.u.cv=1'b1;
 force impl[1].dut.g_cand.u.cv=1'b1;
 force impl[0].dut.g_ref.u.state=2'd3;
 force impl[1].dut.g_cand.u.state=2'd3;
 force impl[0].dut.g_ref.u.count=6'd1;
 force impl[1].dut.g_cand.u.count=6'd1;
 force impl[0].dut.g_ref.u.cwe=1'b0;
 force impl[1].dut.g_cand.u.cwe=1'b0;
 force impl[0].dut.g_ref.u.cb=5'd0;
 force impl[1].dut.g_cand.u.cb=5'd0;
 force impl[0].dut.g_ref.u.cc=5'd0;
 force impl[1].dut.g_cand.u.cc=5'd0;
 force impl[0].dut.g_ref.u.caq=1'b1;
 force impl[1].dut.g_cand.u.caq=1'b1;
 force impl[0].dut.g_ref.u.head=320'd0;
 force impl[1].dut.g_cand.u.head=320'd0;
 force impl[0].dut.g_ref.u.pending_count=6'd32;
 force impl[1].dut.g_cand.u.pending_count=6'd32;
end
4:begin
 force impl[0].dut.g_ref.u.response_take=1'b1;
 force impl[1].dut.g_cand.u.response_take=1'b1;
 force impl[0].dut.g_ref.u.read_reserved=6'd0;
 force impl[1].dut.g_cand.u.read_reserved=6'd0;
 force impl[0].dut.g_ref.u.response_count=6'd0;
 force impl[1].dut.g_cand.u.response_count=6'd0;
end
5:begin
 force impl[0].dut.g_ref.u.read_reserved=6'd33;
 force impl[1].dut.g_cand.u.read_reserved=6'd33;
end
endcase
 @(posedge clk);#1;
 if(owner_fault!==2'b11 || impl[1].dut.g_cand.u.owner_fault_split!==(6'b1<<c))
 $fatal(1,"FAULT_CLASS mismatch case=%0d scalar=%b split=%b",c,owner_fault,impl[1].dut.g_cand.u.owner_fault_split);
 checks=checks+1;
 case(c)
0:begin
 release impl[0].dut.g_ref.u.i_v;
 release impl[1].dut.g_cand.u.i_v;
 release impl[0].dut.g_ref.u.legal;
 release impl[1].dut.g_cand.u.legal;
end
1:begin
 release impl[0].dut.g_ref.u.cv;
 release impl[1].dut.g_cand.u.cv;
 release impl[0].dut.g_ref.u.state;
 release impl[1].dut.g_cand.u.state;
 release impl[0].dut.g_ref.u.count;
 release impl[1].dut.g_cand.u.count;
end
2:begin
 release impl[0].dut.g_ref.u.cv;
 release impl[1].dut.g_cand.u.cv;
 release impl[0].dut.g_ref.u.state;
 release impl[1].dut.g_cand.u.state;
 release impl[0].dut.g_ref.u.count;
 release impl[1].dut.g_cand.u.count;
 release impl[0].dut.g_ref.u.cwe;
 release impl[1].dut.g_cand.u.cwe;
 release impl[0].dut.g_ref.u.cb;
 release impl[1].dut.g_cand.u.cb;
 release impl[0].dut.g_ref.u.cc;
 release impl[1].dut.g_cand.u.cc;
 release impl[0].dut.g_ref.u.head;
 release impl[1].dut.g_cand.u.head;
 release impl[0].dut.g_ref.u.fresh_v;
 release impl[1].dut.g_cand.u.fresh_v;
 release impl[0].dut.g_ref.u.fresh_slot;
 release impl[1].dut.g_cand.u.fresh_slot;
 release impl[0].dut.g_ref.u.rp;
 release impl[1].dut.g_cand.u.rp;
end
3:begin
 release impl[0].dut.g_ref.u.cv;
 release impl[1].dut.g_cand.u.cv;
 release impl[0].dut.g_ref.u.state;
 release impl[1].dut.g_cand.u.state;
 release impl[0].dut.g_ref.u.count;
 release impl[1].dut.g_cand.u.count;
 release impl[0].dut.g_ref.u.cwe;
 release impl[1].dut.g_cand.u.cwe;
 release impl[0].dut.g_ref.u.cb;
 release impl[1].dut.g_cand.u.cb;
 release impl[0].dut.g_ref.u.cc;
 release impl[1].dut.g_cand.u.cc;
 release impl[0].dut.g_ref.u.caq;
 release impl[1].dut.g_cand.u.caq;
 release impl[0].dut.g_ref.u.head;
 release impl[1].dut.g_cand.u.head;
 release impl[0].dut.g_ref.u.pending_count;
 release impl[1].dut.g_cand.u.pending_count;
end
4:begin
 release impl[0].dut.g_ref.u.response_take;
 release impl[1].dut.g_cand.u.response_take;
 release impl[0].dut.g_ref.u.read_reserved;
 release impl[1].dut.g_cand.u.read_reserved;
 release impl[0].dut.g_ref.u.response_count;
 release impl[1].dut.g_cand.u.response_count;
end
5:begin
 release impl[0].dut.g_ref.u.read_reserved;
 release impl[1].dut.g_cand.u.read_reserved;
end
endcase
 end
 $display("PC_CTRL_FAULT_CLASSES PASS checks=%0d",checks);$finish;
 end
endmodule
