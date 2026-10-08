module tb;
reg clk=0,rst_n=0,bf=0,tf=0,cf=0;
always #5 clk=~clk;
wire af,afn;
wire decoded = af;
ot_qwen_die_dualfault_station_r22 #(.ENABLE_FULLWIDTH(1),.TAP(0),.SPLIT(1)) dut
(.clk(clk),.rst_n(rst_n),.a_d(508'b0),.b_fault(bf),.b_fault_n(~bf),
 .t_fault(tf),.t_fault_n(~tf),.c_fault(cf),.c_fault_n(~cf),.a_fault(af),.a_fault_n(afn));
integer checks=0,errors=0;
initial begin
 #1; rst_n=1; #1; rst_n=0;
 repeat(3) @(negedge clk);
 if ({af,afn} !== 2'b01) $fatal(1,"cold reset pair");
 rst_n=1;
 // bf_q, valid starting fault=0
            @(negedge clk); bf=0; tf=0; cf=0;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b0) $fatal(1,"baseline bf_q");
            force dut.g_selected.bf_q = 1'b1;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED bf_q from fault=0"); end
            @(negedge clk); release dut.g_selected.bf_q;
            repeat(4) @(negedge clk);

// bf_q, valid starting fault=1
            @(negedge clk); bf=1; tf=1; cf=1;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b1) $fatal(1,"baseline bf_q");
            force dut.g_selected.bf_q = 1'b0;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED bf_q from fault=1"); end
            @(negedge clk); release dut.g_selected.bf_q;
            repeat(4) @(negedge clk);

// bfn_q, valid starting fault=0
            @(negedge clk); bf=0; tf=0; cf=0;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b0) $fatal(1,"baseline bfn_q");
            force dut.g_selected.bfn_q = 1'b0;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED bfn_q from fault=0"); end
            @(negedge clk); release dut.g_selected.bfn_q;
            repeat(4) @(negedge clk);

// bfn_q, valid starting fault=1
            @(negedge clk); bf=1; tf=1; cf=1;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b1) $fatal(1,"baseline bfn_q");
            force dut.g_selected.bfn_q = 1'b1;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED bfn_q from fault=1"); end
            @(negedge clk); release dut.g_selected.bfn_q;
            repeat(4) @(negedge clk);

// af_q, valid starting fault=0
            @(negedge clk); bf=0; tf=0; cf=0;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b0) $fatal(1,"baseline af_q");
            force dut.g_selected.af_q = 1'b1;
            #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED af_q from fault=0"); end
            @(negedge clk); release dut.g_selected.af_q;
            repeat(4) @(negedge clk);

// af_q, valid starting fault=1
            @(negedge clk); bf=1; tf=1; cf=1;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b1) $fatal(1,"baseline af_q");
            force dut.g_selected.af_q = 1'b0;
            #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED af_q from fault=1"); end
            @(negedge clk); release dut.g_selected.af_q;
            repeat(4) @(negedge clk);

// afn_q, valid starting fault=0
            @(negedge clk); bf=0; tf=0; cf=0;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b0) $fatal(1,"baseline afn_q");
            force dut.g_selected.afn_q = 1'b0;
            #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED afn_q from fault=0"); end
            @(negedge clk); release dut.g_selected.afn_q;
            repeat(4) @(negedge clk);

// afn_q, valid starting fault=1
            @(negedge clk); bf=1; tf=1; cf=1;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b1) $fatal(1,"baseline afn_q");
            force dut.g_selected.afn_q = 1'b1;
            #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED afn_q from fault=1"); end
            @(negedge clk); release dut.g_selected.afn_q;
            repeat(4) @(negedge clk);

// cf_q, valid starting fault=0
            @(negedge clk); bf=0; tf=0; cf=0;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b0) $fatal(1,"baseline cf_q");
            force dut.g_selected.cf_q = 1'b1;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED cf_q from fault=0"); end
            @(negedge clk); release dut.g_selected.cf_q;
            repeat(4) @(negedge clk);

// cf_q, valid starting fault=1
            @(negedge clk); bf=1; tf=1; cf=1;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b1) $fatal(1,"baseline cf_q");
            force dut.g_selected.cf_q = 1'b0;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED cf_q from fault=1"); end
            @(negedge clk); release dut.g_selected.cf_q;
            repeat(4) @(negedge clk);

// cfn_q, valid starting fault=0
            @(negedge clk); bf=0; tf=0; cf=0;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b0) $fatal(1,"baseline cfn_q");
            force dut.g_selected.cfn_q = 1'b0;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED cfn_q from fault=0"); end
            @(negedge clk); release dut.g_selected.cfn_q;
            repeat(4) @(negedge clk);

// cfn_q, valid starting fault=1
            @(negedge clk); bf=1; tf=1; cf=1;
            repeat(4) @(negedge clk);
            if (decoded !== 1'b1) $fatal(1,"baseline cfn_q");
            force dut.g_selected.cfn_q = 1'b1;
            @(posedge clk); #1;
            checks=checks+1;
            if (decoded !== 1'b1) begin errors=errors+1; $display("MISSED cfn_q from fault=1"); end
            @(negedge clk); release dut.g_selected.cfn_q;
            repeat(4) @(negedge clk);

 if(errors) $fatal(1,"FAIL checks=%0d missed=%0d",checks,errors);
 $display("PASS checks=%0d",checks); $finish;
end
endmodule
