`timescale 1ps/1fs
// Changed32-PC topology gate, not another per-PC codec qualification.
// Actual released sectors are stimulus; no PHY/fulltoken claim is made.
// KV_MAP: sector map of the stimulus (0 base, 1 option M via ot_qwen_kv_map_m.svh; stack 0, PC_BASE 0).
// KV_MAP_DUT: the DUT's PC identity map (-1: = KV_MAP); a differing value is the negative control,
// which must fail (identity rejects every landing; the watchdog fatals).
module tb_qwen_p0_parallel_bank #(parameter integer KV_MAP=0, KV_MAP_DUT=-1);
    reg clk=0,hclk=0,por=0,warm=1;
    always begin #416.666 clk=1;#416.667 clk=0;end
    always #512 hclk=~hclk;
    reg [31:0] h_lv=0,h_av=0,pop_enable=0,w_v=0,ack_enable=0,h_hand=0,h_wcon=0;
    reg [543:0] h_lsec=0;reg [255:0] h_lrow=0;
    reg [8191:0] h_ldata=0,w_data=0;
    reg [767:0] w_sec=0;reg [287:0] w_tag=0,h_atag=0;
    wire [31:0] l_pop=pop_enable&l_v,wd_accept=ack_enable&wd_v;
    wire [31:0] l_v,w_room,wd_v,c_fault,h_fault,c_quiet,h_quiet,h_wv,h_cv;
    wire [543:0] l_sec;wire [255:0] l_row;wire [8191:0] l_data,h_cdata;
    wire [287:0] wd_tag,h_ctag;wire [95:0] h_cred;
    wire [767:0] h_wsec,h_csec;
    ot_qwen_p0_parallel_bank #(.ENABLE(1),.LANDING_RSEL(1),.LOCAL_WIRE_SPANS(14),
        .KV_MAP(KV_MAP_DUT<0?KV_MAP:KV_MAP_DUT)) dut(.*);
    initial begin repeat(200000)@(negedge clk); $fatal(1,"watchdog: parallel bank did not complete"); end
    // Module cold/warm names are explicit: warm never resets accepted owners.
    // The aliases are inputs, not tied control/ready substitutes.
    wire por_n=por,warm_rst_n=warm;
    reg [255:0] gold[0:127];string gold_path;
    integer taken[0:31],acked[0:31],credits[0:31],captured[0:31];
    integer max_parallel=0,total=0;
    bit sample_faults=0;
`include "ot_qwen_kv_map_m.svh"
    function automatic [16:0] sec(input integer pc,input integer j);
        sec=(KV_MAP!=0)?m_p2l(pc,10'(j)):17'(((j&1)<<16)|((pc>>4)<<15)|((j>>1)<<6)|((pc&15)<<2));
    endfunction
    always @(posedge clk)if(sample_faults)begin
        if(|c_fault||(|h_fault))$fatal(1,"parallel healthy state fault");
        if($countones(l_v&l_pop)>max_parallel)max_parallel=$countones(l_v&l_pop);
        for(integer p=0;p<32;p=p+1)begin
            if(l_v[p]&&l_pop[p])begin
                if(taken[p]>=4||l_sec[p*17+:17]!==sec(p,taken[p])||l_row[p*8+:8]!==0||
                    l_data[p*256+:256]!==gold[taken[p]*32+p])$fatal(1,"PC%0d row%0d changed source/gold/identity",p,taken[p]);
                taken[p]++;total++;
            end
            if(wd_v[p]&&wd_accept[p])begin
                if(wd_tag[p*9+:9]!==9'(256+p)||acked[p]!=0)$fatal(1,"PC ACK mismatch/replay %0d",p);
                acked[p]++;
            end
        end
    end
    always @(posedge hclk)if(sample_faults)
        for(integer p=0;p<32;p=p+1)credits[p]+=h_cred[p*3+:3];
    always @(negedge hclk)if(sample_faults)
        for(integer p=0;p<32;p=p+1)if(h_cv[p])begin
            if(h_csec[p*24+:24]!==24'(sec(p,2))||h_cdata[p*256+:256]!==gold[64+p]||
                h_ctag[p*9+:9]!==9'(256+p)||captured[p]!=0)$fatal(1,"PC%0d WR capture changed",p);
            captured[p]++;
        end
    reg [8191:0] held_data;reg [543:0] held_sec;
    initial begin
        if(!$value$plusargs("GOLD=%s",gold_path))$fatal(1,"actual released gold path required");
        $readmemh(gold_path,gold);
        for(integer p=0;p<32;p=p+1)begin taken[p]=0;acked[p]=0;credits[p]=0;captured[p]=0;end
        repeat(5)@(negedge clk);por=1;
        repeat(32)@(negedge hclk);sample_faults=1;
        for(integer j=0;j<4;j=j+1)begin
            @(negedge hclk);
            for(integer p=0;p<32;p=p+1)begin
                h_lsec[p*17+:17]=sec(p,j);h_lrow[p*8+:8]=0;h_ldata[p*256+:256]=gold[j*32+p];
            end
            h_lv='1;
        end
        @(negedge hclk);h_lv=0;
        while(l_v!='1)@(negedge clk);
        held_data=l_data;held_sec=l_sec;
        repeat(24)begin @(negedge clk);if(l_v!='1||l_data!==held_data||l_sec!==held_sec)$fatal(1,"32 held outputs changed");end
        while(w_room!='1)@(negedge clk);
        for(integer p=0;p<32;p=p+1)begin
            w_sec[p*24+:24]=24'(sec(p,2));w_data[p*256+:256]=gold[64+p];w_tag[p*9+:9]=9'(256+p);
        end
        w_v='1;@(negedge clk);w_v=0;
        while(h_wv!='1)@(negedge hclk);
        warm=0;repeat(12)@(negedge clk);
        if(w_room!=0||l_v!='1||h_wv!='1||l_data!==held_data)$fatal(1,"warm erased owners/admitted new WR");
        @(negedge hclk);h_hand='1;@(negedge hclk);h_hand=0;
        @(negedge hclk);h_wcon='1;@(negedge hclk);h_wcon=0;
        for(integer p=0;p<32;p=p+1)h_atag[p*9+:9]=9'(256+p);
        h_av='1;@(negedge hclk);h_av=0;
        while(wd_v!='1)@(negedge clk);
        repeat(16)begin @(negedge clk);if(wd_v!='1)$fatal(1,"parallel ACK held debt lost");end
        if((&c_quiet)||(&h_quiet))$fatal(1,"premature drain with held landing/ACK");
        // One actual edge must accept32 distinct PCs, rejecting a serial funnel.
        pop_enable='1;
        @(negedge clk);pop_enable=0;
        repeat(12)@(negedge clk);
        // Half the PCs drain independently; the others retain the next row.
        pop_enable=32'h55555555;ack_enable=32'h55555555;
        repeat(16)@(negedge clk);
        if((l_v&32'haaaaaaaa)!=32'haaaaaaaa||(wd_v&32'haaaaaaaa)!=32'haaaaaaaa)$fatal(1,"one PC pop cleared peer owner");
        pop_enable='1;ack_enable='1;
        wait(total==128);
        @(negedge clk);pop_enable=0;ack_enable=0;
        wait((&c_quiet)&&(&h_quiet));
        for(integer p=0;p<32;p=p+1)
            if(taken[p]!=4||acked[p]!=1||captured[p]!=1||credits[p]!=4)$fatal(1,"PC%0d missing row/WR/ACK/credit",p);
        if(max_parallel!=32)$fatal(1,"serialized response mechanism max%0d",max_parallel);
        $display("KV_MAP=%0d PASS parallel32",KV_MAP," releasedK/V rows128 simultaneous32 WR32 ACK32 debt0 warmheld realcredits CLK833.333 HCLK1024 scopeCOMPONENT");
        $finish;
    end
endmodule
