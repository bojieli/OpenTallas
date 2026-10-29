`timescale 1ns/1ps
// Compare the default frozen root-count structure to the opt-in 28/27 split
// at every actual decoder output cycle; omitted Forney division must diverge.
module tb_head_serdes_dchn;
    reg clk=0, rst_n=0;
    always #0.4165 clk=~clk;
    reg [3:0] k_v=0;
    reg [309:0] k_lo=0;
    reg [4:0] k_L=1;
    reg k_any=1;
    wire [543:0] a_cw,b_cw,m_cw;
    wire [7:0] a_ap,b_ap,m_ap;
    wire a_un,b_un,m_un,a_fs,b_fs,m_fs;
    wire [4:0] a_ne,b_ne,m_ne;
    wire [31:0] a_nc,b_nc,m_nc,a_nu,b_nu,m_nu;
    ot_s81_kp4_dchn #(.MUT(0)) a(
        .clk(clk),.rst_n(rst_n),.k_v(k_v),.k_lo(k_lo),.k_L(k_L),.k_any(k_any),
        .cw_q(a_cw),.apply(a_ap),.o_unc(a_un),.o_ne(a_ne),.fs(a_fs),.n_corr(a_nc),.n_unc(a_nu));
    ot_s81_kp4_dchn #(.ROOT_COUNT_SPLIT(1)) b(
        .clk(clk),.rst_n(rst_n),.k_v(k_v),.k_lo(k_lo),.k_L(k_L),.k_any(k_any),
        .cw_q(b_cw),.apply(b_ap),.o_unc(b_un),.o_ne(b_ne),.fs(b_fs),.n_corr(b_nc),.n_unc(b_nu));
    ot_s81_kp4_dchn #(.MUT(2),.ROOT_COUNT_SPLIT(1)) mutant(
        .clk(clk),.rst_n(rst_n),.k_v(k_v),.k_lo(k_lo),.k_L(k_L),.k_any(k_any),
        .cw_q(m_cw),.apply(m_ap),.o_unc(m_un),.o_ne(m_ne),.fs(m_fs),.n_corr(m_nc),.n_unc(m_nu));
    integer n=0, checked=0, caught=0, frames=0;
    always @(negedge clk) if (rst_n) begin
        n=n+1;
        if(n>10) begin
            if({a_cw,a_ap,a_un,a_ne,a_fs,a_nc,a_nu} !== {b_cw,b_ap,b_un,b_ne,b_fs,b_nc,b_nu})
                $fatal(1,"DCHN extraction mismatch at %0d",n);
            checked=checked+1;
            if(a_cw !== m_cw) caught=caught+1;
        end
    end
    initial begin
        repeat(6) @(negedge clk);
        rst_n=1;
        repeat(8) @(negedge clk);
        // A degree-one locator gives one real root in the 544-symbol scan.
        // Its non-unit derivative makes the MUT2 omitted division observable.
        repeat(64) begin
            @(negedge clk);
            k_lo=0;
            k_lo[9:0]=10'd7;
            k_lo[19:10]=10'd7;
            k_lo[169:160]=10'd11+frames;
            k_v=4'hf;
            @(negedge clk); k_v=0;
            repeat(9) @(negedge clk);
            frames=frames+1;
        end
        repeat(30) @(negedge clk);
        if(checked<600 || caught==0) $fatal(1,"inadequate gate checked=%0d mutant=%0d",checked,caught);
        $display("HEAD_DCHN PASS checked=%0d mutant_caught=%0d frames=%0d added_cycles=0",checked,caught,frames);
        $finish;
    end
endmodule
