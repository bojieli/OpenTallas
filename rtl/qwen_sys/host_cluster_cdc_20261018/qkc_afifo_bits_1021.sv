// Opt-in atomic bit-sliced completion FIFO. Pinned ot_link_afifo is unchanged.
// Independent synchronizers may expose readiness on different edges: every slice
// advances only when ALL can advance. No sibling-pointer visibility assumption.
module qkc_afifo_bits_1021 #(
    parameter integer W=64, AW=4, SYNC=2,
    parameter integer MUT_ROTATE=0,
    parameter integer SKEW_SYNC=0, MUT_UNCOORD=0
)(
    input wire wclk,wrst_n,wr,
    input wire [W-1:0] wdata,
    output wire wfull,output wire [AW:0] wfreed,output wire ovf,
    input wire rclk,rrst_n,rd,
    output wire rempty,output wire [W-1:0] rdata,output wire [W-1:0] rd_valid,output wire [AW:0] rcount
);
    localparam integer LEAVES=1<<$clog2(W), CW=AW+2;
    wire [W-1:0] full_b,empty_b,ovf_b,head;
    wire [(AW+1)*W-1:0] freed_b,count_b;
    assign wfull=|full_b;
    assign rempty=|empty_b;
    wire all_push=wr&&!wfull,all_pop=rd&&!rempty;
    for(genvar b=0;b<W;b=b+1)begin:g_bit
        // SKEW_SYNC is a validation-only model of unequal legal visibility.
        // The release uses SYNC=2 on every original primitive.
        if(AW==4 && SYNC==2 && SKEW_SYNC==0)begin:g_fixed
        qkc_afifo_w1a4s2_1021 u_fifo(
            .wclk(wclk),.wrst_n(wrst_n),.wr((MUT_UNCOORD!=0)?wr:all_push),.wdata(wdata[b]),
            .wfull(full_b[b]),.wfreed(freed_b[(AW+1)*b +: AW+1]),.ovf(ovf_b[b]),
            .rclk(rclk),.rrst_n(rrst_n),.rd((MUT_UNCOORD!=0)?rd:all_pop),.rempty(empty_b[b]),
            .rdata(head[b]),.rcount(count_b[(AW+1)*b +: AW+1])
        );
        end else begin:g_generic
        ot_link_afifo #(.W(1),.AW(AW),.SYNC(SYNC+((SKEW_SYNC!=0)?b%2:0))) u_fifo(
            .wclk(wclk),.wrst_n(wrst_n),.wr((MUT_UNCOORD!=0)?wr:all_push),.wdata(wdata[b]),
            .wfull(full_b[b]),.wfreed(freed_b[(AW+1)*b +: AW+1]),.ovf(ovf_b[b]),
            .rclk(rclk),.rrst_n(rrst_n),.rd((MUT_UNCOORD!=0)?rd:all_pop),.rempty(empty_b[b]),
            .rdata(head[b]),.rcount(count_b[(AW+1)*b +: AW+1])
        );
        end
    end
    // Preserve the original sticky overflow meaning even though blocked writes
    // are suppressed before reaching the slices. Keep every slice fault visible.
    reg ovf_q;
    always @(posedge wclk or negedge wrst_n)
        if(!wrst_n)ovf_q<=1'b0;else if(wr&&wfull)ovf_q<=1'b1;
    assign ovf=ovf_q|(|ovf_b);
    // Read count is the conservative coherent count, never one slice's view.
    wire [AW:0] count_tree[1:2*LEAVES-1];
    wire [CW-1:0] free_tree[1:2*LEAVES-1];
    reg [CW-1:0] pending_free[0:W-1];
    for(genvar b=0;b<LEAVES;b=b+1)begin:g_credit_leaf
        if(b<W)begin:g_real
            assign count_tree[LEAVES+b]=count_b[(AW+1)*b +: AW+1];
            assign free_tree[LEAVES+b]=pending_free[b]+{{(CW-AW-1){1'b0}},freed_b[(AW+1)*b +: AW+1]};
            always @(posedge wclk or negedge wrst_n)
                if(!wrst_n)pending_free[b]<=0;
                else pending_free[b]<=free_tree[LEAVES+b]-free_tree[1];
        end else begin:g_pad
            assign count_tree[LEAVES+b]={AW+1{1'b1}};
            assign free_tree[LEAVES+b]={CW{1'b1}};
        end
    end
    for(genvar n=1;n<LEAVES;n=n+1)begin:g_min
        assign count_tree[n]=(count_tree[2*n]<count_tree[2*n+1])?count_tree[2*n]:count_tree[2*n+1];
        assign free_tree[n]=(free_tree[2*n]<free_tree[2*n+1])?free_tree[2*n]:free_tree[2*n+1];
    end
    // Per-slice freed pulses may arrive on different edges. Retain each slice's
    // unreturned credit until every slice has observed it; min(pulses) would lose
    // credits. Equal visibility reduces exactly to the original pulse/edge.
    assign wfreed=free_tree[1][AW:0];
    assign rcount=count_tree[1];
    assign rd_valid=~empty_b;
    assign rdata=(MUT_ROTATE!=0)?{head[W-2:0],head[W-1]}:head;
endmodule

// Fixed release leaf: keep this ordinary module using existing
// route.synth_keep_modules. The pinned FIFO source remains unchanged and plain
// source CDC elaboration traverses this wrapper to its reviewed original.
module qkc_afifo_w1a4s2_1021(
 input wire wclk,wrst_n,wr,wdata,
 output wire wfull,output wire[4:0]wfreed,output wire ovf,
 input wire rclk,rrst_n,rd,
 output wire rempty,rdata,output wire[4:0]rcount
);
 ot_link_afifo #(.W(1),.AW(4),.SYNC(2)) u_fifo(
  .wclk(wclk),.wrst_n(wrst_n),.wr(wr),.wdata(wdata),.wfull(wfull),.wfreed(wfreed),.ovf(ovf),
  .rclk(rclk),.rrst_n(rrst_n),.rd(rd),.rempty(rempty),.rdata(rdata),.rcount(rcount));
endmodule
