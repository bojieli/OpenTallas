`timescale 1ns/1ps
module tb_vms_calendar_host_static;
    parameter integer MUT=0;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0;
    reg s_awvalid=0,s_wvalid=0,s_arvalid=0;
    reg [11:0] s_awaddr=0,s_araddr=0;
    reg [31:0] s_wdata=0;
    wire s_awready,s_wready,s_bvalid,s_arready,s_rvalid;
    wire [31:0] s_rdata;
    wire c_awvalid,c_awready,c_wvalid,c_wready,c_bvalid,c_arvalid,c_arready,c_rvalid,c_bready,c_rready;
    wire [11:0] c_awaddr,c_araddr;
    wire [31:0] c_wdata,c_rdata;
    wire [3:0] c_wstrb;
    wire [459:0] lcp_full;
    wire [418:0] lcp=lcp_full[418:0];
    wire loader_fault,host_fault;
    wire [3:0] cfg_we,start_v,program_active,program_done,program_fault;
    wire [39:0] cfg_addr,start_base;
    wire [43:0] start_limit;
    wire [63:0] start_loops;
    wire [1023:0] cfg_data;
    wire [3:0] calendar_v;
    wire [4*202-1:0] calendar;
    wire [127:0] ordinal;
    wire ext_cfg_v,ext_desc_v,ext_launch_v;
    wire [7:0] ext_target;
    wire [11:0] ext_cfg_addr,ext_base;
    wire [255:0] ext_cfg_data;
    wire [12:0] ext_limit;
    wire [15:0] ext_loops;
    wire ecfg,estart,eactive,edone,efault,econfigured,target_fault,ecal_v;
    wire [9:0] ecfg_addr,ebase;
    wire [255:0] ecfg_data;
    wire [10:0] elimit;
    wire [15:0] eloops;
    wire [47:0] ecal;
    wire [31:0] eordinal;
    wire wide_cfg,wide_start,wide_configured,wide_fault;
    wire [11:0] wide_addr,wide_base;
    wire [12:0] wide_limit;
    wire [15:0] wide_loops;
    wire [255:0] wide_data;
    ot_vms_calendar_host_static host(
        .clk(clk),.rst_n(rst_n),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(4'hf),
        .s_bvalid(s_bvalid),.s_bready(1'b1),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
        .s_rvalid(s_rvalid),.s_rready(1'b1),.s_rdata(s_rdata),
        .c_awvalid(c_awvalid),.c_awready(c_awready),.c_awaddr(c_awaddr),
        .c_wvalid(c_wvalid),.c_wready(c_wready),.c_wdata(c_wdata),.c_wstrb(c_wstrb),
        .c_bvalid(c_bvalid),.c_bready(c_bready),.c_arvalid(c_arvalid),.c_arready(c_arready),.c_araddr(c_araddr),
        .c_rvalid(c_rvalid),.c_rready(c_rready),.c_rdata(c_rdata),.lcp_doorbell(lcp[71]),
        .program_active(program_active),.program_done(program_done),.program_fault(program_fault),
        .cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),.start_v(start_v),
        .start_base(start_base),.start_limit(start_limit),.start_loops(start_loops),
        .ext_cfg_v(ext_cfg_v),.ext_target(ext_target),.ext_cfg_addr(ext_cfg_addr),.ext_cfg_data(ext_cfg_data),
        .ext_desc_v(ext_desc_v),.ext_base(ext_base),.ext_limit(ext_limit),.ext_loops(ext_loops),.ext_launch_v(ext_launch_v),
        .fault(host_fault));
    ot_static_program_target #(.TARGET(8'd48)) target48(
        .clk(clk),.rst_n(rst_n),.cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(eactive),.program_cfg_we(ecfg),.program_cfg_addr(ecfg_addr),.program_cfg_data(ecfg_data),
        .program_start_v(estart),.program_start_base(ebase),.program_start_limit(elimit),.program_start_loops(eloops),
        .configured(econfigured),.fault(target_fault));
    ot_vms_calendar_static #(.W(48)) engine48(
        .clk(clk),.rst_n(rst_n),.cfg_we(ecfg),.cfg_addr(ecfg_addr),.cfg_data(ecfg_data ^ ((MUT==2)?256'd1:256'd0)),
        .start_v(estart),.start_base(ebase),.start_limit(elimit),.start_loops(eloops),
        .calendar(ecal),.calendar_v(ecal_v),.ordinal(eordinal),.active(eactive),.done(edone),.fault(efault));
    // This endpoint proves the production paged SFU/HC transport does not
    // truncate addresses. Their actual paged SRAM/arithmetic gates are separate.
    ot_static_program_target #(.TARGET(8'd80),.PCW(12)) paged_target(
        .clk(clk),.rst_n(rst_n),.cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(1'b0),.program_cfg_we(wide_cfg),.program_cfg_addr(wide_addr),.program_cfg_data(wide_data),
        .program_start_v(wide_start),.program_start_base(wide_base),.program_start_limit(wide_limit),.program_start_loops(wide_loops),
        .configured(wide_configured),.fault(wide_fault));
    // The actual existing loader/CP producer, rather than an idealized LCP pulse.
    ot_hgi_loader_cp #(.MTPH(1)) loader(
        .clk(clk),.rst_n(rst_n),.s_awvalid(c_awvalid),.s_awready(c_awready),.s_awaddr(c_awaddr),
        .s_wvalid(c_wvalid),.s_wready(c_wready),.s_wdata(c_wdata),.s_wstrb(c_wstrb),
        .s_bvalid(c_bvalid),.s_bready(c_bready),.s_arvalid(c_arvalid),.s_arready(c_arready),.s_araddr(c_araddr),
        .s_rvalid(c_rvalid),.s_rready(c_rready),.s_rdata(c_rdata),
        .c_awvalid(),.c_awready(1'b1),.c_awaddr(),.c_wvalid(),.c_wready(1'b1),.c_wdata(),.c_wstrb(),
        .c_bvalid(1'b0),.c_bready(),.c_arvalid(),.c_arready(1'b1),.c_araddr(),
        .c_rvalid(1'b0),.c_rready(),.c_rdata(32'd0),.lcp(lcp_full),.cpl(230'd0),
        .m_req_v(),.m_req_rdy(1'b1),.m_req_addr(),.m_req_len(),.m_rsp_v(1'b0),.m_rsp_data(256'd0),.fault(loader_fault));
    genvar Q;
    generate for(Q=0;Q<4;Q=Q+1)begin:g_programme
        ot_vms_calendar_static #(.W(202)) prog(
            .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we[Q]),.cfg_addr(cfg_addr[Q*10+:10]),
            .cfg_data(cfg_data[Q*256+:256] ^ ((MUT==1 && Q==2)?256'h1:256'd0)),
            .start_v(start_v[Q]),.start_base(start_base[Q*10+:10]),.start_limit(start_limit[Q*11+:11]),.start_loops(start_loops[Q*16+:16]),
            .calendar(calendar[Q*202+:202]),.calendar_v(calendar_v[Q]),.ordinal(ordinal[Q*32+:32]),
            .active(program_active[Q]),.done(program_done[Q]),.fault(program_fault[Q]));
    end endgenerate
    integer cycle=0,launch=-1,emitted=0,engine_count=0,writes=0,wide_writes=0,wide_starts=0,narrow_writes=0;
    reg monitor_run=0;
    function automatic [201:0] pattern(input integer q,input integer pc);
        pattern=({10'h135,64'h79a2468ace013579,64'ha2468ace013579a2,64'h468ace013579a246} ^ 202'(q*128+pc));
    endfunction
    task automatic step;
        begin
            @(posedge clk);#1;cycle++;
            writes+=$countones(cfg_we);
            if(ecfg)narrow_writes++;
            if(wide_cfg)begin
                wide_writes++;
                if(wide_addr!=2053 || wide_data[235:224]!=12'd2053)$fatal(1,"HOST_CALENDAR truncated paged configuration");
            end
            if(wide_start)begin
                wide_starts++;
                if(wide_base!=2053 || wide_limit!=2056 || wide_loops!=17)$fatal(1,"HOST_CALENDAR truncated paged launch");
            end
            if(lcp[71])launch=cycle;
            if(monitor_run && launch>=0 && cycle>=launch+6 && emitted<51)begin
                if(calendar_v!==4'hf)$fatal(1,"HOST_CALENDAR missing fixed output");
                for(integer q=0;q<4;q++)begin
                    if(calendar[q*202+:202]!==pattern(q,5+emitted%3))$fatal(1,"HOST_CALENDAR wrong actual programme q%0d cycle%0d",q,emitted);
                    if(ordinal[q*32+:32]!==32'(emitted))$fatal(1,"HOST_CALENDAR ordinal");
                end
                emitted++;
            end
            if(monitor_run && launch>=0 && cycle>=launch+8 && engine_count<51)begin
                if(!ecal_v || ecal!==48'(pattern(4,5+engine_count%3)) || eordinal!==32'(engine_count))
                    $fatal(1,"HOST_CALENDAR wrong engine target48 word%0d",engine_count);
                engine_count++;
            end
        end
    endtask
    task automatic write32(input [11:0] addr,input [31:0] data_);
        begin
            @(negedge clk);s_awaddr=addr;s_wdata=data_;s_awvalid=1;s_wvalid=1;
            #1;while(!s_awready || !s_wready)begin step();@(negedge clk);#1;end
            step();@(negedge clk);s_awvalid=0;s_wvalid=0;step();
        end
    endtask
    reg [255:0] word_;
    initial begin
        step();@(negedge clk);rst_n=1;
        for(integer q=0;q<4;q++)begin
            write32(12'hf00,32'((5<<2)|q));
            for(integer pc=5;pc<8;pc++)begin
                word_=0;word_[255:240]=16'hc7a1;word_[233:224]=10'(pc);word_[201:0]=pattern(q,pc);
                for(integer w=0;w<8;w++)write32(12'hf04,word_[w*32+:32]);
            end
            write32(12'hf08,32'((8<<10)|5));write32(12'hf0c,17);
        end
        repeat(3)step();if(writes!=12)$fatal(1,"HOST_CALENDAR missing native config writes");
        write32(12'hf20,32'((5<<8)|48));
        for(integer pc=5;pc<8;pc++)begin
            word_=0;word_[255:240]=16'hc7a1;word_[233:224]=10'(pc);word_[47:0]=48'(pattern(4,pc));
            for(integer w=0;w<8;w++)write32(12'hf24,word_[w*32+:32]);
        end
        write32(12'hf28,32'((8<<12)|5));write32(12'hf2c,17);
        repeat(3)step();if(!econfigured)$fatal(1,"HOST_CALENDAR external target not configured");
        write32(12'hf20,32'((2053<<8)|80));
        word_=0;word_[255:240]=16'hc7a1;word_[235:224]=12'd2053;
        for(integer w=0;w<8;w++)write32(12'hf24,word_[w*32+:32]);
        write32(12'hf28,32'((2056<<12)|2053));write32(12'hf2c,17);
        repeat(3)step();if(!wide_configured || wide_writes!=1)$fatal(1,"HOST_CALENDAR paged target missing configuration");
        // Existing MTP E window remains a real producer, not intercepted by F.
        write32(12'he00,32'h12345678);
        // Real C10 doorbell causes actual loader LCP[71], then four programmes.
        monitor_run=1;write32(12'hc10,1);
        while(emitted<51)step();
        if(program_done!==4'hf || host_fault || loader_fault || (|program_fault))$fatal(1,"HOST_CALENDAR fault/completion");
        while(engine_count<51)step();
        if(!edone || efault || target_fault || wide_fault || wide_starts!=1)$fatal(1,"HOST_CALENDAR engine target completion");
        step();if(calendar_v!=0 || ecal_v)$fatal(1,"HOST_CALENDAR late programme replay");
        // A 10-bit engine cannot alias a legal 12-bit host address into its
        // low programme page. The typed target must reject it before SRAM WE.
        write32(12'hf20,32'((2053<<8)|48));
        for(integer w=0;w<8;w++)write32(12'hf24,word_[w*32+:32]);
        repeat(3)step();
        if(!target_fault || narrow_writes!=3)$fatal(1,"HOST_CALENDAR narrow target silently aliased wide PC");
        $display("VMS_STATIC_HOST_CALENDAR PASS real loaderCP doorbell five actual programme SRAMs15 configwords51 gapless slots VM LCP+6 engine48 LCP+8 paged2053 transport no truncation");$finish;
    end
endmodule
