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
  // in-order DRAM: every column read returns one beat 14 edges later
  reg [63:0] rq [0:255]; reg [7:0] rq_w=0, rq_r=0; integer now=0;
  integer edges=0,acc_rd=0,acc_wr=0,kr=0,wdone=0,cols=0,rows=0,illegal_phase=0;
  reg [31:0] rng=32'h1d872b41; reg row_sel=0;
  function [31:0] nx(input [31:0] r); nx={r[30:0],r[31]^r[21]^r[1]^r[0]}; endfunction
  always @(negedge clk) if(rst_n) begin
    edges=edges+1;
    if({k_rdy[0],kr_v[0],k_wr_done[0],row_v[0],col_v[0],pc_fault[0],owner_fault[0]}!=={k_rdy[1],kr_v[1],k_wr_done[1],row_v[1],col_v[1],pc_fault[1],owner_fault[1]} ||
       (kr_v[0] && {kr_tag[0],kr_beat[0],kr_data[0]}!=={kr_tag[1],kr_beat[1],kr_data[1]}) ||
       (row_v[0] && {row_op[0],row_bank[0],row_row[0]}!=={row_op[1],row_bank[1],row_row[1]}) ||
       (col_v[0] && {col_we[0],col_bank[0],col_col[0]}!=={col_we[1],col_bank[1],col_col[1]}) ||
       (col_v[0] && col_we[0] && {col_data[0],col_strb[0]}!=={col_data[1],col_strb[1]}))
      $fatal(1,"QREG miter mismatch edge%0d acc_rd%0d acc_wr%0d kr%0d",edges,acc_rd,acc_wr,kr);
    // the valid-qualified fields must also equal ungated (historical) values whenever their valid is high
    if(impl[0].dut.state!==impl[1].dut.state || impl[0].dut.count!==impl[1].dut.count || impl[0].dut.sticky!==impl[1].dut.sticky)
      $fatal(1,"QREG miter state mismatch edge%0d",edges);
    if(impl[1].dut.unposted!=0 && impl[1].dut.push_q!==impl[1].dut.queue[impl[1].dut.ep])
      $fatal(1,"QREG push_q invariant broken edge%0d",edges);
  end
  always @(posedge clk) begin
    now=now+1;
    if(!rst_n) begin rq_w<=0; rq_r<=0; dram_rvalid<=0; end
    else begin
      if(col_v[0] && !col_we[0]) begin rq[rq_w]<=now+14; rq_w<=rq_w+1; cols=cols+1; end
      else if(col_v[0]) cols=cols+1;
      if(row_v[0]) rows=rows+1;
      if(rq_r!=rq_w && rq[rq_r]<=now) begin dram_rvalid<=1; dram_rdata<={8{now[31:0]^32'h5a5a0000}}; rq_r<=rq_r+1; end
      else dram_rvalid<=0;
      if(k_v && k_rdy[0]) begin if(k_we) acc_wr=acc_wr+1; else acc_rd=acc_rd+1; end
      if(kr_v[0] && kr_rdy) kr=kr+1;
      if(k_wr_done[0]) wdone=wdone+1;
    end
  end
  task drive; input integer bad;
    reg [29:0] a; reg [3:0] l; reg [4:0] x;
    begin
      rng=nx(rng); k_v=(rng[2:0]!=0); k_we=(rng[5:3]==0);
      rng=nx(rng); a=rng[29:0]; a[29:15]=15'(5+row_sel); if(rng[8:2]==0) row_sel=~row_sel; rng=nx(rng);
      l=k_we?4'd1:4'(1+rng[1:0]); a[1:0]=2'(rng[3:2]%(5-l));
      x=pc_id^a[11:7]^a[16:12]; a[6:2]=bad?~x:x;
      k_addr=a; k_len=l; k_tag=rng[16:0]; rng=nx(rng); k_wstrb=rng; k_wdata={8{rng^32'h3c3c3c3c}};
      rng=nx(rng); kr_rdy=(rng[3:0]!=0);
    end
  endtask
  integer phase,c,ncyc;
  initial begin
    if(!$value$plusargs("ncyc=%d",ncyc)) ncyc=12000;
    for(phase=0;phase<4;phase=phase+1)begin
      rst_n=0; k_v=0; repeat(6)@(posedge clk); @(negedge clk); #1 rst_n=1;
      for(c=0;c<ncyc;c=c+1)begin @(negedge clk); #1 drive(phase==3 && c>9000 && c%97==0); end
      k_v=0; repeat(400)@(negedge clk);
    end
    if(acc_rd<2000||acc_wr<300||kr<3000||wdone<300||rows<2000)
      $fatal(1,"insufficient coverage pc_fault%0d owner_fault%0d state%0d acc_rd%0d acc_wr%0d kr%0d wdone%0d rows%0d",pc_fault[0],owner_fault[0],impl[0].dut.state,acc_rd,acc_wr,kr,wdone,rows);
    $display("PC_CTRL_QREG_MITER PASS edges%0d acc_rd%0d acc_wr%0d kr%0d wdone%0d cols%0d rows%0d sticky_final%0d",
             edges,acc_rd,acc_wr,kr,wdone,cols,rows,owner_fault[0]);
    $finish;
  end
endmodule
