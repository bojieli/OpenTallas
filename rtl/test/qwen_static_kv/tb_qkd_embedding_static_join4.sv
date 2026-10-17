`timescale 1ns/1ps
// KVJ-C2: qkd_embedding_static_join4 under legal static traffic: per token 64 code words (low half then high half) and
// one packed scale beat, every beat on a random one of the 4 trains with random gaps; the word stream must equal the
// expected words ({high, low}; scale = BF16 lane token[3:0]) with no fault.  Then a conflict (two trains on one edge)
// must fault.  MUT via -DOT_KVJ_J4_MUT (1 = no conflict fault, 2 = train 3 ignored).
`ifndef OT_KVJ_J4_MUT
`define OT_KVJ_J4_MUT 0
`endif
module tb_qkd_embedding_static_join4;
    reg ck=0, rst_n=0, slot=0;
    reg [298:0] up [0:3];
    wire wv, ws; wire [511:0] wd; wire [17:0] wt; wire [5:0] wi; wire [15:0] we; wire f;
    always #1 ck=~ck;
    qkd_embedding_static_join4 #(.MUT(`OT_KVJ_J4_MUT)) dut (.ck(ck),.rst_n(rst_n),.up0(up[0]),.up1(up[1]),.up2(up[2]),.up3(up[3]),
        .beat_slot(slot),.word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),.fault(f));
    reg [255:0] lo [0:63]; reg [255:0] hi [0:63]; reg [255:0] sc;
    reg [17:0] tok; reg [15:0] ep;
    integer t, b, s, n_exp, n_got, err=0, i, g, words=0;
    reg [511:0] exp_d [0:64]; reg [5:0] exp_i [0:64]; reg exp_s [0:64];
    task clr; integer q; begin for (q=0;q<4;q=q+1) up[q]=299'd0; slot=0; end endtask
    task beat(input [255:0] d, input [5:0] wd_, input h, input sca); begin
        s=$urandom%4; clr; up[s]={ep, sca, h, wd_, tok, d, 1'b1}; slot=1; @(negedge ck); clr;
        g=$urandom%3; repeat(g) @(negedge ck);
    end endtask
    always @(posedge ck) if (rst_n && wv) begin
        if (n_got>64 || wd!==exp_d[n_got] || wi!==exp_i[n_got] || ws!==exp_s[n_got] || wt!==tok || we!==ep) begin
            err=err+1; if (err<5) $display("FAIL word %0d tok %0d", n_got, tok); end
        n_got=n_got+1; words=words+1;
    end
    initial begin
        clr; repeat(3) @(negedge ck); rst_n=1; @(negedge ck);
        for (t=0; t<12; t=t+1) begin
            tok=$urandom%151936; ep=$urandom; n_got=0;
            for (b=0;b<64;b=b+1) begin lo[b]={8{$urandom}}; hi[b]={8{$urandom}}; exp_d[b]={hi[b],lo[b]}; exp_i[b]=b; exp_s[b]=0; end
            sc={8{$urandom}}; exp_d[64]={496'd0, sc[tok[3:0]*16 +: 16]}; exp_i[64]=0; exp_s[64]=1;
            for (b=0;b<64;b=b+1) begin beat(lo[b],b,0,0); beat(hi[b],b,1,0); end
            beat(sc,0,0,1);
            repeat(4) @(negedge ck);
            if (n_got!=65) begin err=err+1; $display("FAIL token %0d words %0d", t, n_got); end
        end
        if (f) begin err=err+1; $display("FAIL fault on legal traffic"); end
        // negative: two trains on one edge
        tok=5; ep=1; clr; up[0]={ep,1'b0,1'b0,6'd0,tok,256'd1,1'b1}; up[2]={ep,1'b0,1'b0,6'd0,tok,256'd2,1'b1}; slot=1;
        @(negedge ck); clr; repeat(4) @(negedge ck);
        if (!f) begin err=err+1; $display("FAIL conflict not faulted"); end
        if (err==0) $display("PASS join4 tokens=12 words=%0d conflict_faults", words);
        else $display("FAIL join4 errors=%0d", err);
        $finish;
    end
endmodule
