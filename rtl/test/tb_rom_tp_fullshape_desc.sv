`timescale 1ns/1ps
module tb_rom_tp_fullshape_desc;
    reg clk=0, rst_n=0, start=0;
    always #5 clk=~clk;
    reg core_done=0;
    wire core_start, done, fault;
    wire [17:0] next_token;
    wire [5:0] desc_addr;
    wire desc_re;
    wire [63:0] desc_q = (64'd10432 << 48) | (64'd1 << 18);
    ot_rom_tp_seq #(.N(2),.NW(18),.TAGW(34),.QWEN_FULLSHAPE(1)) dut (
        .clk(clk),.rst_n(rst_n),.start(start),.token(18'd151935),.pos(18'd0),
        .done(done),.next_token(next_token),.next_val(),.fault(fault),.coll_busy(),
        .core_start(core_start),.core_token(),.core_pos(),.core_done(core_done),
        .core_next_token(18'd10),.core_next_val(32'h3f800000),.core_fault(1'b0),
        .prog_base(),.desc_re(desc_re),.desc_addr(desc_addr),.desc_q(desc_q),
        .vm_re(),.vm_raddr(),.vm_rq(512'b0),.vm_we(),.vm_waddr(),.vm_wdata(),
        .c_valid(),.c_ready(1'b1),.c_data(),.c_last(),.c_mode(),.c_tag(),
        .r_valid(1'b0),.r_data(512'b0),.r_last(1'b0),.r_rank(1'b0),.r_err(1'b0));
    always @(posedge clk) core_done <= core_start;
    integer cycles;
    initial begin
        repeat(4) @(negedge clk);
        rst_n=1;
        @(negedge clk); start=1;
        @(negedge clk); start=0;
        cycles=0;
        while (!done && cycles<20) begin @(negedge clk); cycles=cycles+1; end
        if (!done || fault || next_token !== 18'd75978)
            $fatal(1,"TP descriptor row0 got=%0d done=%0d fault=%0d",next_token,done,fault);
        $display("QWEN_TP_DESC row0=75968 next_token=%0d",next_token);
        $finish;
    end
endmodule
