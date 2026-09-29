`timescale 1ns/1ps
module tb_w11_idx_reader_rate #(
    parameter integer NKEYS=65, QUANTUM=1, MAX_CYCLES=400000,
    // reader configuration; defaults are the legacy four-stack gate
    parameter integer WB=32, GA=24, QD=64, RQD=32, RW=16, MAXSKIP=16, CLK_PS=1000, COLLECT=0,
    parameter longint REFI_PS=3900000  // diagnostic only; the model default
) (input wire clk,rst_n,cmd_v);
    localparam integer NPC=32,AW=28,HW=20,TAGW=16,LENW=4,BEATW=4,DW=256;
    wire [16*30-1:0] first_local,count;
    wire [16*HW-1:0] base_block;
    wire [16*10-1:0] skip;
    wire [15:0] stream_busy,stream_valid,stream_ready;
    wire [16*16-1:0] stream_kv;
    wire [16*16*544-1:0] stream_key;
    wire [16*48-1:0] stream_keys,stream_beats;
    wire [4*32-1:0] h_req_v,h_req_rdy,h_rsp_v,h_rsp_rdy;
    wire [4*32*AW-1:0] h_req_addr;
    wire [4*32*LENW-1:0] h_req_len;
    wire [4*32*TAGW-1:0] h_req_tag,h_rsp_tag;
    wire [4*32*BEATW-1:0] h_rsp_beat;
    wire [4*32*DW-1:0] h_rsp_data;
    wire [4*4*32-1:0] c_req_v,c_req_rdy,c_rsp_v,c_rsp_rdy;
    wire [4*4*32*AW-1:0] c_req_addr;
    wire [4*4*32*LENW-1:0] c_req_len;
    wire [4*4*32*TAGW-1:0] c_req_tag,c_rsp_tag;
    wire [4*4*32*BEATW-1:0] c_rsp_beat;
    wire [4*4*32*DW-1:0] c_rsp_data;
    wire [4*32-1:0] grants;
    wire collect_busy,collect_fault,out_valid;
    wire [63:0] out_kv,out_ref;
    wire [3:0] out_last;
    wire [64*544-1:0] out_key;
    reg dump=0;
    ot_hdc_v41x_idx_quarter_ranges geom (
        .i_nkeys(30'(NKEYS)),.i_base_block(HW'(0)),
        .o_first_local(first_local),.o_count(count),
        .o_base_block(base_block),.o_skip(skip));
    generate if(COLLECT==0) begin:g_col_legacy
    ot_hdc_v41x_idx_shard_quarter_collect collect (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(30'(NKEYS)),
        .busy(collect_busy),.fault(collect_fault),
        .i_valid(stream_valid),.i_ready(stream_ready),.i_kv(stream_kv),
        .i_key(stream_key),.o_valid(out_valid),.o_ready(1'b1),
        .o_kv(out_kv),.o_last(out_last),.o_key(out_key),.o_ref(out_ref));
    end else begin:g_col_pipe
    ot_hdc_v41x_idx_quarter_collect_pipe collect (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(30'(NKEYS)),
        .busy(collect_busy),.fault(collect_fault),
        .i_valid(stream_valid),.i_ready(stream_ready),.i_kv(stream_kv),
        .i_key(stream_key),.o_valid(out_valid),.o_ready(1'b1),
        .o_kv(out_kv),.o_last(out_last),.o_key(out_key),.o_ref(out_ref));
    end endgenerate
    genvar s,q;
    generate for(s=0;s<4;s=s+1) begin:g_stack
        ot_hdc_v41x_idx_range_pc_arb #(.NPC(NPC),.AW(AW),.LENW(LENW),
            .TAGW(TAGW),.BEATW(BEATW),.DW(DW),.QUANTUM(QUANTUM)) arb (
            .clk(clk),.rst_n(rst_n),
            .i_req_v(c_req_v[s*4*NPC +:4*NPC]),.i_req_rdy(c_req_rdy[s*4*NPC +:4*NPC]),
            .i_req_addr(c_req_addr[s*4*NPC*AW +:4*NPC*AW]),
            .i_req_len(c_req_len[s*4*NPC*LENW +:4*NPC*LENW]),
            .i_req_tag(c_req_tag[s*4*NPC*TAGW +:4*NPC*TAGW]),
            .h_req_v(h_req_v[s*NPC +:NPC]),.h_req_rdy(h_req_rdy[s*NPC +:NPC]),
            .h_req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .h_req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .h_req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .h_rsp_v(h_rsp_v[s*NPC +:NPC]),.h_rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .h_rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .h_rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .h_rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_rsp_v(c_rsp_v[s*4*NPC +:4*NPC]),
            .o_rsp_rdy(c_rsp_rdy[s*4*NPC +:4*NPC]),
            .o_rsp_tag(c_rsp_tag[s*4*NPC*TAGW +:4*NPC*TAGW]),
            .o_rsp_beat(c_rsp_beat[s*4*NPC*BEATW +:4*NPC*BEATW]),
            .o_rsp_data(c_rsp_data[s*4*NPC*DW +:4*NPC*DW]),
            .dbg_grants(grants[s*32 +:32]));
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(1),
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(QD),.RQD(RQD),.RW(RW),.MAXSKIP(MAXSKIP),.CLK_PS(CLK_PS),.REFI_PS(REFI_PS),
            .REFPB(3),.MEM_MODE(1)) hm (
            .clk(clk),.rst_n(rst_n),.req_v(h_req_v[s*NPC +:NPC]),
            .req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .req_we({NPC{1'b0}}),.req_wdata({NPC*DW{1'b0}}),
            .req_wstrb({NPC*32{1'b0}}),.wr_done(),
            .rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]));
        // per-stack HBM statistics, printed once at the end
        always @(posedge clk) if(dump) begin : g_dump
            longint rd,act,hit,conf,refs,latsum,rmin,rmax;
            rd=0;act=0;hit=0;conf=0;refs=0;rmin=64'h7fffffffffffffff;rmax=0;
            for(integer p=0;p<NPC;p=p+1) begin
                rd+=hm.st_rd[p];act+=hm.st_act[p];hit+=hm.st_hit[p];
                conf+=hm.st_conf[p];refs+=hm.st_ref[p];
                if(hm.st_rd[p]<rmin) rmin=hm.st_rd[p];
                if(hm.st_rd[p]>rmax) rmax=hm.st_rd[p];
            end
            $display("W11_STACK s=%0d rd=%0d act=%0d hit=%0d conf=%0d ref=%0d bp=%0d lat_sum_ps=%0d lat_max_ps=%0d pc_rd_min=%0d pc_rd_max=%0d grants=%0d",
                     s,rd,act,hit,conf,refs,hm.st_bp_cycles,hm.st_rd_lat_sum,hm.st_rd_lat_max,rmin,rmax,grants[s*32 +:32]);
        end
        for(q=0;q<4;q=q+1) begin:g_context
            localparam integer I=4*s+q;
            ot_hdc_v41x_idx_kstream_range #(.NPC(NPC),.WB(WB),.GA(GA),
                .AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
                .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v && count[I*30 +:30]!=0),
                .cmd_base(base_block[I*HW +:HW]),.cmd_skip(skip[I*10 +:10]),
                .cmd_nkeys(count[I*30 +:30]),.busy(stream_busy[I]),
                .req_v(c_req_v[I*NPC +:NPC]),.req_rdy(c_req_rdy[I*NPC +:NPC]),
                .req_addr(c_req_addr[I*NPC*AW +:NPC*AW]),
                .req_len(c_req_len[I*NPC*LENW +:NPC*LENW]),
                .req_tag(c_req_tag[I*NPC*TAGW +:NPC*TAGW]),
                .rsp_v(c_rsp_v[I*NPC +:NPC]),.rsp_rdy(c_rsp_rdy[I*NPC +:NPC]),
                .rsp_tag(c_rsp_tag[I*NPC*TAGW +:NPC*TAGW]),
                .rsp_beat(c_rsp_beat[I*NPC*BEATW +:NPC*BEATW]),
                .rsp_data(c_rsp_data[I*NPC*DW +:NPC*DW]),
                .o_valid(stream_valid[I]),.o_ready(stream_ready[I]),
                .o_kv(stream_kv[I*16 +:16]),.o_key(stream_key[I*16*544 +:16*544]),
                .cnt_keys_streamed(stream_keys[I*48 +:48]),
                .cnt_hbm_beats(stream_beats[I*48 +:48]));
        end
    end endgenerate
    function automatic [255:0] pat(input [AW-1:0] sec);
        integer w;
        begin for(w=0;w<8;w=w+1)
            pat[32*w +:32]=(sec*32'd8+w)*32'h9E3779B1 ^ 32'h5bd1e995;
        end
    endfunction
    function automatic [543:0] expkey(input integer g);
        integer stack,local_key,sb,pos;
        reg [AW-1:0] sc,cs;
        reg [255:0] sw;
        begin
            stack=(g%64)/16;
            local_key=(g/64)*16+(g%16);
            sb=local_key/1024;pos=local_key%1024;
            sc=AW'(2176*sb+pos/8);
            cs=AW'(2176*sb+128+2*pos);
            sw=pat(sc);
            expkey={sw[32*(pos%8) +:32],pat(cs+1),pat(cs)};
        end
    endfunction
    function automatic ref_key(input [31:0] scale);
        ref_key=(scale[7:0]>=253 || scale[15:8]>=253 ||
                 scale[23:16]>=253 || scale[31:24]>=253);
    endfunction
    function automatic integer rank(input integer x,input integer stack);
        integer t;
        begin t=x%64-16*stack;if(t<0)t=0;if(t>16)t=16;rank=(x/64)*16+t;end
    endfunction
    function automatic integer sector_total(input integer n);
        integer st,quarter,qs0,lo,hi,total;
        begin
            qs0=(n/32)*8;total=0;
            for(st=0;st<4;st=st+1)
                for(quarter=0;quarter<4;quarter=quarter+1) begin
                    lo=rank(quarter*qs0,st);
                    hi=rank(quarter==3?n:(quarter+1)*qs0,st);
                    if(hi>lo) total=total+2*(hi-lo)+(hi+7)/8-lo/8;
                end
            sector_total=total;
        end
    endfunction
    localparam integer EXPECTED_SECTORS=sector_total(NKEYS);
    integer cycle=0,received=0,checked=0,expected_beats,qs,qlen,pos,g;
    integer stalled_cycles=0,request_stall_cycles=0,output_stall_cycles=0;
    integer i,j,qidx,first,cnt,hits;
    reg [543:0] want;
    reg done=0;
    integer ctx_blocked [0:15];
    integer ctx_idle [0:15];
    integer first_out=-1, mid_lo=-1, mid_hi=-1;
    initial for(integer z=0;z<16;z=z+1) begin ctx_blocked[z]=0; ctx_idle[z]=0; end
    reg [2:0] finish_wait=0;
    initial begin
        qs=(NKEYS/32)*8;
        expected_beats=(NKEYS-3*qs+15)/16;
    end
    always @(posedge clk) if(done) begin
        if(finish_wait==0) dump<=1; else dump<=0;
        if(finish_wait<2) finish_wait<=finish_wait+1'b1;
        else begin
        for(i=0;i<16;i=i+1)
            if(count[i*30 +:30]!=0 && stream_keys[i*48 +:48] < count[i*30 +:30])
                $fatal(1,"context underflow i=%0d got=%0d expected=%0d",i,stream_keys[i*48 +:48],count[i*30 +:30]);
        j=0;
        for(i=0;i<16;i=i+1) j=j+int'(stream_beats[i*48 +:48]);
        if(j!=EXPECTED_SECTORS) $fatal(1,"sectors got=%0d expected=%0d",j,EXPECTED_SECTORS);
        if(collect_fault || checked!=NKEYS || received!=expected_beats)
            $fatal(1,"final fault=%b checked=%0d received=%0d",collect_fault,checked,received);
        for(i=0;i<16;i=i+1) $display("W11_CTX i=%0d blocked=%0d idle=%0d",i,ctx_blocked[i],ctx_idle[i]);
        $display("W11_FIRST_OUT cycle=%0d mid_lo=%0d mid_hi=%0d mid_beats=%0d",first_out,mid_lo,mid_hi,expected_beats-2*(expected_beats/8));
        $display("W11_CONFIG wb=%0d ga=%0d qd=%0d rqd=%0d rw=%0d maxskip=%0d clk_ps=%0d collect=%0d quantum=%0d",WB,GA,QD,RQD,RW,MAXSKIP,CLK_PS,COLLECT,QUANTUM);
        $display("V41X_FOUR_STACK_PASS n=%0d quantum=%0d checked=%0d sectors=%0d cycles=%0d stalled=%0d request_stalls=%0d output_stalls=%0d",NKEYS,QUANTUM,checked,j,cycle,stalled_cycles,request_stall_cycles,output_stall_cycles);
        $finish;
        end
    end
    always @(posedge clk) if(rst_n) begin
        cycle<=cycle+1;
        if(cycle>MAX_CYCLES) $fatal(1,"timeout n=%0d checked=%0d received=%0d",NKEYS,checked,received);
        if(collect_busy && !out_valid) stalled_cycles<=stalled_cycles+1;
        if(|(h_req_v & ~h_req_rdy)) request_stall_cycles<=request_stall_cycles+1;
        if(|(h_rsp_v & ~h_rsp_rdy)) output_stall_cycles<=output_stall_cycles+1;
        for(integer z=0;z<16;z=z+1) begin
            if(stream_valid[z] && !stream_ready[z]) ctx_blocked[z]<=ctx_blocked[z]+1;
            if(stream_busy[z] && !stream_valid[z]) ctx_idle[z]<=ctx_idle[z]+1;
        end
        if(out_valid && first_out<0) first_out<=cycle;
        if(out_valid && received==expected_beats/8) mid_lo<=cycle;
        if(out_valid && received==expected_beats-expected_beats/8) mid_hi<=cycle;
        if(out_valid) begin
            hits=0;
            for(integer a=0;a<4;a=a+1) begin
                qlen=(a==3)?NKEYS-3*qs:qs;
                if(out_last[a] !== ((qlen==0)?(received==0):(received==(qlen-1)/16)))
                    $fatal(1,"last beat=%0d q=%0d",received,a);
                for(integer b=0;b<16;b=b+1) begin
                    pos=received*16+b;
                    if(out_kv[a*16+b] !== (pos<qlen))
                        $fatal(1,"mask beat=%0d q=%0d lane=%0d",received,a,b);
                    if(pos<qlen) begin
                        g=a*qs+pos;want=expkey(g);
                        if(out_key[(a*16+b)*544 +:544] !== want)
                            $fatal(1,"key g=%0d beat=%0d q=%0d lane=%0d",g,received,a,b);
                        if(out_ref[a*16+b] !== ref_key(want[543:512]))
                            $fatal(1,"ref g=%0d",g);
                        hits=hits+1;
                    end else if(out_key[(a*16+b)*544 +:544] !== 544'd0 || out_ref[a*16+b] !== 0)
                        $fatal(1,"padding beat=%0d q=%0d lane=%0d",received,a,b);
                end
            end
            received<=received+1;
            checked<=checked+hits;
            if(received+1==expected_beats) done<=1;
        end
    end
endmodule
