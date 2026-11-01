`timescale 1ns/1ps
// KV-FN-4 unit test (tools/qwen_layerbench/kv_dieslice/run_kvfn4_witness.sh): the far end's program witness of
// kvs_compute_end.sv against the KV die's own receiver.  KV qkd_program_auth_tx sends BEGIN then AUTH (epoch 0b0b, the
// boot image digest) in the compute auth slot -> compute qfd_program_auth_rx -> install model (commit one edge after the
// AUTH, cap = CAP) -> qfd_program_witness_tx in the witness slot -> KV qkd_program_witness_rx with the KV boot image's
// target-0 footer 0x5850463100001046.  MODE 0 (as kvs_compute_end): commit_v + installed_valid, no fault.  MODE 1
// (the old placeholder {18'h2a5a5, 2'd3, 528'h717}): no commit (the symptom).  MODE 2 (cap 0 vs footer cap 1): no
// commit, fault.  Prints UT_KVFN4 PASS/FAIL.
module tb_kvfn4_witness;
    parameter integer MODE = 0;
    reg ck = 0; always #1 ck = ~ck;
    reg rst_n = 0;
    // KV side AUTH TX
    reg send = 0; reg [1:0] stype = 0; reg bv = 0, av = 0;
    wire k_tv, k_to, k_af; wire [547:0] k_rec;
    qkd_program_auth_tx u_ktx(.ck(ck), .rst_n(rst_n), .send_slot(send), .send_type(stype), .begin_v(bv), .begin_epoch(16'h0b0b),
        .expected_pw(11'd1024), .expected_dw(4'd8), .auth_v(av), .auth_epoch(16'h0b0b), .auth_digest(64'h514bb0b28004c8e8),
        .tx_v(k_tv), .tx_observed_v(k_to), .tx_record(k_rec), .fault(k_af));
    // compute side (same logic as kvs_compute_end.sv KV-FN-4 block)
    reg c_auth = 0, wslot = 0; reg wit_cap = (MODE == 2) ? 0 : 1;
    wire w_bv, w_av, w_af, w_wv, w_wo, w_wf; wire [15:0] w_be, w_ae; wire [10:0] w_pw; wire [3:0] w_dw; wire [63:0] w_ad;
    wire [547:0] w_rec;
    qfd_program_auth_rx u_wauth (.ck(ck), .rst_n(rst_n), .receive_slot(c_auth), .rx_v(k_to && c_auth), .rx_record(k_rec),
        .begin_v(w_bv), .begin_epoch(w_be), .expected_pw(w_pw), .expected_dw(w_dw),
        .auth_v(w_av), .auth_epoch(w_ae), .auth_digest(w_ad), .fault(w_af));
    reg w_ready = 0, w_commit = 0; reg [15:0] w_ep = 0; reg [63:0] w_dg = 0;
    always @(posedge ck) begin
        w_commit <= 0;
        if (!rst_n || w_bv) w_ready <= 0;
        else if (w_av && !w_af) begin w_ready <= 1; w_ep <= w_ae; w_dg <= w_ad; end
        w_commit <= w_av && !w_af && !w_bv;
    end
    qfd_program_witness_tx u_wtx (.ck(ck), .rst_n(rst_n), .send_slot(wslot), .commit_v(w_commit),
        .program_ready(w_ready), .installed_fusedcap(w_ready & wit_cap), .program_fault(w_af),
        .program_epoch(w_ep), .program_digest(w_dg), .tx_v(w_wv), .tx_observed_v(w_wo), .tx_record(w_rec), .fault(w_wf));
    reg wd = 0; always @(posedge ck) wd <= wslot;
    wire [547:0] wrec = (MODE == 1) ? (wd ? {18'h2a5a5, 2'd3, 528'h717} : 548'd0) : w_rec;
    wire wobs = (MODE == 1) ? wd : w_wo;
    // KV side witness RX (receive slot = the edge the record is presented)
    wire cv, iv, cap, kf; wire [15:0] ce; wire [63:0] cd;
    qkd_program_witness_rx u_krx(.ck(ck), .rst_n(rst_n), .program_begin_v(bv), .receive_slot(wobs), .rx_v(wobs), .rx_record(wrec),
        .expected_epoch(16'h0b0b), .expected_digest(64'h514bb0b28004c8e8), .authorized_footer_valid(1'b1),
        .authorized_footer(64'h5850463100001046), .program_commit_v(cv), .program_commit_epoch(ce), .program_commit_digest(cd),
        .program_installed_valid(iv), .installed_fusedcap(cap), .fault(kf));
    integer ncommit = 0; always @(posedge ck) if (cv) ncommit <= ncommit + 1;
    task tick(input integer n); repeat (n) @(posedge ck); #0.1; endtask
    initial begin
        tick(3); rst_n = 1; tick(2);
        wslot = 1; tick(1); wslot = 0; tick(3);                 // a witness slot before any AUTH: not-ready witness
        bv = 1; tick(1); bv = 0; tick(1);
        send = 1; stype = 1; tick(1); send = 0; c_auth = 1; tick(1); c_auth = 0;   // BEGIN record (KV TX register -> compute auth slot)
        tick(3);
        av = 1; tick(1); av = 0; tick(1);
        send = 1; stype = 2; tick(1); send = 0; c_auth = 1; tick(1); c_auth = 0; tick(4);   // AUTH record
        wslot = 1; tick(1); wslot = 0; tick(4);                 // admission witness slot
        $display("UT_KVFN4 MODE %0d k_af %0d w_af %0d w_wf %0d kv_fault %0d commits %0d installed %0d cap %0d epoch %h digest %h",
                 MODE, k_af, w_af, w_wf, kf, ncommit, iv, cap, ce, cd);
        if (MODE == 0) $display("UT_KVFN4 %s", (!k_af && !w_af && !w_wf && !kf && ncommit == 1 && iv && cap && ce == 16'h0b0b && cd == 64'h514bb0b28004c8e8) ? "PASS" : "FAIL");
        else $display("UT_KVFN4 %s", (ncommit == 0 && !iv) ? "PASS" : "FAIL");
        $finish;
    end
endmodule
