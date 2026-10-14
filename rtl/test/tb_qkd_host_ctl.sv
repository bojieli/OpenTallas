`timescale 1ns/1ps
module tb_qkd_host_ctl;
    parameter integer MUT=0;
    localparam integer ND=8, WDOG=80;
    reg ck=0,rst_n=0,ready=0;
    always #0.4165 ck=~ck;
    reg [60:0] req=0;
    reg [142:0] pr=0;
    reg [ND*93-1:0] tk=0;
    wire [181:0] hc;
    wire [119:0] res;
    qkd_host_ctl #(.ND(ND),.WDOG(WDOG),.MUT(MUT)) dut(.*);
    // Independent production pkgctl instance fed by the port samples; its
    // die interfaces are unpacked separately in the TB, never by DUT wires.
    reg ready_r=0;
    reg [60:0] req_r=0;
    reg [142:0] pr_r=0;
    reg [ND*93-1:0] tk_r=0;
    always @(posedge ck) begin
        if(!rst_n) begin ready_r<=0; req_r<=0; pr_r<=0; tk_r<=0; end
        else begin ready_r<=ready; req_r<=req; pr_r<=pr; tk_r<=tk; end
    end
    wire [ND-1:0] rd,rr,rf;
    wire [2*ND-1:0] rg;
    wire [18*ND-1:0] rt;
    wire [32*ND-1:0] rv;
    for(genvar g=0;g<ND;g=g+1) begin:ref_unpack
        wire [92:0] word_r=tk_r[g*93+:93];
        assign rd[g]=word_r[92]; assign rr[g]=word_r[89]; assign rf[g]=word_r[88];
        assign rg[g*2+:2]=word_r[91:90]; assign rt[g*18+:18]=word_r[81:64]; assign rv[g*32+:32]=word_r[63:32];
    end
    wire start_r,done_r,fault_r,dis_r,wd_r,ur_r,df_r;
    wire [17:0] token_r,pos_r,next_r;
    wire [1:0] gen_r;
    wire [23:0] base_r;
    wire [31:0] val_r,cyc_r,steps_r;
    ot_qfd_pkgctl #(.D(ND),.WDOG(WDOG),.DONE_REG(1)) ref_pkg(
        .clk(ck),.rst_n(rst_n),.ready(ready_r),.eng_start(req_r[0]),.eng_token(req_r[18:1]),
        .eng_pos(req_r[36:19]),.eng_kv_base(req_r[60:37]),
        .eng_done(done_r),.eng_next_token(next_r),.eng_next_val(val_r),.eng_cycles(cyc_r),.eng_fault(fault_r),
        .d_start(start_r),.d_token(token_r),.d_pos(pos_r),.d_kv_base(base_r),.d_gen(gen_r),
        .d_done(rd),.d_done_gen(rg),.d_next_token(rt),.d_next_val(rv),.d_drained(rr),.d_fault(rf),
        .disagree(dis_r),.wdog_fault(wd_r),.start_unready(ur_r),.die_fault(df_r),.n_steps(steps_r));
    reg [119:0] expected;
    always @(posedge ck) if(!rst_n) expected<=0;
        else expected<={steps_r,df_r,ur_r,wd_r,dis_r,cyc_r,val_r,next_r,fault_r,done_r};
    integer checks=0,errors=0,starts=0,successes=0,stale_checks=0,drain_checks=0,d,step,n;
    reg [1:0] gen;
    reg [17:0] ntok;
    reg [31:0] nval;
    always @(posedge ck) begin
        #0.01;
        if(rst_n) begin
            checks=checks+1;
            if(hc!=={pr_r,start_r,gen_r,token_r,pos_r} || res!==expected) begin
                if(errors<4) $display("MISMATCH hc=%h ref=%h res=%h ref=%h",hc,{pr_r,start_r,gen_r,token_r,pos_r},res,expected);
                errors=errors+1;
            end
            if(hc[38]) starts=starts+1;
        end
    end
    task tick; begin @(negedge ck); end endtask
    task reset;
        begin rst_n=0; req=0;pr=0;tk=0;ready=0; repeat(6) tick; rst_n=1;ready=1;repeat(5) tick; end
    endtask
    task launch(input integer s);
        begin
            req={24'(s*32),18'(s+11),18'(s*731+199),1'b1};tick;req[0]=0;
            n=0;while(!hc[38] && n<15) begin tick;n=n+1; end
            if(!hc[38]) begin errors=errors+1;$display("FAIL no start");end
            gen=hc[37:36];tick;
        end
    endtask
    task wait_done;
        begin n=0;while(!res[0] && n<WDOG+20) begin tick;n=n+1; end
            if(!res[0]) begin errors=errors+1;$display("FAIL no completion");end
        end
    endtask
    initial begin
        reset;
        for(step=0;step<40;step=step+1) begin
            launch(step);
            ntok=18'(step+37);nval=32'h3f800000+step;
            // A previous-generation done level must not complete the new step.
            for(d=0;d<ND;d=d+1) tk[d*93+:93]={1'b1,2'(gen-1),1'b1,1'b0,4'd0,1'b0,1'b0,ntok,nval,32'(d)};
            repeat(8) begin tick; stale_checks=stale_checks+1;if(res[0]) errors=errors+1; end
            // Current generation, all done, but one undrained die blocks finish.
            for(d=0;d<ND;d=d+1) tk[d*93+:93]={1'b1,gen,(d!=7),1'b0,4'd0,1'b0,1'b0,ntok,nval,32'(d)};
            repeat(8) begin tick;drain_checks=drain_checks+1;if(res[0]) errors=errors+1; end
            // Program and descriptor words are posted raw, even while waiting.
            pr={$random,$random,$random,$random,$random};tick;pr[142]=0;pr[74]=0;
            // Staggered completions test each status slice including die seven.
            for(d=0;d<ND;d=d+1) begin tk[d*93+89]=1;tick;end
            wait_done;
            if(res[1] || res[19:2]!==ntok || res[51:20]!==nval || res[119:88]!==32'(step+1)) begin
                errors=errors+1;$display("FAIL successful token step=%0d res=%h",step,res);
            end
            successes=successes+1;
        end
        // Disagreement is a fail-closed package completion.
        reset;launch(2);
        for(d=0;d<ND;d=d+1) tk[d*93+:93]={1'b1,gen,1'b1,1'b0,4'd0,1'b0,1'b0,18'(100+d/7),32'h3f800000,32'd0};
        wait_done;if(!res[1] || !res[84]) errors=errors+1;
        // A fault on the highest status slice must reach the host.
        reset;launch(3);tk[7*93+:93]={1'b1,gen,1'b0,1'b1,4'd3,1'b0,1'b0,18'd42,32'd1,32'd0};
        wait_done;if(!res[1] || !res[87]) errors=errors+1;
        reset;launch(4);wait_done;if(!res[1] || !res[85]) errors=errors+1;
        reset;ready=0;repeat(3) tick;req[0]=1;tick;req[0]=0;wait_done;if(!res[1] || !res[86]) errors=errors+1;
        repeat(5) tick;
        if(checks<1000 || starts<43 || successes!=40 || stale_checks!=320 || drain_checks!=320) errors=errors+1;
        if(errors) begin $display("FAIL qkd_host_ctl mutant=%0d detected errors=%0d checks=%0d",MUT,errors,checks);$fatal(1);end
        $display("PASS qkd_host_ctl exact checks=%0d starts=%0d tokens=%0d stale=%0d drain=%0d",checks,starts,successes,stale_checks,drain_checks);$finish;
    end
endmodule
