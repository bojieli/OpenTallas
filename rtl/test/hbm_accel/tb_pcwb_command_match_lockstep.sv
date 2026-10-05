`timescale 1ps/1fs
// Same actual inputs to retained r9d and both successor settings. No oracle or grant overrides.
module tb_pcwb_command_match_lockstep;
  parameter integer LATE=1, MODE=1, PC=0, WQ=8;
  reg clk=0; always #416.5 clk=~clk;
  reg rst_n=0, desc_v=0, go=0, next_posted=0, notice=0, row_gnt=0, wq_v=0;
  reg [18:0] desc_row=0, wq_row=0;
  reg [10:0] desc_n=0;
  reg [4:0] wq_bank=0,wq_col=0;
  reg [255:0] wq_data=0;
  reg [2:0] cred_ret=0;
  wire [321:0] observed [0:2];
  wire [2:0] busy, ready;
  integer seed=1, cycles=200000, pushes=0, acks=0, acts=0, pres=0, refs=0;
  integer overlap=0, stalled=0, used=0;
  reg [31:0] rng;
  function automatic [31:0] step(input [31:0] x);
    reg [31:0] y;
    begin y=x^(x<<13); y=y^(y>>17); step=y^(y<<5); end
  endfunction
`define INPUTS .clk(clk),.rst_n(rst_n),.desc_v(desc_v),.desc_row(desc_row),.desc_n(desc_n), \
    .go(go),.next_posted(next_posted),.notice(notice),.row_gnt(row_gnt),.cred_ret(cred_ret), \
    .wq_v(wq_v),.wq_bank(wq_bank),.wq_row(wq_row),.wq_col(wq_col),.wq_data(wq_data)
  for(genvar g=0;g<3;g=g+1) begin: pair
    wire desc_r,row_v,row_prio,col_v,ref_fault,col_we,wr_ack,wq_empty;
    wire [2:0] row_op;
    wire [4:0] row_bank,col_bank,col_col;
    wire [18:0] row_row,col_row;
    wire [255:0] col_wdata;
`define OUTPUTS .desc_r(desc_r),.row_v(row_v),.row_prio(row_prio),.row_op(row_op), \
    .row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_bank(col_bank),.col_col(col_col), \
    .busy(busy[g]),.ref_fault(ref_fault),.wq_r(ready[g]),.col_we(col_we),.col_wdata(col_wdata), \
    .col_row(col_row),.wr_ack(wr_ack),.wq_empty(wq_empty)
    if(g==0) begin: reference
      ot_hbm_accel_stream_pc_wb_digest #(.ENABLE(1),.WB_EN(1),.WA_LATE(LATE),.WQ(WQ),
        .REF_MODE(MODE),.PC(PC),.CRED(64),.DIGEST_CUT(1)) u (`INPUTS, `OUTPUTS);
    end else begin: candidate
      ot_hbm_accel_stream_pc_wb_command_match #(.ENABLE(1),.WB_EN(1),.WA_LATE(LATE),.WQ(WQ),
        .REF_MODE(MODE),.PC(PC),.CRED(64),.DIGEST_CUT(1),.CMD_MATCH_CUT(g==2)) u (`INPUTS, `OUTPUTS);
    end
    assign observed[g]={desc_r,row_v,row_prio,row_op,row_bank,row_row,col_v,col_bank,col_col,
      busy[g],ref_fault,ready[g],col_we,col_wdata,col_row,wr_ack,wq_empty};
  end
`undef INPUTS
`undef OUTPUTS
  initial begin
    used=$value$plusargs("seed=%d",seed); used=$value$plusargs("cycles=%d",cycles);
    rng=32'(seed); repeat(4) @(negedge clk); rst_n=1;
    for(integer c=0;c<cycles;c=c+1) begin
      rng=step(rng);
      // Refresh grant is preserved as actual input. Backpressure away from
      // refresh tests write-ACT retry without invalidating the reference service.
      row_gnt=pair[0].row_prio || (rng[3:0]!=0);
      desc_v=!busy[0] && rng[7:4]==0;
      desc_row={15'b0,rng[11:8]};
      desc_n=(rng[15:12]==0)?11'd1:((rng[15:12]==1)?11'd31:11'd1024);
      go=1; next_posted=rng[16]; notice=rng[17];
      cred_ret=pair[0].col_v && !pair[0].col_we ? 3'd1:3'd0;
      // Repeated banks with alternating rows exercise same-bank older conflicts,
      // hits, replacement after wrap, and simultaneous push/WR/row commands.
      wq_v=rng[19:18]!=0;
      wq_bank=rng[24:20]; wq_row={17'b0,rng[26:25]}; wq_col=rng[31:27];
      wq_data={8{rng}};
      #1;
      if(observed[0] !== observed[1] || observed[0] !== observed[2])
        $fatal(1,"output mismatch cycle=%0d seed=%0d",c,seed);
      if(pair[0].reference.u.on.wbr_n !== pair[2].candidate.u.on.wbr_n)
        $fatal(1,"next-head readiness mismatch cycle=%0d seed=%0d",c,seed);
      if(pair[0].reference.u.on.wr_ok && pair[0].reference.u.on.wq_n==0)
        $fatal(1,"accepted pop on empty queue");
      if(wq_v && ready[0]) pushes++;
      if(pair[0].wr_ack) acks++;
      if(pair[0].row_v && row_gnt && pair[0].row_op==1) acts++;
      if(pair[0].row_v && row_gnt && pair[0].row_op==0) pres++;
      if(pair[0].row_v && row_gnt && (pair[0].row_op==4 || pair[0].row_op==6)) refs++;
      if(wq_v && ready[0] && pair[0].wr_ack) overlap++;
      if(pair[0].row_v && !row_gnt) stalled++;
      @(negedge clk);
    end
    if(acks<10 || acts<10 || pres<10 || refs<10 || overlap<1 || stalled<1)
      $fatal(1,"insufficient activity acks=%0d acts=%0d pres=%0d refs=%0d overlap=%0d stalled=%0d",acks,acts,pres,refs,overlap,stalled);
    $display("PASS seed=%0d cycles=%0d WA_LATE=%0d REF_MODE=%0d PC=%0d WQ=%0d pushes=%0d acks=%0d acts=%0d pres=%0d refs=%0d overlap=%0d stalled=%0d mismatches=0",seed,cycles,LATE,MODE,PC,WQ,pushes,acks,acts,pres,refs,overlap,stalled);
    $finish;
  end
endmodule
