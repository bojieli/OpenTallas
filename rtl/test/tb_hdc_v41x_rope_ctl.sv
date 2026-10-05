`timescale 1ns/1ps
module tb_hdc_v41x_rope_ctl;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, start=0, pf_done=0;
    wire done, fault, pf_v, pf_kind, pf_release;
    wire [20:0] pf_pos;
    wire prog_re;
    wire [13:0] prog_addr;
    reg [2047:0] prog_q;
    reg [2047:0] prog [0:2];
    string program_path;
    integer cycles=0, requests=0, releases=0, issue_cycle=-1, release_cycle=-1;

    ot_hdc_core_v41x #(.FULL_SHAPE(1), .X_HE(0), .X_ME(0), .X_ATT(0), .X_IDX(0),
        .X_SEL(0), .X_EG(0), .X_SU(0), .W_HBM(0), .KV_HBM(0)) dut (
        .clk(clk), .rst_n(rst_n), .start(start), .token(21'd3582), .pos(21'd199999),
        .entry(14'd0), .done(done), .fault(fault),
        .prog_re(prog_re), .prog_addr(prog_addr), .prog_q(prog_q),
        .coll_busy(1'b0), .coll_fault(1'b0),
        .rope_pf_v(pf_v), .rope_pf_rdy(1'b1), .rope_pf_kind(pf_kind),
        .rope_pf_pos(pf_pos), .rope_pf_done(pf_done),
        .rope_pf_release(pf_release), .rope_pf_fault(1'b0));

    always @(posedge clk) begin
        cycles <= cycles+1;
        if (prog_re) prog_q <= prog[prog_addr];
        if (pf_v) begin
            if (requests != 0 || pf_kind != 0 || pf_pos != 21'd199999)
                $fatal(1,"bad RoPE prefetch kind=%b pos=%0d requests=%0d",pf_kind,pf_pos,requests);
            requests <= requests+1; issue_cycle <= cycles;
        end
        if (pf_release) begin
            if (requests != 1 || releases != 0 || !pf_done && cycles-issue_cycle < 3)
                $fatal(1,"premature/duplicate release");
            releases <= releases+1; release_cycle <= cycles;
        end
    end

    initial begin
        if (!$value$plusargs("PROG=%s",program_path)) $fatal(1,"program missing");
        $readmemh(program_path,prog);
        repeat(3) @(negedge clk);
        rst_n=1;
        @(negedge clk); start=1;
        @(negedge clk); start=0;
        wait(requests==1);
        repeat(4) @(negedge clk);
        if (releases != 0 || done) $fatal(1,"prefetch was not blocking");
        pf_done=1;
        @(negedge clk); pf_done=0;
        wait(done);
        if (fault || requests!=1 || releases!=1 || release_cycle<=issue_cycle+3)
            $fatal(1,"RoPE CTL result fault=%b req=%0d rel=%0d",fault,requests,releases);
        $display("ROPE_CTL_PASS requests=%0d releases=%0d cycles=%0d",requests,releases,cycles);
        $finish;
    end
    initial begin #100000; $fatal(1,"RoPE CTL timeout"); end
endmodule
