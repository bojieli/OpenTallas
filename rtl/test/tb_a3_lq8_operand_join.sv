`timescale 1ns/1ps
module tb_a3_lq8_operand_join;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,clear=0,operand_request=1,issue_enable=0;
    reg [31:0] generation=7;
    reg [31:0] operand_a_addr=3,operand_s_addr=4,operand_ws_addr=5,operand_w_addr=6;
    reg scale_a=1,scale_b=1,weight_valid=0,auxiliary_valid=0;
    wire operand_credit,identity_mismatch,weight_ready,auxiliary_ready;
    wire operand_issue=issue_enable && operand_credit;
    reg [31:0] weight_generation=7,weight_address=6,auxiliary_generation=7;
    reg [127:0] weight_data=128'h123;
    reg [31:0] auxiliary_a_addr=3,auxiliary_s_addr=4,auxiliary_ws_addr=5;
    reg [63:0] auxiliary_a_data=64'h456,auxiliary_ws_data=64'h789;
    reg [31:0] auxiliary_s_data=32'habc;
    wire [63:0] a_rd_data,ws_rd_data;
    wire [31:0] s_rd_data;
    wire [127:0] w_rd_data;
    ot_a3_lq8_operand_join dut(.*);
    task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
    task refused;begin #1;if(operand_credit || weight_ready || auxiliary_ready)$fatal(1,"invalid bundle accepted");end endtask
    initial begin
        tick();rst_n=1;refused();
        weight_valid=1;refused();auxiliary_valid=1;#1;
        if(!operand_credit || weight_ready || auxiliary_ready)$fatal(1,"reservation consumed without issue");
        weight_generation=6;refused();if(!identity_mismatch)$fatal(1,"old weight generation not detected");
        weight_generation=7;weight_address=9;refused();weight_address=6;
        auxiliary_generation=6;refused();auxiliary_generation=7;
        auxiliary_a_addr=9;refused();auxiliary_a_addr=3;
        auxiliary_s_addr=9;refused();scale_a=0;#1;if(!operand_credit)$fatal(1,"disabled scale required");
        scale_a=1;auxiliary_s_addr=4;auxiliary_ws_addr=9;refused();auxiliary_ws_addr=5;
        issue_enable=1;tick();
        if(w_rd_data!=0)$fatal(1,"delivery too early");
        weight_data=128'hdef;auxiliary_a_data=64'h321;tick();
        if(w_rd_data!=128'h123 || a_rd_data!=64'h456 || s_rd_data!=32'habc || ws_rd_data!=64'h789)$fatal(1,"first bundle alignment");
        issue_enable=0;tick();
        if(w_rd_data!=128'hdef || a_rd_data!=64'h321)$fatal(1,"back-to-back bundle alignment");
        issue_enable=1;weight_data=128'hbad;tick();clear=1;refused();tick();
        clear=0;issue_enable=0;weight_valid=0;auxiliary_valid=0;tick();
        if(w_rd_data!=0 || a_rd_data!=0)$fatal(1,"clear left pending delivery");
        $display("PASS LQ8 operand join identity, readiness, full-rate alignment and flush");$finish;
    end
endmodule
