`timescale 1ns/1ps
module tb_hdc_v41x_idx_score_select_checkpoint;
    localparam NK=4,NB=1,IW=16,N=40,K=8,AW=4;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,ql_v=0,i_valid=0,i_last=0;
    reg [7:0] ql_head=0;
    reg [127:0] ql_codes=0;
    reg [7:0] ql_sc=0;
    reg [15:0] ql_w=0;
    reg [IW-1:0] i_first_index=0;
    reg [NK-1:0] i_kv=0,i_ref=0,i_keep=0;
    reg [NK*136-1:0] i_key=0;
    wire i_ready,score_v,score_ready,sel_ready,score_last,ql_ready;
    wire [NK-1:0] score_kv,score_fault;
    wire [NK*16-1:0] score_val;
    wire [NK*IW-1:0] score_idx;
    reg [151:0] qmem[0:63];
    reg [136:0] kmem[0:79];
    reg [16:0] emem[0:79];
    reg [15:0] topidx[0:15],topval[0:15];
    integer case_no,head,beat,lane,hits,gap_cycles,cycles=0,scores_seen=0,selected=0,score_stalls=0,select_segments=0;
    integer first_score=-1,last_score=-1,first_select=-1,last_select=-1;
    wire gate_ready=(cycles%7)!=0;
    assign score_ready=sel_ready && gate_ready;

    ot_hdc_v41x_idx_score_slice #(.NK(NK),.NB(NB),.IW(IW),.MD(64)) score (
        .clk(clk),.rst_n(rst_n),.ql_v(ql_v),.ql_ready(ql_ready),.ql_head(ql_head),
        .ql_codes(ql_codes),.ql_sc(ql_sc),.ql_w(ql_w),
        .i_valid(i_valid),.i_ready(i_ready),.i_last(i_last),
        .i_first_index(i_first_index),.i_kv(i_kv),.i_ref(i_ref),
        .i_keep(i_keep),.i_key(i_key),
        .o_valid(score_v),.o_ready(score_ready),.o_last(score_last),
        .o_kv(score_kv),.o_score(score_val),.o_index(score_idx),.o_fault(score_fault));
    wire sel_v,sel_last,sel_busy,mem_we,mem_re;
    wire [NK-1:0] sel_lv,sel_ninf;
    wire [NK*16-1:0] sel_val,sel_idx;
    wire [AW-1:0] mem_waddr,mem_raddr;
    wire [NK*(1+16+IW)-1:0] mem_wdata;
    reg [NK*(1+16+IW)-1:0] mem_rdata;
    reg [NK*(1+16+IW)-1:0] mem[0:(1<<AW)-1];
    always @(posedge clk) begin
        if(mem_we) mem[mem_waddr]<=mem_wdata;
        if(mem_re) mem_rdata<=mem[mem_raddr];
    end
    ot_hdc_tselect #(.W(NK),.VW(16),.IW(IW),.K(K),.AW(AW)) sel (
        .clk(clk),.rst_n(rst_n),.in_valid(score_v && gate_ready),.in_ready(sel_ready),
        .in_last(score_last),.in_lv(score_kv),.in_val(score_val),
        .in_idx(score_idx),.in_k(4'(K)),
        .out_valid(sel_v),.out_last(sel_last),.out_lv(sel_lv),
        .out_val(sel_val),.out_idx(sel_idx),.out_ninf(sel_ninf),
        .mem_we(mem_we),.mem_waddr(mem_waddr),.mem_wdata(mem_wdata),
        .mem_re(mem_re),.mem_raddr(mem_raddr),.mem_rdata(mem_rdata),.busy(sel_busy));

    always @(posedge clk) if(rst_n) begin
        cycles<=cycles+1;
        if(cycles>2000) $fatal(1,"timeout score=%0d selected=%0d",scores_seen,selected);
        if(score_v && !score_ready) score_stalls<=score_stalls+1;
        if(score_v && score_ready) begin
            for(integer j=0;j<NK;j=j+1) begin
                if(!score_kv[j] || score_fault[j] ||
                   score_idx[IW*j +: IW]!==IW'(scores_seen%N+j) ||
                   score_val[16*j +: 16]!==emem[scores_seen+j][15:0])
                    $fatal(1,"score mismatch index=%0d got=%h expected=%h",
                           scores_seen+j,score_val[16*j +:16],emem[scores_seen+j][15:0]);
            end
            if(score_last!==(scores_seen%N==N-NK)) $fatal(1,"score last mismatch");
            if(first_score<0) first_score<=cycles;
            last_score<=cycles;
            scores_seen<=scores_seen+NK;
        end
        if(sel_v) begin
            hits=0;
            for(integer j=0;j<NK;j=j+1) if(sel_lv[j]) begin
                if(selected+hits>=2*K || sel_idx[IW*j +: IW]!==topidx[selected+hits] ||
                   sel_val[16*j +: 16]!==topval[selected+hits])
                    $fatal(1,"topK mismatch selected=%0d idx=%0d val=%h expected=%0d/%h",
                           selected+hits,sel_idx[IW*j +: IW],sel_val[16*j +:16],
                           topidx[selected+hits],topval[selected+hits]);
                hits=hits+1;
            end
            selected<=selected+hits;
            if(sel_last) select_segments<=select_segments+1;
            if(first_select<0) first_select<=cycles;
            last_select<=cycles;
        end
    end
    initial begin
        if(!$value$plusargs("GAP=%d",gap_cycles)) gap_cycles=-1;
        $readmemh("idx_q.mem",qmem);
        $readmemh("idx_k.mem",kmem);
        $readmemh("idx_e.mem",emem);
        $readmemh("top_idx.mem",topidx);
        $readmemh("top_val.mem",topval);
        repeat(4) @(negedge clk);rst_n=1;
        for(case_no=0;case_no<2;case_no=case_no+1) begin
            for(head=0;head<32;head=head+1) begin
                ql_v=1;ql_head=head;
                {ql_w,ql_sc,ql_codes}=qmem[case_no*32+head];
                @(negedge clk);
            end
            ql_v=0;repeat(4) @(negedge clk);
            for(beat=0;beat<N/NK;beat=beat+1) begin
                i_valid=1;i_last=beat==N/NK-1;i_first_index=beat*NK;
                i_kv='1;i_ref=0;
                for(lane=0;lane<NK;lane=lane+1) begin
                    i_key[lane*136 +: 136]=kmem[case_no*N+beat*NK+lane][135:0];
                    i_keep[lane]=kmem[case_no*N+beat*NK+lane][136];
                end
                do @(posedge clk); while(!i_ready);
                @(negedge clk);
            end
            i_valid=0;
            if(gap_cycles<0) begin
                wait(ql_ready);
                @(negedge clk);
            end else repeat(gap_cycles) @(negedge clk);
        end
        wait(selected==2*K);
        repeat(4) @(negedge clk);
        if(scores_seen!=2*N || select_segments!=2)
            $fatal(1,"score/ready coverage scores=%0d stalls=%0d segments=%0d",scores_seen,score_stalls,select_segments);
        $display("PASS checkpoint score+topK scores=%0d selected=%0d cycles=%0d score_stalls=%0d first_score=%0d last_score=%0d first_select=%0d last_select=%0d",
                 scores_seen,selected,cycles,score_stalls,first_score,last_score,first_select,last_select);
        $finish;
    end
endmodule
