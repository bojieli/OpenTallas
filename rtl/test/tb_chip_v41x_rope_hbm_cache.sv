`timescale 1ns/1ps
module tb_chip_v41x_rope_hbm_cache;
    localparam HAW=30, TAGW=16;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, pf_v=0, pf_kind=0, pf_release=0;
    reg [20:0] pf_pos=0;
    wire pf_rdy,pf_done,cache_valid,cache_hold,cache_kind,fault;
    wire [20:0] cache_pos;
    wire [2047:0] cache_pairs;
    reg [1:0] table_present=2'b11;
    reg [4*HAW-1:0] plain_base=0,yarn_base=0;
    wire [3:0] req_v,req_we,rsp_rdy;
    wire [4*HAW-1:0] req_addr;
    wire [15:0] req_len;
    wire [4*TAGW-1:0] req_tag;
    wire [1023:0] req_wdata;
    wire [127:0] req_wstrb;
    reg [3:0] req_rdy=0,rsp_v=0;
    reg [4*TAGW-1:0] rsp_tag=0;
    reg [15:0] rsp_beat=0;
    reg [1023:0] rsp_data=0;
    wire [31:0] issued_sectors,received_sectors,stalled_cycles,cache_hits;
    reg [63:0] plain200k [0:31],plain1m [0:31],yarn200k [0:31];
    reg pending [0:3][0:1];
    reg [255:0] pending_data [0:3][0:1];
    integer due [0:3][0:1];
    integer cycles=0,case_id=0,out_of_order=0;
    string dir;

    ot_chip_v41x_rope_hbm_cache #(.HAW(HAW),.TAGW(TAGW)) dut (
        .clk(clk),.rst_n(rst_n),.pf_v(pf_v),.pf_rdy(pf_rdy),.pf_kind(pf_kind),.pf_pos(pf_pos),
        .pf_release(pf_release),.pf_done(pf_done),.cache_valid(cache_valid),.cache_hold(cache_hold),
        .cache_kind(cache_kind),.cache_pos(cache_pos),.cache_pairs(cache_pairs),
        .table_present(table_present),.plain_base(plain_base),.yarn_base(yarn_base),
        .req_v(req_v),.req_rdy(req_rdy),.req_addr(req_addr),.req_len(req_len),
        .req_tag(req_tag),.req_we(req_we),.req_wdata(req_wdata),.req_wstrb(req_wstrb),
        .rsp_v(rsp_v),.rsp_rdy(rsp_rdy),.rsp_tag(rsp_tag),.rsp_beat(rsp_beat),.rsp_data(rsp_data),
        .fault(fault),.issued_sectors(issued_sectors),.received_sectors(received_sectors),
        .stalled_cycles(stalled_cycles),.cache_hits(cache_hits));

    function automatic [63:0] word(input integer c,input integer i);
        if (c==0) word=plain200k[i];
        else if (c==1) word=yarn200k[i];
        else word=plain1m[i];
    endfunction
    task automatic check_cache(input integer c,input bit kind,input [20:0] pos);
        begin
            if (!cache_valid || !cache_hold || cache_kind!==kind || cache_pos!==pos)
                $fatal(1,"cache tag mismatch case=%0d",c);
            for (integer i=0;i<32;i++)
                if (cache_pairs[i*64+:64]!==word(c,i))
                    $fatal(1,"cache pair mismatch case=%0d pair=%0d got=%h expected=%h",
                           c,i,cache_pairs[i*64+:64],word(c,i));
        end
    endtask
    task automatic prefetch(input integer c,input bit kind,input [20:0] pos);
        begin
            case_id=c;
            @(negedge clk); pf_kind=kind;pf_pos=pos;pf_v=1;
            #1;
            if (!pf_rdy) $fatal(1,"prefetch not ready case=%0d",c);
            @(negedge clk); pf_v=0;
            wait(pf_done);
            @(negedge clk); check_cache(c,kind,pos);
        end
    endtask
    task automatic free_cache;
        begin
            @(negedge clk);pf_release=1;
            @(negedge clk);pf_release=0;
            if (cache_hold) $fatal(1,"cache did not release");
        end
    endtask

    initial begin
        if (!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR missing");
        $readmemh({dir,"/plain200k.hex"},plain200k);
        $readmemh({dir,"/plain1m.hex"},plain1m);
        $readmemh({dir,"/yarn200k.hex"},yarn200k);
        if (plain200k[0]!==64'hbf60bfc03ef524d5)
            $fatal(1,"plain200k golden coefficient changed");
        for (integer s=0;s<4;s++) begin
            plain_base[s*HAW+:HAW]=HAW'(10000+s*100);
            yarn_base[s*HAW+:HAW]=HAW'(5000000+s*100);
            for (integer p=0;p<2;p++) pending[s][p]=0;
        end
        repeat(5) @(negedge clk);rst_n=1;
        prefetch(0,0,21'd199999);
        // A different token cannot evict a held cache entry.
        @(negedge clk);pf_v=1;pf_kind=0;pf_pos=21'd200000;
        #1;
        if (pf_rdy) $fatal(1,"held cache was evictable");
        @(negedge clk);pf_v=0;
        // Same tag reuses it without HBM traffic.
        prefetch(0,0,21'd199999);
        free_cache();
        prefetch(1,1,21'd199999);
        free_cache();
        prefetch(2,0,21'd1048575);
        free_cache();
        @(negedge clk);pf_v=1;pf_kind=0;pf_pos=21'd1048576;
        @(negedge clk);pf_v=0;
        repeat(4) @(negedge clk);
        if (!fault || pf_done || issued_sectors!=24 || received_sectors!=24 ||
            cache_hits!=1 || stalled_cycles==0 || out_of_order==0)
            $fatal(1,"coverage/fault mismatch issue=%0d recv=%0d hit=%0d stall=%0d reorder=%0d fault=%0d",
                   issued_sectors,received_sectors,cache_hits,stalled_cycles,out_of_order,fault);
        $display("ROPE_HBM_PASS fills=3 sectors=%0d hits=%0d stalls=%0d reordered=%0d cycles=%0d",
                 received_sectors,cache_hits,stalled_cycles,out_of_order,cycles);
        $finish;
    end

    // Timed, sometimes-not-ready HBM response model. Phase 1 overtakes phase 0
    // on at least one stack; each reply carries the original tag.
    always @(*) begin
        req_rdy=0;rsp_v=0;rsp_tag=0;rsp_beat=0;rsp_data=0;
        for (integer s=0;s<4;s++) begin
            req_rdy[s]=((cycles+s)%3!=0);
            for (integer p=1;p>=0;p--) if (pending[s][p] && due[s][p]<=cycles && !rsp_v[s]) begin
                rsp_v[s]=1;
                rsp_tag[s*TAGW+:TAGW]=TAGW'(p);
                rsp_data[s*256+:256]=pending_data[s][p];
            end
        end
    end
    always @(posedge clk) if (rst_n) begin
        cycles<=cycles+1;
        if (cycles>2000) $fatal(1,"RoPE HBM timeout");
        for (integer s=0;s<4;s++) begin
            if (req_v[s] && req_rdy[s]) begin
                integer p,base,idx;
                p=req_tag[s*TAGW];
                base=case_id==1 ? 5000000+s*100 : 10000+s*100;
                if (req_we[s] || req_len[s*4+:4]!=1 ||
                    req_addr[s*HAW+:HAW]!==HAW'(base+(case_id==2?1048575:199999)*2+p))
                    $fatal(1,"bad sector request case=%0d stack=%0d phase=%0d addr=%0d",case_id,s,p,req_addr[s*HAW+:HAW]);
                if (pending[s][p]) $fatal(1,"duplicate sector request");
                idx=s*8+p*4;
                pending_data[s][p]<={word(case_id,idx+3),word(case_id,idx+2),
                                      word(case_id,idx+1),word(case_id,idx)};
                due[s][p]<=cycles+(p==0?9:2);
                pending[s][p]<=1;
            end
            if (rsp_v[s] && rsp_rdy[s]) begin
                integer p;
                p=rsp_tag[s*TAGW];
                if (p==1 && pending[s][0]) out_of_order++;
                pending[s][p]<=0;
            end
        end
    end
endmodule
