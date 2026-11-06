module tb_legacy_input_freg;
    timeunit 1ps; timeprecision 1fs;
    localparam int W = 517;
    bit fclk=0, clk=0;
    int phase=0, cyc=0;
    bit rst_n=0;
    logic [W-1:0] d='0;
    int unsigned sample=0;
    always #416.5 fclk = ~fclk;
    initial begin
        void'($value$plusargs("PHASE=%d", phase));
        #(phase); forever #416.5 clk=~clk;
    end
    always @(posedge fclk) begin
        sample <= sample + 1;
        for (int k=0;k<W;k++) d[k] <= ((sample*32'h9e3779b9) >> (k%32)) ^ (sample >> ((k/32)%16));
    end
    always @(negedge clk) begin
        cyc <= cyc+1;
        case(cyc)
            4,210,730: rst_n<=1;
            200,710: rst_n<=0;
        endcase
        if (cyc == 1800) begin
            $display("CASE_RESULT WNEG=0 checks=%0d errors=%0d",case0.checks,case0.errors);
            $display("CASE_RESULT WNEG=1 checks=%0d errors=%0d",case1.checks,case1.errors);
            if (case0.checks<1400 || case1.checks<1400) $fatal(1,"insufficient ready comparisons");
            if (case0.errors || case1.errors) $fatal(1,"LOCKSTEP_ERRORS");
            $display("LEGACY_FREG_PASS phase=%0d checks=%0d/%0d",phase,case0.checks,case1.checks);
            $finish;
        end
    end
    freg_case #(.W(W),.WNEG(0)) case0(.fclk(fclk),.clk(clk),.rst_n(rst_n),.d(d));
    freg_case #(.W(W),.WNEG(1)) case1(.fclk(fclk),.clk(clk),.rst_n(rst_n),.d(d));
endmodule

module freg_case #(parameter int W=517,parameter bit WNEG=1)(
    input fclk,clk,rst_n,input [W-1:0]d);
    timeunit 1ps;timeprecision 1fs;
    wire [W-1:0] old_q,new_q;
    wire old_ready,new_ready,old_fault,new_fault;
    logic [W-1:0] old_prev='0;
    bit prev_ready=0;
    int checks=0, errors=0;
    ot_dp_clk_landing_gold #(.W(W),.WNEG(WNEG)) gold(
      .fclk(fclk),.clk(clk),.rst_n(rst_n),.d(d),.q(old_q),.ready(old_ready),.fault(old_fault));
    ot_dp_clk_landing #(.W(W),.WNEG(WNEG),.FREG(1)) candidate(
      .fclk(fclk),.clk(clk),.rst_n(rst_n),.d(d),.q(new_q),.ready(new_ready),.fault(new_fault));
    always @(posedge clk) begin
        #0.001;
        if (old_ready !== new_ready || old_fault !== new_fault)
            errors++;
        if (old_ready && old_fault) errors++;
        if (old_ready && prev_ready && rst_n) begin
            if (new_q !== old_prev) errors++;
            checks++;
        end
        old_prev=old_q;
        prev_ready=old_ready && rst_n;
    end
endmodule
