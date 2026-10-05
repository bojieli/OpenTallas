`timescale 1ns/1ps
module tb_hdc_v41x_idx_reader_score_select_all #(
    parameter integer NKEYS=1040, QUANTUM=64, MAX_CYCLES=200000
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
    wire collector_ready,score_ready,score_valid,score_last,slice_ready;
    wire [3:0] score_kv,score_fault;
    wire [4*16-1:0] score_value,score_index;
    reg buf_valid=0;
    reg [3:0] buf_last;
    reg [63:0] buf_kv,buf_ref;
    reg [64*544-1:0] buf_key;
    reg [29:0] buf_base;
    reg [1:0] subbeat=0,quarter=0;
    assign collector_ready=!buf_valid;
    reg weight_v=0;
    reg [7:0] weight_head=0;
    ot_hdc_v41x_idx_quarter_ranges geom (
        .i_nkeys(30'(NKEYS)),.i_base_block(HW'(0)),
        .o_first_local(first_local),.o_count(count),
        .o_base_block(base_block),.o_skip(skip));
    ot_hdc_v41x_idx_shard_quarter_collect collect (
        .clk(clk),.rst_n(rst_n),.cmd_v(cmd_v),.cmd_nkeys(30'(NKEYS)),
        .busy(collect_busy),.fault(collect_fault),
        .i_valid(stream_valid),.i_ready(stream_ready),.i_kv(stream_kv),
        .i_key(stream_key),.o_valid(out_valid),.o_ready(collector_ready),
        .o_kv(out_kv),.o_last(out_last),.o_key(out_key),.o_ref(out_ref));
    always @(posedge clk) begin
        if(!rst_n) begin weight_v<=0;weight_head<=0;end
        else if(cmd_v) begin weight_v<=1;weight_head<=0;end
        else if(weight_v) begin
            if(weight_head==31) weight_v<=0;
            else weight_head<=weight_head+1'b1;
        end
    end
    wire [3:0] in_kv=buf_kv[16*quarter+4*subbeat +:4];
    wire slice_take=buf_valid && ((|in_kv) ? slice_ready : 1'b1);
    always @(posedge clk) begin
        if(!rst_n) begin buf_valid<=0;subbeat<=0;quarter<=0;end
        else begin
            if(out_valid && collector_ready) begin
                buf_valid<=1;buf_key<=out_key;
                buf_kv<=out_kv;buf_ref<=out_ref;
                buf_last<=out_last;buf_base<=30'(received*16);
                subbeat<=0;quarter<=0;
            end else if(slice_take) begin
                if(subbeat==3) begin
                    subbeat<=0;
                    if(quarter==3) buf_valid<=0;
                    else quarter<=quarter+1'b1;
                end else subbeat<=subbeat+1'b1;
            end
        end
    end
    ot_hdc_v41x_idx_score_slice #(.NK(4),.NB(4),.IH(32),.IW(16),.MD(64)) score (
        .clk(clk),.rst_n(rst_n),.ql_v(weight_v),.ql_head(weight_head),
        .ql_codes(512'd0),.ql_sc(32'd0),.ql_w(16'd0),
        .i_valid(buf_valid && |in_kv),.i_ready(slice_ready),
        .i_last(buf_last[quarter] && subbeat==3),
        .i_first_index(16'(quarter*((NKEYS/32)*8)+buf_base+4*subbeat)),
        .i_kv(in_kv),.i_ref(buf_ref[16*quarter+4*subbeat +:4]),
        .i_keep(in_kv),.i_key(buf_key[(16*quarter+4*subbeat)*544 +:4*544]),
        .o_valid(score_valid),.o_ready(score_ready),.o_last(score_last),
        .o_kv(score_kv),.o_score(score_value),.o_index(score_index),.o_fault(score_fault));
    wire [3:0] sel_valid,sel_last,sel_busy,sel_ready;
    wire [4*4-1:0] sel_lv,sel_ninf;
    wire [4*4*16-1:0] sel_value,sel_index;
    wire [1:0] score_quarter=(score_index[15:0]>=3*((NKEYS/32)*8)) ? 2'd3 :
                             (score_index[15:0]>=2*((NKEYS/32)*8)) ? 2'd2 :
                             (score_index[15:0]>=((NKEYS/32)*8)) ? 2'd1 : 2'd0;
    assign score_ready=sel_ready[score_quarter];
    genvar z;
    generate for(z=0;z<4;z=z+1) begin:g_selector
        wire mem_we,mem_re;
        wire [6:0] mem_waddr,mem_raddr;
        wire [4*33-1:0] mem_wdata;
        reg [4*33-1:0] mem_rdata;
        reg [4*33-1:0] mem[0:127];
        always @(posedge clk) begin
            if(mem_we) mem[mem_waddr]<=mem_wdata;
            if(mem_re) mem_rdata<=mem[mem_raddr];
        end
        ot_hdc_tselect #(.W(4),.VW(16),.IW(16),.K(8),.AW(7)) selector (
            .clk(clk),.rst_n(rst_n),.in_valid(score_valid && score_quarter==z),
            .in_ready(sel_ready[z]),.in_last(score_last),.in_lv(score_kv),
            .in_val(score_value),.in_idx(score_index),.in_k(4'd8),
            .out_valid(sel_valid[z]),.out_last(sel_last[z]),
            .out_lv(sel_lv[z*4 +:4]),.out_val(sel_value[z*64 +:64]),
            .out_idx(sel_index[z*64 +:64]),.out_ninf(sel_ninf[z*4 +:4]),
            .mem_we(mem_we),.mem_waddr(mem_waddr),.mem_wdata(mem_wdata),
            .mem_re(mem_re),.mem_raddr(mem_raddr),.mem_rdata(mem_rdata),
            .busy(sel_busy[z]));
    end endgenerate
    reg [15:0] candidate_idx[0:31],candidate_val[0:31];
    reg merge_go=0;
    integer merge_sent=0,merged=0;
    wire merge_ready,merge_valid,merge_last,merge_busy,merge_mem_we,merge_mem_re;
    wire [3:0] merge_lv,merge_ninf;
    wire [63:0] merge_value,merge_index;
    wire [6:0] merge_mem_waddr,merge_mem_raddr;
    wire [4*33-1:0] merge_mem_wdata;
    reg [4*33-1:0] merge_mem_rdata;
    reg [4*33-1:0] merge_mem[0:127];
    always @(posedge clk) begin
        if(merge_mem_we) merge_mem[merge_mem_waddr]<=merge_mem_wdata;
        if(merge_mem_re) merge_mem_rdata<=merge_mem[merge_mem_raddr];
    end
    wire [63:0] merge_in_idx={candidate_idx[merge_sent+3],candidate_idx[merge_sent+2],
                              candidate_idx[merge_sent+1],candidate_idx[merge_sent]};
    wire [63:0] merge_in_val={candidate_val[merge_sent+3],candidate_val[merge_sent+2],
                              candidate_val[merge_sent+1],candidate_val[merge_sent]};
    ot_hdc_tselect #(.W(4),.VW(16),.IW(16),.K(8),.AW(7)) final_selector (
        .clk(clk),.rst_n(rst_n),.in_valid(merge_go && merge_sent<32),
        .in_ready(merge_ready),.in_last(merge_sent==28),.in_lv(4'hf),
        .in_val(merge_in_val),.in_idx(merge_in_idx),.in_k(4'd8),
        .out_valid(merge_valid),.out_last(merge_last),.out_lv(merge_lv),
        .out_val(merge_value),.out_idx(merge_index),.out_ninf(merge_ninf),
        .mem_we(merge_mem_we),.mem_waddr(merge_mem_waddr),.mem_wdata(merge_mem_wdata),
        .mem_re(merge_mem_re),.mem_raddr(merge_mem_raddr),
        .mem_rdata(merge_mem_rdata),.busy(merge_busy));
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
            .TAGW(TAGW),.LENW(LENW),.BEATW(BEATW),.QD(64),.RQD(32),
            .REFPB(3),.MEM_MODE(0)) hm (
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
        initial hm.mem[0]='0;
        for(q=0;q<4;q=q+1) begin:g_context
            localparam integer I=4*s+q;
            ot_hdc_v41x_idx_kstream_range #(.NPC(NPC),.WB(32),.GA(24),
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
        expkey=544'd0;
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
    integer cycle=0,received=0,checked=0,scored=0,selected[0:3],expected_beats,qs,qlen,pos,g;
    integer stalled_cycles=0,request_stall_cycles=0,output_stall_cycles=0;
    integer collector_stall_cycles=0,stream_stall_cycles=0;
    integer first_handoff=-1,last_handoff=-1,first_score=-1,last_score=-1,last_select=-1;
    reg [NKEYS-1:0] seen='0;
    integer i,j,qidx,first,cnt,hits;
    reg [543:0] want;
    reg done=0;
    reg [2:0] finish_wait=0;
    initial begin
        qs=(NKEYS/32)*8;
        expected_beats=(NKEYS-3*qs+15)/16;
        for(integer t=0;t<4;t=t+1) selected[t]=0;
    end
    always @(posedge clk) if(done) begin
        if(finish_wait<2) finish_wait<=finish_wait+1'b1;
        else begin
        for(i=0;i<16;i=i+1)
            if(count[i*30 +:30]!=0 && stream_keys[i*48 +:48] < count[i*30 +:30])
                $fatal(1,"context underflow i=%0d got=%0d expected=%0d",i,stream_keys[i*48 +:48],count[i*30 +:30]);
        j=0;
        for(i=0;i<16;i=i+1) j=j+int'(stream_beats[i*48 +:48]);
        if(j!=EXPECTED_SECTORS) $fatal(1,"sectors got=%0d expected=%0d",j,EXPECTED_SECTORS);
        if(collect_fault || checked!=NKEYS || scored!=NKEYS || merged!=8 ||
           selected[0]!=8 || selected[1]!=8 || selected[2]!=8 || selected[3]!=8 ||
           received!=expected_beats)
            $fatal(1,"final fault=%b checked=%0d scored=%0d selected=%0d,%0d,%0d,%0d merged=%0d received=%0d",collect_fault,checked,scored,selected[0],selected[1],selected[2],selected[3],merged,received);
        $display("V41X_READER_SCORE_SELECT_ALL_PASS n=%0d checked=%0d scored=%0d selected=%0d,%0d,%0d,%0d merged=%0d sectors=%0d cycles=%0d handoffs=%0d collector_stall=%0d stream_stall=%0d first_score=%0d last_score=%0d last_select=%0d",NKEYS,checked,scored,selected[0],selected[1],selected[2],selected[3],merged,j,cycle,received,collector_stall_cycles,stream_stall_cycles,first_score,last_score,last_select);
        $finish;
        end
    end
    always @(posedge clk) if(rst_n) begin
        cycle<=cycle+1;
        if(cycle>MAX_CYCLES) $fatal(1,"timeout n=%0d checked=%0d received=%0d",NKEYS,checked,received);
        if(collect_busy && !out_valid) stalled_cycles<=stalled_cycles+1;
        if(|(h_req_v & ~h_req_rdy)) request_stall_cycles<=request_stall_cycles+1;
        if(|(h_rsp_v & ~h_rsp_rdy)) output_stall_cycles<=output_stall_cycles+1;
        if(out_valid && !collector_ready) collector_stall_cycles<=collector_stall_cycles+1;
        if(|(stream_valid & ~stream_ready)) stream_stall_cycles<=stream_stall_cycles+1;
        if(score_valid && score_ready) begin
            for(integer si=0;si<4;si=si+1) begin
                g=int'(score_index[16*si +:16]);
                if(!score_kv[si] || score_fault[si] || g>=NKEYS ||
                   score_value[16*si +:16]!==16'd0 || seen[g])
                    $fatal(1,"score index=%0d value=%h fault=%b",score_index[16*si +:16],score_value[16*si +:16],score_fault[si]);
                seen[g]<=1'b1;
            end
            scored<=scored+4;
            if(first_score<0) first_score<=cycle;
            last_score<=cycle;
        end
        if(merge_go && merge_sent<32 && merge_ready) merge_sent<=merge_sent+4;
        if(merge_valid) begin
            hits=0;
            for(integer mi=0;mi<4;mi=mi+1) if(merge_lv[mi]) begin
                if(merged+hits>=8 || merge_index[16*mi +:16]!==16'(merged+hits) ||
                   merge_value[16*mi +:16]!==16'd0)
                    $fatal(1,"global merge index=%0d value=%h",merge_index[16*mi +:16],merge_value[16*mi +:16]);
                hits=hits+1;
            end
            merged<=merged+hits;
            if(merge_last) begin done<=1;last_select<=cycle;end
        end
        for(integer sq=0;sq<4;sq=sq+1) if(sel_valid[sq]) begin
            hits=0;
            for(integer si=0;si<4;si=si+1) if(sel_lv[sq*4+si]) begin
                if(selected[sq]+hits>=8 ||
                   sel_index[(sq*4+si)*16 +:16]!==16'(sq*qs+selected[sq]+hits) ||
                   sel_value[(sq*4+si)*16 +:16]!==16'd0)
                    $fatal(1,"selection q=%0d index=%0d value=%h",sq,sel_index[(sq*4+si)*16 +:16],sel_value[(sq*4+si)*16 +:16]);
                hits=hits+1;
                candidate_idx[sq*8+selected[sq]+hits-1]<=sel_index[(sq*4+si)*16 +:16];
                candidate_val[sq*8+selected[sq]+hits-1]<=sel_value[(sq*4+si)*16 +:16];
            end
            selected[sq]<=selected[sq]+hits;
            if(sel_last[sq] && sq==3) merge_go<=1;
        end
        if(out_valid && collector_ready) begin
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
            if(first_handoff<0) first_handoff<=cycle;
            last_handoff<=cycle;
        end
    end
endmodule

module tb_hdc_v41x_idx_reader_score_select_all_runner;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,cmd_v=0;
    tb_hdc_v41x_idx_reader_score_select_all dut(.clk(clk),.rst_n(rst_n),.cmd_v(cmd_v));
    initial begin
        repeat(4) @(negedge clk);rst_n=1;
        @(negedge clk);cmd_v=1;
        @(negedge clk);cmd_v=0;
    end
endmodule
