`timescale 1ns/1ps
// KVJ-C2: ot_qkvd_split_kvlink_se (no gateway SU face) lock-step against ot_qkvd_split_kvlink with no EMBQ / EMBD
// traffic (r_v[3] = 0, eq_v = 0, ea_cr = 0) under random CTL / Q / KVN / RES / SCTL traffic and credits, 20 reset
// windows; then an EMBQ arrival must fault.  MUT via -DOT_KVJ_LNK_MUT (2 = an EMBQ arrival does not fault).
`ifndef OT_KVJ_LNK_MUT
`define OT_KVJ_LNK_MUT 0
`endif
module tb_ot_qkvd_split_kvlink_se;
    localparam integer W = 528;
    reg clk=0, rst_n=0;
    always #1 clk=~clk;
    reg [3:0] r_v=0; reg [4*W-1:0] r_d=0; reg [2:0] t_cr=0; reg x3_cr=0, ar_v=0; reg [518:0] ar_d=0;
    reg [186:0] ds=0; reg [74:0] pw=0; reg d2d_fault=0; reg [4:0] d2d_cause=0;
    wire [3:0] rcr_a, rcr_b; wire [2:0] tv_a, tv_b; wire [3*W-1:0] td_a, td_b;
    wire x3v_a, x3v_b, arcr_a, arcr_b, f_a, f_b; wire [10:0] x3t_a, x3t_b; wire [511:0] x3d_a, x3d_b;
    wire [55:0] sd_a, sd_b; wire [43:0] kvd_a, kvd_b;
    wire ea_v, ea_kind; wire [23:0] ea_addr;
    ot_qkvd_split_kvlink u_a (.clk(clk),.rst_n(rst_n),.r_v(r_v),.r_d(r_d),.r_cr(rcr_a),.t_v(tv_a),.t_d(td_a),.t_cr(t_cr),
        .x3_v(x3v_a),.x3_tag(x3t_a),.x3_d(x3d_a),.x3_cr(x3_cr),.sd(sd_a),.kvd(kvd_a),.ar_v(ar_v),.ar_d(ar_d),.ar_cr(arcr_a),
        .ds(ds),.pw(pw),.ea_v(ea_v),.ea_kind(ea_kind),.ea_addr(ea_addr),.ea_cr(1'b0),.eq_v(1'b0),.eq_d(512'd0),
        .d2d_fault(d2d_fault),.d2d_cause(d2d_cause),.fault(f_a));
    ot_qkvd_split_kvlink_se #(.MUT(`OT_KVJ_LNK_MUT)) u_b (.clk(clk),.rst_n(rst_n),.r_v(r_v),.r_d(r_d),.r_cr(rcr_b),.t_v(tv_b),.t_d(td_b),.t_cr(t_cr),
        .x3_v(x3v_b),.x3_tag(x3t_b),.x3_d(x3d_b),.x3_cr(x3_cr),.sd(sd_b),.kvd(kvd_b),.ar_v(ar_v),.ar_d(ar_d),.ar_cr(arcr_b),
        .ds(ds),.pw(pw),.d2d_fault(d2d_fault),.d2d_cause(d2d_cause),.fault(f_b));
    integer w, k, err=0, x3n=0, tn=0, i;
    task rnd_word(input integer c); integer j; begin for (j=0;j<W/32+1;j=j+1) r_d[c*W+32*j +: 32] = $urandom; end endtask
    initial begin
        for (w=0; w<20; w=w+1) begin
            rst_n=0; r_v=0; repeat(3) @(negedge clk); rst_n=1;
            for (k=0; k<3000; k=k+1) begin
                @(negedge clk);
                if (k>3 && ({rcr_a,tv_a,td_a,x3v_a,x3t_a,arcr_a,sd_a,f_a} !== {rcr_b,tv_b,td_b,x3v_b,x3t_b,arcr_b,sd_b,f_b} ||
                            kvd_a!==kvd_b || (x3v_a && x3d_a!==x3d_b))) begin
                    err=err+1; if (err<5) $display("FAIL mismatch w%0d k%0d", w, k); end
                if (x3v_a) x3n=x3n+1; if (|tv_a) tn=tn+1;
                for (i=0;i<3;i=i+1) rnd_word(i);
                // CTL ops 1 / 2 mostly (a rare bad op exercises the fault), Q / KVN at a rate the 40 x3 credits sustain
                r_d[0*W+524 +: 4] = ($urandom%50==0) ? 4'd7 : 4'd1 + ($urandom%2);
                r_v = {1'b0, ($urandom%6==0), ($urandom%6==0), ($urandom%8==0)};
                x3_cr = ($urandom%3==0); t_cr = $urandom; ar_v = ($urandom%4==0); ar_d = {17{$urandom}};
                ds = {6{$urandom}}; pw = {3{$urandom}}; d2d_fault = (w%5==4) && ($urandom%500==0); d2d_cause = $urandom;
            end
        end
        // negative: an EMBQ word (retired class) must fault the successor
        rst_n=0; r_v=0; repeat(3) @(negedge clk); rst_n=1; repeat(3) @(negedge clk);
        r_v=4'b1000; @(negedge clk); r_v=0; repeat(4) @(negedge clk);
        if (!f_b) begin err=err+1; $display("FAIL EMBQ arrival not faulted"); end
        if (err==0 && x3n>1000 && tn>1000) $display("PASS kvlink_se lock-step windows=20 x3=%0d t=%0d embq_fault", x3n, tn);
        else $display("FAIL kvlink_se err=%0d x3=%0d t=%0d", err, x3n, tn);
        $finish;
    end
endmodule
