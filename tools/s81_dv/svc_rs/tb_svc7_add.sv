`timescale 1ns/1ps
module tb_svc7_add;
    reg clk=0;
    always #1 clk=~clk;
    reg rst_n=0, valid_in=0;
    reg [31:0] a=0,b=0;
    wire [31:0] y,ref_y;
    wire [1:0] err,ref_err;
    wire vo,ref_vo;
    ot_s81svc7_add dut(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),
        .a(a),.b(b),.y(y),.err(err),.valid_out(vo));
    ot_hdc_fp32_add_f12_l4 ref_add(.clk(clk),.rst_n(rst_n),.valid_in(valid_in),
        .a(a),.b(b),.y(ref_y),.err(ref_err),.valid_out(ref_vo));
    reg [34:0] h0=0,h1=0;
    integer cyc=0,checked=0,errors=0;
    always @(negedge clk) begin
        if (cyc>40 && {vo,err,y} !== h1) begin
            $display("SVC7_ADD_MISMATCH cyc=%0d got=%h expected=%h",cyc,{vo,err,y},h1);
            errors=errors+1;
        end
        if (cyc>40) checked=checked+1;
        h1=h0; h0={ref_vo,ref_err,ref_y};
        rst_n=(cyc>=12);
        valid_in=($urandom_range(0,7)!=0);
        a=$urandom; b=$urandom;
        case(cyc%16)
            0: a=32'h7f800000;
            1: b=32'h7fc00001;
            2: a=32'h00000000;
            3: b=32'h80000000;
            4: a=32'h00000001;
            5: begin a=32'h7f7fffff; b=32'h7f7fffff; end
            6: begin a=32'h3f800000; b=32'hbf800000; end
            default: begin end
        endcase
        cyc=cyc+1;
        if(cyc==12000) begin
            $display("SVC7_ADD checked=%0d errors=%0d latency=6 verdict=%s",checked,errors,errors==0?"PASS":"FAIL");
            if(errors!=0) $fatal(1,"SVC7_ADD_FAIL");
            $finish;
        end
    end
endmodule
