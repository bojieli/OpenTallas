`timescale 1fs/1fs
// Minimum actual selected controller and unchanged parent fractional generator.
module tb_qwen_service_actual_edges;
  reg clk=0, rst_n=0;
  always begin #416666 clk=1; #416667 clk=0; end
  reg [31:0] acc=0; reg tick_q=0;
  always @(posedge clk)
    if(acc+833333>=1024000) begin acc<=acc+833333-1024000;tick_q<=1;end
    else begin acc<=acc+833333;tick_q<=0;end
  wire hclk=~clk & tick_q;
  reg desc_v=0,go=0;
  wire desc_r,row_v,row_prio,col_v,busy,fault,wr_r,col_we,col_aq;
  wire [2:0] row_op;
  wire [4:0] row_bank,col_bank,col_col;
  wire [18:0] row_row;
  wire [2:0] credit_return=col_v?3'd1:3'd0;
  ot_hbm_r14_stream_pc #(.ENABLE(1),.REF_MODE(1),.PC(0),.CRED(32),.WR_EN(1),.WQ(4),.PULLIN(16),.AQ_RD(1)) u (
    .clk(hclk),.rst_n(rst_n),.desc_v(desc_v),.desc_r(desc_r),.desc_row(19'd0),.desc_n(11'd256),
    .go(go),.next_posted(1'b0),.row_v(row_v),.row_prio(row_prio),.row_gnt(1'b1),
    .row_op(row_op),.row_bank(row_bank),.row_row(row_row),.col_v(col_v),.col_bank(col_bank),.col_col(col_col),
    .cred_ret(credit_return),.busy(busy),.ref_fault(fault),.wr_v(1'b0),.wr_bank(5'd0),.wr_col(5'd0),
    .wr_r(wr_r),.col_we(col_we),.wr_rd(1'b0),.col_aq(col_aq));
  time last_col=0; integer cols=0,violations=0,edges=0; reg posted=0;
  always @(posedge hclk) if(rst_n) begin
    edges=edges+1;
    if(desc_v&&desc_r) posted=1;
    if(col_v) begin
      if(cols!=0&&$time-last_col<1024000) begin
        violations=violations+1;
        if(violations==1) $display("FIRST_TCCD_S_VIOLATION edge=%0d time_fs=%0t previous_fs=%0t interval_fs=%0t required_fs=1024000 bank=%0d",edges,$time,last_col,$time-last_col,col_bank);
      end
      last_col=$time;cols=cols+1;
    end
    if(fault) $fatal(1,"controller fault");
  end
  initial begin
    repeat(100) @(negedge clk);rst_n=1;
    @(negedge hclk);desc_v=1;
    wait(posted);@(negedge hclk);desc_v=0;go=1;
    @(negedge hclk);go=0;
    repeat(800) @(negedge hclk);
    $display("ACTUAL_EDGE_RESULT columns=%0d tccd_s_violations=%0d controller_fault=%0d",cols,violations,fault);
    if(cols<2) $fatal(1,"insufficient real controller columns");
    $finish;
  end
endmodule
