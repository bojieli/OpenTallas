`timescale 1ns/1fs
// Minimum persistent-controller embedding path with real core/HBM clocks.
// PROFILE1 records a compiler calendar only. A fresh process runs PROFILE0
// against frozen files. Only the external raw HBM PHY/memory is modeled.
module tb_static_embed_controller;
    localparam HC=8000,CC=9000,RL=23;
    reg hclk=0,ck=0;
    always #0.512 hclk=~hclk;
    initial begin #0.137;forever #0.416667 ck=~ck;end
    reg reset=0,issue=0,ret_slot=0,read_scale=0;
    reg [17:0] token=0;
    reg sr_reserved=0,raw_reserved=0;
    reg [288:0] pi=0;
    wire [287:0] es;
    wire [260:0] er[0:1];wire [327:0] po[0:1];wire [1:0] cf,completion_fault;
    integer calibrate=0,mode=0;
    string folder,vectors;
    wire replay=calibrate==0;
    // Negative control corrupts an actual controller input bank bit.
    wire [287:0] controller_es=(replay&&mode==4)?(es^(288'd1<<281)):es;
    wire beat_v,pcfault;
    wire [255:0] beat_data;
    wire [17:0] beat_token;wire [5:0] beat_word;
    wire beat_half,beat_scale;wire [15:0] beat_epoch;
    qkd_embedding_static_pc #(.STACK(0),.PC(0)) endpoint(
        .ck(ck),.rst_n(reset),.boot_ready(1'b1),.issue_v(issue),.token(token),
        .word_index(6'd0),.half(1'b0),.scale(read_scale),.epoch(16'd43),.return_slot(ret_slot),
        .es(es),.er(replay?er[1]:er[0]),.beat_v(beat_v),.beat_data(beat_data),.beat_token(beat_token),
        .beat_word(beat_word),.beat_half(beat_half),.beat_scale(beat_scale),.beat_epoch(beat_epoch),
        .corrected(),.fault(pcfault),.outstanding());
    genvar g;
    generate for(g=0;g<2;g=g+1) begin:controllers
        qkd_ctrl_pc_host_static #(.PROFILE(g==0?1:0)) dut(
            .pll_hbm(hclk),.hrst(reset&&(replay?(g==1):(g==0))),.ck(ck),.rsi(reset&&(replay?(g==1):(g==0))),
            .pc(5'd0),.ci(319'd0),.co(),.es(controller_es),.er(er[g]),.po(po[g]),.pi(pi),.ki(33'd0),.ko(),.fi(1'b0),.fo(cf[g]),
            .static_cmd_owner(1'b0),.static_cmd(43'd0),.reserved_rd(1'b0),.reserved_static_col(sr_reserved),.reserved_write_col(1'b0),
            .static_epoch(16'd43),.expected_raw_valid(raw_reserved),
            .cfg_stack(2'd0),.es_context(318'd0),.es_expected_valid(1'b0),.es_expected_identity(61'd0),
            .es_expected_address(29'd0),.es_expected_pc(5'd0),.es_expected_stack(2'd0),
            .native_commit_valid(),.native_commit_identity(),.native_commit_address(),.corrected_epoch(),.completion_v(),.completion_we(),.completion_fault(completion_fault[g]));
    end endgenerate
    bit srslots[0:HC-1],rawslots[0:HC-1],retslots[0:CC-1];
    bit due[0:HC+RL];reg [287:0] raw[0:HC+RL];
    reg [18:0] openrow[0:31];
    integer tokens[0:8];reg [255:0] external_hbm_samples[0:8];reg [511:0] tmp[0:63];reg [255:0] packed_scale[0:0];
    integer h=0,reads=0,returns=0,checked=0;
    integer i,t,n,index;
    function automatic [71:0] ecc(input [63:0] d);
        reg [71:0] c;integer j;begin
            c=0;j=0;
            for(integer p=1;p<=71;p=p+1) if((p&(p-1))!=0) begin c[p-1]=d[j];j=j+1;end
            for(integer k=0;k<7;k=k+1)for(integer p=1;p<=71;p=p+1)if((p&(1<<k))!=0)c[(1<<k)-1]^=c[p-1];
            c[71]=^c[70:0];ecc=c;
        end
    endfunction
    function automatic [287:0] encode(input [255:0] d);
        for(integer k=0;k<4;k=k+1)encode[k*72+:72]=ecc(d[k*64+:64]);
    endfunction
    always @(negedge hclk) begin
        if(h<HC) begin
            sr_reserved=replay?srslots[h]:0;
            if(replay&&mode==1&&h>0)sr_reserved=srslots[h-1];
            pi={raw[h],due[h]};
            raw_reserved=replay?rawslots[h]:due[h];
            if(replay&&mode==3&&due[h])pi[0]=0;
        end
    end
    always @(posedge hclk) begin:phy
        integer b,c,row,physical_token,found;
        if(h<HC) begin
            if(!replay) begin
                rawslots[h]=due[h];
                if(h>=2)srslots[h-2]=controllers[0].dut.u_ctl.core.on.legal_static;
            end
            if(reset) begin
                if(po[replay][0]&&po[replay][3:1]==1)openrow[po[replay][8:4]]=po[replay][27:9];
                if(po[replay][28]) begin
                    if(po[replay][29])$fatal(1,"unexpected write in embedding read calendar");
                    b=po[replay][34:30];c=po[replay][39:35];row=openrow[b];
                    physical_token=(row-24427)*1024+((b>>2)<<7)+(c<<2)+(b&3);
                    found=-1;
                    for(integer k=0;k<8;k=k+1)if(tokens[k]==physical_token)found=k;
                    if(physical_token==151936)found=8;
                    if(found<0)$fatal(1,"actual PHY address selects absent external sample token=%0d",physical_token);
                    due[h+RL]=1;raw[h+RL]=encode(external_hbm_samples[found]);reads=reads+1;
                end
                if(cf[replay]||completion_fault[replay])$fatal(1,"controller schedule/PHY fault h=%0d",h);
            end
            h=h+1;
        end
    end
    initial begin
        void'($value$plusargs("CALIBRATE=%d",calibrate));void'($value$plusargs("MUT=%d",mode));
        if(!$value$plusargs("CALENDAR=%s",folder)||!$value$plusargs("VECTORS=%s",vectors))$fatal(1,"CALENDAR/VECTORS required");
        tokens[0]=0;tokens[1]=63;tokens[2]=64;tokens[3]=511;tokens[4]=512;tokens[5]=65535;tokens[6]=65536;tokens[7]=151935;tokens[8]=0;
        for(i=0;i<8;i=i+1)begin
            $readmemh($sformatf("%s/vectors_%0d/codes.hex",vectors,tokens[i]),tmp);
            external_hbm_samples[i]=tmp[0][255:0];
        end
        $readmemh({vectors,"/vectors_0/scale_sector.hex"},packed_scale);external_hbm_samples[8]=packed_scale[0];
        for(i=0;i<HC;i=i+1)begin srslots[i]=0;rawslots[i]=0;end
        for(i=0;i<HC+RL+1;i=i+1)begin due[i]=0;raw[i]=0;end
        for(i=0;i<CC;i=i+1)retslots[i]=0;
        if(calibrate==0)begin
            $readmemh({folder,"/static_columns.hex"},srslots);$readmemh({folder,"/raw_returns.hex"},rawslots);
            $readmemh({folder,"/core_returns.hex"},retslots);
        end
        for(t=0;t<CC;t=t+1)begin
            @(negedge ck);
            if(t==20)reset=1;
            issue=0;
            for(n=0;n<9;n=n+1)if(t==300+n*700)begin issue=1;token=tokens[n];read_scale=(n==8);end
            ret_slot=replay?retslots[t]:0;
            if(replay&&mode==2&&t>0)ret_slot=retslots[t-1];
            @(posedge ck);
            if(replay&&(issue||ret_slot||er[1][0]))$display("TRACE t=%0d issue=%b pending=%b slot=%b er=%b token=%0d stack=%0d pc=%0d valid=%b",t,issue,endpoint.pending,ret_slot,er[1][0],token,endpoint.stack,endpoint.pc,endpoint.valid_address);
            if(!replay&&er[0][0])begin retslots[t]=1;returns=returns+1;end
            #0.001;
            if(replay&&beat_v)begin
                if(checked>=9||beat_token!=tokens[checked]||beat_word!=0||beat_half||beat_scale!=(checked==8)||beat_epoch!=43||beat_data!==external_hbm_samples[checked])
                    $fatal(1,"actual persistent embedding response mismatch index=%0d",checked);
                checked=checked+1;
            end
            if(replay&&pcfault)$fatal(1,"embedding endpoint missed compiled slot t=%0d",t);
        end
        if(calibrate)begin
            if(reads!=9||returns!=9)$fatal(1,"compiler coverage reads=%0d returns=%0d",reads,returns);
            $writememh({folder,"/static_columns.hex"},srslots);$writememh({folder,"/raw_returns.hex"},rawslots);$writememh({folder,"/core_returns.hex"},retslots);
            $display("PASS compiler PROFILE1 only: actual8codeReads+1scaleRead dualclock core833.334ps phase137ps HBM1024ps");
        end else begin
            if(reads!=9||checked!=9)$fatal(1,"production component coverage reads=%0d checked=%0d",reads,checked);
            $display("PASS fresh PROFILE0 embedding replay: actual8releasedCodeBeats+1packedBF16ScaleSector dualclock core833.334ps phase137ps HBM1024ps no-readyissue");
        end
        $finish;
    end
endmodule
