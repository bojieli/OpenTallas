`timescale 1ns/1ps
// Production 788-bit operand ring versus legacy r0w/w3/w3b pipeline.
// Both sides use the same XSE/reset-landing contract. Every input randomized;
// asynchronous reset bursts every257 cycles, compare after pipeline warmup.
// All1615 output bits checked every eligible cycle, including invalid data.
module tb_xs_ring_equiv;
    localparam integer NC = `XSE_CYCLES;
    reg clk = 1'b0, rst_a = 1'b0;
    reg [8:0] xs_a1; reg [4:0] xs_g1; reg [6:0] xs_a2; reg [4:0] xs_g2;
    reg [817:0] rl1; reg [2068:0] bk1; reg [12:0] ohl1;
    wire [1614:0] od, orf;
    `define XS_PORTS(o) .clk(clk), .rst_a(rst_a), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), \
        .rl1(rl1), .bk1(bk1), .ohl1(ohl1), .o_iv_b(o[0]), .o_iv_f(o[1]), .o_ifirst(o[2]), .o_ilast(o[3]), .o_ifp4(o[4]), \
        .o_itag(o[20:5]), .o_iw(o[808:21]), .o_ix(o[1596:809]), .o_ifirst_e(o[1597]), .o_ilast_e(o[1598]), .o_itag_e(o[1614:1599])
    ot_hbm_accel_smh_xs #(.TAGW(16), .NBEAT(13)) u_dut (`XS_PORTS(od));
    ref_ot_hbm_accel_smh_xs #(.TAGW(16), .NBEAT(13)) u_ref (`XS_PORTS(orf));
    always #1 clk = ~clk;
    integer c,i,mism,tog,nzv,seed;
`ifndef XSE_NRG
`define XSE_NRG 4
`endif
`ifdef OT_SMH_RING_LOCAL_CHECK
    // DUT ring macro g (any ring geometry, XSE_NRG macros) against reference ring macro 0 (all reference ring macros
    // share one address): read AND write address, every posedge after the DUT ring reset releases.
    integer addr_checks=0,addr_mismatches=0;
    generate for(genvar g=0;g<`XSE_NRG;g=g+1)begin:g_address_check
        always @(posedge clk)if(u_dut.u_leaf.rst_n)begin
            addr_checks=addr_checks+1;
            if(u_dut.u_leaf.g_wr_ring[g].u_w.r_addr_in[1:0] !== u_ref.u_leaf.g_wr_ring[0].u_w.r_addr_in[1:0] ||
               u_dut.u_leaf.g_wr_ring[g].u_w.w_addr_in[1:0] !== u_ref.u_leaf.g_wr_ring[0].u_w.w_addr_in[1:0])begin
                addr_mismatches=addr_mismatches+1;
                if(addr_mismatches<5)$display("XS_RING_MACRO_ADDR_MISMATCH macro%0d r new%0d old%0d w new%0d old%0d",g,
                    u_dut.u_leaf.g_wr_ring[g].u_w.r_addr_in[1:0],u_ref.u_leaf.g_wr_ring[0].u_w.r_addr_in[1:0],
                    u_dut.u_leaf.g_wr_ring[g].u_w.w_addr_in[1:0],u_ref.u_leaf.g_wr_ring[0].u_w.w_addr_in[1:0]);
            end
        end
    end endgenerate
`endif
    reg [15:0] tprev;
    task rnd;
        begin
            xs_a1 = $urandom; xs_g1 = $urandom; xs_a2 = $urandom; xs_g2 = $urandom; ohl1 = $urandom;
            for (i = 0; i < 26; i = i + 1) rl1[i*32 +: 32] = $urandom;
            for (i = 0; i < 65; i = i + 1) bk1[i*32 +: 32] = $urandom;
        end
    endtask
    initial begin
        seed = `XSE_SEED; void'($urandom(seed));
        mism = 0; tog = 0; nzv = 0; tprev = 16'h0;
        rnd;
        for (c = 0; c < NC; c = c + 1) begin
            @(negedge clk);
            rst_a = (c >= 6) && ((c % 257) >= 3);
            rnd;
            if (c >= 24 && ((c % 257) >= 24)) begin
                if (od !== orf) begin
                    mism = mism + 1;
                    if (mism <= 5) $display("XS_RING_EQUIV MISMATCH cycle=%0d itag_e dut=%h ref=%h first_e %b/%b last_e %b/%b other_diff=%0d",
                        c, od[1614:1599], orf[1614:1599], od[1597], orf[1597], od[1598], orf[1598], (od[1596:0] !== orf[1596:0]));
                end
                if (od[1614:1599] != tprev) tog = tog + 1;
                if (od[1] | od[0]) nzv = nzv + 1;
                tprev = od[1614:1599];
            end
        end
        $display("XS_RING_EQUIV cycles=%0d seed=%0d mismatches=%0d itag_e_toggles=%0d valid_cycles=%0d", NC, seed, mism, tog, nzv);
`ifdef OT_SMH_RING_LOCAL_CHECK
        $display("XS_RING_MACRO_ADDR checks%0d mismatches%0d resetstartup_wrap",addr_checks,addr_mismatches);
        if(addr_mismatches!=0 || addr_checks<NC*`XSE_NRG/2)mism=mism+1;
`endif
        if (mism == 0 && tog > NC/4 && nzv > 0) $display("XS_RING_EQUIV PASS");
        else $display("XS_RING_EQUIV FAIL");
        $finish;
    end
endmodule
