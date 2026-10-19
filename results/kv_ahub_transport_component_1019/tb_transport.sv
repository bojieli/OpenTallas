`timescale 1ns/1ps
module tb_transport;
  parameter integer W=268;
  parameter integer MUT=0;
  reg clk=0;
  reg tx_rst_n=1,rx_rst_n=1,in_valid=0;
  reg [W-1:0] d;
  wire [W-1:0] q;
  wire out_valid,accept;
  generate if(W==268) begin:g_cmd
    qkd_ahub_zh_transport_private #(.ENABLE(1),.MUT_CMD(MUT)) dut(
      .clk(clk),.core_rst_n(tx_rst_n),.child_rst_n(rx_rst_n),
      .command_valid(in_valid),.command_word(d),.child_command(q),
      .command_out_valid(out_valid),.command_accept(accept),
      .return_valid(1'b0),.return_word(68'b0),.core_return(),
      .return_out_valid(),.return_accept());
  end else begin:g_return
    qkd_ahub_zh_transport_private #(.ENABLE(1),.MUT_RETURN(MUT)) dut(
      .clk(clk),.child_rst_n(tx_rst_n),.core_rst_n(rx_rst_n),
      .return_valid(in_valid),.return_word(d),.core_return(q),
      .return_out_valid(out_valid),.return_accept(accept),
      .command_valid(1'b0),.command_word(268'b0),.child_command(),
      .command_out_valid(),.command_accept());
  end endgenerate
  // Independent recurrence for the real two synchronizer plus two regional hops.
  reg ts0,ts1,tq0,tq1,rs0,rs1,rq0,rq1;
  always @(posedge clk or negedge tx_rst_n)
    if (!tx_rst_n) begin ts0<=0;ts1<=0;end
    else begin ts0<=1;ts1<=ts0;end
  always @(posedge clk or negedge rx_rst_n)
    if (!rx_rst_n) begin rs0<=0;rs1<=0;end
    else begin rs0<=1;rs1<=rs0;end
  always @(posedge clk) begin tq0<=ts1;tq1<=tq0;rq0<=rs1;rq1<=rq0;end
  reg [W-1:0] expected[0:4095];
  reg expected_v[0:4095];
  integer cycle=0, accepted=0, observed=0, cleared=0;
  integer first_accept=-1, first_output=-1, wraps=0;
  integer i,j;
  localparam integer BANKS=(W+7)/8;
  wire [BANKS-1:0] observed_tx,observed_rx;
  genvar k;
  generate for(k=0;k<BANKS;k=k+1)begin:g_observe
    if(W==268)begin:g_c
      initial begin
        #0.5;
        g_cmd.dut.g_private.u_command.g_bank[k].u_tx_reset.q0=1;
        g_cmd.dut.g_private.u_command.g_bank[k].u_tx_reset.q1=1;
        g_cmd.dut.g_private.u_command.g_bank[k].u_rx_reset.q0=1;
        g_cmd.dut.g_private.u_command.g_bank[k].u_rx_reset.q1=1;
      end
      assign observed_tx[k]=g_cmd.dut.g_private.u_command.g_bank[k].tx_ready;
      assign observed_rx[k]=g_cmd.dut.g_private.u_command.g_bank[k].rx_ready;
    end else begin:g_r
      initial begin
        #0.5;
        g_return.dut.g_private.u_return.g_bank[k].u_tx_reset.q0=1;
        g_return.dut.g_private.u_return.g_bank[k].u_tx_reset.q1=1;
        g_return.dut.g_private.u_return.g_bank[k].u_rx_reset.q0=1;
        g_return.dut.g_private.u_return.g_bank[k].u_rx_reset.q1=1;
      end
      assign observed_tx[k]=g_return.dut.g_private.u_return.g_bank[k].tx_ready;
      assign observed_rx[k]=g_return.dut.g_private.u_return.g_bank[k].rx_ready;
    end
  end endgenerate
  bit reset_authority=0,previous_clear=0;
  reg a_pre,rx_pre,ev;
  reg [W-1:0] word_pre;
  function automatic [W-1:0] pattern(input integer n);
    integer b;
    reg [W-1:0] v;
    begin
      for(b=0;b<W;b=b+1) v[b]=((n*17+b*13+(b/7)*n)>>(b%5))&1;
      // Return fault nibble deliberately changes independently of root data.
      if(W==68) v[W-1 -: 4]=(n%15)+1;
      pattern=v;
    end
  endfunction
  task automatic edge_step(input bit valid_word,input integer tag);
    begin
      in_valid=valid_word;d=pattern(tag);
      #4;
      // Witness the actual regional assertion, rather than waiting a fixed
      // number of cycles. Two consecutive all-bank clear observations while
      // both raw resets are asserted establish the synchronous relay history.
      if(!reset_authority)begin
        if(previous_clear && !(|observed_rx) && !(|observed_tx) &&
           !rx_rst_n && !tx_rst_n) reset_authority=1;
        previous_clear=!(|observed_rx) && !(|observed_tx) && !rx_rst_n && !tx_rst_n;
      end
      if(reset_authority && (observed_tx!=={BANKS{tq1}} || observed_rx!=={BANKS{rq1}}))
        $fatal(1,"TRANSPORT_FAIL reset_frontier cycle=%0d",cycle);
      a_pre=in_valid&&tq1&&rq1&&ts1&&rs1;
      rx_pre=rq1&&rs1;word_pre=d;
      if(accept!==a_pre)
        $fatal(1,"TRANSPORT_FAIL accept_frontier cycle=%0d got=%b want=%b",cycle,accept,a_pre);
      clk=1;
      #1;
      begin
        if(!rx_pre) begin
          for(j=cycle;j<4096;j=j+1) begin
            if(expected_v[j]) cleared=cleared+1;
            expected_v[j]=0;
          end
        end
        if(a_pre) begin
          expected[cycle+4]=word_pre;expected_v[cycle+4]=1;
          accepted=accepted+1;
          if(first_accept<0) first_accept=cycle;
        end
        ev=expected_v[cycle];
        if(out_valid!==ev)
          $fatal(1,"TRANSPORT_FAIL valid_frontier cycle=%0d got=%b want=%b first_accept=%0d",cycle,out_valid,ev,first_accept);
        if(ev) begin
          if(q!==expected[cycle])
            $fatal(1,"TRANSPORT_FAIL payload cycle=%0d got=%h want=%h",cycle,q,expected[cycle]);
          observed=observed+1;
          if(first_output<0)first_output=cycle;
        end
        expected_v[cycle]=0;
      end
      #4;clk=0;#1;cycle=cycle+1;
    end
  endtask
  initial begin
    for(i=0;i<4096;i=i+1) expected_v[i]=0;
    d='1;
    #1;tx_rst_n=0;rx_rst_n=0;
    // Before witnessed regional assertion, arbitrary power-up valid storage
    // has no qualified authority (HOLD). No post-release/programme mask.
    repeat(8)edge_step(1,900+cycle);
    tx_rst_n=1;
    repeat(7)edge_step(1,1000+cycle);
    rx_rst_n=1;
    repeat(48)edge_step(1,2000+cycle);
    // Owned words must drain when only the transmitter is reset.
    tx_rst_n=0;
    repeat(9)edge_step(1,3000+cycle);
    tx_rst_n=1;
    repeat(23)edge_step(1,4000+cycle);
    // Receiver reset explicitly discards its outstanding valid ownership.
    rx_rst_n=0;
    repeat(8)edge_step(1,5000+cycle);
    tx_rst_n=0;
    repeat(7)edge_step(0,6000+cycle);
    rx_rst_n=1;
    repeat(9)edge_step(1,7000+cycle);
    tx_rst_n=1;
    repeat(80)edge_step((cycle%7)!=0 && (cycle%11)!=0,8000+cycle);
    // Idle words carry faults too: they may never acquire validity.
    repeat(24)edge_step(0,9000+cycle);
    repeat(128)edge_step(1,10000+cycle);
    repeat(12)edge_step(0,11000+cycle);
    for(i=cycle;i<4096;i=i+1)
      if(expected_v[i])$fatal(1,"TRANSPORT_FAIL undrained cycle=%0d",i);
    if(accepted<200 || observed<200 || cleared==0)
      $fatal(1,"TRANSPORT_FAIL coverage accepted=%0d observed=%0d cleared=%0d",accepted,observed,cleared);
    if(observed+cleared!=accepted)
      $fatal(1,"TRANSPORT_FAIL accounting accepted=%0d observed=%0d cleared=%0d",accepted,observed,cleared);
    $display("TRANSPORT_PASS W=%0d MUT=%0d edges=%0d accepted=%0d observed=%0d reset_discarded=%0d first_accept=%0d first_output=%0d",W,MUT,cycle,accepted,observed,cleared,first_accept,first_output);
    $finish;
  end
endmodule
