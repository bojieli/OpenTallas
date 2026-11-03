`timescale 1ns/1ps
`default_nettype none
// DIE-HBM-61/RTL-C3 RE-FORM 11-03: ot_hgi_coll_static_seq_ctl #(RXPRE=1) == origin/main ot_hgi_coll_static_seq_ctl
// (renamed *_old) on EVERY edge, all outputs, shift 0.  RX frames are legal (good CRC, slot, epoch, sequence) most of
// the time, with CRC / field corruption, missing / unexpected frames, random TX traffic and epoch restarts.
module tb_c3_seq_ctl_rxpre_eq;
    parameter integer SEED=11, NCYC=60000;
    localparam integer FW=561, PW=612;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, epoch_begin=0, abort_in=0, wr_v=0, wr_observed_v=0, rd_v=0, rx_expect_v=0, p_tx_up=1, p_rx_v=0;
    reg [1:0] abort_cause=0; reg [15:0] rd_seq=0, rx_expect_seq=0; reg [7:0] epoch=0;
    reg [5:0] wr_slot=0, rd_slot=0, rx_expect_slot=0; reg [560:0] q_data=0; reg [611:0] p_rx_flit=0;
    wire [FW+18:0] body; wire [31:0] crc;
    reg [FW+18:0] body_r;
    assign body = body_r;
    ot_qwen_crc_parallel #(.DW(FW+19),.CW(32)) u_gen(.d(body),.q(crc));
    wire n_tv, n_rv, n_ab, o_tv, o_rv, o_ab; wire [611:0] n_tf, o_tf; wire [560:0] n_rf, o_rf; wire [10:0] n_fc, o_fc;
`define C3_SEQ(M,N,TV,TF,RV,RF,AB,FC) M N(.clk(clk),.rst_n(rst_n),.epoch_begin(epoch_begin),.abort_in(abort_in), \
        .abort_cause(abort_cause),.rd_seq(rd_seq),.rx_expect_seq(rx_expect_seq),.epoch(epoch),.wr_v(wr_v), \
        .wr_observed_v(wr_observed_v),.wr_slot(wr_slot),.q_data(q_data),.rd_v(rd_v),.rd_slot(rd_slot), \
        .rx_expect_v(rx_expect_v),.rx_expect_slot(rx_expect_slot),.p_tx_up(p_tx_up),.p_tx_v(TV),.p_tx_flit(TF), \
        .p_rx_v(p_rx_v),.p_rx_flit(p_rx_flit),.rx_v(RV),.rx_flit(RF),.epoch_abort(AB),.fault_cause(FC));
    `C3_SEQ(ot_hgi_coll_static_seq_ctl #(.RXPRE(1)), dut, n_tv, n_tf, n_rv, n_rf, n_ab, n_fc)
    `C3_SEQ(ot_hgi_coll_static_seq_ctl_old, ref_c, o_tv, o_tf, o_rv, o_rf, o_ab, o_fc)
    integer errors=0, checked=0, rxv=0, txv=0, crcf=0, seed, cyc=0, k;
    always @(negedge clk) if (rst_n) begin
        checked=checked+1;
        if ({n_tv,n_tf,n_rv,n_rf,n_ab,n_fc} !== {o_tv,o_tf,o_rv,o_rf,o_ab,o_fc}) begin
            errors=errors+1; if (errors<5) $display("MISMATCH t=%0t tv %b/%b rv %b/%b ab %b/%b fc %h/%h",$time,n_tv,o_tv,n_rv,o_rv,n_ab,o_ab,n_fc,o_fc);
        end
        if (o_rv) rxv=rxv+1; if (o_tv) txv=txv+1; if (ref_c.crc_bad) crcf=crcf+1;
    end
    initial begin
        seed=SEED; repeat(3) @(posedge clk); #1 rst_n=1;
        while (cyc<NCYC) begin
            @(posedge clk); #1; cyc=cyc+1;
            k=$random(seed);
            epoch_begin = ((k&31)==0) || (o_ab && ((k&3)==0));
            if (epoch_begin) epoch = $random(seed);
            abort_in = (($random(seed)&1023)==0); abort_cause = (($random(seed)&1023)==0) ? $random(seed) : 0;
            p_tx_up = (($random(seed)&255)!=0);
            // TX side: write then read the same slot a few edges later (mostly legal), random otherwise
            wr_v = (($random(seed)&3)==0); wr_observed_v = (($random(seed)&127)!=0); wr_slot = $random(seed)&7;
            rd_v = (($random(seed)&3)==0); rd_slot = $random(seed)&7; rd_seq = {$random(seed)} & 16'h0007;
            q_data = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                      $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                      $random(seed),$random(seed),$random(seed),$random(seed)};
            if (($random(seed)&1)==0) q_data[560:545] = rd_seq;   // tx sequence sometimes matches the 3-edge-old one
            // RX side: expected frames, legal (CRC / slot / epoch / sequence) with occasional corruption
            rx_expect_v = (($random(seed)&1)==0); rx_expect_slot = $random(seed); rx_expect_seq = $random(seed);
            p_rx_v = (($random(seed)&63)==0) ? !rx_expect_v : rx_expect_v;
            body_r = {$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                      $random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),$random(seed),
                      $random(seed),$random(seed),$random(seed),$random(seed),$random(seed)};
            if (($random(seed)&15)!=0) begin
                body_r[FW+18]=1'b0; body_r[FW+17-:8]=epoch; body_r[FW+9]=1'b0; body_r[FW+8]=1'b1;
                body_r[FW+7:FW]={2'b00,rx_expect_slot}; body_r[560:545]=rx_expect_seq;
            end
            #1;
            p_rx_flit = {crc, body_r};
            k=$random(seed)&15;
            if (k==0) p_rx_flit[PW-1-($random(seed)&31)] = ~p_rx_flit[PW-1-($random(seed)&31)];   // CRC field bit
            else if (k==1) p_rx_flit[{$random(seed)}%(FW+19)] = ~p_rx_flit[{$random(seed)}%(FW+19)]; // body bit
        end
        $display("C3_SEQ_EQ %s errors=%0d checks=%0d rx_v=%0d tx_v=%0d crc_bad_edges=%0d",
            (errors==0 && rxv>100 && crcf>100) ? "PASS" : "FAIL", errors, checked, rxv, txv, crcf);
        $finish;
    end
endmodule
`default_nettype wire
