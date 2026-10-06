`timescale 1ns/1ps
// Selected STREAM4 descriptor/GO boundary, one finite outstanding of each.
// The descriptor ring retires only on acceptance by every real controller.
// GO carries that descriptor's ordinal, not a reset-replayable toggle.
module ot_qwen_s4_protected_control #(parameter integer MEM_ROWS=3) (
    input wire clk,hclk,por_n,warm_rst_n,
    input wire d_v, output wire d_rdy,
    input wire [18:0] d_row,input wire [10:0] d_n,input wire go,
    output wire desc_v,input wire desc_r,
    output wire [18:0] desc_row,output wire [10:0] desc_n,
    input wire busy_all, output wire h_go,
    output wire go_ready,desc_commit,go_commit,
    output wire [2:0] desc_ordinal,go_ordinal,
    input wire c_external_fault,h_external_fault,
    output wire c_fault,h_fault
);
    wire warm0,warm1;
    ot_reset_sync u_warm0(.clk(clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm0));
    ot_reset_sync u_warm1(.clk(clk),.async_rst_n(warm_rst_n),.sync_rst_n(warm1));
    wire warm_ok=warm0&&warm1;
    wire [6:0] cs,hs,hsi;
    wire cb,hb,dr,gr,dwbad,drbad,gwbad,grbad,dvalid,gvalid;
    wire [2:0] di=cs[2:0],gi=cs[5:3],dc=hs[2:0],gc=hs[5:3];
    wire [2:0] docc,gocc,do_owner,go_owner,dret,gret;
    wire [29:0] ddata;wire [2:0] gdata;
    wire cfg_ok=(d_row<MEM_ROWS)&&(d_n>0)&&(d_n<=1024);
    wire ca=d_v&&d_rdy&&cfg_ok;
    wire ga=go&&gr&&warm_ok&&!c_fault&&(gocc==0)&&((di+3'(ca)-gi)!=0);
    wire d_take=desc_v&&desc_r, g_take=h_go;
    wire identity_bad=gvalid&&((gdata!=go_owner)||(go_owner!=gc));
    (* async_reg="true", keep *) reg hf0,hf1,hi0,hi1;
    always @(posedge clk or negedge por_n)
        if(!por_n)begin hf0<=0;hf1<=0;hi0<=1;hi1<=1;end
        else begin hf0<=hs[6];hf1<=hf0;hi0<=hsi[6];hi1<=hi0;end
    assign c_fault=cb||cs[6]||dwbad||gwbad||hf1||(hf1!=~hi1);
    assign h_fault=hb||hs[6]||drbad||grbad||identity_bad||h_external_fault;
    assign d_rdy=dr&&warm_ok&&!c_fault&&(docc==0);
    assign desc_v=dvalid&&!h_fault;
    assign {desc_row,desc_n}=ddata;
    assign h_go=gvalid&&!h_fault&&busy_all&&((dc-gc)!=0);
    assign go_ready=gr&&warm_ok&&!c_fault&&(gocc==0)&&((di-gi)!=0);
    assign desc_commit=d_take;assign go_commit=g_take;
    assign desc_ordinal=do_owner;assign go_ordinal=go_owner;
    ot_qwen_s4_checked_state #(.W(7)) u_cs(.clk(clk),.por_n(por_n),.en(!cb),
        .d({cs[6]||c_external_fault||(d_v&&(!d_rdy||!cfg_ok))||(go&&!ga),gi+3'(ga),di+3'(ca)}),.q(cs),.bad(cb));
    ot_qwen_s4_checked_state #(.W(7)) u_hs(.clk(hclk),.por_n(por_n),.en(!hb),
        .d({hs[6]||drbad||grbad||identity_bad||h_external_fault,gc+3'(g_take),dc+3'(d_take)}),.q(hs),.qi(hsi),.bad(hb));
    ot_qwen_s4_protected_ring #(.WIDTH(30),.DEPTH(4),.KIND(3)) u_desc(
        .wr_clk(clk),.rd_clk(hclk),.por_n(por_n),.allow_new(warm_ok&&!c_fault),
        .wr_valid(ca),.wr_ready(dr),.wr_data({d_row,d_n}),.wr_occupancy(docc),.wr_fault(dwbad),
        .rd_valid(dvalid),.rd_ready(d_take),.rd_data(ddata),.rd_owner(do_owner),
        .retire(d_take),.retired(dret),.rd_fault(drbad));
    ot_qwen_s4_protected_ring #(.WIDTH(3),.DEPTH(4),.KIND(4)) u_go(
        .wr_clk(clk),.rd_clk(hclk),.por_n(por_n),.allow_new(warm_ok&&!c_fault),
        .wr_valid(ga),.wr_ready(gr),.wr_data(gi),.wr_occupancy(gocc),.wr_fault(gwbad),
        .rd_valid(gvalid),.rd_ready(g_take),.rd_data(gdata),.rd_owner(go_owner),
        .retire(g_take),.retired(gret),.rd_fault(grbad));
endmodule
