`timescale 1ns/1ps
// Component composition: real returned-beat boundary -> native word join ->
// registered epoch checked face -> mapped SRAM -> unchanged 64-lane decoder.
module tb_static_embed_core_provider;
    reg ck=0;always #0.4166665 ck=~ck;
    reg rn=0,go=0,fill=0,bs=0,bv=0,bh=0,bscale=0,expect_slot=0,expect_scale=0;
    reg [255:0] bd=0;reg [17:0] token=0;reg [5:0] bw=0,expect_word=0;
    reg [15:0] epoch=43;
    wire [511:0] code_q;wire [15:0] scale_q;wire fault;
    reg code_re=0,scale_re=0;reg [23:0] code_addr=0;
    qkd_embedding_static_core_provider provider(.ck(ck),.rst_n(rn),.beat_slot(bs),.beat_v(bv),.beat_data(bd),
      .beat_token(token),.beat_word(bw),.beat_half(bh),.beat_scale(bscale),.beat_epoch(epoch),
      .fill_begin(fill),.fill_token(token),.fill_epoch(16'd43),.expected_word_slot(expect_slot),
      .expected_token(token),.expected_word(expect_word),.expected_scale(expect_scale),.expected_epoch(16'd43),
      .core_start(go),.core_token(token),.core_epoch(16'd43),.embed_code_re(code_re),.embed_code_addr(code_addr),
      .embed_code_q(code_q),.embed_scale_re(scale_re),.embed_scale_addr(token),.embed_scale_q(scale_q),.fault(fault));
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
        scale_re=1;@(posedge ck);#0.01;if(scale_q!==sc[0])$fatal(1,"actual scale mismatch");
        @(negedge ck);go=0;
        scale_re=0;code_re=1;
        for(w=0;w<64;w=w+1)begin
            code_addr=token*64+w;
            @(posedge ck);#0.01;
            if(code_q!==codes[w])$fatal(1,"actual join code mismatch word%0d",w);
            count=count+1;@(negedge ck);
        end
        code_re=0;repeat(2)@(negedge ck);
        if(fault)$fatal(1,"schedule or producer identity fault");
        if(count!=64||beat_count!=129)$fatal(1,"full row/throughput incomplete");
        $display("PASS actualwordjoin+epochguard+mappedcoreprovider token=%0d exact64codewords reserved129beats129consecutiveEdges no-unplanned-gaps",token);$finish;
    end
endmodule
