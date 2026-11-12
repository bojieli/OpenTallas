// CLAND-QREG-1 lock-step: every landing ring form with QREG 0 (gold) vs 1 (candidate) on one stimulus.  Declared
// change: q is the gold word stream exactly ONE clk later (+1 data cycle); ready and fault unchanged at every edge.
// Covered: ot_dp_clk_landing (WNEG 0/1, FREG 0/1) and ot_dp_clk_landing_cas (DEPTH 4/8, STATUS_REG 0/1, WFALL 0/1,
// WREG 0/1), receiver phases +PHASE, healthy + forwarded-clock slip + sender restart + origin-late epochs.
// Negative controls: OT_MESO_MUTANT_QREG_BYPASS (stage bypassed: 0 cycles) must fail; +SHIFT=0 / +SHIFT=2 (wrong
// declared latency) must fail.
module tb_qreg;
    timeunit 1ps; timeprecision 1fs;
    logic fclk_r=0, clk=0, t_rst_n=0, r_rst_n=0, fen=1;
    wire fclk = fclk_r & fen;
    logic [63:0] data=64'h123456789abcdef1;
    integer phase=0, shift=1, fails=0, words=0;
    always #416.5 fclk_r=~fclk_r;
    initial begin
        void'($value$plusargs("PHASE=%d",phase)); void'($value$plusargs("SHIFT=%d",shift));
        #(phase);
        forever #416.5 clk=~clk;
    end
    always @(negedge fclk_r) data <= {data[62:0],data[63]^data[62]^data[60]^data[59]};
    // gold q history: h[0] = gold q at this edge, h[k] = k edges ago
    `define CHECK(TAG, Q0, Q1, R0, R1, F0, F1) \
        logic [63:0] h0=0, h1=0, h2=0; logic hv1=0, hv2=0; \
        always @(posedge clk) begin #1; \
            if (r_rst_n) begin \
                if ((shift==0 ? 1'b1 : shift==1 ? hv1 : hv2) && Q1 !== (shift==0 ? Q0 : shift==1 ? h1 : h2)) begin \
                    $display("QR_MISMATCH q %s phase=%0d", TAG, phase); fails=fails+1; end \
                else if (R0) words=words+1; \
                if (R0 !== R1 || F0 !== F1) begin $display("QR_MISMATCH status %s phase=%0d rdy %b/%b flt %b/%b", TAG, phase, R0, R1, F0, F1); fails=fails+1; end \
                h2=h1; hv2=hv1; h1=Q0; hv1=1; \
            end else begin hv1=0; hv2=0; end \
        end
    for(genvar n=0;n<2;n++) for(genvar fr=0;fr<2;fr++) begin: p
        wire [63:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
        ot_dp_clk_landing #(.W(64),.WNEG(n),.FREG(fr),.QREG(0)) u_gold (.fclk(fclk),.clk(clk),.rst_n(r_rst_n),.d(data),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing #(.W(64),.WNEG(n),.FREG(fr),.QREG(1)) u_cand (.fclk(fclk),.clk(clk),.rst_n(r_rst_n),.d(data),.q(q1),.ready(rdy1),.fault(flt1));
        `CHECK($sformatf("plain wneg=%0d freg=%0d",n,fr), q0, q1, rdy0, rdy1, flt0, flt1)
    end
    for(genvar g=0;g<2;g++) for(genvar s=0;s<2;s++) for(genvar f=0;f<2;f++) for(genvar r=0;r<2;r++) begin: m
        localparam integer D=4<<g;
        localparam integer KW=$clog2(D)+4;
        wire [KW-1:0] k=KW'(r ? 3 : 2);
        wire [63:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(s),.STATUS_REG(s),.WFALL(f),.WREG(r),.QREG(0)) u_gold (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.strap_k(k),.d(data),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(s),.STATUS_REG(s),.WFALL(f),.WREG(r),.QREG(1)) u_cand (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.strap_k(k),.d(data),.q(q1),.ready(rdy1),.fault(flt1));
        `CHECK($sformatf("cas D=%0d sreg=%0d wfall=%0d wreg=%0d",D,s,f,r), q0, q1, rdy0, rdy1, flt0, flt1)
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
        if(fails!=0) $fatal(1,"QR_FAIL fails=%0d",fails);
        if(words<1000) $fatal(1,"QR_FAIL no ready words (%0d): bench did not exercise the rings",words);
        $display("QREG_PASS phase=%0d shift=%0d ready_word_checks=%0d",phase,shift,words);
        $finish;
    end
endmodule
