`timescale 1ns/1ps
module tb_bfqg;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0;
    reg [1023:0] c_d=0;
    reg wce=0,mhi=0,mlo=0;
    reg [6:0] wa=0,r_a=0;
    reg [7:0] r_ce=0;
    wire [255:0] ref_q,dut_q;
    integer mut=-1,cycles=0,checks=0,errors=0,writes=0,reads=0;
    reg [31:0] rng=32'h2589abcd;
    function automatic [31:0] step(input [31:0] x);
        reg [31:0] y; begin y=x^(x<<13);y=y^(y>>17);step=y^(y<<5);end
    endfunction
    wire [7:0] lc;
    for(genvar k=0;k<8;k=k+1) begin
        assign lc[k]=(mut==k)?1'b0:clk;
    end
    wire ctrl_clk=(mut==8)?1'b0:clk;
    wire [7:0] dhi=(mut==9)?{8{mlo}}:{8{mhi}};
    bfqg_reference ref_rtl(.clk(clk),.clk_n(clk),.clk_s(clk),
        .clk_m0(clk),.clk_m1(clk),.clk_m2(clk),.clk_m3(clk),
        .clk_m4(clk),.clk_m5(clk),.clk_m6(clk),.clk_m7(clk),
        .rst_n(rst_n),.c_d(c_d),.wce(wce),.mhi(mhi),.mlo(mlo),
        .wa(wa),.r_ce(r_ce),.r_a(r_a),.rwq(ref_q));
    ot_hgi_sm_xload_cl2_bfqg dut(.clk(clk),.clk_n(clk),.clk_s(clk),.clk_ctrl(ctrl_clk),
        .clk_m0(clk),.clk_m1(clk),.clk_m2(clk),.clk_m3(clk),
        .clk_m4(clk),.clk_m5(clk),.clk_m6(clk),.clk_m7(clk),
        .clk_l0(lc[0]),.clk_l1(lc[1]),.clk_l2(lc[2]),.clk_l3(lc[3]),
        .clk_l4(lc[4]),.clk_l5(lc[5]),.clk_l6(lc[6]),.clk_l7(lc[7]),
        .rst_n(rst_n),.c_d(c_d),.wce(wce),.mhi0(dhi[0]),.mhi1(dhi[1]),.mhi2(dhi[2]),.mhi3(dhi[3]),.mhi4(dhi[4]),.mhi5(dhi[5]),.mhi6(dhi[6]),.mhi7(dhi[7]),
        .mlo0(mlo),.mlo1(mlo),.mlo2(mlo),.mlo3(mlo),.mlo4(mlo),.mlo5(mlo),.mlo6(mlo),.mlo7(mlo),
        .wa(wa),.r_ce(r_ce),.r_a(r_a),.rwq(dut_q));
    task automatic tick(input bit compare);
        begin
            @(posedge clk);#1;cycles++;
            if(compare) begin
                checks++;
                if(ref_q!==dut_q) begin
                    if(errors<8)$display("BFQG_DIFF cycle=%0d ref=%h dut=%h",cycles,ref_q,dut_q);
                    errors++;
                end
            end
            @(negedge clk);
        end
    endtask
    initial begin
        if($value$plusargs("MUT=%d",mut))begin end
        repeat(8)tick(0);rst_n=1;repeat(8)tick(0);
        // Initialize every row of all eight actual SRAM models through real write ports.
        for(integer a=0;a<128;a++)begin
            wa=7'(a);wce=1;mhi=1;mlo=1;
            for(integer j=0;j<32;j++)begin rng=step(rng);c_d[j*32+:32]=rng;end
            writes+=8;tick(0);
        end
        wce=0;repeat(8)tick(0);
        // Exercise all128 addresses of every bank and compare every cycle.
        for(integer a=0;a<128;a++)for(integer bank=0;bank<8;bank++)begin
            r_a=7'(a);r_ce=8'b1<<bank;reads++;tick(1);
        end
        // Simultaneous reads and masked writes at deterministic independent addresses.
        for(integer n=0;n<4096;n++)begin
            rng=step(rng);wa=rng[6:0];r_a=~rng[6:0];
            wce=rng[7];mhi=rng[8];mlo=rng[9];r_ce=8'b1<<rng[12:10];
            for(integer j=0;j<32;j++)begin rng=step(rng);c_d[j*32+:32]=rng;end
            if(wce)writes+=8;reads++;tick(1);
        end
        wce=0;r_ce=0;repeat(16)tick(1);
        $display("BFQG_RESULT cycles=%0d checks=%0d bank_writes=%0d bank_reads=%0d errors=%0d mutant=%0d actual_models=16",cycles,checks,writes,reads,errors,mut);
        if(errors)$fatal(1,"BFQG_FAIL");
        $display("BFQG_PASS");$finish;
    end
endmodule
