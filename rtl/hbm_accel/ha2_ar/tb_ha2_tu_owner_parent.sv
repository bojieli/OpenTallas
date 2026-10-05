`timescale 1ps/1fs
module tb_ha2_tu_owner_parent;
  reg clk=0,pclk=0;always #416.666667 clk=~clk;always #500 pclk=~pclk;
  reg rst_n=0,prst_n=0,go=0;reg [63:0] operation=1;reg [31:0] phase=0;
  reg [15:0] pf=64;reg [7:0] rxv=0;reg [519:0] rxf=0;
  wire ready,qcore,qphy,fault;wire [31:0] idx,stall;
  wire [1:0] rd;wire [7:0] txv,credit;wire [519:0] txf;
  wire [3:0] dv;wire [259:0] df;
  // Same finite queues, clock domains and eight real ports; one lane only.
  ot_hbm_accel_tu_endpoint_owner #(.ENABLE(1),.OWNER_REDUCER(1),.PFMAX(384),.LANES(1)) dut
    (.clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),.rank(8'd19),.pf(pf),.go(go),
    .context_operation(operation),.context_phase(phase),.endpoint_rearm_ready(ready),
    .endpoint_quiet_core(qcore),.endpoint_quiet_phy(qphy),.inj_idx(idx),.inj_rd(rd),.inj_data(64'h3f8000003f800000),
    .ph_tx_v(txv),.ph_tx_flit(txf),.sw_cr_ret(8'b0),.ph_rx_v(rxv),.ph_rx_flit(rxf),
    .rx_credit(credit),.del_valid(dv),.del_flit(df),.fault(fault),.stat_credit_stall(stall));
  wire orig_ready,orig_fault;
  ot_hbm_accel_tu_endpoint_owner #(.LANES(1)) default_off
    (.clk(clk),.rst_n(rst_n),.pclk(pclk),.prst_n(prst_n),.rank(8'd19),.pf(pf),.go(go),
    .context_operation(operation),.context_phase(phase),.endpoint_rearm_ready(orig_ready),
    .inj_data(64'b0),.sw_cr_ret(8'b0),.ph_rx_v(8'b0),.ph_rx_flit(520'b0),.fault(orig_fault));
  integer pulses=0;
  always @(posedge clk)if(|credit)pulses=pulses+1;
  task automatic cold;
    rst_n=0;prst_n=0;go=0;rxv=0;operation=1;phase=0;pf=64;pulses=0;
    repeat(5)@(negedge clk);rst_n=1;prst_n=1;
    repeat(12)@(negedge clk);
    if(!ready||fault||orig_ready||orig_fault)$fatal(1,"cold/default-off contract");
  endtask
  initial begin
    cold();go=1;@(negedge clk);go=0;
    repeat(5)@(negedge clk);
    if(ready||fault)$fatal(1,"active source incorrectly quiet");
    operation=2;@(negedge clk);@(negedge clk);
    if(!fault||ready)$fatal(1,"held tuple changed without fault");
    $display("PARENT PASS held tuple and outstanding source prevent rearm");
    cold();
    @(negedge pclk);rxv=1;rxf[0+:65]={1'b0,8'd18,8'd0,16'd0,32'h3f800000};
    @(negedge pclk);rxv=0;
    repeat(45)@(negedge clk);
    if(!fault||pulses!=0||ready)$fatal(1,"foreign destination ACKed or not held");
    if(dut.g_candidate.g_on.g_owner.u_owner.u_reduce.pres[0][0])$fatal(1,"foreign source slot write");
    $display("PARENT PASS wrong destination held at actual RX buffer; no credit or slot write");
    $display("PASS parent changed-source boundary; full fabric/publication qualification remains open");$finish;
  end
endmodule
