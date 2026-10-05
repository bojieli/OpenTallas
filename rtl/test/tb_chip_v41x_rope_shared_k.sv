`timescale 1ns/1ps
module tb_chip_v41x_rope_shared_k;
    localparam HAW=30, TAGW=16;
    localparam [20:0] POS=21'd199999;
    reg clk=0;
    always #5 clk=~clk;
    reg rn=0, pf_v=0;
    wire pf_rdy,pf_done,cache_valid,cache_hold,cache_kind,cache_fault;
    wire [20:0] cache_pos;
    wire [2047:0] cache_pairs;
    reg [119:0] plain_base=0;
    wire [3:0] p_v,p_rdy,p_we,p_sv,p_srdy;
    wire [119:0] p_addr;
    wire [15:0] p_len,p_sbeat;
    wire [63:0] p_tag,p_stag;
    wire [1023:0] p_wdata,p_sdata;
    wire [127:0] p_wstrb;
    wire [31:0] issued,received,stalls,hits;
    reg [63:0] coeff [0:31];
    string dir;
    ot_chip_v41x_rope_hbm_cache #(.HAW(HAW),.TAGW(TAGW)) u_cache (
        .clk(clk),.rst_n(rn),.pf_v(pf_v),.pf_rdy(pf_rdy),.pf_kind(1'b0),
        .pf_pos(POS),.pf_release(1'b0),.pf_done(pf_done),
        .cache_valid(cache_valid),.cache_hold(cache_hold),
        .cache_kind(cache_kind),.cache_pos(cache_pos),.cache_pairs(cache_pairs),
        .table_present(2'b01),.plain_base(plain_base),.yarn_base('0),
        .req_v(p_v),.req_rdy(p_rdy),.req_addr(p_addr),.req_len(p_len),
        .req_tag(p_tag),.req_we(p_we),.req_wdata(p_wdata),.req_wstrb(p_wstrb),
        .rsp_v(p_sv),.rsp_rdy(p_srdy),.rsp_tag(p_stag),.rsp_beat(p_sbeat),
        .rsp_data(p_sdata),.fault(cache_fault),.issued_sectors(issued),
        .received_sectors(received),.stalled_cycles(stalls),.cache_hits(hits));
    reg [1:0] su_src=0;
    reg [29:0] su_addr=0;
    wire su_rope,su_bad;
    wire [31:0] su_data;
    ot_chip_v41x_rope_su_word #(.AW(30),.PW(21)) u_su_word (
        .src(su_src),.addr(su_addr),.cache_valid(cache_valid),
        .cache_hold(cache_hold),.cache_kind(cache_kind),
        .cache_pos(cache_pos),.cache_pairs(cache_pairs),
        .is_rope(su_rope),.bad(su_bad),.data(su_data));

    reg [3:0] w_v=0,b_v=0;
    wire [3:0] w_rdy,b_rdy,w_sv,w_srdy,w_wdone,c_rdy,c_sv,c_wdone;
    wire [63:0] w_stag;
    wire [15:0] w_sbeat;
    wire [1023:0] w_sdata;
    wire [3:0] m_v,m_rdy,m_we,m_wdone,s_v,s_rdy;
    wire [119:0] m_addr;
    wire [15:0] m_len,s_beat;
    wire [63:0] m_tag,s_tag;
    wire [1023:0] m_wdata,s_data;
    wire [127:0] m_wstrb;
    wire mux_fault;
    wire [31:0] rope_grants,rope_wait;
    ot_chip_v41x_kv_rope_reqmux #(.HAW(HAW),.TAGW(TAGW)) u_mux (
        .clk(clk),.rst_n(rn),
        .w_v(w_v),.w_rdy(w_rdy),.w_addr('0),.w_len(16'h1111),
        .w_tag('0),.w_we('0),.w_wdata('0),.w_wstrb('0),
        .w_wr_done(w_wdone),.w_sv(w_sv),.w_srdy(4'hf),
        .w_stag(w_stag),.w_sbeat(w_sbeat),.w_sdata(w_sdata),
        .c_v(4'b0),.c_rdy(c_rdy),.c_addr('0),.c_len('0),
        .c_tag('0),.c_we('0),.c_wdata('0),.c_wstrb('0),
        .c_wr_done(c_wdone),.c_sv(c_sv),.c_srdy(4'hf),
        .c_stag(),.c_sbeat(),.c_sdata(),
        .p_v(p_v),.p_rdy(p_rdy),.p_addr(p_addr),.p_len(p_len),
        .p_tag(p_tag),.p_we(p_we),.p_wdata(p_wdata),.p_wstrb(p_wstrb),
        .p_wr_done(),.p_sv(p_sv),.p_srdy(p_srdy),.p_stag(p_stag),
        .p_sbeat(p_sbeat),.p_sdata(p_sdata),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_len(m_len),
        .m_tag(m_tag),.m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),
        .m_wr_done(m_wdone),.s_v(s_v),.s_rdy(s_rdy),.s_tag(s_tag),
        .s_beat(s_beat),.s_data(s_data),.fault(mux_fault),
        .rope_grants(rope_grants),.rope_wait_cycles(rope_wait));

    wire [3:0] h_v,h_rdy,h_we,r_v,r_rdy,br_v;
    wire [119:0] h_addr;
    wire [15:0] h_len,h_beat;
    wire [67:0] h_tag,r_tag;
    wire [1023:0] h_wdata,r_data;
    wire [127:0] h_wstrb;
    wire [31:0] k_grants [0:3],b_grants [0:3],contended [0:3];
    genvar s;
    generate for(s=0;s<4;s=s+1) begin:g_stack
        wire [15:0] br_tag;
        wire [3:0] br_beat;
        wire [255:0] br_data;
        ot_chip_v41x_hbm_karb #(.NPC(1),.AW(HAW),.TAGW(TAGW)) u_arb (
            .clk(clk),.rst_n(rn),
            .b_v(b_v[s]),.b_rdy(b_rdy[s]),.b_addr(HAW'(1)),
            .b_len(4'd1),.b_tag(TAGW'(3)),.b_we(1'b0),
            .b_wdata('0),.b_wstrb('0),.b_wr_done(),
            .b_rsp_v(br_v[s]),.b_rsp_rdy(1'b1),.b_rsp_tag(br_tag),
            .b_rsp_beat(br_beat),.b_rsp_data(br_data),
            .k_v(m_v[s]),.k_rdy(m_rdy[s]),
            .k_addr(m_addr[s*HAW+:HAW]),.k_len(m_len[s*4+:4]),
            .k_tag(m_tag[s*TAGW+:TAGW]),.k_we(m_we[s]),
            .k_wdata(m_wdata[s*256+:256]),.k_wstrb(m_wstrb[s*32+:32]),
            .k_wr_done(m_wdone[s]),.k_rsp_v(s_v[s]),.k_rsp_rdy(s_rdy[s]),
            .k_rsp_tag(s_tag[s*TAGW+:TAGW]),.k_rsp_beat(s_beat[s*4+:4]),
            .k_rsp_data(s_data[s*256+:256]),
            .h_v(h_v[s]),.h_rdy(h_rdy[s]),.h_addr(h_addr[s*HAW+:HAW]),
            .h_len(h_len[s*4+:4]),.h_tag(h_tag[s*(TAGW+1)+:TAGW+1]),
            .h_we(h_we[s]),.h_wdata(h_wdata[s*256+:256]),
            .h_wstrb(h_wstrb[s*32+:32]),.h_wr_done(1'b0),
            .r_v(r_v[s]),.r_rdy(r_rdy[s]),
            .r_tag(r_tag[s*(TAGW+1)+:TAGW+1]),.r_beat(h_beat[s*4+:4]),
            .r_data(r_data[s*256+:256]),
            .k_grants(k_grants[s]),.b_grants(b_grants[s]),
            .contended(contended[s]));
    end endgenerate

    reg [3:0] pending=0;
    reg [67:0] saved_tag=0;
    reg [1023:0] saved_data=0;
    integer cycles=0,w_replies=0,b_replies=0;
    assign r_v=pending;
    assign r_tag=saved_tag;
    assign r_data=saved_data;
    assign h_beat='0;
    assign h_rdy=~pending | r_rdy;
    always @(posedge clk) if(rn) begin
        cycles<=cycles+1;
        if(cycles>300) $fatal(1,"shared-K timeout");
        for(integer i=0;i<4;i++) begin
            if(w_v[i] && w_rdy[i]) w_v[i]<=0;
            if(b_v[i] && b_rdy[i]) b_v[i]<=0;
            if(w_sv[i] && w_srdy[i]) w_replies<=w_replies+1;
            if(br_v[i]) b_replies<=b_replies+1;
            if(pending[i] && r_rdy[i]) pending[i]<=0;
            if(h_v[i] && h_rdy[i]) begin
                integer phase, idx;
                if(h_we[i] || h_len[i*4+:4]!=1) $fatal(1,"bad read");
                saved_tag[i*(TAGW+1)+:TAGW+1]<=h_tag[i*(TAGW+1)+:TAGW+1];
                saved_data[i*256+:256]<=0;
                if(h_tag[i*(TAGW+1)+TAGW-1 -: 2]==2'b10) begin
                    phase=h_tag[i*(TAGW+1)];
                    if(h_addr[i*HAW+:HAW]!==HAW'(10000+i*100+199999*2+phase))
                        $fatal(1,"bad RoPE sector address");
                    idx=i*8+phase*4;
                    saved_data[i*256+:256]<={coeff[idx+3],coeff[idx+2],coeff[idx+1],coeff[idx]};
                end
                pending[i]<=1;
            end
        end
    end
    initial begin
        if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"DIR missing");
        $readmemh({dir,"/plain200k.hex"},coeff);
        for(integer i=0;i<4;i++) plain_base[i*HAW+:HAW]=HAW'(10000+i*100);
        repeat(5) @(negedge clk);
        rn=1;
        @(negedge clk);pf_v=1;
        @(negedge clk);pf_v=0; w_v=4'hf; b_v=4'hf;
        wait(pf_done);
        @(negedge clk);
        if(!cache_valid || !cache_hold || cache_kind || cache_pos!=POS ||
           cache_fault || mux_fault || issued!=8 || received!=8 ||
           rope_grants!=8 || rope_wait==0 || w_v || b_v)
            $fatal(1,"shared K status mismatch issued=%0d received=%0d grants=%0d wait=%0d",issued,received,rope_grants,rope_wait);
        for(integer i=0;i<32;i++)
            if(cache_pairs[i*64+:64]!==coeff[i]) $fatal(1,"pair mismatch %0d",i);
        for(integer i=0;i<32;i++) begin
            su_addr={2'b10,28'(POS*32+i)};
            su_src=2'd1; #1;
            if(!su_rope || su_bad || su_data!==coeff[i][31:0])
                $fatal(1,"SU cosine mismatch %0d",i);
            su_src=2'd2; #1;
            if(!su_rope || su_bad || su_data!==coeff[i][63:32])
                $fatal(1,"SU sine mismatch %0d",i);
        end
        for(integer i=0;i<4;i++)
            if(k_grants[i]!=3 || b_grants[i]!=1 || contended[i]==0)
                $fatal(1,"arbiter coverage stack=%0d K=%0d B=%0d contention=%0d",i,k_grants[i],b_grants[i],contended[i]);
        $display("ROPE_SHARED_K_PASS sectors=%0d pairs=32 su_reads=64 rope_wait=%0d cycles=%0d",received,rope_wait,cycles);
        $finish;
    end
endmodule
