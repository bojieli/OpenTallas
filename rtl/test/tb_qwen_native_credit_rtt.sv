`timescale 1ns/1ps
// Minimum native SQ credit mechanism: retained PIPE0 channel and actual TAP0
// stations, with a fastest legal consumer. No collective arithmetic or die array.
// NF is the count of physical forward relay stations. Each station captures
// data/valid once and credit twice; this verifies that distinction in real RTL.
module tb_qwen_native_credit_rtt;
    parameter integer NF=1, WORDS=32, EARLY_RST=0;
    reg ck=0, ckd=0, rst_n=0, go=0;
    always #0.416667 ck=~ck;
    always #0.555556 ckd=~ckd;
    reg iv=0; reg [545:0] id=0;
    wire [546:0] forward [0:NF];
    wire credit [0:NF];
    assign forward[0]={iv,id};
    genvar j;
    generate for(j=0;j<NF;j=j+1) begin:g_relay
        ot_qwen_die_station #(.DW(547),.TAP(0)) station(
            .clk(ckd),.rst_n(rst_n),.a_d(forward[j]),.a_r(credit[j]),
            .b_d(forward[j+1]),.b_r(credit[j+1]),.t_d(),.t_r(1'b1),.c_d(),.c_r(1'b1));
    end endgenerate
    wire ov, cv, fck, fckd; wire [545:0] od; wire [515:0] cd;
    reg ocr=0, cv_in=0, ccr=0; reg [515:0] cd_in=0;
    ot_qwen_die_coll_xfifo #(.PIPE(0)) dut(
        .ck(ck),.ckd(ckd),.rst_n(rst_n),
        .i_seq_coll_v(forward[NF][546]),.i_seq_coll(forward[NF][545:0]),.i_seq_coll_cr(credit[NF]),
        .o_seq_coll_v(ov),.o_seq_coll(od),.o_seq_coll_cr(ocr),
        .i_coll_seq_v(cv_in),.i_coll_seq(cd_in),.o_coll_seq_v(cv),.o_coll_seq(cd),
        .o_coll_seq_cr(ccr),.fault_ck(fck),.fault_ckd(fckd));
    integer cyc=0, sent=0, recv=0, returned=0, credits=4, bad=0;
    integer first_send=-1, first_credit=-1, last_send=-1;
    // The same edge sees a launch and its credit debit; no hidden sender pipeline.
    always @(posedge ckd) begin
        cyc=cyc+1;
        // A finite credit-respecting experiment cannot require more than one
        // full relay RTT plus 100 local cycles per word; detect a deadlock.
        if(cyc>(3*NF+100)*WORDS+NF+100)
            $fatal(1,"credit deadlock sent=%0d recv=%0d returned=%0d credits=%0d first_rtt=%0d faults=%b%b",sent,recv,returned,credits,first_credit-first_send,fck,fckd);
        if(go) begin
            if(iv) begin
                if(first_send<0) first_send=cyc;
                last_send=cyc; sent=sent+1;
            end
            if(credit[0]) begin
                if(first_credit<0) first_credit=cyc;
                returned=returned+1; credits=credits+1;
            end
            if(sent<WORDS && credits>0) begin
                iv<=1; id<=sent; credits=credits-1;
            end else iv<=0;
        end
        ccr<=cv;
    end
    // Minimum response: consume one word each cycle, echo a reduce result to
    // release its reservation. All words use mode=0 (all-reduce, one result).
    always @(posedge ck) begin
        ocr<=ov; cv_in<=ov; cd_in<=od[515:0];
        if(go && ov) begin
            if(od !== recv) bad=bad+1;
            recv=recv+1;
        end
    end
    initial begin
        // Stations have no data reset: hold the channel in reset until invalid
        // has crossed every station. This is a required reset-release contract,
        // not evidence that production wiring already implements it.
        repeat(EARLY_RST ? 10 : NF+20) @(negedge ckd); rst_n=1;
        repeat(EARLY_RST ? NF+20 : 20) @(negedge ckd); go=1;
        wait(returned==WORDS);
        repeat(20) @(negedge ckd);
        if(sent!=WORDS || recv!=WORDS || bad!=0 || fck || fckd)
            $fatal(1,"native credit mismatch sent=%0d recv=%0d bad=%0d faults=%b%b",sent,recv,bad,fck,fckd);
        $display("PASS native_credit_rtt relays=%0d words=%0d first_rtt_ckd=%0d launch_window_ckd=%0d returned=%0d",NF,WORDS,first_credit-first_send,last_send-first_send+1,returned);
        $finish;
    end
endmodule
