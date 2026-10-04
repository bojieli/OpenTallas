`timescale 1ns/1ps
// Source-sized successor facts: 72 table bits + 11 facts + 1 validity at N=8.
// No pipeline stage, bubble or arithmetic state. Stall holds all added state.
module ot_v41_need_lookahead #(parameter integer N=8, SW=$clog2(N), UW=1+3+3+SW+3,
    TB=N*(SW+1)+SW+1) (
    input wire clk, rst_n, go, go_bf, accept,
    input wire [2:0] q,b,j,pos,qlast,plast,
    input wire [SW-1:0] c,
    input wire [6*N-1:0] current_desc,next_desc,q2_desc,seed0,seed1,restart0,restart1,
    output reg [UW-1:0] nx
);
    function automatic [TB-1:0] make_priority(input [N-1:0] live);
        integer i,k; reg found; reg [SW-1:0] first,nextc;
        begin
            make_priority='0;first='0;
            for(k=N-1;k>=0;k=k-1) if(live[k]) first=SW'(k);
            make_priority[N*(SW+1)+:SW]=first;
            make_priority[TB-1]=|live;
            for(i=0;i<N;i=i+1) begin
                found=0;nextc='0;
                for(k=N-1;k>=0;k=k-1) if(live[k] && k>i) begin found=1;nextc=SW'(k);end
                make_priority[(SW+1)*i+:SW+1]={found,nextc};
            end
        end
    endfunction
    (* keep, dont_touch="true" *) reg [TB-1:0] cur_table,nxt_table;
    (* keep, dont_touch="true" *) reg last_unit,has_class,last_round,last_q,last_pos;
    (* keep, dont_touch="true" *) reg [SW-1:0] next_class,first_next;
    (* keep, dont_touch="true" *) reg valid;
    wire [SW-1:0] first_current=cur_table[N*(SW+1)+:SW];
    always @* begin
        nx='0;
        if(valid) begin
            if(!last_unit) nx={1'b1,q,b,c,j+3'd1};
            else if(has_class) nx={1'b1,q,b,next_class,3'd0};
            else if(!(last_round && last_q))
                nx={1'b1,last_round ? q+3'd1:q,b+3'd1,last_round ? first_next:first_current,3'd0};
        end
    end
    wire [2:0] nxq=nx[UW-2-:3], nxb=nx[UW-5-:3];
    wire [SW-1:0] nxc=nx[3+:SW];
    wire [2:0] nxj=nx[2:0];
    wire advance_q=nx[UW-1] && nxq!=q;
    wire restart=accept && !nx[UW-1] && !last_pos;
    reg [TB-1:0] facts_cur,facts_next;
    reg [6*N-1:0] facts_desc;
    reg [2:0] fq,fb,fj,fp;
    reg [SW-1:0] fc;
    always @* begin
        // Default next facts are selected from cached make_priority tables. No live
        // make_priority encoder is in the ordinary accepted-beat recurrence.
        facts_cur=cur_table;facts_next=nxt_table;facts_desc=current_desc;
        fq=nxq;fb=nxb;fc=nxc;fj=nxj;fp=pos;
        if(advance_q) begin
            facts_cur=nxt_table;facts_next=make_priority(q2_desc[N-1:0]);facts_desc=next_desc;
        end
        if(restart) begin
            facts_cur=make_priority(restart0[N-1:0]);facts_next=make_priority(restart1[N-1:0]);facts_desc=restart0;
            fq=0;fb=0;fc=facts_cur[N*(SW+1)+:SW];fj=0;fp=pos+3'd1;
        end
        if(go) begin
            facts_cur=make_priority(seed0[N-1:0]);facts_next=make_priority(seed1[N-1:0]);facts_desc=seed0;
            fq=0;fb=0;fc=facts_cur[N*(SW+1)+:SW];fj=0;fp=0;
        end
    end
    // Data FF intentionally have no reset; async valid isolates them until go.
    always @(posedge clk) if(go || accept) begin
        last_unit <= {1'b0,fj}+4'd1 >= facts_desc[N+4*fc+:4];
        {has_class,next_class} <= facts_cur[(SW+1)*fc+:SW+1];
        first_next <= facts_next[N*(SW+1)+:SW];
        last_round <= fb==3'd7;last_q <= fq==qlast;last_pos <= fp==plast;
        if(go || restart || advance_q) begin cur_table<=facts_cur;nxt_table<=facts_next;end
    end
    always @(posedge clk or negedge rst_n)
        if(!rst_n) valid<=0;
        else if(go) valid<=!go_bf && facts_cur[TB-1];
        else if(accept) valid<=(nx[UW-1] || restart) && facts_cur[TB-1];
`ifdef XNEED_CHECK
    // Use after settling in the connected parent gate. These are assertions,
    // never stimulus or activation/golden injection.
    wire [UW-1:0] expected;
    ot_v41_walk2_w10 #(.N(N)) reference_walker(.q(q),.b(b),.c(c),.j(j),
        .live(current_desc[N-1:0]),.livq1(next_desc[N-1:0]),.cur(current_desc[5*N-1:N]),.qlast(qlast),.nx(expected));
    always @(negedge clk) begin
        #0.001;
        if(rst_n && valid && nx!==expected) begin
            $display("DIFF XNEED q=%0d b=%0d c=%0d j=%0d pos=%0d expected=%h actual=%h",q,b,c,j,pos,expected,nx);
            $fatal(1);
        end
    end
`endif
endmodule
