`timescale 1ns/1ps
`default_nettype none
// hfd_vms_bank_native_q1_core_pr == hfd_vms_bank_native_q1_core with every data input one edge later (literal pin flops),
// every output identical, every edge.  MUT=1 drives the reference WITHOUT the one-edge delay (must FAIL).
module tb_q1core_pr;
    parameter integer N = 4000, MUT = 0;
    reg clk = 0; always #5 clk = ~clk;
    reg rst_n = 0;
    reg [16:0] rq0, rq3; reg [280:0] wq0, kq; reg [275:0] xq, xq2; reg [284:0] pq;
    reg [2:0] bid, rslot, wslot; reg [1:0] sid; reg rslot_v, wslot_v;
    reg [16:0] rq0_d, rq3_d; reg [280:0] wq0_d, kq_d; reg [275:0] xq_d, xq2_d; reg [284:0] pq_d;
    reg [2:0] bid_d, rslot_d, wslot_d; reg [1:0] sid_d; reg rslot_v_d, wslot_v_d;
    always @(posedge clk) begin rq0_d<=rq0; rq3_d<=rq3; wq0_d<=wq0; kq_d<=kq; xq_d<=xq; xq2_d<=xq2; pq_d<=pq;
        bid_d<=bid; rslot_d<=rslot; wslot_d<=wslot; sid_d<=sid; rslot_v_d<=rslot_v; wslot_v_d<=wslot_v; end
    wire [256:0] a_rr0, a_rr3, b_rr0, b_rr3; wire [275:0] a_eg, b_eg; wire [265:0] a_pr, b_pr; wire [17:0] a_st, b_st;
    wire a_w0, b_w0, a_k, b_k, a_x, b_x, a_x2, b_x2;
    hfd_vms_bank_native_q1_core_pr dut(.rq0(rq0),.rr0(a_rr0),.rq3(rq3),.rr3(a_rr3),.wq0(wq0),.wq_done0(a_w0),.bid(bid),.sid(sid),
      .clk(clk),.rst_n(rst_n),.rslot_v(rslot_v),.rslot(rslot),.wslot_v(wslot_v),.wslot(wslot),.kq(kq),.kq_done(a_k),
      .xq(xq),.xq_done(a_x),.xq2(xq2),.xq2_done(a_x2),.eg(a_eg),.pq(pq),.pr(a_pr),.status(a_st));
    hfd_vms_bank_native_q1_core ref_(.rq0(MUT?rq0:rq0_d),.rr0(b_rr0),.rq3(MUT?rq3:rq3_d),.rr3(b_rr3),.wq0(MUT?wq0:wq0_d),.wq_done0(b_w0),
      .bid(MUT?bid:bid_d),.sid(MUT?sid:sid_d),.clk(clk),.rst_n(rst_n),.rslot_v(MUT?rslot_v:rslot_v_d),.rslot(MUT?rslot:rslot_d),
      .wslot_v(MUT?wslot_v:wslot_v_d),.wslot(MUT?wslot:wslot_d),.kq(MUT?kq:kq_d),.kq_done(b_k),.xq(MUT?xq:xq_d),.xq_done(b_x),
      .xq2(MUT?xq2:xq2_d),.xq2_done(b_x2),.eg(b_eg),.pq(MUT?pq:pq_d),.pr(b_pr),.status(b_st));
    integer t, err = 0, checks = 0, seed = 7;
    function automatic [15:0] sec(input integer row, input bit mir);
        sec = mir ? {1'b1, 2'b00, 10'(row), 3'd3} : {1'b0, 2'd1, 10'(row), 3'd3};
    endfunction
    initial begin
        {rq0,rq3,wq0,kq,xq,xq2,pq,rslot,wslot,rslot_v,wslot_v} = 0; bid = 3; sid = 1;
        repeat (6) @(posedge clk); #1 rst_n = 1;
        for (t = 0; t < N; t = t + 1) begin
            @(posedge clk); #1;
            {rq0,rq3,wq0,kq,xq,xq2,pq,rslot_v,wslot_v} = 0;
            case ($urandom(seed) % 4)
              0: begin wq0 = {1'b1, 1'($urandom(seed)), sec($urandom(seed)%64, $urandom(seed)%2), 8'hff, {8{32'($urandom(seed))}}}; wslot_v = 1; wslot = 0; end
              1: begin kq = {1'b1, 1'b0, sec($urandom(seed)%64, 0), 8'hff, {8{32'($urandom(seed))}}}; wslot_v = 1; wslot = 3; end
              default: ;
            endcase
            case ($urandom(seed) % 3)
              0: begin rq0 = {1'b1, sec($urandom(seed)%64, $urandom(seed)%2)}; rslot_v = 1; rslot = 0; end
              1: begin rq3 = {1'b1, sec($urandom(seed)%64, 0)}; rslot_v = 1; rslot = 3; end
              default: ;
            endcase
        end
        repeat (20) @(posedge clk);
        if (err == 0 && checks > 1000) $display("Q1CORE_PR EQUIV PASS checks=%0d errors=0", checks);
        else $display("Q1CORE_PR EQUIV FAIL checks=%0d errors=%0d", checks, err);
        $finish;
    end
    always @(negedge clk) if (rst_n) begin
        checks++;
        if ({a_rr0,a_rr3,a_eg,a_pr,a_st,a_w0,a_k,a_x,a_x2} !== {b_rr0,b_rr3,b_eg,b_pr,b_st,b_w0,b_k,b_x,b_x2}) begin
            err++; if (err < 4) $display("MISMATCH @%0t", $time); end
    end
endmodule
`default_nettype wire
