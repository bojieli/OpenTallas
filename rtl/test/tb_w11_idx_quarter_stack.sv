`timescale 1ns/1ps
// W11 reader-rate bench, QUARTER-PER-STACK layout: stack q holds quarter q's
// keys as one contiguous super-block range (base block BASE + q BSTEP, first
// key at offset q OSTEP of its first super-block -- a ring head), read by one
// ot_hdc_v41x_idx_kstream_range per stack straight into its HBM model; the
// four streams are joined by ot_hdc_v41x_idx_quarter_join.  Every key, lane
// mask, last flag and refusal bit of every beat is checked against the
// sector pattern the HBM model returns.
module tb_w11_idx_quarter_stack #(
    parameter integer NKEYS=65, MAX_CYCLES=400000,
    parameter integer WB=32, GA=24, QD=64, RQD=32, RW=16, MAXSKIP=16, CLK_PS=1000,
    parameter integer BASE=0, BSTEP=1000, OSTEP=136
) (input wire clk,rst_n,cmd_v);
    localparam integer NPC=32,AW=28,HW=20,TAGW=16,LENW=4,BEATW=4,DW=256;
    localparam integer QS=(NKEYS/32)*8;
    reg dump=0;
    wire [3:0] s_busy,s_valid,s_ready;
    wire [4*16-1:0] s_kv;
    wire [4*16*544-1:0] s_key;
    wire [4*48-1:0] s_keys,s_beats;
    wire [4*NPC-1:0] h_req_v,h_req_rdy,h_rsp_v,h_rsp_rdy;
    wire [4*NPC*AW-1:0] h_req_addr;
    wire [4*NPC*LENW-1:0] h_req_len;
    wire [4*NPC*TAGW-1:0] h_req_tag,h_rsp_tag;
    wire [4*NPC*BEATW-1:0] h_rsp_beat;
    wire [4*NPC*DW-1:0] h_rsp_data;
    wire join_busy,join_fault,out_valid;
    wire [63:0] out_kv,out_ref;
    wire [3:0] out_last;
    wire [64*544-1:0] out_key;
    function automatic integer qlen(input integer q);
        qlen=(q==3) ? NKEYS-3*QS : QS;
    endfunction
    function automatic integer ooff(input integer q);  ooff=(q*OSTEP)%1024; endfunction
    function automatic integer obase(input integer q); obase=BASE+q*BSTEP; endfunction
    ot_hdc_v41x_idx_quarter_join join_u (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(30'(NKEYS)),
        .cmd_skip({10'(ooff(3)),10'(ooff(2)),10'(ooff(1)),10'(ooff(0))}),
        .busy(join_busy),.fault(join_fault),
        .i_valid(s_valid),.i_ready(s_ready),.i_kv(s_kv),.i_key(s_key),
        .o_valid(out_valid),.o_ready(1'b1),.o_kv(out_kv),.o_last(out_last),
        .o_key(out_key),.o_ref(out_ref));
    genvar s;
    generate for(s=0;s<4;s=s+1) begin:g_stack
        always @(posedge clk) if(dump) begin : g_dump
            longint rd,act,hit,conf,refs,rmin,rmax;
            rd=0;act=0;hit=0;conf=0;refs=0;rmin=64'h7fffffffffffffff;rmax=0;
            for(integer p=0;p<NPC;p=p+1) begin
                rd+=hm.st_rd[p];act+=hm.st_act[p];hit+=hm.st_hit[p];
                conf+=hm.st_conf[p];refs+=hm.st_ref[p];
                if(hm.st_rd[p]<rmin) rmin=hm.st_rd[p];
                if(hm.st_rd[p]>rmax) rmax=hm.st_rd[p];
            end
            $display("W11_STACK s=%0d rd=%0d act=%0d hit=%0d conf=%0d ref=%0d bp=%0d lat_sum_ps=%0d lat_max_ps=%0d pc_rd_min=%0d pc_rd_max=%0d",
                     s,rd,act,hit,conf,refs,hm.st_bp_cycles,hm.st_rd_lat_sum,hm.st_rd_lat_max,rmin,rmax);
        end
        ot_hdc_v41x_idx_hbm #(.NPC(NPC),.AW(AW),.DW(DW),.MEM_WORDS(1),
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(QD),.RQD(RQD),.RW(RW),.MAXSKIP(MAXSKIP),.CLK_PS(CLK_PS),
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
        localparam integer OFF=(s*OSTEP)%1024;
        ot_hdc_v41x_idx_kstream_range #(.NPC(NPC),.WB(WB),.GA(GA),
            .AW(AW),.HW(HW),.TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.DW(DW)) ks (
            .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v && qlen(s)!=0),
            .cmd_base(HW'(BASE+s*BSTEP)),.cmd_skip(10'(OFF)),
            .cmd_nkeys(30'(qlen(s))),.busy(s_busy[s]),
            .req_v(h_req_v[s*NPC +:NPC]),.req_rdy(h_req_rdy[s*NPC +:NPC]),
            .req_addr(h_req_addr[s*NPC*AW +:NPC*AW]),
            .req_len(h_req_len[s*NPC*LENW +:NPC*LENW]),
            .req_tag(h_req_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_v(h_rsp_v[s*NPC +:NPC]),.rsp_rdy(h_rsp_rdy[s*NPC +:NPC]),
            .rsp_tag(h_rsp_tag[s*NPC*TAGW +:NPC*TAGW]),
            .rsp_beat(h_rsp_beat[s*NPC*BEATW +:NPC*BEATW]),
            .rsp_data(h_rsp_data[s*NPC*DW +:NPC*DW]),
            .o_valid(s_valid[s]),.o_ready(s_ready[s]),
            .o_kv(s_kv[s*16 +:16]),.o_key(s_key[s*16*544 +:16*544]),
            .cnt_keys_streamed(s_keys[s*48 +:48]),
            .cnt_hbm_beats(s_beats[s*48 +:48]));
    end endgenerate
    function automatic [255:0] pat(input [AW-1:0] sec);
        integer w;
        begin for(w=0;w<8;w=w+1)
            pat[32*w +:32]=(sec*32'd8+w)*32'h9E3779B1 ^ 32'h5bd1e995;
        end
    endfunction
    // quarter a, position j of the quarter: local key ooff(a)+j of stack a
    function automatic [543:0] expkey(input integer a,input integer j);
        integer lk,sb,pos;
        reg [AW-1:0] sc,cs;
        reg [255:0] sw;
        begin
            lk=ooff(a)+j; sb=lk/1024; pos=lk%1024;
            sc=AW'((obase(a)+17*sb)*128+pos/8);
            cs=AW'((obase(a)+17*sb+1)*128+2*pos);
            sw=pat(sc);
            expkey={sw[32*(pos%8) +:32],pat(cs+1),pat(cs)};
        end
    endfunction
    function automatic ref_key(input [31:0] scale);
        ref_key=(scale[7:0]>=253 || scale[15:8]>=253 ||
                 scale[23:16]>=253 || scale[31:24]>=253);
    endfunction
    function automatic integer sector_total(input integer dummy);
        integer st,lo,hi,total;
        begin
            total=0;
            for(st=0;st<4;st=st+1) begin
                lo=ooff(st); hi=lo+qlen(st);
                if(hi>lo) total=total+2*(hi-lo)+(hi+7)/8-lo/8;
            end
            sector_total=total;
        end
    endfunction
    localparam integer EXPECTED_SECTORS=sector_total(0);
    integer cycle=0,received=0,checked=0,expected_beats,ql,pos;
    integer stalled_cycles=0,request_stall_cycles=0,output_stall_cycles=0;
    integer i,j,hits,first_out=-1,mid_lo=-1,mid_hi=-1;
    reg [543:0] want;
    reg done=0;
    reg [2:0] finish_wait=0;
    initial expected_beats=(NKEYS-3*QS+15)/16;
    always @(posedge clk) if(done) begin
        if(finish_wait==0) dump<=1; else dump<=0;
        if(finish_wait<2) finish_wait<=finish_wait+1'b1;
        else begin
        for(i=0;i<4;i=i+1)
            if(qlen(i)!=0 && s_keys[i*48 +:48] != ooff(i)+qlen(i))
                $fatal(1,"stream %0d keys=%0d expected=%0d",i,s_keys[i*48 +:48],ooff(i)+qlen(i));
        j=0;
        for(i=0;i<4;i=i+1) j=j+int'(s_beats[i*48 +:48]);
        if(j!=EXPECTED_SECTORS) $fatal(1,"sectors got=%0d expected=%0d",j,EXPECTED_SECTORS);
        if(join_fault || checked!=NKEYS || received!=expected_beats)
            $fatal(1,"final fault=%b checked=%0d received=%0d",join_fault,checked,received);
        $display("W11_FIRST_OUT cycle=%0d mid_lo=%0d mid_hi=%0d mid_beats=%0d",first_out,mid_lo,mid_hi,expected_beats-2*(expected_beats/8));
        $display("W11_CONFIG layout=quarter_stack wb=%0d ga=%0d qd=%0d rqd=%0d rw=%0d maxskip=%0d clk_ps=%0d base=%0d bstep=%0d ostep=%0d",WB,GA,QD,RQD,RW,MAXSKIP,CLK_PS,BASE,BSTEP,OSTEP);
        $display("V41X_FOUR_STACK_PASS n=%0d quantum=0 checked=%0d sectors=%0d cycles=%0d stalled=%0d request_stalls=%0d output_stalls=%0d",NKEYS,checked,j,cycle,stalled_cycles,request_stall_cycles,output_stall_cycles);
        $finish;
        end
    end
    always @(posedge clk) if(rst_n) begin
        cycle<=cycle+1;
        if(cycle>MAX_CYCLES) $fatal(1,"timeout n=%0d checked=%0d received=%0d",NKEYS,checked,received);
        if(join_busy && !out_valid) stalled_cycles<=stalled_cycles+1;
        if(|(h_req_v & ~h_req_rdy)) request_stall_cycles<=request_stall_cycles+1;
        if(|(h_rsp_v & ~h_rsp_rdy)) output_stall_cycles<=output_stall_cycles+1;
        if(out_valid && first_out<0) first_out<=cycle;
        if(out_valid && received==expected_beats/8) mid_lo<=cycle;
        if(out_valid && received==expected_beats-expected_beats/8) mid_hi<=cycle;
        if(out_valid) begin
            hits=0;
            for(integer a=0;a<4;a=a+1) begin
                ql=qlen(a);
                if(out_last[a] !== ((ql==0)?(received==0):(received==(ql-1)/16)))
                    $fatal(1,"last beat=%0d q=%0d",received,a);
                for(integer b=0;b<16;b=b+1) begin
                    pos=received*16+b;
                    if(out_kv[a*16+b] !== (pos<ql))
                        $fatal(1,"mask beat=%0d q=%0d lane=%0d",received,a,b);
                    if(pos<ql) begin
                        want=expkey(a,pos);
                        if(out_key[(a*16+b)*544 +:544] !== want)
                            $fatal(1,"key q=%0d pos=%0d beat=%0d lane=%0d",a,pos,received,b);
                        if(out_ref[a*16+b] !== ref_key(want[543:512]))
                            $fatal(1,"ref q=%0d pos=%0d",a,pos);
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
