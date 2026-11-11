// GUARD-REG-1 ring bench (CLAND-RING-NEGEDGE, COORD 11-11 09:47).  Three ot_dp_clk_landing_cas rings on ONE stimulus:
//   gold = STATUS_REG 0 (the legacy ring the failing kv3_io_cor_v1 kit carries: oh -> ghi0/glo0 on the falling edge),
//   mid  = STATUS_REG 1 (STATUS-REG-1 form, guard compare still on a falling -> rising T/2 path),
//   cand = STATUS_REG 1 + GUARD_REG 1 (no logic on any half-cycle rclk path).
// Sweep: DEPTH 4/8, status copy on/off, WREG on/off, WFALL on/off, read offset K at the window centre and at BOTH window
// edges (K = 0 and K = DEPTH, where the opposite-edge guards really trip), receiver phase +PHASE (ps).
// Claims checked every rclk edge after the reader start:
//   (1) ring order: q identical on gold/mid/cand; the sender count in q[31:0] advances by exactly 1 per clk while ready;
//   (2) guards: r_glo_ok / r_ghi_ok of cand == gold == mid on EVERY edge, incl. fault epochs and window-edge K (0 added
//       cycles; the falling-edge sample instant, hence the (GUARD + 0.5) T window, is unchanged);
//   (3) cand vs mid: q, rv, lap_ok, guards, ready, fault identical every edge (GUARD_REG adds 0 cycles to STATUS_REG);
//   (4) cand vs gold: rv/lap_ok = gold one clk later (the declared STATUS_REG +1 status cycle); ready/fault identical on
//       healthy centre-K epochs, else cand fault/ready = gold now or gold one clk ago.
// Mutants that must FAIL: SR_GUARD (sample on the rising edge = the naive "move the negedge capture to posedge" fix),
// GR_OH (select with the wrong one-hot), GR_LATE (guards one clk late = the "+1 cycle" form).
module tb_guard_reg;
    timeunit 1ps; timeprecision 1fs;
    logic fclk=0, clk=0, t_rst_n=0, r_rst_n=0;
    logic [31:0] lfsr=32'h1234abcd, cnt=0;
    wire  [63:0] data={lfsr, cnt};
    integer phase=0, checks=0, epoch=0, fails=0, guard_trips=0, order_checks=0;
    logic healthy=1;
    always #416.5 fclk=~fclk;
    initial begin
        void'($value$plusargs("PHASE=%d",phase));
        #(phase);
        forever #416.5 clk=~clk;
    end
    // sender: one word per fclk, the count in the low half (word n carries n since the sender start)
    always @(negedge fclk) begin
        lfsr <= {lfsr[30:0], lfsr[31]^lfsr[21]^lfsr[1]^lfsr[0]};
        cnt  <= t_rst_n ? cnt + 1 : 0;
    end
    for(genvar g=0;g<2;g++) for(genvar c=0;c<2;c++) for(genvar r=0;r<2;r++) for(genvar f=0;f<2;f++) for(genvar e=0;e<3;e++) begin: m
        localparam integer D=4<<g;
        localparam integer KW=$clog2(D)+4;
        localparam integer KB= e==0 ? 2 : (e==1 ? 0 : D);   // window centre, low edge, high edge
        // WREG: the bind ties K + 1 for the registered start
        wire [KW-1:0] k=KW'(KB + (r ? 1 : 0));
        wire [63:0] q0,q1,q2; wire rdy0,rdy1,rdy2,flt0,flt1,flt2;
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(c),.WREG(r),.WFALL(f),.STATUS_REG(0)) u_gold (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data),.q(q0),.ready(rdy0),.fault(flt0));
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(c),.WREG(r),.WFALL(f),.STATUS_REG(1)) u_mid (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data),.q(q1),.ready(rdy1),.fault(flt1));
        ot_dp_clk_landing_cas #(.W(64),.DEPTH(D),.GUARD_HI(D),.CONTROL_STATUS_COPY(c),.WREG(r),.WFALL(f),.STATUS_REG(1),.GUARD_REG(1)) u_cand (
            .fclk(fclk),.t_rst_n(t_rst_n),.clk(clk),.rst_n(r_rst_n),.rst_xn(1'b1),.strap_k(k),.d(data),.q(q2),.ready(rdy2),.fault(flt2));
        integer ready_n=0, trips=0, faults=0, ordered=0;
        logic flt0_d=0, rdy0_d=0, rv0_d=0, lap0_d=1, rdy2_d=0;
        logic [31:0] q2_d=0;
        always @(posedge clk) begin
            #1;
            if(r_rst_n) begin
                // (1) order
                if(q0!==q2 || q1!==q2) begin $display("GR_MISMATCH q D=%0d c=%0d r=%0d f=%0d K=%0d phase=%0d epoch=%0d",D,c,r,f,KB,phase,epoch); fails=fails+1; end
                if(healthy && rdy2 && rdy2_d) begin
                    order_checks=order_checks+1; ordered=ordered+1;
                    if(q2[31:0]!==q2_d+1) begin $display("GR_ORDER D=%0d c=%0d r=%0d f=%0d K=%0d phase=%0d epoch=%0d %0d after %0d",D,c,r,f,KB,phase,epoch,q2[31:0],q2_d); fails=fails+1; end
                end
                // (2) guards, exact, every epoch
                if(u_gold.glo_ok!==u_cand.glo_ok || u_gold.ghi_ok!==u_cand.ghi_ok || u_mid.glo_ok!==u_cand.glo_ok || u_mid.ghi_ok!==u_cand.ghi_ok) begin
                    $display("GR_MISMATCH guard D=%0d c=%0d r=%0d f=%0d K=%0d phase=%0d epoch=%0d glo %b/%b/%b ghi %b/%b/%b",D,c,r,f,KB,phase,epoch,
                             u_gold.glo_ok,u_mid.glo_ok,u_cand.glo_ok,u_gold.ghi_ok,u_mid.ghi_ok,u_cand.ghi_ok); fails=fails+1; end
                if(!u_gold.glo_ok || !u_gold.ghi_ok) begin trips=trips+1; guard_trips=guard_trips+1; end
                // (3) cand == mid, every signal, every epoch
                if(u_mid.rv!==u_cand.rv || u_mid.lap_ok!==u_cand.lap_ok || rdy1!==rdy2 || flt1!==flt2) begin
                    $display("GR_MISMATCH mid D=%0d c=%0d r=%0d f=%0d K=%0d phase=%0d epoch=%0d rv %b/%b lap %b/%b rdy %b/%b flt %b/%b",D,c,r,f,KB,phase,epoch,
                             u_mid.rv,u_cand.rv,u_mid.lap_ok,u_cand.lap_ok,rdy1,rdy2,flt1,flt2); fails=fails+1; end
                // (4) cand vs gold: status +1 clk; ready/fault exact when healthy at the window centre, else within 1 clk
                if(u_cand.rv!==rv0_d || u_cand.lap_ok!==lap0_d) begin
                    $display("GR_MISMATCH status+1 D=%0d c=%0d r=%0d f=%0d K=%0d phase=%0d epoch=%0d rv %b/%b lap %b/%b",D,c,r,f,KB,phase,epoch,rv0_d,u_cand.rv,lap0_d,u_cand.lap_ok); fails=fails+1; end
                if(healthy && e==0) begin
                    if(rdy0!==rdy2 || flt0!==flt2) begin $display("GR_MISMATCH healthy D=%0d c=%0d r=%0d f=%0d phase=%0d epoch=%0d rdy %b/%b flt %b/%b",D,c,r,f,phase,epoch,rdy0,rdy2,flt0,flt2); fails=fails+1; end
                end else begin
                    if(!(flt2===flt0 || flt2===flt0_d) || !(rdy2===rdy0 || rdy2===rdy0_d)) begin
                        $display("GR_MISMATCH bound D=%0d c=%0d r=%0d f=%0d K=%0d phase=%0d epoch=%0d flt %b,%b/%b rdy %b,%b/%b",D,c,r,f,KB,phase,epoch,flt0,flt0_d,flt2,rdy0,rdy0_d,rdy2); fails=fails+1; end
                end
                if(rdy2) ready_n=ready_n+1;
                if(flt0) faults=faults+1;
                rv0_d=u_gold.rv; lap0_d=u_gold.lap_ok; flt0_d=flt0; rdy0_d=rdy0; rdy2_d=rdy2; q2_d=q2[31:0];
            end else begin rv0_d=0; lap0_d=1; flt0_d=0; rdy0_d=0; rdy2_d=0; end
        end
        final $display("GR_CASE D=%0d copy=%0d wreg=%0d wfall=%0d K=%0d phase=%0d ready_cycles=%0d ordered=%0d guard_trip_cycles=%0d gold_fault_cycles=%0d",
                       D,c,r,f,KB,phase,ready_n,ordered,trips,faults);
    end
    always @(posedge clk) if(r_rst_n) checks<=checks+1;
    task automatic go(input integer t_extra);
        @(negedge fclk);t_rst_n=0;
        @(negedge clk);r_rst_n=0;
        repeat(12) @(negedge fclk);
        if(t_extra<=0) t_rst_n=1;
        repeat(1) @(negedge clk);
        r_rst_n=1;
        if(t_extra>0) begin repeat(t_extra) @(negedge fclk); t_rst_n=1; end
    endtask
    initial begin
        for(epoch=0;epoch<3;epoch++) begin healthy=1; go(0); repeat(600) @(negedge clk); end
        // sender restarts under an armed reader
        epoch=10; healthy=0; go(0); repeat(300) @(negedge clk);
        @(negedge fclk); t_rst_n=0; repeat(5) @(negedge fclk); t_rst_n=1; repeat(300) @(negedge clk);
        // sender origin late by 1, 3, 8, 16, 64 counts (guard window / lap / tag verdicts)
        epoch=11; go(1); repeat(300) @(negedge clk);
        epoch=12; go(3); repeat(300) @(negedge clk);
        epoch=13; go(8); repeat(300) @(negedge clk);
        epoch=14; go(16); repeat(300) @(negedge clk);
        epoch=15; go(64); repeat(400) @(negedge clk);
        if(fails!=0) $fatal(1,"GR_FAIL fails=%0d",fails);
        if(order_checks==0 || guard_trips==0) $fatal(1,"GR_VACUOUS order_checks=%0d guard_trips=%0d",order_checks,guard_trips);
        $display("GUARD_REG_PASS phase=%0d checks=%0d order_checks=%0d guard_trip_cycles=%0d",phase,checks,order_checks,guard_trips);
        $finish;
    end
endmodule
