`timescale 1ns/1ps
module tb_s81ph_gbx_pipeline;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, f_tx_v=0, r_tx_v=0, beat_rx_v=0;
    reg [594:0] f_tx=0;
    reg [52:0] r_tx=0;
    reg [511:0] beat_rx=0;
    wire [511:0] b0,b1,b2;
    wire v0,v1,v2,rv0,rv1,rv2,l0,l1,l2,e0,e1,e2;
    wire [594:0] f0,f1,f2;
    wire [52:0] r0,r1,r2;
    ot_s81ph_link_gbx a(.clk, .rst_n, .f_tx_v, .f_tx, .r_tx_v, .r_tx,
        .beat_rx_v,.beat_rx,.beat_tx(b0),.f_rx_v(v0),.f_rx(f0),.r_rx_v(rv0),.r_rx(r0),.locked(l0),.fault(e0));
    ot_s81ph_link_gbx_pipeline #(.PIPE_TX(1)) b(.clk, .rst_n, .f_tx_v, .f_tx, .r_tx_v, .r_tx,
        .beat_rx_v,.beat_rx,.beat_tx(b1),.f_rx_v(v1),.f_rx(f1),.r_rx_v(rv1),.r_rx(r1),.locked(l1),.fault(e1));
    ot_s81ph_link_gbx_pipeline c(.clk, .rst_n, .f_tx_v, .f_tx, .r_tx_v, .r_tx,
        .beat_rx_v,.beat_rx,.beat_tx(b2),.f_rx_v(v2),.f_rx(f2),.r_rx_v(rv2),.r_rx(r2),.locked(l2),.fault(e2));
    reg [511:0] history0=0, history1=0;
    wire [511:0] expected = history1;
    always @(posedge clk or negedge rst_n) begin
        if(!rst_n) begin history0<=0; history1<=0; end
        else begin history0<=b0; history1<=history0; end
    end
    integer takes=0,bypass=0,overflow=0,idles=0,locks=0,frames=0,empty=0,full=0;
    integer i,j; reg [31:0] rng=32'h42feed01;
    function automatic [31:0] rnd();
        rng=rng ^ (rng<<13); rng=rng ^ (rng>>17); rng=rng ^ (rng<<5); return rng;
    endfunction
    initial begin
        repeat(3) @(negedge clk);
        for(i=0;i<24000;i=i+1) begin
            rst_n = !(i==0 || i==8000 || i==16000);
            // Paced traffic and empty intervals, then deliberate overflow.
            f_tx_v = (i%8000 < 5000) ? ((i%4)!=0 && i%200<160) : (rnd()%4 != 0);
            for(j=0;j<19;j=j+1) f_tx = (f_tx << 32) | 595'(rnd());
            r_tx={rnd(),rnd()}; r_tx_v=rnd()%2;
            beat_rx=b0; beat_rx_v=1;
            // After a clean lock interval, exercise dropped/false markers.
            if(i%8000>6000) begin
                beat_rx_v=rnd()%8!=0;
                if(rnd()%23==0) beat_rx[0]=~beat_rx[0];
            end
            if(rst_n) begin
                takes+=a.take; bypass+=(a.take && f_tx_v && a.st == b.next_sh);
                overflow+=(f_tx_v && a.sn==4 && !a.take);
                idles+=a.idle_now; empty+=(a.sn==0); full+=(a.sn==4);
            end
            @(posedge clk); #1;
            if({expected,v0,f0,rv0,r0,l0,e0} !== {b1,v1,f1,rv1,r1,l1,e1})
                $fatal(1,"PIPE mismatch cycle %0d",i);
            if({b0,v0,f0,rv0,r0,l0,e0} !== {b2,v2,f2,rv2,r2,l2,e2})
                $fatal(1,"DEFAULT mismatch cycle %0d",i);
            locks+=l0; frames+=v0;
            @(negedge clk);
        end
        if(!takes || !bypass || !overflow || !idles || !locks || !frames || !empty || !full)
            $fatal(1,"missing coverage");
        $display("PASS cycles=24000 takes=%0d bypass=%0d overflow=%0d idles=%0d locked_cycles=%0d frames=%0d empty=%0d full=%0d",takes,bypass,overflow,idles,locks,frames,empty,full);
        $finish;
    end
endmodule
