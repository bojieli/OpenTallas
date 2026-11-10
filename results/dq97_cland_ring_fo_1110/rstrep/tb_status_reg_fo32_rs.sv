// DIE-QC-97 (d): cand also RSTREP 2 (rst_xn = equal copies of rst_n: oh + the read-select chunk group)
// DIE-QC-97: sender inputs (data, t_rst_n) change 208 ps after the falling fclk edge, away from both writer edges
// (the stock bench changes them ON the falling edge, a simulator race once gold and cand differ in structure).
// DIE-QC-97 combined form (cand = clock.landing_ring_fanout_max 32 + landing_ring_status_reg: DSREP 2, WRITE_CHUNK 32 on WREG rings, STATUS_REG 1)
// STATUS-REG-1 lock-step: ot_dp_clk_landing_cas STATUS_REG 0 vs 1 on the same stimulus, over DEPTH 4/8, status copy on/off,
// WREG on/off, WFALL on/off and receiver phases (+PHASE, ps).
// Healthy epochs: q and ready identical every clk edge, fault 0 on both, ring words really flow.
// Fault epochs (sender restarted while armed, sender origin off by whole laps): a gold fault appears on the candidate
// 0 or 1 clk later, a candidate fault never appears without gold within that bound.
module tb_status_reg;
    timeunit 1ps; timeprecision 1fs;
    logic fclk=0, clk=0, t_rst_n=0, r_rst_n=0;
    logic [63:0] data=64'h123456789abcdef1;
    integer phase=0, checks=0, epoch=0, fails=0;
    logic healthy=1;
    always #416.5 fclk=~fclk;
    initial begin
        void'($value$plusargs("PHASE=%d",phase));
        #(phase);
        forever #416.5 clk=~clk;
    end
    always @(negedge fclk) data <= #208 {data[62:0],data[63]^data[62]^data[60]^data[59]};
    for(genvar g=0;g<2;g++) for(genvar c=0;c<2;c++) for(genvar r=0;r<2;r++) for(genvar f=0;f<2;f++) begin: m
        localparam integer D=4<<g;
        localparam integer KW=$clog2(D)+4;
        // WREG: the bind ties K + 1 for the registered start
        wire [KW-1:0] k=KW'(r ? 3 : 2);
        wire [63:0] q0,q1; wire rdy0,rdy1,flt0,flt1;
        // written so the WFALL writer gets the same word stream on both instances
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(c),.WREG(r),.WFALL(f),.STATUS_REG(0)) u_gold (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.strap_k(k),.d(data),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(c),.WREG(r),.WFALL(f),.STATUS_REG(1),.DSREP(r ? 2 : 1),.WRITE_CHUNK(r ? 32 : 64),.RSTREP(2)) u_cand (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn({2{r_rst_n}}),.strap_k(k),.d(data),.q(q1),.ready(rdy1),.fault(flt1));
        integer ready_n=0, words=0, gold_only=0, cand_only=0, faults_seen=0;
        logic flt0_d=0, rv0_d=0, lap0_d=1;
        // ring level, every epoch incl. faults: guard samples identical; rv/lap = gold of one clk ago
        always @(posedge clk) begin
            #1;
            if(r_rst_n) begin
                if(u_gold.glo_ok!==u_cand.glo_ok || u_gold.ghi_ok!==u_cand.ghi_ok) begin
                    $display("SR_MISMATCH guard D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d glo %b/%b ghi %b/%b",D,c,r,f,phase,epoch,u_gold.glo_ok,u_cand.glo_ok,u_gold.ghi_ok,u_cand.ghi_ok); fails=fails+1; end
                if(u_cand.rv!==rv0_d || u_cand.lap_ok!==lap0_d) begin
                    $display("SR_MISMATCH delay D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d rv %b/%b lap %b/%b",D,c,r,f,phase,epoch,rv0_d,u_cand.rv,lap0_d,u_cand.lap_ok); fails=fails+1; end
                rv0_d=u_gold.rv; lap0_d=u_gold.lap_ok;
            end else begin rv0_d=0; lap0_d=1; end
        end
        always @(posedge clk) begin
            #1;
            if(r_rst_n) begin
                if(rdy0) ready_n=ready_n+1;
                if(q0===q1) words=words+1;
                if(q0!==q1) begin $display("SR_MISMATCH q D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d",D,c,r,f,phase,epoch); fails=fails+1; end
                if(healthy && rdy0!==rdy1) begin $display("SR_MISMATCH ready D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d %b/%b",D,c,r,f,phase,epoch,rdy0,rdy1); fails=fails+1; end
                if(healthy && (flt0!==flt1)) begin $display("SR_MISMATCH fault-healthy D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d %b/%b",D,c,r,f,phase,epoch,flt0,flt1); fails=fails+1; end
                // bound: candidate is gold, or gold of one clk ago
                if(!healthy && !(flt1===flt0 || flt1===flt0_d)) begin $display("SR_MISMATCH fault-bound D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d gold=%b gold_d=%b cand=%b",D,c,r,f,phase,epoch,flt0,flt0_d,flt1); fails=fails+1; end
                if(!healthy && flt0) faults_seen=faults_seen+1;
                flt0_d=flt0;
            end else flt0_d=0;
        end
        final $display("SR_CASE D=%0d copy=%0d wreg=%0d wfall=%0d phase=%0d ready_cycles=%0d equal_words=%0d fault_cycles=%0d",D,c,r,f,phase,ready_n,words,faults_seen);
    end
    always @(posedge clk) if(r_rst_n) checks<=checks+1;
    task automatic go(input integer t_extra);
        @(negedge fclk); #208 t_rst_n=0;
        @(negedge clk);r_rst_n=0;
        repeat(12) @(negedge fclk);
        if(t_extra<=0) begin #208 t_rst_n=1; end
        repeat(1) @(negedge clk);
        r_rst_n=1;
        if(t_extra>0) begin repeat(t_extra) @(negedge fclk); #208 t_rst_n=1; end
    endtask
    initial begin
        for(epoch=0;epoch<3;epoch++) begin healthy=1; go(0); repeat(600) @(negedge clk); end
        // sender restarts under an armed reader
        epoch=10; healthy=0; go(0); repeat(300) @(negedge clk);
        @(negedge fclk); #208 t_rst_n=0; repeat(5) @(negedge fclk); #208 t_rst_n=1; repeat(300) @(negedge clk);
        // sender origin late by one and by two rings of eight (tag/lap verdict)
        epoch=11; go(8); repeat(300) @(negedge clk);
        epoch=12; go(16); repeat(300) @(negedge clk);
        epoch=13; go(64); repeat(400) @(negedge clk);
        if(fails!=0) $fatal(1,"SR_FAIL fails=%0d",fails);
        $display("STATUS_REG_PASS phase=%0d checks=%0d",phase,checks);
        $finish;
    end
endmodule
