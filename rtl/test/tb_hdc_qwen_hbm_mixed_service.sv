`timescale 1ns/1ps
// Bounded six-owner traffic on one of the adopted four-stack, 128-PC service
// lanes. The controller intentionally delays, reorders and backpressures
// responses. Cycle counts describe this finite test only, not model tokens.
module tb_hdc_qwen_hbm_mixed_service;
    localparam NPC=128, NC=6, AW=32, CTAGW=32, PTAGW=35;
    localparam PC=0, REQUESTS=4, MAX_EVENTS=NC*REQUESTS;
    reg clk=0, rst_n=0, bind_region=0, head_mode=0, inject_bad=0;
    always #5 clk=~clk;
    reg [5:0] layer=0;
    reg [8:0] user_id=0;
    wire region_valid,region_fault;
    wire [AW-1:0] layer_code_base,layer_scale_base,qk_norm_base;
    wire [AW-1:0] post_tp_base,packed_kv_base,head_code_base;
    wire [AW-1:0] head_scale_base,head_norm_base,embed_code_base,embed_scale_base;
    ot_hdc_qwen_hbm_regions u_regions (.valid(region_valid),.fault(region_fault),.*);
    reg [NPC*NC-1:0] c_req_v=0,c_req_we=0,c_rsp_rdy='1;
    reg [NPC*NC*AW-1:0] c_req_addr=0;
    reg [NPC*NC*CTAGW-1:0] c_req_tag=0;
    reg [NPC*NC*256-1:0] c_req_data=0;
    wire [NPC*NC-1:0] c_req_rdy,c_rsp_v,c_wr_done_v;
    wire [NPC*NC*CTAGW-1:0] c_rsp_tag,c_wr_done_tag;
    wire [NPC*NC*256-1:0] c_rsp_data;
    wire [NPC-1:0] p_req_v,p_req_we,p_rsp_rdy,pc_fault;
    reg [NPC-1:0] p_req_rdy=0,p_rsp_v=0,p_wr_done_v=0;
    wire [NPC*AW-1:0] p_req_addr;
    wire [NPC*PTAGW-1:0] p_req_tag;
    wire [NPC*256-1:0] p_req_data;
    reg [NPC*PTAGW-1:0] p_rsp_tag=0,p_wr_done_tag=0;
    reg [NPC*256-1:0] p_rsp_data=0;
    wire [NPC*NC-1:0] g_req_v,g_req_rdy;
    wire guard_fault;
    ot_hdc_qwen_hbm_region_guard u_guard (
        .in_req_v(c_req_v),.in_req_we(c_req_we),.in_req_addr(c_req_addr),
        .out_req_v(g_req_v),.out_req_rdy(g_req_rdy),
        .in_req_rdy(c_req_rdy),.fault(guard_fault),.*);
    ot_hdc_qwen_hbm_service #(.MAX_OUT(2)) u_service (
        .c_req_v(g_req_v),.c_req_rdy(g_req_rdy),.*);
    integer issued[0:NC-1],finished[0:NC-1];
    integer cycle=0,accepted=0,returned=0,stalled=0,max_wait=0;
    integer rsp_blocked=0,credit_blocked=0;
    integer last_grant[0:NC-1];
    integer due[0:MAX_EVENTS-1];
    reg pending[0:MAX_EVENTS-1];
    reg [PTAGW-1:0] event_tag[0:MAX_EVENTS-1];
    reg [AW-1:0] event_addr[0:MAX_EVENTS-1];
    reg event_we[0:MAX_EVENTS-1];
    integer event_count=0, selected=-1;
    integer c, k, idx, owner, seq, total_finished;
    reg [AW-1:0] addr;
    function automatic [AW-1:0] source_addr(input integer owner_id,input integer n);
        case(owner_id)
            0: source_addr=(n==2 ? layer_scale_base : layer_code_base)+AW'(n*128);
            1: source_addr=qk_norm_base+AW'(n*128);
            2: source_addr=post_tp_base+AW'(n*128);
            3: source_addr=(n==2 ? embed_scale_base : embed_code_base)+AW'(n*128);
            4: source_addr=head_norm_base+AW'(n*128);
            default: source_addr=packed_kv_base+AW'(n*128);
        endcase
    endfunction
    initial begin
        for (k=0;k<NC;k=k+1) begin
            issued[k]=0;finished[k]=0;last_grant[k]=0;
        end
        for (k=0;k<MAX_EVENTS;k=k+1) pending[k]=0;
        repeat(2) @(negedge clk); rst_n=1; bind_region=1;
        @(negedge clk); bind_region=0;
        if (!region_valid || region_fault) $fatal(1,"full-token HBM region bind failed");
        wait(returned==NC*REQUESTS);
        @(negedge clk);
        total_finished=0;
        for (k=0;k<NC;k=k+1) total_finished+=finished[k];
        if (accepted!=NC*REQUESTS || total_finished!=NC*REQUESTS ||
            |pc_fault || guard_fault || region_fault || stalled==0 || rsp_blocked==0 ||
            credit_blocked==0 || max_wait>NC*REQUESTS+20)
            $fatal(1,"mixed service count/fairness/fault mismatch");
        $display("RESULT cycles=%0d requests=%0d responses=%0d phy_stalls=%0d rsp_blocked=%0d credit_blocked=%0d max_wait=%0d pc=%0d clients=%0d",
                 cycle,accepted,returned,stalled,rsp_blocked,credit_blocked,max_wait,PC,NC);
        inject_bad=1;
        @(negedge clk);
        #1;
        if (p_req_v[PC] || c_req_rdy[PC*NC+3])
            $fatal(1,"cross-region embedding request escaped guard");
        @(negedge clk);
        if (!guard_fault || |pc_fault)
            $fatal(1,"cross-region request did not fault locally");
        $display("GUARD PASS rejected cross-region embedding to KV page");
        $finish;
    end
    // Keep one request per owner asserted until accepted. All six owners
    // target PC0, so the finite arbiter must rotate rather than drain one.
    always @(negedge clk) if (rst_n && region_valid) begin
        c_req_v=0;c_req_we=0;c_req_addr=0;c_req_tag=0;c_req_data=0;
        c_rsp_rdy='1;
        if (cycle<40) c_rsp_rdy[PC*NC+2]=0;
        p_req_rdy=0;p_req_rdy[PC]=(cycle%3!=0);
        for (integer j=0;j<NC;j=j+1) if (issued[j]<REQUESTS) begin
            idx=PC*NC+j;
            c_req_v[idx]=1;
            c_req_we[idx]=(j==5 && issued[j]==3);
            c_req_addr[idx*AW +: AW]=source_addr(j,issued[j]);
            c_req_tag[idx*CTAGW +: CTAGW]=CTAGW'(j*16+issued[j]);
            c_req_data[idx*256 +: 256]=256'hfeed0000+j*16+issued[j];
        end
        if (inject_bad) begin
            c_req_v[PC*NC+3]=1;
            c_req_addr[(PC*NC+3)*AW +: AW]=packed_kv_base;
            c_req_tag[(PC*NC+3)*CTAGW +: CTAGW]=32'hbad;
        end
        p_rsp_v=0;p_wr_done_v=0;p_rsp_tag=0;p_wr_done_tag=0;p_rsp_data=0;
        selected=-1;
        // Newest ready event first deliberately reorders completions.
        for (integer j=0;j<event_count;j=j+1)
            if (pending[j] && due[j]<=cycle) selected=j;
        if (selected>=0) begin
            if (event_we[selected]) begin
                p_wr_done_v[PC]=1;
                p_wr_done_tag[PC*PTAGW +: PTAGW]=event_tag[selected];
            end else begin
                p_rsp_v[PC]=1;
                p_rsp_tag[PC*PTAGW +: PTAGW]=event_tag[selected];
                p_rsp_data[PC*256 +: 256]={8{event_addr[selected]}};
            end
        end
    end
    always @(posedge clk) if (rst_n && region_valid) begin
        cycle=cycle+1;
        if (|pc_fault || region_fault || (guard_fault && !inject_bad))
            $fatal(1,"shared HBM fault");
        if (cycle>300) $fatal(1,"mixed service timeout");
        if (|c_req_v && !p_req_rdy[PC]) stalled=stalled+1;
        if (p_rsp_v[PC] && !p_rsp_rdy[PC]) rsp_blocked=rsp_blocked+1;
        if (|c_req_v[PC*NC +: NC] && p_req_rdy[PC] && !p_req_v[PC])
            credit_blocked=credit_blocked+1;
        if (p_req_v[PC] && p_req_rdy[PC]) begin
            owner=p_req_tag[PC*PTAGW+CTAGW +: 3];
            seq=p_req_tag[PC*PTAGW +: CTAGW]-owner*16;
            if (owner>=NC || seq<0 || seq>=REQUESTS ||
                p_req_addr[PC*AW +: AW] !== source_addr(owner,seq) ||
                p_req_addr[PC*AW +: 7] !== 7'(PC) ||
                !c_req_rdy[PC*NC+owner])
                $fatal(1,"mixed service owner/address/region mismatch");
            if (cycle-last_grant[owner]>max_wait) max_wait=cycle-last_grant[owner];
            last_grant[owner]=cycle;
            due[event_count]=cycle+24+(seq%3);
            event_tag[event_count]=p_req_tag[PC*PTAGW +: PTAGW];
            event_addr[event_count]=p_req_addr[PC*AW +: AW];
            event_we[event_count]=p_req_we[PC];
            pending[event_count]=1;
            event_count=event_count+1;
            issued[owner]=issued[owner]+1;
            accepted=accepted+1;
        end
        if (selected>=0 &&
            (event_we[selected] || (p_rsp_v[PC] && p_rsp_rdy[PC]))) begin
            owner=event_tag[selected][CTAGW +: 3];
            seq=event_tag[selected][CTAGW-1:0]-owner*16;
            if (event_we[selected]) begin
                if (!c_wr_done_v[PC*NC+owner] ||
                    c_wr_done_tag[(PC*NC+owner)*CTAGW +: CTAGW] !== CTAGW'(owner*16+seq))
                    $fatal(1,"KV write completion tag lost");
            end else if (!c_rsp_v[PC*NC+owner] ||
                c_rsp_tag[(PC*NC+owner)*CTAGW +: CTAGW] !== CTAGW'(owner*16+seq) ||
                c_rsp_data[(PC*NC+owner)*256 +: 256] !== {8{event_addr[selected]}})
                $fatal(1,"mixed client read response mismatch");
            pending[selected]=0;
            finished[owner]=finished[owner]+1;
            returned=returned+1;
        end
    end
endmodule
