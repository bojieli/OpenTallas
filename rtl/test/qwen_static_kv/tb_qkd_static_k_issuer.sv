`timescale 1ns/1ps
// Control/mapped-SRAM proof at the native TP8 QK shape; head arithmetic is a separate owner proof.
module tb_qkd_static_k_issuer;
    parameter integer MUT=0;
    // KV-ECTL4 2026-10-18: RL = the landing round trip (req pin -> rsp pin edges) and QK = QK_ISSUE_AGE of the frame under
    // test (die: one K round trip RL 80 for every frame, QK = RL + 11; defaults = the unit bench's RL 2 / QK 34).
    // MUT 8: the landing answers one edge late (RL + 1) -> the issuer must fault; MUT 9: K issued at QK - 1 vs the bench
    // calendar (the frame is built with QK_ISSUE_AGE = QK - 1) -> consume slot mismatch.
    parameter integer RL=2, QK=34;
    localparam integer QKB = (MUT==9) ? QK-1 : QK;
    localparam integer RLR = (MUT==8) ? RL+1 : RL;
    reg ck=0,rst_n=0;
    always #0.5 ck=~ck;
    reg [633:0] si=0;
    integer ctx=8192,stack=1,engine=3,ns,limit,nexpected=0;
    integer et[0:255],esc[0:255];
    wire [4:0] cfg=5'(engine*4+stack);
    wire [1024:0] rs;
    wire req_valid,req_v,bridge_fault;
    wire [13:0] req_t;
    wire [15:0] req_epoch;wire [5:0] req_layer;
    reg [5:0] layer_cur=0;
    reg rsp_valid=0;reg [1023:0] rsp_data=0;reg [13:0] rsp_t=0;
    reg rsp_v=0;reg [15:0] rsp_epoch=0;reg [5:0] rsp_layer=0;
`ifdef OT_KISS_ST
    // KV-ECTL4: the frame the die binds (qkd_ectl3_kiss_st: C = qkd_ectl_c_st, si 633 b, so 413 b)
    wire [412:0] so_st;
    wire [424:0] so={so_st[412],1'b0,dut.u_c.u.k_done,10'd0,so_st[411:0]};   // the kiss_s so layout the checks read
    wire [16:0] rq=dut.u_a.rq;
    wire [1558:0] t0,t1;
    qkd_ectl3_kiss_st #(.RESPONSE_LAT(RL),.QK_ISSUE_AGE(QKB),.MUT(MUT==4?2:(MUT==5?1:0))) dut (
        .ck({3{ck}}),.rst_n(rst_n),.cfg(cfg),.e0(),.e1(),.e2(),.e3(),
        .s0(34'd0),.s1(34'd0),.s2(34'd0),.s3(34'd0),.t0(t0),.t1(t1),
        .kgo(si[0]),.epoch(16'h1234),.layer(layer_cur),
        .req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
        .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),
        .fault(bridge_fault),.si(si[632:0]),.so(so_st));
    assign rs=dut.u_a.rs;
`elsif OT_KISS
    // KVJ-D 2026-10-17: the fused ECTL A + K issuer tile (qkd_static_ectla_kiss) inside its A|B|C parent.
    wire [424:0] so;
    wire [16:0] rq=dut.u_a.rq;
    wire [1558:0] t0,t1;
    qkd_ectl3_kiss_s #(.RESPONSE_LAT(RL),.QK_ISSUE_AGE(QKB),.MUT(MUT==4?2:(MUT==5?1:0))) dut (
        .ck({3{ck}}),.rst_n(rst_n),.cfg(cfg),.e0(),.e1(),.e2(),.e3(),
        .s0(34'd0),.s1(34'd0),.s2(34'd0),.s3(34'd0),.t0(t0),.t1(t1),
        .kgo(si[0]),.epoch(16'h1234),.layer(layer_cur),
        .req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
        .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),
        .fault(bridge_fault),.si(si),.so(so));
    assign rs=dut.u_a.rs;
`else
    qkd_static_k_issuer #(.RESPONSE_LAT(RL),.MUT(MUT==4?2:(MUT==5?1:0))) bridge(
      .ck(ck),.rst_n(rst_n),.kgo(si[0]),.epoch(16'h1234),.layer(layer_cur),.rq(rq),
      .req_valid(req_valid),.req_t(req_t),.req_v(req_v),.req_epoch(req_epoch),.req_layer(req_layer),
      .rsp_valid(rsp_valid),.rsp_data(rsp_data),.rsp_t(rsp_t),.rsp_v(rsp_v),.rsp_epoch(rsp_epoch),.rsp_layer(rsp_layer),
      .rs(rs),.fault(bridge_fault));
    wire [424:0] so;
    wire [16:0] rq;
    wire [1558:0] t0,t1;
    qkd_ectl3_epoch_direct_s #(.STATIC_QK(1),.QK_ISSUE_AGE(QKB),.ROW_RETURN_LAT(RL+7)) dut (
        .ck({3{ck}}),.rst_n(rst_n),.cfg(cfg),.e0(),.e1(),.e2(),.e3(),
        .s0(34'd0),.s1(34'd0),.s2(34'd0),.s3(34'd0),.t0(t0),.t1(t1),.rq(rq),.rs(rs),.si(si),.so(so));
`endif
    function automatic [1023:0] rowf(input integer n);
        for(integer j=0;j<32;j=j+1) rowf[j*32+:32]=32'h42000000 ^ (n*32'h10203) ^ j;
    endfunction
    reg [1023:0] response[0:1023];
    reg rv[0:1023];
    reg [13:0] tags[0:1023];
    integer nbridge=0,nrs=0;
    integer cyc,nreq=0,nconsume=0,startcyc=-1,firstreq=-1,firstconsume=-1;
    integer idx,pidx,tp;
    initial begin
        if($value$plusargs("T=%d",ctx))begin end
        if($value$plusargs("S=%d",stack))begin end
        if($value$plusargs("E=%d",engine))begin end
        ns=(ctx>>9)*128+(((ctx&511)-stack*128)<0?0:(((ctx&511)-stack*128)>128?128:(ctx&511)-stack*128));
        limit=ns>1024?2048:ns;
        for(integer scan=0;engine+8*scan<limit;scan=scan+1)begin
            idx=engine+8*scan;pidx=ns>1024?(((idx>>11)&1)*2048+((idx>>6)&15)*128+((idx>>10)&1)*64+(idx&63)):idx;
            if(pidx<ns)begin et[nexpected]=((pidx>>7)<<9)+(stack<<7)+(pidx&127);esc[nexpected]=scan;nexpected=nexpected+1;end
        end
        for(integer j=0;j<1024;j=j+1) begin rv[j]=0;response[j]=0;end
        repeat(6) @(negedge ck);rst_n=1;
        repeat(80) @(negedge ck);
        for(integer layer_idx=0;layer_idx<36;layer_idx=layer_idx+1)begin
        layer_cur=6'(layer_idx);nreq=0;nconsume=0;nbridge=0;nrs=0;startcyc=-1;firstreq=-1;firstconsume=-1;
        for(integer j=0;j<1024;j=j+1)begin rv[j]=0;response[j]=0;tags[j]=0;end
        for(cyc=0;cyc<500;cyc=cyc+1) begin
            si=0;si[14:1]=14'(ctx);si[17:15]=cyc%8;
            if(cyc==0)si[0]=1;
            if(cyc>=1&&cyc<=32)begin si[18]=1;si[24:19]=cyc-1;end

            rsp_valid=rv[cyc];rsp_data=response[cyc];rsp_t=tags[cyc];
            rsp_epoch=16'h1234;rsp_layer=layer_cur;rsp_v=0;
            if(MUT==1&&cyc==20)rsp_valid=0;
            if(MUT==2&&cyc==20)rsp_t=rsp_t^14'd1;
            if(MUT==3&&cyc==20)rsp_layer=layer_cur^6'd1;
            if(MUT==6&&cyc>=340&&cyc<356)begin rsp_valid=1;rsp_v=1;rsp_t=14'(cyc-340);end
            if(MUT==7&&cyc==20)rsp_v=1;
            @(posedge ck);
            if(dut.u_c.u.start)startcyc=cyc;
            if(layer_idx==0 && cyc<16 && (rq[0] || dut.u_a.u.u.row_slot || dut.u_c.u.start))
                $display("TRACE c%0d localstart%0d rq%0d rs%0d captured%0d slot%0d",cyc,dut.u_c.u.start,rq[0],rs[0],dut.u_a.u.u.rsp_valid,dut.u_a.u.u.row_slot);
            if(rq[0])begin
                if(firstreq<0)firstreq=cyc;
                if(nreq>=nexpected||cyc!=startcyc+4+esc[nreq])$fatal(1,"request slot %0d at %0d",nreq,cyc);
                tp=et[nreq];
                if(rq[15:3]!=tp||rq[2:1]!=0)$fatal(1,"request tag %0d t%0d expected%0d",nreq,rq[15:3],tp);
                nreq=nreq+1;
            end
            if(req_valid)begin
                tp=et[nbridge];
                if(req_t!=tp||cyc!=startcyc+5+esc[nbridge])$fatal(1,"bridge request row/edge");
                if(req_epoch!=16'h1234||req_layer!=layer_cur||req_v) $fatal(1,"request identity");
                rv[cyc+RLR]=1;response[cyc+RLR]=rowf(nbridge);tags[cyc+RLR]=req_t;nbridge=nbridge+1;
            end
            if(rs[0])nrs=nrs+1;
            if(dut.u_a.u.u.k_issue!==dut.u_b.u.k_issue||dut.u_a.u.u.k_issue!==dut.u_c.u.k_issue)$fatal(1,"copies diverged");
            if(dut.u_a.u.u.k_issue)begin
                if(firstconsume<0)firstconsume=cyc;
                if(cyc!=startcyc+QK+esc[nconsume])$fatal(1,"consume slot %0d at %0d S%0d",nconsume,cyc,startcyc);
                if((MUT==0||MUT==4||MUT==6) && {dut.u_b.u.row,dut.u_a.u.u.row}!==rowf(nconsume))$fatal(1,"SRAM row mismatch %0d at%0d got%h expected%h",nconsume,cyc,dut.u_a.u.u.row[31:0],rowf(nconsume));
                nconsume=nconsume+1;
            end
            @(negedge ck);
        end
        if(nreq!=nexpected||nconsume!=nexpected||!so[422])$fatal(1,"shape req%0d consume%0d done%0d",nreq,nconsume,so[422]);
        if((MUT==0||MUT==6) && (so[424]||bridge_fault))$fatal(1,"unexpected normal fault ECTL%0d bridge%0d",so[424],bridge_fault);
        if(((MUT>=1&&MUT<=3)||MUT==7||MUT==8)&&!bridge_fault)$fatal(1,"missing bridge identity/slot fault");
        if(nbridge!=nexpected||((MUT==0||MUT==6)&&nrs!=nexpected))$fatal(1,"bridge shape");
        if(MUT==8)$fatal(1,"late landing response faulted (RL %0d + 1)",RL);
        $display("STATIC_K PASS RL=%0d QK=%0d layer=%0d mutant=%0d req=%0d consume=%0d bridge=%0d rs=%0d firstreq=%0d localstart=%0d firstconsume=%0d bridgefault=%0d",RL,QK,layer_cur,MUT,nreq,nconsume,nbridge,nrs,firstreq,startcyc,firstconsume,bridge_fault);
        end
        $finish;
    end
endmodule
