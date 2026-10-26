`timescale 1ps/1fs
module tb;
  reg clk=0;
  always #512 clk=~clk;
  reg rst_n=0, slot_parity=0, desc_v=0, go=0, next_posted=0, row_gnt=1;
  reg [7:0] refresh_reload=118;
  reg [18:0] desc_row=1;
  reg [10:0] desc_n=512;
  reg [2:0] cred_ret=0;
  reg wr_v=0,wr_rd=0;
  reg [4:0] wr_bank=0,wr_col=0;
  wire [1:0] desc_r,row_v,row_prio,col_v,busy,ref_fault,wr_r,col_we,col_aq;
  wire [2:0] row_op[2];
  wire [4:0] row_bank[2],col_bank[2],col_col[2];
  wire [18:0] row_row[2];
  for(genvar g=0;g<2;g=g+1)begin:impl
    ot_hbm_r14_stream_pc_strap #(.ENABLE(1),.REF_MODE(1),.WR_EN(1),.AQ_RD(1),.WQ(32),.PHYS_WACT(g)) dut(
      .clk(clk),.rst_n(rst_n),.slot_parity(slot_parity),.refresh_reload(refresh_reload),
      .desc_v(desc_v),.desc_r(desc_r[g]),.desc_row(desc_row),.desc_n(desc_n),.go(go),.next_posted(next_posted),
      .row_v(row_v[g]),.row_prio(row_prio[g]),.row_gnt(row_gnt),.row_op(row_op[g]),.row_bank(row_bank[g]),.row_row(row_row[g]),
      .col_v(col_v[g]),.col_bank(col_bank[g]),.col_col(col_col[g]),.cred_ret(cred_ret),
      .busy(busy[g]),.ref_fault(ref_fault[g]),.wr_v(wr_v),.wr_bank(wr_bank),.wr_col(wr_col),
      .wr_r(wr_r[g]),.col_we(col_we[g]),.wr_rd(wr_rd),.col_aq(col_aq[g]));
  end
  integer edges=0,pushes=0,pops=0,rows=0,wraps=0,simultaneous=0;
  reg [31:0] rng=32'h8b17c34d;
  reg [4:0] oldrp=0;
  always @(posedge clk) if(rst_n)begin
    if(wr_v&&wr_r[0])pushes=pushes+1;
    if(col_v[0]&&(col_we[0]||col_aq[0]))pops=pops+1;
    if(row_v[0])rows=rows+1;
    if(wr_v&&wr_r[0]&&col_v[0]&&(col_we[0]||col_aq[0]))simultaneous=simultaneous+1;
    if(impl[0].dut.on.wq_rp<oldrp)wraps=wraps+1;
    oldrp=impl[0].dut.on.wq_rp;
  end
  always @(negedge clk)begin
    if(rst_n)begin
      edges=edges+1;
      if({desc_r[0],row_v[0],row_prio[0],row_op[0],row_bank[0],row_row[0],col_v[0],col_bank[0],col_col[0],busy[0],ref_fault[0],wr_r[0],col_we[0],col_aq[0]} !==
         {desc_r[1],row_v[1],row_prio[1],row_op[1],row_bank[1],row_row[1],col_v[1],col_bank[1],col_col[1],busy[1],ref_fault[1],wr_r[1],col_we[1],col_aq[1]})
        $fatal(1,"physical_write_act mismatch edge%0d pushes%0d pops%0d",edges,pushes,pops);
      if(impl[0].dut.on.wcand!==impl[1].dut.on.wcand ||
         (impl[0].dut.on.wcand && {impl[0].dut.on.wab_n,impl[0].dut.on.wcrd_n}!=={impl[1].dut.on.wab_n,impl[1].dut.on.wcrd_n}))
        $fatal(1,"physical_write_act candidate mismatch edge%0d",edges);
    end
  end
  integer cycle,phase;
  initial begin
    for(phase=0;phase<3;phase=phase+1)begin
      rst_n=0;wr_v=0;desc_v=0;go=0;
      repeat(5)@(posedge clk);
      @(negedge clk);#1;rst_n=1;slot_parity=phase[0];desc_row=19'(phase+1);
      // First post descriptor, then exercise full, wrap and simultaneous push/pop.
      repeat(5)@(negedge clk);
      #1;desc_v=1;
      @(negedge clk);#1;desc_v=0;go=1;
      for(cycle=0;cycle<18000;cycle=cycle+1)begin
        @(negedge clk);#1;
        rng={rng[30:0],rng[31]^rng[21]^rng[1]^rng[0]};
        wr_v=cycle<15000 && (rng[3:0]!=0);
        wr_bank=rng[9:5];wr_col=rng[14:10];wr_rd=rng[15];
        cred_ret=col_v[0] ? 3'd1 : 0;
        // A later descriptor must wait until the old queue has drained.
        desc_v=cycle>16000&&desc_r[0]&&rng[7:0]==0;
        go=1;
      end
    end
    if(pushes<500||pops<400||rows<100||wraps<10||simultaneous<100)
      $fatal(1,"insufficient coverage pushes%0d pops%0d rows%0d wraps%0d simultaneous%0d",pushes,pops,rows,wraps,simultaneous);
    $display("PC_PHYSICAL_WRITE_ACT PASS edges%0d pushes%0d pops%0d rows%0d wraps%0d simultaneous%0d",edges,pushes,pops,rows,wraps,simultaneous);
    $finish;
  end
endmodule
