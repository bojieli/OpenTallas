// R1-NARROW (KV-PVFIN-1 11-13) lock-step: every count-aligned landing ring form with NARROW 0 (gold, the 64-bit padded
// ring) vs NARROW 1 (candidate, a W-bit ring) on one stimulus.  Declared change: none at the ports, 0 added cycles:
// q, ready and fault are identical at EVERY clk edge after the receiver start.
// Covered: ot_dp_clk_landing_cas at W = 1, 2, 7, 32, 33, 44, 64 (narrow) and 65 (NARROW must be a no-op), DEPTH 4/8,
// STATUS_REG (+CONTROL_STATUS_COPY) 0/1, WFALL 0/1, WREG 0/1, FREG 0/1 on half, DSREP 1/2; ot_dp_clk_landing_ca at
// W = 2 / 33 with K = 2 / 3.  Receiver phase +PHASE; healthy, forwarded-clock slip, sender restart, late sender start.
// Negative controls: OT_MESO_CA_MUTANT_NARROW (narrow ring one live bit short) must FAIL; +SHIFT=1 (compare against gold
// q one clk late, i.e. a wrongly declared +1 cycle) must FAIL.
module tb_narrow;
    timeunit 1ps; timeprecision 1fs;
    logic fclk_r=0, clk=0, t_rst_n=0, r_rst_n=0, fen=1;
    wire fclk = fclk_r & fen;
    logic [127:0] data={64'h0f1e2d3c4b5a6978,64'h123456789abcdef1};
    integer phase=0, shift=0, fails=0, words=0, nz=0;
    always #416.5 fclk_r=~fclk_r;
    initial begin
        void'($value$plusargs("PHASE=%d",phase)); void'($value$plusargs("SHIFT=%d",shift));
        #(phase);
        forever #416.5 clk=~clk;
    end
    always @(negedge fclk_r) data <= {data[126:0], data[127]^data[125]^data[100]^data[98]};
    `define CHECK(TAG, WW, Q0, Q1, R0, R1, F0, F1) \
        logic [WW-1:0] h1=0; logic hv1=0; \
        always @(posedge clk) begin #1; \
            if (r_rst_n) begin \
                if ((shift==0 || hv1) && Q1 !== (shift==0 ? Q0 : h1)) begin \
                    $display("NR_MISMATCH q %s phase=%0d gold=%h cand=%h", TAG, phase, Q0, Q1); fails=fails+1; end \
                else if (R0) begin words=words+1; if (Q0 != 0) nz=nz+1; end \
                if (R0 !== R1 || F0 !== F1) begin $display("NR_MISMATCH status %s phase=%0d rdy %b/%b flt %b/%b", TAG, phase, R0, R1, F0, F1); fails=fails+1; end \
                h1=Q0; hv1=1; \
            end else hv1=0; \
        end
    localparam int NW = 8;
    localparam int WS [NW] = '{1, 2, 7, 32, 33, 44, 64, 65};
    for (genvar wi=0; wi<NW; wi++) begin: w
        localparam int W = WS[wi];
        for(genvar g=0;g<2;g++) for(genvar s=0;s<2;s++) for(genvar f=0;f<2;f++) for(genvar r=0;r<2;r++) for(genvar ds=0;ds<2;ds++) begin: m
            localparam integer D=4<<g;
            localparam integer KW=$clog2(D)+4;
            localparam integer DSR = (ds && W % 2 == 0) ? 2 : 1;
            localparam bit FR = (wi + g + r) % 2;
            wire [KW-1:0] k=KW'(r ? 3 : 2);
            wire [W-1:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
            ot_dp_clk_landing_cas #(.W(W),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(s),.STATUS_REG(s),.WFALL(f),.WREG(r),.FREG(FR),.DSREP(DSR),.NARROW(0)) u_gold (
                .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data[W-1:0]),.q(q0),.ready(rdy0),.fault(flt0));
            ot_dp_clk_landing_cas #(.W(W),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(s),.STATUS_REG(s),.WFALL(f),.WREG(r),.FREG(FR),.DSREP(DSR),.NARROW(1)) u_cand (
                .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data[W-1:0]),.q(q1),.ready(rdy1),.fault(flt1));
            `CHECK($sformatf("cas W=%0d D=%0d sreg=%0d wfall=%0d wreg=%0d freg=%0d dsrep=%0d",W,D,s,f,r,FR,DSR), W, q0, q1, rdy0, rdy1, flt0, flt1)
        end
    end
    localparam int CWS [2] = '{2, 33};
    for (genvar wi=0; wi<2; wi++) for (genvar kk=2; kk<4; kk++) begin: c
        localparam int W = CWS[wi];
        wire [W-1:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
        ot_dp_clk_landing_ca #(.W(W),.K(kk),.NARROW(0)) u_gold (.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.d(data[W-1:0]),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing_ca #(.W(W),.K(kk),.NARROW(1)) u_cand (.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.d(data[W-1:0]),.q(q1),.ready(rdy1),.fault(flt1));
        `CHECK($sformatf("ca W=%0d K=%0d",W,kk), W, q0, q1, rdy0, rdy1, flt0, flt1)
    end
    task automatic go(input integer t_extra);
        @(negedge fclk_r);t_rst_n=0;
        @(negedge clk);r_rst_n=0;
        repeat(12) @(negedge fclk_r);
        if(t_extra<=0) t_rst_n=1;
        repeat(1) @(negedge clk);
        r_rst_n=1;
        if(t_extra>0) begin repeat(t_extra) @(negedge fclk_r); t_rst_n=1; end
    endtask
    initial begin
        repeat(2) begin go(0); repeat(600) @(negedge clk); end
        go(0); repeat(300) @(negedge clk); @(negedge fclk_r); fen=0; repeat(2) @(negedge fclk_r); fen=1; repeat(300) @(negedge clk);
        go(0); repeat(300) @(negedge clk); @(negedge fclk_r); t_rst_n=0; repeat(5) @(negedge fclk_r); t_rst_n=1; repeat(300) @(negedge clk);
        go(8); repeat(300) @(negedge clk);
        go(64); repeat(400) @(negedge clk);
        if(fails!=0) $fatal(1,"NR_FAIL fails=%0d",fails);
        if(words<1000 || nz<500) $fatal(1,"NR_FAIL too few ready words (%0d, nonzero %0d): bench did not exercise the rings",words,nz);
        $display("NARROW_PASS phase=%0d shift=%0d ready_word_checks=%0d nonzero=%0d",phase,shift,words,nz);
        $finish;
    end
endmodule
