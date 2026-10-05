`timescale 1ns/1ps
module tb_v41_macro_local_cuts;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0,wr_v=0,rd_v=0,pre_v=0,rq_v=0;
    reg [3:0] wr_group=0,rd_group=0;
    reg [8:0] wr_row=0,rd_row=0;
    reg [127:0] wr_data=0,wr_mask=0,pre_d=0;
    reg [12:0] pre_e=0;
    reg [13:0] rq_q=0;
    reg [1:0] rq_plg=0;
    wire [127:0] vm_q,me_q;
    wire vm_qv;
    reg seen=0;
    localparam [127:0] WORD=128'hd14edcba98765432123456789abcdef0;

    ot_v41_vm_macro_local_cut u_vm(
        .clk(clk),.rst_n(rst_n),.rd_v(rd_v),.rd_group(rd_group),
        .rd_row(rd_row),.wr_v(wr_v),.wr_group(wr_group),.wr_row(wr_row),
        .wr_data(wr_data),.wr_mask(wr_mask),.rd_capture(vm_q),
        .rd_capture_v(vm_qv));
    ot_v41_me_macro_local_cut u_me(
        .clk(clk),.pre_v(pre_v),.pre_e(pre_e),.pre_d(pre_d),
        .rq_v(rq_v),.rq_q(rq_q),.rq_plg(rq_plg),.q_local_r(me_q));

    always @(posedge clk) begin
        #1;
        if (vm_qv) begin
            if (vm_q !== WORD) $fatal(1,"VM read mismatch %h",vm_q);
            seen=1;
        end
    end

    initial begin
        repeat (2) @(negedge clk);
        rst_n=1; wr_v=1; wr_row=9'd5; wr_data=WORD; wr_mask='1;
        pre_v=1; pre_e=13'd64; pre_d=WORD;
        @(negedge clk); wr_v=0; pre_v=0;
        repeat (3) @(negedge clk);
        rd_v=1; rd_row=9'd5; rq_v=1; rq_q=14'd8;
        @(negedge clk); rd_v=0; rq_v=0;
        repeat (4) @(negedge clk);
        if (!seen) $fatal(1,"VM read-valid latency failed");
        if (me_q !== WORD) $fatal(1,"ME read mismatch %h",me_q);
        $display("PASS VM and MP1 one-macro cut exact word and registered latency");
        $finish;
    end
endmodule
