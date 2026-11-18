// RING-LITE-1 (KV-RING2-LIGHT 11-18) lock-step: every count-aligned landing ring form with LITE 0 (gold, the full ring
// with its monitor) vs LITE 1 (candidate, data path only) on one stimulus.  Declared change: none on q, 0 added cycles:
// q is identical at EVERY clk edge after the receiver start, in the window AND through forwarded-clock slip, sender
// restart and late sender start (the data path never depended on the monitor).  The lite status is checked as declared:
// fault = 0, ready = rst_n one clk later.
// Covered: ot_dp_clk_landing_cas at W = 1, 2, 3, 4, 7, 32, DEPTH 4/8, STATUS_REG+GUARD_REG 0/1, WFALL 0/1, WREG 0/1,
// FREG 0/1 on half, gold NARROW 0/1; ot_dp_clk_landing_ca at W = 2 / 4 with K = 2 / 3.  Receiver phase +PHASE.
// Negative controls: OT_MESO_CA_MUTANT_LITE (lite ring reads one slot late) must FAIL; +SHIFT=1 (compare against gold
// q one clk late, i.e. a wrongly declared +1 cycle) must FAIL.
module tb_lite;
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
    `define CHECK(TAG, WW, Q0, Q1, R0, R1, F1) \
        logic [WW-1:0] h1=0; logic hv1=0; logic rq=0; \
        always @(posedge clk) begin #1; \
            if (r_rst_n) begin \
                if ((shift==0 || hv1) && Q1 !== (shift==0 ? Q0 : h1)) begin \
                    $display("LT_MISMATCH q %s phase=%0d gold=%h cand=%h", TAG, phase, Q0, Q1); fails=fails+1; end \
                else if (R0) begin words=words+1; if (Q0 != 0) nz=nz+1; end \
                h1=Q0; hv1=1; \
            end else hv1=0; \
            if (F1 !== 1'b0 || (rq && r_rst_n && R1 !== 1'b1) || (!rq && !r_rst_n && R1 !== 1'b0)) begin \
                $display("LT_MISMATCH status %s phase=%0d rdy %b flt %b", TAG, phase, R1, F1); fails=fails+1; end \
            rq=r_rst_n; \
        end
    localparam int NW = 6;
    localparam int WS [NW] = '{1, 2, 3, 4, 7, 32};
    for (genvar wi=0; wi<NW; wi++) begin: w
        localparam int W = WS[wi];
        for(genvar g=0;g<2;g++) for(genvar s=0;s<2;s++) for(genvar f=0;f<2;f++) for(genvar r=0;r<2;r++) for(genvar n=0;n<2;n++) begin: m
            localparam integer D=4<<g;
            localparam integer KW=$clog2(D)+4;
            localparam bit FR = (wi + g + r) % 2;
            wire [KW-1:0] k=KW'(r ? 3 : 2);
            wire [W-1:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
            ot_dp_clk_landing_cas #(.W(W),.DEPTH(D),.GUARD_HI(D),.STATUS_REG(s),.GUARD_REG(s),.WFALL(f),.WREG(r),.FREG(FR),.NARROW(n),.LITE(0)) u_gold (
                .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data[W-1:0]),.q(q0),.ready(rdy0),.fault(flt0));
            ot_dp_clk_landing_cas #(.W(W),.DEPTH(D),.GUARD_HI(D),.STATUS_REG(s),.GUARD_REG(s),.WFALL(f),.WREG(r),.FREG(FR),.NARROW(n),.LITE(1)) u_cand (
                .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data[W-1:0]),.q(q1),.ready(rdy1),.fault(flt1));
            `CHECK($sformatf("cas W=%0d D=%0d sreg=%0d wfall=%0d wreg=%0d freg=%0d narrow=%0d",W,D,s,f,r,FR,n), W, q0, q1, rdy0, rdy1, flt1)
        end
    end
    localparam int CWS [2] = '{2, 4};
    for (genvar wi=0; wi<2; wi++) for (genvar kk=2; kk<4; kk++) begin: c
        localparam int W = CWS[wi];
        wire [W-1:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
        ot_dp_clk_landing_ca #(.W(W),.K(kk),.LITE(0)) u_gold (.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.d(data[W-1:0]),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing_ca #(.W(W),.K(kk),.LITE(1)) u_cand (.fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.d(data[W-1:0]),.q(q1),.ready(rdy1),.fault(flt1));
        `CHECK($sformatf("ca W=%0d K=%0d",W,kk), W, q0, q1, rdy0, rdy1, flt1)
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
        if(fails!=0) $fatal(1,"LT_FAIL fails=%0d",fails);
        if(words<1000 || nz<500) $fatal(1,"LT_FAIL too few ready words (%0d, nonzero %0d): bench did not exercise the rings",words,nz);
        $display("LITE_PASS phase=%0d shift=%0d ready_word_checks=%0d nonzero=%0d",phase,shift,words,nz);
        $finish;
    end
endmodule
