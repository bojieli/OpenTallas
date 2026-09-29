`timescale 1ns/1ps
module tb_chip_v41x_window_attn_source;
    localparam integer BASE=64, COUNT=2*2176, HAW=30, TAGW=16;
    reg clk=0; always #2 clk=~clk;
    reg rst_n=0,prime_v=0,start_v=0,stream_go=0,kv_ready=1;
    reg [9:0] prime_user=0,start_user=0;
    reg [20:0] prime_row=0,start_first=0;
    reg [7:0] start_count=0;
    wire prime_ready,start_ready,staged_v,busy,done,fault,kv_v;
    wire [31:0] refill_cycles,sectors_read;
    wire [7:0] rows_refilled;
    wire [3:0] kv_m,m_v,m_we,s_rdy;
    wire [4*16*265-1:0] kv_w;
    reg [3:0] m_rdy=4'hf,s_v=0;
    wire [4*HAW-1:0] m_addr;
    wire [15:0] m_len;
    wire [4*TAGW-1:0] m_tag;
    wire [1023:0] m_wdata;
    wire [127:0] m_wstrb;
    reg [4*TAGW-1:0] s_tag=0;
    reg [1023:0] s_data=0;
    reg engine_idle=1;
    reg [15:0] active_gen=0;
    wire life_accept,life_issue_ok,life_done,life_fault;
    wire [15:0] life_gen;
    wire [10:0] life_rows,life_beats;
    wire [3:0] life_code;
    reg [255:0] mem [0:BASE+COUNT-1];
    integer hbm_reads=0,beats=0,jobs=0,cycle=0,hold=0,total_hold=0,stages=0;
    integer first_refill_cycles=0,second_refill_cycles=0;
    reg [4*16*265-1:0] held_beat;
    reg [3:0] held_mask;
    wire [15:0] s_beat=0;
    ot_chip_v41x_window_attn_source #(.WIN_STACK(2)) dut (
        .clk(clk),.rst_n(rst_n),
        .region_base_sector(30'(BASE)),.region_sector_count(30'(COUNT)),
        .prime_v(prime_v),.prime_ready(prime_ready),
        .prime_user(prime_user),.prime_row(prime_row),
        .blk_v(1'b0),.blk_ready(),.blk_user(10'd0),.blk_row(21'd0),
        .blk_idx(4'd0),.blk_codes(256'd0),.blk_scale(8'd0),
        .start_v(start_v),.start_ready(start_ready),
        .start_user(start_user),.start_first(start_first),.start_count(start_count),
        .staged_v(staged_v),.stream_go(stream_go),
        .busy(busy),.done(done),.fault(fault),
        .refill_cycles(refill_cycles),.sectors_read(sectors_read),
        .rows_refilled(rows_refilled),.kv_v(kv_v),.kv_ready(kv_ready),
        .kv_m(kv_m),.kv_w(kv_w),
        .m_v(m_v),.m_rdy(m_rdy),.m_addr(m_addr),.m_len(m_len),
        .m_tag(m_tag),.m_we(m_we),.m_wdata(m_wdata),.m_wstrb(m_wstrb),
        .m_wr_done(4'd0),.s_v(s_v),.s_rdy(s_rdy),
        .s_tag(s_tag),.s_beat(s_beat),.s_data(s_data));
    ot_chip_v41x_attn_desc_lifecycle #(.L0_ONLY(1)) u_life (
        .clk(clk),.rst_n(rst_n),
        .desc_v(start_v && start_count==8'd128),
        .desc_user(start_user),.desc_pos(start_first+21'd127),
        .desc_tiles(21'd128),.desc_k(21'd128),.desc_nout(21'd128),
        .desc_wbase(30'd0),.desc_ts(30'd1),.desc_ks(30'd0),.desc_js(30'd0),
        .desc_hg(2'd0),.desc_mmode(1'b1),
        .desc_accept(life_accept),.desc_gen(life_gen),.desc_rows(life_rows),
        .stage_v(staged_v),.stage_gen(active_gen),.stage_rows(11'd128),
        .beat_v(kv_v),.beat_ready(kv_ready),.beat_gen(active_gen),.beat_mask(kv_m),
        .issue_v(stream_go),.engine_idle(engine_idle),
        .service_fault(fault && start_count==8'd128),.wrap_drained(!busy),
        .issue_ok(life_issue_ok),.done(life_done),.fault(life_fault),
        .fault_code(life_code),.beats_accepted(life_beats));
    function automatic [255:0] codes(input integer row,input integer sec);
        reg [255:0] c;
        begin
            c=0;
            for(integer n=0;n<32;n=n+1)
                c[8*n +: 8]=8'(1+((row*3+sec+n)%100));
            codes=c;
        end
    endfunction
    function automatic [7:0] scale(input integer row,input integer g);
        scale=8'(1+((row+g)%200));
    endfunction
    task automatic prime(input integer p,input integer u);
        begin
            while(!prime_ready) @(negedge clk);
            @(negedge clk); prime_v=1; prime_row=21'(p); prime_user=10'(u);
            @(negedge clk); prime_v=0;
        end
    endtask
    task automatic launch(input integer p,input integer u,input integer n);
        begin
            while(!start_ready) @(negedge clk);
            @(negedge clk); start_v=1; start_first=21'(p);
            start_user=10'(u); start_count=8'(n);
            @(negedge clk); start_v=0;
        end
    endtask
    always @(posedge clk) begin
        cycle<=cycle+1;
        s_v<=0;
        if(life_accept) active_gen<=life_gen;
        if(stream_go) engine_idle<=0;
        if(done) engine_idle<=1;
        if(rst_n && m_v[2] && m_rdy[2]) begin
            if(m_we[2] || m_len[2*4 +: 4]!=4'd1 ||
                m_addr[2*HAW +: HAW]<BASE || m_addr[2*HAW +: HAW]>=BASE+COUNT)
                $fatal(1,"bad real HBM sector request");
            s_tag[2*TAGW +: TAGW]<=m_tag[2*TAGW +: TAGW];
            s_data[2*256 +: 256]<=mem[m_addr[2*HAW +: HAW]];
            s_v[2]<=1; hbm_reads<=hbm_reads+1;
        end
        if(rst_n && kv_v) begin
            if(stages != jobs+1) $fatal(1,"packed beat before staged notification");
            if(beats==0 && jobs==0) first_refill_cycles<=refill_cycles;
            if(beats==0 && jobs==1) second_refill_cycles<=refill_cycles;
            if(sectors_read != (jobs+1)*2176 || rows_refilled != 128)
                $fatal(1,"packed beat before complete HBM refill");
            if(kv_m!==4'hf) $fatal(1,"non-full WINDOW beat");
            for(integer lane=0;lane<4;lane=lane+1)
                for(integer g=0;g<16;g=g+1) begin
                    if(kv_w[(lane*16+g)*265 +: 265] !==
                        {1'b0,scale(126+beats*4+lane,g),codes(126+beats*4+lane,g)})
                        $fatal(1,"packed row mismatch job%0d beat%0d lane%0d group%0d",
                               jobs,beats,lane,g);
                end
            if(!kv_ready) begin
                if(hold>0 && (kv_w!==held_beat || kv_m!==held_mask))
                    $fatal(1,"packed beat changed under backpressure");
                held_beat<=kv_w; held_mask<=kv_m; hold<=hold+1;
                total_hold<=total_hold+1;
            end else beats<=beats+1;
        end
        if(done) begin
            if(beats!=32) $fatal(1,"job finished before 32 accepted beats");
            jobs<=jobs+1; beats<=0; hold<=0;
        end
        if(staged_v) stages<=stages+1;
    end
    initial begin
        for(integer i=0;i<BASE+COUNT;i=i+1) mem[i]=0;
        for(integer row=126;row<254;row=row+1) begin
            for(integer sec=0;sec<16;sec=sec+1)
                mem[BASE+17*(row%128)+sec]=codes(row,sec);
            for(integer g=0;g<16;g=g+1)
                mem[BASE+17*(row%128)+16][8*g +: 8]=scale(row,g);
        end
        repeat(4) @(negedge clk); rst_n=1;
        for(integer row=126;row<254;row=row+1) prime(row,0);
        launch(126,0,128);
        wait(stages==1); repeat(3) @(negedge clk);
        if(kv_v || fault) $fatal(1,"early beat before issue");
        if(!life_issue_ok || life_fault || life_rows!=128)
            $fatal(1,"descriptor not ready after 128 staged rows");
        stream_go=1; @(negedge clk); stream_go=0;
        while(!kv_v) @(negedge clk);
        kv_ready=0; repeat(3) @(negedge clk); kv_ready=1;
        wait(jobs==1); wait(life_done);
        if(life_beats!=32 || life_fault) $fatal(1,"lifecycle QK beat count/fault");
        launch(126,0,128); // same HBM rows, PV replay lifetime
        wait(stages==2); repeat(3) @(negedge clk);
        if(kv_v || fault) $fatal(1,"early replay beat before issue");
        if(!life_issue_ok || life_fault) $fatal(1,"lifecycle PV stage failed");
        stream_go=1; @(negedge clk); stream_go=0;
        wait(jobs==2); wait(life_done);
        if(life_beats!=32 || life_fault) $fatal(1,"lifecycle PV beat count/fault");
        if(hbm_reads!=4352 || sectors_read!=4352 || fault || total_hold<3)
            $fatal(1,"HBM service count/fault mismatch");
        prime(254,1); // overwrites absolute row 126's ring tag
        launch(126,0,1);
        wait(fault); repeat(2) @(negedge clk);
        if(kv_v || jobs!=2) $fatal(1,"stale cross-user ring row leaked");
        $display("WINDOW_ATTN_SOURCE_PASS jobs=2 rows=256 sectors=4352 beats=64 full=1 backpressure=3 stale_fault=1 refill0=%0d refill1=%0d",first_refill_cycles,second_refill_cycles);
        $finish;
    end
    initial begin #3000000; $fatal(1,"WINDOW-only attention source timeout"); end
endmodule
