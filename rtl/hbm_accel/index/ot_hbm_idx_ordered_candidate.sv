`timescale 1ns/1ps
`default_nettype none
// Additive native candidate leaf. Native fixed quarters admit at most 171
// two-block beats each; four real 256-line SRAM FIFOs can retain the complete
// frame even with zero output credits. The scorer/selector credit loop is not
// changed. Every input lands in a register, every output leaves a register.
// Exact native max8 tree and literal-global-newest pin; no local-last pin.
module ot_hbm_idx_ordered_candidate #(
    parameter integer OCRED=8,
    parameter integer MUT=0
) (
    input wire ck, rst,
    input wire [89:0] fs,
    input wire [2439:0] si,
    input wire [1:0] selector_ev,
    output reg [71:0] co,
    input wire coc,
    output reg [1:0] ev,
    output reg co_quarter_last
);
    reg fsv, cocv;
    reg [88:0] fsd;
    reg [3:0] siv;
    reg [608:0] sid[0:3];
    reg [1:0] selector_ev_q;
    integer i;
    always @(posedge ck or negedge rst)
        if (!rst) begin fsv<=0; cocv<=0; siv<=0; selector_ev_q<=0; end
        else begin fsv<=fs[0]; cocv<=coc; selector_ev_q<=selector_ev;
            for (i=0;i<4;i=i+1) siv[i]<=si[610*i];
        end
    always @(posedge ck) begin
        fsd<=fs[89:1];
        for (i=0;i<4;i=i+1) sid[i]<=si[610*i+1 +:609];
    end
    reg active, fault;
    reg frame_active, selector_done, candidate_done;
    reg [19:0] pos;
    reg [6:0] rank;
    reg [13:0] ndie;
    reg [1:0] cq;
    reg [$clog2(OCRED+1)-1:0] credit;
    wire start=fsv && fsd[87];
    wire fifo_rst=rst && active;
    wire [3:0] hv, overflow, front_v, front_last, pop;
    wire [68:0] heads[0:3];
    wire take=active && !fault && credit!=0 && hv[cq];
    wire [68:0] head=heads[cq];
    wire [3:0] qbad;
    generate for(genvar q=0;q<4;q=q+1) begin:gq
        reg [7:0] beats;
        reg ended;
        wire [11:0] nq=(ndie<=2736*q) ? 12'd0 :
            ((ndie-2736*q>=2736) ? 12'd2736 : 12'(ndie-2736*q));
        wire [15:0] lv=sid[q][32:17];
        wire [255:0] val=sid[q][288:33];
        wire [319:0] ids=sid[q][608:289];
        wire last=sid[q][0];
        wire accept=active && siv[q];
        wire [11:0] offset={beats,4'b0};
        wire expect_last=(nq==0) || (offset+12'd16>=nq);
        wire [15:0] expect_lv=(nq<=offset) ? 16'd0 :
            ((nq-offset>=16) ? 16'hffff : 16'((32'd1<<(nq-offset))-1));
        wire [15:0] id_bad;
        wire [255:0] pinned;
        for(genvar lane=0;lane<16;lane=lane+1) begin:gl
            // Score IDs are global keys in rank+96*j owned blocks.
            wire [19:0] expected_id=20'((rank+96*(342*q+2*beats+lane/8))*8+lane%8);
            assign id_bad[lane]=lv[lane] && ids[20*lane +:20]!=expected_id;
            if(lane%8==0) begin:gp
                wire newest=lv[lane] && ((MUT==1) ? last :
                    ids[20*lane+3 +:17]==pos[19:3]);
                assign pinned[16*lane +:16]=newest ? 16'h7f80 : val[16*lane +:16];
            end else begin:gc
                assign pinned[16*lane +:16]=val[16*lane +:16];
            end
        end
        assign qbad[q]=accept && (ended || beats>=171 || last!=expect_last ||
            lv!=expect_lv || |id_bad || |(sid[q][16:1]&lv));
        always @(posedge ck or negedge rst)
            if(!rst) begin beats<=0; ended<=0; end
            else if(start && !active) begin beats<=0; ended<=0; end
            else if(accept) begin beats<=beats+1'b1; if(last) ended<=1; end
        wire [1:0] max_lv;
        wire [31:0] max_val;
        wire [33:0] max_id;
        ot_hdc_v41x_sel_cfront #(.SL(16),.IWP(20),.PIN(0)) front(
            .clk(ck),.rst_n(fifo_rst),.en(1'b1),.in_valid(accept),
            .in_last(last),.in_lv(lv),.in_val(pinned),.in_idx(ids),
            .o_v(front_v[q]),.o_last(front_last[q]),.o_lv(max_lv),
            .o_val(max_val),.o_idx(max_id));
        wire [1:0] publish_lv=max_lv & {
            max_val[31:16]!=16'hff80,max_val[15:0]!=16'hff80};
        ot_fifo_sram_fwft #(.W(69),.DEPTH(256),.MACRO(1)) store(
            .clk(ck),.rst_n(fifo_rst),.push(front_v[q]),
            .wdata({max_id,max_val,publish_lv,front_last[q]}),
            .pop(pop[q]),.hv(hv[q]),.head(heads[q]),.ovf(overflow[q]));
        assign pop[q]=take && cq==q;
    end endgenerate
    always @(posedge ck or negedge rst) begin
        if(!rst) begin active<=0; fault<=0; ev<=0; co<=0;
            frame_active<=0; selector_done<=0; candidate_done<=0;
            cq<=0; credit<=OCRED; co_quarter_last<=0;
        end else begin
            co[0]<=0; ev[0]<=0; co_quarter_last<=0;
            if(fsv) begin
                if(frame_active) fault<=1;
                else begin frame_active<=1; selector_done<=0;
                    candidate_done<=!fsd[87]; end
            end
            if(selector_ev_q[0]) selector_done<=1;
            if(selector_ev_q[1]) fault<=1;
            if(frame_active && selector_done && candidate_done && !fault) begin
                ev[0]<=1; frame_active<=0;
            end
            if(active) credit<=credit+$clog2(OCRED+1)'(cocv)-$clog2(OCRED+1)'(take);
            if(start) begin
                if(active) fault<=1;
                else begin
                    active<=1; fault<=fsd[76:63]>10944 || fsd[62:56]>=96;
                    pos<=fsd[55:36]; rank<=fsd[62:56]; ndie<=fsd[76:63];
                    credit<=OCRED; cq<=(MUT==2)?2'd1:2'd0;
                end
            end
            if(active && (|qbad || |overflow)) fault<=1;
            if(take) begin
                co<={head[68:35], head[34:3] ^ ((MUT==3)?32'h00010001:32'd0),
                     head[2:1],cq,head[0] && cq==3,1'b1};
                co_quarter_last<=head[0];
                if(head[0]) begin
                    if(cq==3) begin active<=0; candidate_done<=1; end
                    else if(MUT==2) cq<=(cq==1)?0:(cq==0)?2:cq+1'b1;
                    else cq<=cq+1'b1;
                end
            end
            ev[1]<=fault;
        end
    end
endmodule
`default_nettype wire
