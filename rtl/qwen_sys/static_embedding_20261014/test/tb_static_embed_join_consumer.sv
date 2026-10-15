`timescale 1ns/1ps
// Component composition: real returned-beat boundary -> native word join ->
// registered epoch checked face -> mapped SRAM -> unchanged 64-lane decoder.
module tb_static_embed_join_consumer;
    reg ck=0;always #0.4166665 ck=~ck;
    reg rn=0,go=0,fill=0,bs=0,bv=0,bh=0,bscale=0,expect_slot=0,expect_scale=0;
    reg [255:0] bd=0;reg [17:0] token=0;reg [5:0] bw=0,expect_word=0;
    reg [15:0] epoch=43;
    wire wv,ws,jfault;wire [511:0] wd;wire [17:0] wt;wire [5:0] wi;wire [15:0] we;
    qkd_embedding_static_join joiner(.ck(ck),.rst_n(rn),.beat_slot(bs),.beat_v(bv),.beat_data(bd),
        .beat_token(token),.beat_word(bw),.beat_half(bh),.beat_scale(bscale),.beat_epoch(epoch),
        .word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),.word_scale(ws),.word_epoch(we),.fault(jfault));
    wire fillout,slot,pv,ps,ffault;wire [17:0] ft,pt;wire [5:0] pw;wire [511:0] pd;
    qkd_embedding_static_preload_face face(.ck(ck),.rst_n(rn),.word_v(wv),.word_data(wd),.word_token(wt),.word_index(wi),
        .word_scale(ws),.word_epoch(we),.expected_slot(expect_slot),.expected_token(token),.expected_word(expect_word),
        .expected_scale(expect_scale),.expected_epoch(16'd43),.i_fill_begin(fill),.i_fill_token(token),.i_fill_epoch(16'd43),
        .fill_begin(fillout),.fill_token(ft),.preload_slot(slot),.preload_v(pv),.preload_scale(ps),
        .preload_word(pw),.preload_token(pt),.preload_data(pd),.fault(ffault));
    reg [63:0] re=0;reg [1535:0] addr=0;wire [2047:0] q;wire fault,goout,pend,fo;wire [63:0] vre;
    ot_qfd_su_embed_static consumer(.clk(ck),.rst_n(rn),.go_in(go),.a_src(1'b1),.tok(token),.f_in(1'b1),
        .go_out(goout),.f_out(fo),.pend(pend),.fill_begin(fillout),.fill_token(ft),
        .preload_slot(slot),.preload_v(pv),.preload_scale(ps),.preload_word(pw),.preload_token(pt),.preload_data(pd),
        .su_va_re(re),.su_va_addr(addr),.su_va_q(q),.va_re(vre),.va_addr(),.va_q(2048'd0),.fault(fault));
    reg [511:0] codes[0:63];reg [31:0] expected[0:4095];reg [15:0] sc[0:0];
    string dir;integer mut=0,tokarg=0,w,l,count=0,beat_count=0;
    // Compiler-side fixed one-edge transfer-to-word calendar. This depends on
    // reserved beat slots, never on actual beat availability or producer valid.
    always @(posedge ck) begin
        expect_slot<=bs&&(bscale||bh);expect_word<=bw;expect_scale<=bscale;
        if(bs)beat_count=beat_count+1;
    end
    initial begin
        if(!$value$plusargs("VECTORS=%s",dir))$fatal(1,"VECTORS required");
        void'($value$plusargs("MUT=%d",mut));void'($value$plusargs("TOKEN=%d",tokarg));token=tokarg;
        $readmemh({dir,"/codes.hex"},codes);$readmemh({dir,"/expected.hex"},expected);$readmemh({dir,"/scale.hex"},sc);
        repeat(3)@(negedge ck);rn=1;fill=1;
        @(negedge ck);fill=0;repeat(2)@(negedge ck);
        for(w=0;w<64;w=w+1)begin
            @(negedge ck);bs=1;bv=1;bh=0;bw=w;bd=codes[w][255:0];epoch=43;
            @(negedge ck);bh=1;bd=codes[w][511:256];if(mut==1&&w==63)epoch=44;
            if(mut==2&&w==63)bv=0;
        end
        @(negedge ck);bs=1;bv=1;bh=0;bscale=1;bw=0;bd=0;bd[token[3:0]*16+:16]=sc[0];epoch=43;
        @(negedge ck);bs=0;bv=0;
        repeat(2)@(negedge ck);go=1;
        #0.01;if(!goout||pend||!fo)$fatal(1,"GO rescheduled");
        @(negedge ck);go=0;
        for(w=0;w<64;w=w+1)begin
            re=~64'd0;for(l=0;l<64;l=l+1)addr[l*24+:24]=w*64+l;
            @(posedge ck);#0.01;
            for(l=0;l<64;l=l+1)begin
                if(q[l*32+:32]!==expected[w*64+l])$fatal(1,"actual join decode mismatch element%0d",w*64+l);
                count=count+1;
            end
            @(negedge ck);
        end
        re=0;repeat(2)@(negedge ck);
        if(fault||jfault||ffault)$fatal(1,"schedule or producer identity fault");
        if(count!=4096||beat_count!=129)$fatal(1,"full row/throughput incomplete");
        $display("PASS actualwordjoin+epochguard+mappedSRAMconsumer token=%0d exact4096 reserved129beats129consecutiveEdges no-unplanned-gaps",token);$finish;
    end
endmodule
