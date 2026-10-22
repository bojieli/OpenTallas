`timescale 1ns/1ps
// STW-S81-TOPK-VMUX (10-21): cycle-exact equivalence bench dsdv_idx_vmux (reference, unchanged) vs dsdv_idx_vmux_n32,
// and dsdv_idx_vdly vs an N-flop shift register.  Random 276-b beats on all 4 inputs every edge (invalid lanes carry
// random data too: the merge must mask them), 0 / 1 valid lanes most edges, 2 valid (fault) after +FAULT_AT, reset
// asserted again mid-run (+RST2).  Every output bit compared every edge.  `VM_MUT / `DL_MUT select the negative controls.
`ifndef VM_MUT
`define VM_MUT 0
`endif
`ifndef DL_MUT
`define DL_MUT 0
`endif
module tb_dsdv_idx_vmux_n32;
    localparam integer V = 276, N = 28;
    reg ck = 0, rst = 0;
    always #0.5 ck = ~ck;
    reg [V-1:0] i_r = 0, i_s = 0, i_a = 0, i_b = 0;
    wire [V-1:0] o_ref, o_dut, d_dut; wire f_ref, f_dut;
    reg [V-1:0] sr [0:N-1];
    reg [1:0] rrs = 0;
    dsdv_idx_vmux     u_ref (.ck(ck), .rst(rst), .i_r(i_r), .i_s(i_s), .i_a(i_a), .i_b(i_b), .o(o_ref), .fault(f_ref));
    dsdv_idx_vmux_n32 #(.MUT(`VM_MUT)) u_dut (.ck(ck), .rst(rst), .i_r(i_r), .i_s(i_s), .i_a(i_a), .i_b(i_b), .o(o_dut), .fault(f_dut));
    dsdv_idx_vdly #(.W(V), .N(N), .MUT(`DL_MUT)) u_dl (.ck(ck), .rst(rst), .i(i_s), .o(d_dut));
    integer cyc = 0, ncyc, fault_at, nerr = 0, nerr_dl = 0, nv = 0, seed = 1;
    function automatic [V-1:0] rnd();
        for (int w = 0; w < (V + 31) / 32; w++) rnd[32 * w +: 32] = $urandom;
    endfunction
    initial begin
        if (!$value$plusargs("NCYC=%d", ncyc)) ncyc = 20000;
        if (!$value$plusargs("FAULT_AT=%d", fault_at)) fault_at = 15000;
        if ($value$plusargs("SEED=%d", seed)) void'($urandom(seed));
        for (int j = 0; j < N; j++) sr[j] = 0;
    end
    always @(negedge ck) begin
        int sel, two;
        reg [V-1:0] a, b, c, d;
        a = rnd(); b = rnd(); c = rnd(); d = rnd();
        a[0] = 0; b[0] = 0; c[0] = 0; d[0] = 0;
        sel = $urandom % 6;                        // 0..3 one lane valid, 4..5 none
        two = (cyc > fault_at) && ($urandom % 50 == 0);
        if (sel == 0 || (two && sel == 1)) a[0] = 1;
        if (sel == 1) b[0] = 1;
        if (sel == 2 || (two && sel == 3)) c[0] = 1;
        if (sel == 3) d[0] = 1;
        i_r <= a; i_s <= b; i_a <= c; i_b <= d;
        if (cyc == 10) rst <= 1;
        if (cyc == 7000) rst <= 0;                 // second reset mid-stream
        if (cyc == 7013) rst <= 1;
    end
    always @(posedge ck) begin
        #0.1;
        for (int j = N - 1; j > 0; j--) sr[j] = sr[j - 1];
        sr[0] = rrs[1] ? i_s : '0;                  // reference: 2-flop reset landing like the DUT's valid chain
        rrs = rst ? {rrs[0], 1'b1} : 2'b00;
        if (o_ref !== o_dut || f_ref !== f_dut) begin
            nerr++;
            if (nerr <= 5) $display("MISMATCH vmux cyc %0d ref %h/%b dut %h/%b", cyc, o_ref[63:0], f_ref, o_dut[63:0], f_dut);
        end
        if (o_ref[0]) nv++;
        // vdly: valid must match the shifted valid exactly; data compared whenever the shifted valid is set
        if (cyc > 40 && !(cyc > 6990 && cyc < 7070) && (d_dut[0] !== sr[N - 1][0] || (sr[N - 1][0] && d_dut !== sr[N - 1]))) begin
            nerr_dl++;
            if (nerr_dl <= 5) $display("MISMATCH vdly cyc %0d exp %h got %h", cyc, sr[N - 1][63:0], d_dut[63:0]);
        end
        cyc++;
        if (cyc >= ncyc) begin
            $display("VMUX_N32 %s nerr %0d valid_beats %0d fault_ref %b | VDLY %s nerr %0d (vm_mut %0d dl_mut %0d)",
                nerr == 0 ? "PASS" : "FAIL", nerr, nv, f_ref, nerr_dl == 0 ? "PASS" : "FAIL", nerr_dl, `VM_MUT, `DL_MUT);
            $finish;
        end
    end
endmodule
