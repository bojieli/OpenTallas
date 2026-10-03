`timescale 1ns/1ps
module tb_partition #(parameter integer OPT=1);
  reg clk=0; always #5 clk=~clk;
  reg rst_n=0, ready=0;
  wire rsp_v, rsp_we, fault, req_ready;
  wire [30:0] rsp_tag; wire [255:0] rsp_data;
  ot_gpu_hbm_partition_held #(.ENABLE(1),.OPT_HELD_RETURN(OPT),.TW(31),.NPC(2),.MEM_WORDS(64)) dut(
    .clk(clk),.rst_n(rst_n),.req_v(1'b0),.req_rdy(req_ready),.req_we(1'b0),
    .req_addr(32'd0),.req_wdata(256'd0),.req_wstrb(32'd0),.req_tag(31'd0),
    .rsp_v(rsp_v),.rsp_rdy(ready),.rsp_tag(rsp_tag),.rsp_we(rsp_we),.rsp_data(rsp_data),.fault(fault));
  reg [1:0] pcvalid=0;
  reg [63:0] pctag={32'h71234567,32'h12345678};
  reg [511:0] pcdata={256'habcdef,256'h987654};
  reg wdvalid=0;
  reg [31:0] wdtag=32'h6abcdef0;
  reg [286:0] saved;
  integer i;
  task edge_tick; begin @(posedge clk); #1; end endtask
  initial begin
    force dut.g_on.m_rsp_v=pcvalid;
    force dut.g_on.m_rsp_tag=pctag;
    force dut.g_on.m_rsp_data=pcdata;
    force dut.g_on.a_wd_v=wdvalid;
    force dut.g_on.a_wd_tag=wdtag;
    edge_tick(); @(negedge clk); rst_n=1; pcvalid=2'b10;
    edge_tick(); saved={rsp_tag,rsp_data};
    if(!rsp_v || rsp_we || rsp_tag!==31'h71234567) $fatal(1,"initial source read offer");
    @(negedge clk); pcvalid=2'b11;
    // Both newly arriving higher priority PC and write completion compete.
    wdvalid=1;
    force dut.g_on.pri=1'b1;
    for(i=0;i<6;i=i+1) begin
      edge_tick();
      if(!rsp_v || rsp_we || {rsp_tag,rsp_data}!==saved) $fatal(1,"partition changed stalled identity/data/kind");
      if(dut.g_on.m_rsp_rdy!==0 || dut.g_on.a_wd_rdy) $fatal(1,"premature source acceptance");
    end
    @(negedge clk); ready=1; #1;
    if(dut.g_on.m_rsp_rdy!==2'b10) $fatal(1,"wrong PC accepted");
    edge_tick(); @(negedge clk); pcvalid=2'b01; #1;
    if(!rsp_v || !rsp_we || rsp_tag!==31'h6abcdef0 || !dut.g_on.a_wd_rdy) $fatal(1,"held write completion lost");
    edge_tick(); @(negedge clk); wdvalid=0; #1;
    if(!rsp_v || rsp_we || rsp_tag!==31'h12345678 || dut.g_on.m_rsp_rdy!==2'b01) $fatal(1,"remaining read lost");
    edge_tick(); @(negedge clk); pcvalid=0; #1;
    if(rsp_v || fault) $fatal(1,"phantom/fault");
    $display("PASS actual partition two-stage held PC/read/write merges full tag/data/kind");
    $finish;
  end
endmodule
