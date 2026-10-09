`timescale 1ns/1ps
module tb_s81_engram_window(input wire clk);
    reg rst_n=0,cv=0,go=0,wv=0,ws=0;reg [83:0] cd=0;
    reg [11:0] wu=0;reg [20:0] wp=0,wt=0;reg [67:0] wi=0;reg wd=0;
    wire ov,ol,hfault,dn;wire [511:0] data;wire [3:0] hf;wire [7:0] dt;
    wire ready,pfault,jv,jwv,jwd;wire [67:0] jwi;wire [11:0] ju;wire [20:0] jp,jt;wire [3:0] pf;
    integer cy=0,mode=0,seen=0;reg gate=0;
    ot_s81_hop_tx #(.WINDOW_CONTEXT(1),.CMDW(84),.XW(1)) tx(
        .clk(clk),.rst_n(rst_n),.win_ctx_v(wv),.win_ctx_slot(ws),.win_ctx_user(wu),.win_ctx_pos(wp),
        .win_ctx_tok(wt),.win_ctx_ids(wi),.win_ctx_dead(wd),.cmd_v(cv),.cmd_d(cd),.go(go),
        .res_v(1'b0),.res_tok(21'b0),.res_val(32'b0),.res_stop(1'b0),.run_eosen(1'b0),
        .run_eos(21'd2),.run_maxl(22'd1024),.vm_rq(512'h123456),.vm_rvalid(1'b0),
        .out_valid(ov),.out_ready(ready && gate),.out_data(data),.out_last(ol),
        .dn_v(dn),.dn_tag(dt),.fault(hfault),.fault_code(hf));
    wire [511:0] rxdata = mode==3 ? (data & ~(512'b1<<276)) :
        mode==4 ? ((data & ~(512'h1ffff<<208)) | (512'd99092<<208)) : data;
    ot_s81_pkg_ctrl #(.WINDOW_CONTEXT(1),.MAXU(64),.RXW(1)) rx(
        .clk(clk),.rst_n(rst_n),.cfg_users(8'd64),.cfg_prompt_len(21'd1),.cfg_gen_len(21'd1),
        .cfg_max_len(22'd1024),.cfg_eos_en(1'b0),.cfg_eos_id(21'd2),.boot_ok(1'b1),
        .in_valid(ov && gate),.in_ready(ready),.in_data(rxdata),.in_last(ol),.job_v(jv),
        .job_rdy(1'b1),.job_user(ju),.job_pos(jp),.job_tok(jt),.job_done(1'b0),
        .job_win_v(jwv),.job_win_ids(jwi),.job_win_dead(jwd),.pr_q(21'b0),
        .proto_fault(pfault),.fault_code(pf));
    task step;begin @(negedge clk);end endtask
    always @(posedge clk) begin
        cy<=cy+1;if(cy>2000) $fatal(1,"timeout");
        if(jv) begin
            if(mode>=3 || !jwv || jwi!={17'd5,17'd4,17'd3,17'd2} || !jwd || ju!=54 || jp!=0 || jt!=129279) $fatal(1,"header window identity");
            seen<=seen+1;
        end
    end
    initial begin
        if(!$value$plusargs("MODE=%d",mode)) mode=0;
        repeat(4) step();rst_n=1;step();
        wu=54;wp=0;wt=129279;wi={17'd5,17'd4,17'd3,17'd2};wd=1;wv=1;step();wv=0;
        if(mode==2) begin wv=1;step();wv=0;end
        cd={1'b0,10'd54,21'd0,21'd129279,24'h000021,7'd7};
        if(mode==1) cd[82 -:10]=10'd55;
        cv=1;step();cv=0;go=1;step();go=0;
        repeat(20) step();gate=1;
        repeat(80) step();
        if(mode==1 || mode==2) begin if(!hfault || hf!=(mode==1?6:5) || seen) $fatal(1,"context negative");end
        else if(mode>=3) begin if(!pfault || pf!=9 || seen) $fatal(1,"receive negative");end
        else if(hfault || pfault || seen!=1) $fatal(1,"transport");
        if(mode==0) $display("ENGRAM_WINDOW PASS mode0");
        else $display("ENGRAM_WINDOW NEG mode%0d",mode);
        $finish;
    end
endmodule
