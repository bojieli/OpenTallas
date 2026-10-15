`timescale 1ns/1ps
module tb_static_embed_consumer;
    reg clk=0;always #0.4166665 clk=~clk;
    reg rst_n=0,go=0,fill=0,slot=0,pv=0,ps=0;
    reg [5:0] pw=0;reg [17:0] token=0,pt=0;
    reg [511:0] pd=0;
    reg [63:0] re=0;reg [1535:0] addr=0;
    wire [2047:0] q;wire fault,go_out;
    wire [63:0] vre;wire [1535:0] va;wire pend;wire fo;
    ot_qfd_su_embed_static dut(.clk(clk),.rst_n(rst_n),.go_in(go),.a_src(1'b1),.tok(token),
        .f_in(1'b1),.go_out(go_out),.f_out(fo),.pend(pend),.fill_begin(fill),.fill_token(token),
        .preload_slot(slot),.preload_v(pv),.preload_scale(ps),.preload_word(pw),.preload_token(pt),.preload_data(pd),
        .su_va_re(re),.su_va_addr(addr),.su_va_q(q),.va_re(vre),.va_addr(va),.va_q(2048'd0),.fault(fault));
    reg [511:0] codes[0:63];reg [31:0] expected[0:4095];reg [15:0] sc[0:0];
    string dir;integer mut=0,tokarg=0,w,l,checked=0;
    initial begin
        if(!$value$plusargs("VECTORS=%s",dir)) $fatal(1,"VECTORS required");
        void'($value$plusargs("MUT=%d",mut));void'($value$plusargs("TOKEN=%d",tokarg));token=tokarg;pt=tokarg;
        $readmemh({dir,"/codes.hex"},codes);$readmemh({dir,"/expected.hex"},expected);$readmemh({dir,"/scale.hex"},sc);
        repeat(3) @(negedge clk);rst_n=1;fill=1;
        @(negedge clk);fill=0;
        for(w=0;w<65;w=w+1) begin
            slot=1;pv=!(mut==1&&w==63);ps=w==64;pw=w;pt=mut==2?token+1:token;
            pd=w==64?{496'd0,sc[0]}:codes[w];
            if(mut==3&&w==63) go=1;
            @(negedge clk);go=0;
        end
        slot=0;pv=0;go=1;
        #0.01;if(!go_out||pend||!fo) $fatal(1,"GO must pass on its compiled edge");
        @(negedge clk);go=0;
        for(w=0;w<64;w=w+1) begin
            re=~64'd0;
            for(l=0;l<64;l=l+1) addr[l*24+:24]=w*64+l;
            @(posedge clk);#0.01;
            if(|vre) $fatal(1,"embedding read leaked to VM");
            for(l=0;l<64;l=l+1) begin
                if(q[l*32+:32]!==expected[w*64+l]) $fatal(1,"decode mismatch element %0d",w*64+l);
                checked=checked+1;
            end
            @(negedge clk);
        end
        re=0;repeat(2) @(negedge clk);
        if(fault) $fatal(1,"static consumer fault");
        if(checked!=4096) $fatal(1,"incomplete full row");
        $display("PASS static mappedSRAMconsumer token=%0d values=%0d no-heldGO",token,checked);$finish;
    end
endmodule
