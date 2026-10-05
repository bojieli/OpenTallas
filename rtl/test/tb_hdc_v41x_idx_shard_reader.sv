`timescale 1ns/1ps
module tb_hdc_v41x_idx_shard_reader;
    localparam integer NPC=2,HAW=28,TAGW=16,LENW=4,BEATW=4;
    reg clk=0,rst_n=0,cmd_v=0,o_ready=0;
    always #5 clk=~clk;
    reg [HAW-1:0] cmd_base_sec=4096;
    reg [29:0] cmd_nkeys=0;
    wire busy,fault,o_valid;
    wire [4*NPC-1:0] req_v,rsp_rdy;
    wire [4*NPC*HAW-1:0] req_addr;
    wire [4*NPC*LENW-1:0] req_len;
    wire [4*NPC*TAGW-1:0] req_tag;
    reg [4*NPC-1:0] req_rdy='1,rsp_v=0;
    reg [4*NPC*TAGW-1:0] rsp_tag=0;
    reg [4*NPC*BEATW-1:0] rsp_beat=0;
    reg [4*NPC*256-1:0] rsp_data=0;
    wire [63:0] o_kv,o_ref;
    wire [3:0] o_last;
    wire [64*544-1:0] o_key;
    wire [47:0] cnt_keys_streamed,cnt_hbm_beats,cnt_refused;
    ot_hdc_v41x_idx_shard_reader #(.NPC(NPC),.HAW(HAW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW)) dut (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_base_sec(cmd_base_sec),.cmd_nkeys(cmd_nkeys),
        .busy(busy),.fault(fault),.req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),
        .req_len(req_len),.req_tag(req_tag),.rsp_v(rsp_v),.rsp_rdy(rsp_rdy),
        .rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
        .o_valid(o_valid),.o_ready(o_ready),.o_kv(o_kv),.o_last(o_last),
        .o_key(o_key),.o_ref(o_ref),.cnt_keys_streamed(cnt_keys_streamed),
        .cnt_hbm_beats(cnt_hbm_beats),.cnt_refused(cnt_refused));

    function automatic integer global_of(input integer stack,loc_idx);
        global_of=(loc_idx/16)*64+stack*16+(loc_idx%16);
    endfunction
    function automatic [7:0] scale_val(input integer key,dim);
        scale_val=(key==7 && dim==0) ? 8'd253 : 8'(10+((key+17*dim)%200));
    endfunction
    function automatic [7:0] code_val(input integer key,byte_idx);
        code_val=8'((3*key+5*byte_idx)&255);
    endfunction
    function automatic [255:0] sector_data(input integer stack,sec);
        integer rel,sb,in_sb,loc_idx,key,half,j,k,b;
        reg [255:0] data;
        begin
            rel=sec-4096;sb=rel/2176;in_sb=rel%2176;data=0;
            if(in_sb<128) begin
                for(j=0;j<8;j=j+1) begin
                    loc_idx=sb*1024+in_sb*8+j;key=global_of(stack,loc_idx);
                    for(b=0;b<4;b=b+1) data[8*(4*j+b) +:8]=scale_val(key,b);
                end
            end else begin
                loc_idx=sb*1024+(in_sb-128)/2;key=global_of(stack,loc_idx);
                half=(in_sb-128)&1;
                for(j=0;j<32;j=j+1) data[8*j +:8]=code_val(key,32*half+j);
            end
            sector_data=data;
        end
    endfunction
    integer pi,stack,sec,cycle=0;
    always @(negedge clk) if(rst_n) req_rdy=(cycle%7<5) ? '1 : '0;
    always @(posedge clk) begin
        cycle<=cycle+1;
        rsp_v<=0;
        if(rst_n) for(pi=0;pi<4*NPC;pi=pi+1) if(req_v[pi] && req_rdy[pi]) begin
            if(req_len[pi*LENW +:LENW]!=1) $fatal(1,"nonunit read");
            sec=req_addr[pi*HAW +: HAW];stack=pi/NPC;
            rsp_v[pi]<=1;
            rsp_tag[pi*TAGW +: TAGW]<=req_tag[pi*TAGW +: TAGW];
            rsp_beat[pi*BEATW +: BEATW]<=0;
            rsp_data[pi*256 +:256]<=sector_data(stack,sec);
        end
        if(cycle>300000) $fatal(1,"reader timeout");
    end
    task automatic run_scan(input integer n);
        integer qs,l3,beats,b,q,l,key,qlen,j,prior_keys,prior_beats,prior_ref,expect_ref,start_cycle;
        reg [543:0] got;
        begin
            prior_keys=cnt_keys_streamed;prior_beats=cnt_hbm_beats;prior_ref=cnt_refused;
            @(negedge clk);cmd_nkeys=n;cmd_v=1;start_cycle=cycle;
            @(negedge clk);cmd_v=0;
            qs=8*(n/32);l3=n-3*qs;beats=(l3+15)/16;
            for(b=0;b<beats;b=b+1) begin
                wait(o_valid);
                #1;
                for(q=0;q<4;q=q+1) begin
                    qlen=q==3 ? l3 : qs;
                    if(o_last[q] != ((qlen==0) ? (b==0) : (b==(qlen-1)/16)))
                        $fatal(1,"last n=%0d b=%0d q=%0d",n,b,q);
                    for(l=0;l<16;l=l+1) begin
                        key=q*qs+16*b+l;
                        if(o_kv[16*q+l] != (16*b+l<qlen))
                            $fatal(1,"kv n=%0d b=%0d q=%0d l=%0d",n,b,q,l);
                        if(16*b+l<qlen) begin
                            got=o_key[(16*q+l)*544 +:544];
                            for(j=0;j<64;j=j+1)
                                if(got[8*j +:8]!==code_val(key,j))
                                    $fatal(1,"code n=%0d key=%0d byte=%0d got=%0h",n,key,j,got[8*j +:8]);
                            for(j=0;j<4;j=j+1)
                                if(got[512+8*j +:8]!==scale_val(key,j))
                                    $fatal(1,"scale n=%0d key=%0d block=%0d",n,key,j);
                            if(o_ref[16*q+l] != (key==7))
                                $fatal(1,"refusal n=%0d key=%0d",n,key);
                        end
                    end
                end
                repeat(2) @(posedge clk);
                if(!o_valid) $fatal(1,"output lost during backpressure");
                @(negedge clk);o_ready=1;
                @(posedge clk);#1;
                @(negedge clk);o_ready=0;
            end
            wait(!busy);
            expect_ref=n>7 ? 1 : 0;
            if(fault || cnt_keys_streamed-prior_keys!=n ||
               cnt_hbm_beats-prior_beats!=2*n+(n+7)/8 ||
               cnt_refused-prior_ref!=expect_ref)
                $fatal(1,"counts n=%0d keys=%0d sectors=%0d ref=%0d fault=%0b",n,
                    cnt_keys_streamed-prior_keys,cnt_hbm_beats-prior_beats,
                    cnt_refused-prior_ref,fault);
            $display("SCAN n=%0d keys=%0d sectors=%0d beats=%0d ref=%0d cycles=%0d",n,n,
                     2*n+(n+7)/8,beats,expect_ref,cycle-start_cycle);
        end
    endtask
    initial begin
        repeat(4) @(negedge clk);rst_n=1;
        run_scan(1);run_scan(7);run_scan(8);run_scan(9);run_scan(31);
        run_scan(32);run_scan(39);run_scan(40);run_scan(63);run_scan(64);
        run_scan(65);run_scan(1031);run_scan(1040);
        $display("V41X_SHARD_READER_PASS scans=13");
        $finish;
    end
endmodule
