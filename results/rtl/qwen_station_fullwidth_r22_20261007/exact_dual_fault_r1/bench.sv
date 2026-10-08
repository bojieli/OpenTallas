
module tb;
    parameter ENABLE=1,TAP=1,SPLIT=1,NEG=0;
    reg clk=0,rst_n=0,go=0,ready=0;
    reg[378:0] word=0; reg[127:0] xl=0;
    reg bf=0,tf=0,cf=0;
    wire tgo; wire[378:0] tbword; wire[127:0] tx;
    source_cut producer(clk,rst_n,go,ready,word,xl,tgo,tbword,tx);
    wire[507:0] src={tx,tgo,tbword};
    reg[507:0] prevsrc=0;
    always @(posedge clk) prevsrc<=src;
    wire[507:0] changed=(NEG==1) ? (src ^ (508'b1 << 337)) :
       (NEG==2) ? {prevsrc[507:380],src[379:0]} :
       (NEG==3) ? {src[507:380],prevsrc[379],src[378:0]} : src;
    wire[507:0] b;
    wire[(TAP?508:1)-1:0] t;
    wire[(SPLIT?508:1)-1:0] c;
    wire af,afn;
    ot_qwen_die_fullwidth_station_r22 #(.ENABLE_FULLWIDTH(ENABLE),.TAP(TAP),.SPLIT(SPLIT)) station
       (clk,rst_n,changed,b,t,c,bf,(NEG==4)?1'b0:tf,cf,af,~bf,(NEG==4)?1'b1:(NEG==6)?tf:~tf,~cf,afn);   // NEG 6: t rail pair not complementary -> fault
    wire[507:0] expected;
    ot_hdc_delay #(.W(508),.D(ENABLE)) reference(clk,rst_n,src,expected);
    wire[507:0] got,refgot;
    sink_cut tile(clk,rst_n,b[379],b[378:0],b[507:380],got);
    sink_cut ref_tile(clk,rst_n,expected[379],expected[378:0],expected[507:380],refgot);
    wire fault_expected;
    ot_hdc_delay #(.W(1),.D(ENABLE?2:0),.RESET(1)) fault_ref
       (clk,rst_n,bf|(TAP&&tf)|(SPLIT&&cf),fault_expected);
    reg af_prev=0;
    always @(posedge clk) af_prev<=af;
    integer n,k,bad=0,checked=0,accepted=0,seen=0; integer seed=9831;
    always #5 clk=~clk;
    initial begin
        repeat(5) @(negedge clk);
        rst_n=1;
        for(n=0;n<2100;n=n+1) begin
            @(negedge clk);
            if(n>8) begin
                checked=checked+1;
                if(b !== expected || (TAP && t !== expected) || (SPLIT && c !== expected)) bad=bad+1;
                if(got !== refgot) bad=bad+1;
                if(((NEG==5)?af_prev:(af | ~afn)) !== fault_expected) bad=bad+1;
            end
            if(got[379]) seen=seen+1;
            // Random payload on every edge includes x motion without go;
            // admitted launches remain aligned with their379-bit descriptors.
            for(k=0;k<379;k=k+1) word[k]=$random(seed);
            for(k=0;k<128;k=k+1) xl[k]=$random(seed);
            go=n<2000 ? $random(seed) : 0;
            ready=$random(seed);
            if(go && ready) accepted=accepted+1;
            bf=$random(seed); tf=$random(seed); cf=$random(seed);
            // Directed one-branch faults catch dropped OR legs deterministically.
            if(n%16<3) begin bf=n%16==0;tf=n%16==1;cf=n%16==2; end
        end
        if(accepted!==seen) bad=bad+1;
        if(bad!=0) $fatal(1,"FAIL checks=%0d errors=%0d accepted=%0d seen=%0d",checked,bad,accepted,seen);
        $display("PASS checks=%0d accepted=%0d seen=%0d",checked,accepted,seen);
        $finish;
    end
endmodule
