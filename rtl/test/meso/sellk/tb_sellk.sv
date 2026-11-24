// SELLK-1 ring bench (S81-ALLFIX-SVC SERDES-RING 11-24).  ot_dp_clk_landing_cas gold SELLK 0 vs cand SELLK 1 on ONE
// stimulus.  Sweep: DEPTH 4/8, DSREP 1/4 (one select or kept select copies), WREG on/off, WFALL on/off, read offset K at
// the window centre and both window edges, receiver phase +PHASE (ps).  Claim: q, ready, fault and the ring status
// (rv, lap_ok, glo_ok, ghi_ok) identical on EVERY rclk edge (the lockup copy adds 0 cycles), and the sender count in
// q[31:0] advances by exactly 1 per clk while ready.  Mutant that must FAIL: SELLK_POS (the copy on the rising edge =
// the naive "add a register" fix, one cycle late).
module tb_sellk;
    timeunit 1ps; timeprecision 1fs;
    logic fclk=0, clk=0, t_rst_n=0, r_rst_n=0;
    logic [31:0] lfsr=32'h1234abcd, cnt=0;
    wire  [63:0] data={lfsr, cnt};
    integer phase=0, fails=0, checks=0, order_checks=0;
    always #416.5 fclk=~fclk;
    initial begin
        void'($value$plusargs("PHASE=%d",phase));
        #(phase);
        forever #416.5 clk=~clk;
    end
    always @(negedge fclk) begin
        lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
        cnt  <= t_rst_n ? cnt + 1 : 0;
    end
    for(genvar g=0;g<2;g++) for(genvar s=0;s<2;s++) for(genvar r=0;r<2;r++) for(genvar f=0;f<2;f++) for(genvar e=0;e<3;e++) begin: m
        localparam integer D=4<<g;
        localparam integer DS= s ? 4 : 1;
        localparam integer KW=$clog2(D)+4;
        localparam integer KB= e==0 ? 2 : (e==1 ? 0 : D);
        wire [KW-1:0] k=KW'(KB + (r ? 1 : 0));
        wire [63:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.WREG(r),.WFALL(f),.DSREP(DS),.SELLK(0)) u_gold (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.WREG(r),.WFALL(f),.DSREP(DS),.SELLK(1)) u_cand (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data),.q(q1),.ready(rdy1),.fault(flt1));
        logic [31:0] q1_d=0; logic rdy1_d=0;
        always @(posedge clk) begin
            #1;
            if(r_rst_n) begin
                checks=checks+1;
                if(q0!==q1 || rdy0!==rdy1 || flt0!==flt1 || u_gold.rv!==u_cand.rv || u_gold.lap_ok!==u_cand.lap_ok ||
                   u_gold.glo_ok!==u_cand.glo_ok || u_gold.ghi_ok!==u_cand.ghi_ok) begin
                    if(fails<20) $display("SL_MISMATCH D=%0d DS=%0d r=%0d f=%0d K=%0d phase=%0d q %h/%h rdy %b/%b flt %b/%b",D,DS,r,f,KB,phase,q0,q1,rdy0,rdy1,flt0,flt1);
                    fails=fails+1; end
                if(KB==2 && rdy1 && rdy1_d) begin
                    order_checks=order_checks+1;
                    if(q1[31:0]!==q1_d+1) begin if(fails<20) $display("SL_ORDER D=%0d DS=%0d r=%0d f=%0d phase=%0d %0d after %0d",D,DS,r,f,phase,q1[31:0],q1_d); fails=fails+1; end
                end
                q1_d<=q1[31:0]; rdy1_d<=rdy1;
            end
        end
    end
    initial begin
        #5000; t_rst_n=1;
        #3000; r_rst_n=1;
        #(833*400);
        if(fails==0 && order_checks>0) $display("SELLK_PASS phase=%0d checks=%0d order=%0d", phase, checks, order_checks);
        else $display("SELLK_FAIL phase=%0d fails=%0d checks=%0d order=%0d", phase, fails, checks, order_checks);
        $finish;
    end
endmodule
