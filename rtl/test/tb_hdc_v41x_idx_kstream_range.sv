`timescale 1ns/1ps
module tb_hdc_v41x_idx_kstream_range #(
    parameter integer SKIP=1000,COUNT=1050
);
    localparam integer NPC=32,AW=28,HW=20,TAGW=16,LENW=4,BEATW=4,DW=256;
    localparam integer SPAN=SKIP+COUNT;
    reg clk=0,rst_n=0,cmd_v=0;
    always #5 clk=~clk;
    wire busy,o_valid;
    wire [NPC-1:0] req_v,req_rdy,rsp_v,rsp_rdy;
    wire [NPC*AW-1:0] req_addr;
    wire [NPC*LENW-1:0] req_len;
    wire [NPC*TAGW-1:0] req_tag,rsp_tag;
    wire [NPC*BEATW-1:0] rsp_beat;
    wire [NPC*DW-1:0] rsp_data;
    wire [15:0] o_kv;
    wire [16*544-1:0] o_key;
    wire [47:0] cnt_keys_streamed,cnt_hbm_beats;
    ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(1),
        .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(64),.RQD(32),
        .REFPB(3),.MEM_MODE(1)) hm (
        .clk(clk),.rst_n(rst_n),.req_v(req_v),.req_rdy(req_rdy),
        .req_addr(req_addr),.req_len(req_len),.req_tag(req_tag),
        .req_we({NPC{1'b0}}),.req_wdata({NPC*DW{1'b0}}),
        .req_wstrb({NPC*32{1'b0}}),.wr_done(),
        .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),
        .rsp_beat(rsp_beat),.rsp_data(rsp_data));
    ot_hdc_v41x_idx_kstream_range #(.NPC(NPC),.WB(128),.GA(120),
        .AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_base(HW'(0)),
        .cmd_skip(10'(SKIP)),.cmd_nkeys((HW+10)'(COUNT)),.busy(busy),
        .req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),
        .req_len(req_len),.req_tag(req_tag),.rsp_v(rsp_v),
        .rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),
        .rsp_data(rsp_data),.o_valid(o_valid),.o_ready(1'b1),
        .o_kv(o_kv),.o_key(o_key),.cnt_keys_streamed(cnt_keys_streamed),
        .cnt_hbm_beats(cnt_hbm_beats));
    function automatic [255:0] pat(input [AW-1:0] sec);
        integer w;
        begin
            for(w=0;w<8;w=w+1)
                pat[32*w +:32]=(sec*32'd8+w)*32'h9E3779B1 ^ 32'h5bd1e995;
        end
    endfunction
    function automatic [543:0] expkey(input integer key);
        integer sb,pos;
        reg [AW-1:0] sc,cs;
        reg [255:0] sw;
        begin
            sb=key/1024;pos=key%1024;
            sc=AW'(2176*sb+pos/8);
            cs=AW'(2176*sb+128+2*pos);
            sw=pat(sc);
            expkey={sw[32*(pos%8) +:32],pat(cs+1),pat(cs)};
        end
    endfunction
    integer seen=0,checked=0,cycle=0,l,hits;
    always @(posedge clk) begin
        cycle<=cycle+1;
        if(cycle>200000) $fatal(1,"range timeout seen=%0d",seen);
        if(rst_n && o_valid) begin
            hits=0;
            for(l=0;l<16;l=l+1) if(o_kv[l]) begin
                if(seen+l>=SKIP && seen+l<SPAN) begin
                    if(o_key[544*l +:544] !== expkey(seen+l))
                        $fatal(1,"range key=%0d got=%h want=%h",seen+l,
                               o_key[544*l +:544],expkey(seen+l));
                    hits=hits+1;
                end
            end
            checked<=checked+hits;
            seen<=seen+16;
        end
    end
    initial begin
        repeat(4) @(negedge clk);rst_n=1;
        @(negedge clk);cmd_v=1;
        @(negedge clk);cmd_v=0;
        wait(!busy);
        repeat(3) @(posedge clk);
        if(checked!=COUNT || cnt_hbm_beats!=2*COUNT+((SPAN+7)/8)-SKIP/8)
            $fatal(1,"range counts checked=%0d beats=%0d expected=%0d",checked,cnt_hbm_beats,
                   2*COUNT+((SPAN+7)/8)-SKIP/8);
        $display("V41X_RANGE_PASS skip=%0d count=%0d checked=%0d sectors=%0d cycles=%0d",
                 SKIP,COUNT,checked,cnt_hbm_beats,cycle);
        $finish;
    end
endmodule
