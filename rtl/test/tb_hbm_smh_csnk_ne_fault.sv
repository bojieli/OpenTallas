`timescale 1ns/1ps
// Full production front_s is the minimum vehicle containing the actual public
// sticky-fault path. Arithmetic and the rest of the SM are not simulated.
module tb_hbm_smh_csnk_ne_fault;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, fq_v=0, req_ready=0;
    wire fault, req_v;
    wire [31:0] req_addr;
    wire [9:0] req_tag;
    ot_hbm_accel_smh_front_s dut(
        .clk(clk),.rst_n(rst_n),.d_valid(1'b0),.d_base(32'b0),.d_lines(24'b0),
        .req_ready(req_ready),.req_v(req_v),.req_addr(req_addr),.req_tag(req_tag),
        .rsp_v(1'b0),.rsp_tag(10'b0),.rsp_data(1088'b0),.fault(fault),
        .qin_l(184'b0),.qin_r(184'b0),.fd_ret(1'b0),.fq_v(fq_v),
        .fq_d({32'h12345678,10'h155}),.fi_row3(818'b0));
    integer publications=0, injections=0;
    always @(posedge clk) if(rst_n) begin
        if(dut.rch_state_fault && dut.u_rch.pop) $fatal(1,"false pop under invalid rails");
        if(req_v) begin
            publications=publications+1;
            if(req_addr!==32'h12345678 || req_tag!==10'h155) $fatal(1,"false published data");
        end
    end
    task reset_block;
        begin
            @(negedge clk);rst_n=0;fq_v=0;req_ready=0;
            repeat(3) @(negedge clk);
            if(fault!==0) $fatal(1,"reset failed to clear public fault");
            publications=0;rst_n=1;
        end
    endtask
    task inject;
        input integer occupied,rail;
        begin
            reset_block;
            if(occupied) begin
                @(negedge clk);fq_v=1;
                @(negedge clk);fq_v=0;
                repeat(2) @(negedge clk);
            end
            if(dut.u_rch.cnt!==occupied) $fatal(1,"bad injection precondition");
            req_ready=1;
            if(rail==0) begin
                if(occupied) force dut.u_rch.nonempty=1'b0;
                else force dut.u_rch.nonempty=1'b1;
            end else begin
                if(occupied) force dut.u_rch.empty=1'b1;
                else force dut.u_rch.empty=1'b0;
            end
            #1;
            if(dut.rch_state_fault!==1 || dut.u_rch.m_valid!==0 || dut.u_rch.pop!==0)
                $fatal(1,"single-rail error not detected/fail-closed");
            @(posedge clk);#1;
            if(dut.fault_q!==1 || req_v!==0) $fatal(1,"missing sticky fault or false publication");
            if(rail==0) release dut.u_rch.nonempty;
            else release dut.u_rch.empty;
            @(posedge clk);#1;
            if(dut.rch_state_fault!==0 || dut.fault_q!==1)
                $fatal(1,"rails failed to resynchronize or sticky fault lost");
            repeat(8) @(negedge clk);
            if(fault!==1 || publications!=occupied)
                $fatal(1,"public fault/publication mismatch occupied=%0d rail=%0d pub=%0d fault=%b",occupied,rail,publications,fault);
            injections=injections+1;
        end
    endtask
    initial begin
        inject(0,0);inject(0,1);inject(1,0);inject(1,1);
        reset_block;
        $display("PASS injections=%0d empty/nonempty x both rails; no false pop/publication; repair sticky fault and reset",injections);
        $finish;
    end
endmodule
