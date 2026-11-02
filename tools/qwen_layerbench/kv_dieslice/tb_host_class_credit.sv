`timescale 1ns/1ps
module tb_host_class_credit;
    reg ck=0; always #0.4165 ck=~ck;
    reg rst_n=0, issue=0, enable_return=0;
    reg [511:0] payload=0;
    wire tx_v,tx_fault,rx_fault,cv;
    wire [527:0] tx_d,credit_d;
    wire [23:0] peer_credit;
    wire credit_v;
    wire ack=enable_return&&credit_v;
    wire [527:0] returned=$test$plusargs("DROP_CTRL_CREDIT") ? (credit_d & ~(528'hff<<8)) : credit_d;
    wire hc,cc,ic;
    integer seen_host=0,seen_ctrl=0,seen_done=0,idx=0;
    qkd_host_tx_class tx(.ck(ck),.rst_n(rst_n),.host_v(issue),.host_d(payload),.host_cr(hc),
      .ctrl_v(issue),.ctrl_d(payload),.ctrl_cr(cc),.ing_v(issue),.ing_d(payload[63:0]),.ing_cr(ic),
      .credit_return(24'd0),.peer_credit(peer_credit),.irq(1'b0),.tx_v(tx_v),.tx_d(tx_d),.tx_cr(tx_v),.fault(tx_fault));
    qwen_kv_board_class_credit board(.ck(ck),.rst_n(rst_n),.consume_v(tx_v),.consume_d(tx_d),
      .credit_v(credit_v),.credit_d(credit_d),.credit_ack(ack));
    qkd_host_rx_class rx(.ck(ck),.rst_n(rst_n),.die_id(3'd1),.rx_v(ack),.rx_d(returned),.rx_cr(),
      .host_v(),.host_d(),.host_cr(1'b0),.ctrl_v(),.ctrl_d(),.ctrl_cr(1'b0),
      .ing_v(),.ing_cls(),.ing_d(),.ing_crn(5'd0),.credit_return(),.peer_credit(peer_credit),.fault(rx_fault));
    always @(negedge ck) if(rst_n)begin
      if(tx_fault||rx_fault)$fatal(1,"transport fault");
      if(tx_v)case(tx_d[527:524])
        0:begin if(tx_d[511:0]!==((512'(seen_host)<<153)|512'(seen_host)))$fatal(1,"HOST payload/order");seen_host=seen_host+1;end
        1:begin if(tx_d[511:0]!==((512'(seen_ctrl)<<153)|512'(seen_ctrl)))$fatal(1,"CTRL payload/order");seen_ctrl=seen_ctrl+1;end
        5:begin if(tx_d[63:0]!==64'(seen_done))$fatal(1,"DONE payload/order");seen_done=seen_done+1;end
        default:$fatal(1,"unexpected class");
      endcase
    end
    initial begin
      repeat(4)@(negedge ck);rst_n=1;
      for(idx=0;idx<6;idx=idx+1)begin
        @(negedge ck);payload=(512'(idx)<<153)|512'(idx);issue=1;
        @(negedge ck);issue=0;repeat(12)@(negedge ck);
      end
      repeat(20)@(negedge ck);
      if(seen_host!=4||seen_ctrl!=4||seen_done!=4)$fatal(1,"physical credit must not replace application credit");
      $display("PHYSICAL_ONLY_STALL host=%0d ctrl=%0d done=%0d",seen_host,seen_ctrl,seen_done);
      enable_return=1;
      repeat(80)@(negedge ck);
      if(seen_host!=6||seen_ctrl!=6||seen_done!=6)$fatal(1,"class credit did not resume all six payloads %0d/%0d/%0d",seen_host,seen_ctrl,seen_done);
      if(credit_v)$fatal(1,"credit-only frame incorrectly acquired an application credit");
      $display("PASS_CLASS_CREDIT host=6 ctrl=6 done=6 exact_payload=18 physical_only_stall=12");$finish;
    end
endmodule
