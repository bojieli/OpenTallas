// S81-LEPENH2 (10-20): tb_stimulus of the lepe_nh landed-parent lockstep (tools/landed_parent/specs/dsdv_slice_lepe_nh.json).
// Included at module level of tb_ot_s81sl_slice_lepe_nh_x_lp (lp.py scripted mode: the compare runs every negedge after warm).
// Why: the random-word bench never trained the UCIe lanes (link-up needs ~8k cycles and CRC-valid peer words), so the
// lep -> slice landing (lri) carried no beat and MUT 1/2/4 passed (08f4a85fd).  Here the FLAT reference's two lanes are
// cross-wired through two ot_pdie_ucie models (lane 0 tx -> lane 1 rx, lane 1 tx -> lane 0 rx); the same rx words drive
// both DUTs (fi_rx0/1), so the landed parent sees exactly the flat parent's line.  After link-up, 200 CTL line beats
// (kind CTL, slice mask 0, hops 3; the tb_s81sl_slice_lep beat) enter ri_w: ring stop -> ro_e -> landing lro -> lep ->
// lane tx -> loop -> lane rx -> lep -> landing lri -> ri_e -> ro_w.  Both 1104-b landings carry traffic; the bench is
// marked FAIL (vacuous) unless line beats reach ro_w.  Statics as tb_static: sid 4'd14, ch_b 1'b1 (die strap).
wire [511:0] lb_r0, lb_r1; wire [1:0] lb_s0, lb_s1; wire [512:0] lb_p0, lb_p1; wire lb_t0, lb_t1;
ot_pdie_ucie #(.PMA_LAT(2)) u_lb0 (.clk(clk), .rst(rst), .tx(fo_tx0), .rx(lb_r0), .st(lb_s0), .pma_tx(lb_p0), .pma_tck(lb_t0),
    .pma_rx(lb_p1), .pma_rck(lb_t1));
ot_pdie_ucie #(.PMA_LAT(5)) u_lb1 (.clk(clk), .rst(rst), .tx(fo_tx1), .rx(lb_r1), .st(lb_s1), .pma_tx(lb_p1), .pma_tck(lb_t1),
    .pma_rx(lb_p0), .pma_rck(lb_t0));
always @* begin fi_rx0 = {lb_s0, lb_r0}; fi_rx1 = {lb_s1, lb_r1}; end
function automatic [1103:0] lb_beat(input [3:0] src);
    integer i; reg [1103:0] b;
    begin
        for (i = 0; i < 34; i = i + 1) b[i * 32 +: 32] = $urandom; b[1103:1088] = $urandom;
        b[0] = 1'b1; b[3:1] = 3'd0; b[8:4] = 5'd3; b[12:9] = src; b[21 +: 16] = 16'd0;   // CTL, hops 3, mask 0
        lb_beat = b;
    end
endfunction
integer lb_n = 0, lb_ro = 0, lb_tx = 0;
always @(posedge clk) begin
    if (fo_ro_w[0]) lb_ro = lb_ro + 1;
    if (fo_tx0 != 512'd0 || fo_tx1 != 512'd0) lb_tx = lb_tx + 1;
end
initial begin
    fi_sid = 4'd14; fi_ch_b = 1'b1; fi_ri_w = 1104'd0; fi_vi = 276'd0; fi_bi = 1104'd0; fi_rt = 560'd0;
    repeat (16) @(negedge clk);
    rst = 1'b1;
    repeat (10000) @(negedge clk);
    while (lb_n < 200) begin
        @(negedge clk); fi_ri_w = 1104'd0;
        if (($urandom % 100) < 50) begin fi_ri_w = lb_beat(4'd9); lb_n = lb_n + 1; end
    end
    @(negedge clk); fi_ri_w = 1104'd0;
    repeat (3000) @(negedge clk);
    $display("LB_STATS beats_in=%0d ro_w_beats=%0d tx_nonzero_cycles=%0d", lb_n, lb_ro, lb_tx);
    if (lb_ro == 0) begin bad = bad + 1; $display("LB_VACUOUS no line beat reached ro_w: the lri landing carried no traffic"); end
    lp_finish("ucie loopback lane0<->lane1, 200 CTL beats");
end
