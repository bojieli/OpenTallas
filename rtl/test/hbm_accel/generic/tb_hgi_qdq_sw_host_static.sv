`timescale 1ns/1ps
// Actual QDQ decoder + eight actual VM bank pipelines and 24 mapped SRAM macros.
// Golden vectors and external preload are declared component-boundary stimuli.
// SW replica component boundary: real L0 FP8 shape; external original operands and expected golden,
// no substitution inside arithmetic. SU producer norm/rope and DMA consumer epochs remain unbound.
module tb_hgi_qdq_sw_host_static #(parameter integer MUT=0,PIN_BOUNDARY=0);
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, cv=0, last=0;
    reg [5:0] op=0; reg [7:0] block_n=0;
    reg [15:0] src=0,dst=0;

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
    ot_hgi_loader_cp #(.MTPH(1)) loader(
        .clk(clk),.rst_n(rst_n),.s_awvalid(c_awvalid),.s_awready(c_awready),.s_awaddr(c_awaddr),
        .s_wvalid(c_wvalid),.s_wready(c_wready),.s_wdata(c_wdata),.s_wstrb(c_wstrb),
        .s_bvalid(c_bvalid),.s_bready(c_bready),.s_arvalid(c_arvalid),.s_arready(c_arready),.s_araddr(c_araddr),
        .s_rvalid(c_rvalid),.s_rready(c_rready),.s_rdata(c_rdata),
        .c_awvalid(),.c_awready(1'b1),.c_awaddr(),.c_wvalid(),.c_wready(1'b1),.c_wdata(),.c_wstrb(),
        .c_bvalid(1'b0),.c_bready(),.c_arvalid(),.c_arready(1'b1),.c_araddr(),
        .c_rvalid(1'b0),.c_rready(),.c_rdata(32'd0),.lcp(lcp_full),.cpl(230'd0),
        .m_req_v(),.m_req_rdy(1'b1),.m_req_addr(),.m_req_len(),.m_rsp_v(1'b0),.m_rsp_data(256'd0),.fault(loader_fault));
    wire [135:0] rq; wire [2055:0] rr; wire [2055:0] rr_bank;
    reg [2055:0] rr_late; always @(posedge clk) rr_late<=rr_bank;
    assign rr=(MUT==3)?rr_late:rr_bank; wire [2247:0] wq;
    wire done,rdone,fault; wire [7:0] bankdone;
    reg preload=1;
    reg [2247:0] pwq=0;
    reg [135:0] prq=0;
    wire [143:0] status;
    ot_hgi_qdq_sw_host_static #(.MUT(MUT==1?1:MUT==2?2:0),.COMPACT(1),.PIN_BOUNDARY(PIN_BOUNDARY)) dut(
        .clk_program(clk),.clk_transport(clk),.clk_dxl(clk),.clk_dbq(clk),.clk_daq(clk),.rst_n(rst_n),
        .cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(eactive),.program_done(edone),.configured(econfigured),
        .rq(rq),.rr(rr),.wq(wq),.beat_done(done),.record_done(rdone),.fault(fault));
    wire [7:0] nw_rslot_v,nw_wslot_v;wire [23:0] nw_rslot,nw_wslot;
    for(genvar Q=0;Q<4;Q=Q+1) begin: vm_programmes
        if(Q==0) begin: actual_SW
            hfd_hgi_vm_calendar_SW_quant prog(
                .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we[Q]),.cfg_addr(cfg_addr[Q*10+:10]),.cfg_data(cfg_data[Q*256+:256]),
                .start_v(start_v[Q]),.start_base(start_base[Q*10+:10]),.start_limit(start_limit[Q*11+:11]),.start_loops(start_loops[Q*16+:16]),
                .active(program_active[Q]),.done(program_done[Q]),.fault(program_fault[Q]),
                .calendar_v(calendar_v[Q]),.rslot_v(nw_rslot_v),.rslot(nw_rslot),.wslot_v(nw_wslot_v),.wslot(nw_wslot));
        end else begin: idle_other_quadrants
            ot_vms_calendar_static #(.W(202)) prog(
                .clk(clk),.rst_n(rst_n),.cfg_we(cfg_we[Q]),.cfg_addr(cfg_addr[Q*10+:10]),.cfg_data(cfg_data[Q*256+:256]),
                .start_v(start_v[Q]),.start_base(start_base[Q*10+:10]),.start_limit(start_limit[Q*11+:11]),.start_loops(start_loops[Q*16+:16]),
                .active(program_active[Q]),.done(program_done[Q]),.fault(program_fault[Q]),.calendar(),.calendar_v(calendar_v[Q]),.ordinal());
        end
    end
    for(genvar g=0;g<8;g=g+1) begin: banks
        wire [16:0] arq=preload?prq[g*17+:17]:rq[g*17+:17];
        wire [280:0] awq=preload?pwq[g*281+:281]:wq[g*281+:281];
        wire [17:0] st;
        wire [6*257-1:0] fullrr;wire [1:0] fulldone;
        assign rr_bank[g*257+:257]=fullrr[5*257+:257];
        assign bankdone[g]=fulldone[1];
        ot_vms_bank_static #(.RG(6),.WG(2)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(g)),.sid(2'd0),
            .rslot_v(preload?arq[16]:nw_rslot_v[g]),.rslot(preload?3'd5:nw_rslot[g*3+:3]),
            .wslot_v(preload?awq[280]:nw_wslot_v[g]),.wslot(preload?3'd1:(nw_wslot[g*3+:3] ^ (MUT==4?3'd1:3'd0))),.rq({arq,85'd0}),.rr(fullrr),
            .wq({awq,281'd0}),.wq_done(fulldone),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
            .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(st));
        assign status[g*18+:18]=st;
    end
    reg [255:0] gi[0:127],go[0:127];
    reg [255:0] program_image[0:1023],nw_program_image[0:174];
    integer fd,nrec,k,s,j,n[0:15],ab[0:15],ob[0:15],ops[0:15],blks[0:15],costs[0:15];
    integer cyc=0,t0=0,total_cost=0,nbeat=0,nreturn=0,nrecord=0,nwrite=0,nissue=0,total_beats=0,ncheck=0,bad=0,exp_commit,last_write=0,last_commit=0,ncommit=0;
    reg launched=0;
    reg check_fault=0; string dir,fn,programfile;
    // Independent scoreboard: compare every actual bank write to immutable golden sectors,
    // then read the physically mapped macro output back after commit.
    reg [255:0] expect_word[0:32767]; reg [32767:0] expect_valid='0;
    integer bankidx,secidx;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(lcp[71] && !launched) begin launched=1;t0=cyc-1;end
        if(!preload && dut.command_v && dut.command[0]) begin
            if(dut.ordinal!=nissue || cyc-t0!=nissue+15) $fatal(1,"programme fixed issue expected%0d actualordinal%0d cycle%0d",nissue,dut.ordinal,cyc-t0);
            nissue++;
        end
        if(!preload && (dut.engine.transport.bad || dut.engine.decode_fault || (dut.engine.vo&&dut.engine.qfault) || dut.engine.vo!=dut.engine.transport.dv[24]))
            $display("FAULT_CAUSE cycle=%0d bad=%b decode=%b qfault=%b vo=%b expected=%b rr_mask=%b",cyc-t0,dut.engine.transport.bad,dut.engine.decode_fault,dut.engine.qfault,dut.engine.vo,dut.engine.transport.dv[24],dut.engine.transport.expected);
    end
    always @(negedge clk) if(!preload && rst_n) begin
        if((host_fault || loader_fault || (|program_fault)) && !check_fault) $fatal(1,"native host/calendar fault");
        if(fault && !check_fault) $fatal(1,"unexpected static fault at cycle %0d vo=%b expected=%b",cyc-t0,dut.engine.vo,dut.engine.transport.dv[24]);
        if(launched && cyc-t0>181 && nreturn!=nbeat) $fatal(1,"native fixed completion missing");
        if(done) nreturn=nreturn+1;
        if(done != (|bankdone)) $fatal(1,"fixed done differs from actual bank commit cycle%0d",cyc-t0);
        for(integer b=0;b<8;b=b+1) if(bankdone[b]) begin ncommit++;last_commit=cyc-t0;end
        if(rdone) nrecord=nrecord+1;
        for(integer b=0;b<8;b=b+1) if(wq[b*281+280]) begin
            integer a;
            a=int'(wq[b*281+264+:16]);
            if(a[2:0]!=3'(b) || !expect_valid[a]) $fatal(1,"unexpected bank write b%0d address%0d",b,a);
            if(wq[b*281+8+:256]!==expect_word[a]) $fatal(1,"gold mismatch addr%0d got%h want%h",a,wq[b*281+8+:256],expect_word[a]);
            if(wq[b*281+:8]!==8'hff) $fatal(1,"write mask");
            expect_valid[a]=0;nwrite=nwrite+1;last_write=cyc-t0;
        end
        for(integer b=0;b<8;b=b+1) if(status[b*18+17]) $fatal(1,"bank fault %0d %h",b,status[b*18+:18]);
    end
    task automatic host_step;
        begin @(posedge clk);#1;end
    endtask
    task automatic write32(input [11:0] addr,input [31:0] data_);
        begin
            @(negedge clk);s_awaddr=addr;s_wdata=data_;s_awvalid=1;s_wvalid=1;
            #1;while(!s_awready || !s_wready)begin host_step();@(negedge clk);#1;end
            host_step();@(negedge clk);s_awvalid=0;s_wvalid=0;host_step();
        end
    endtask
    initial begin
        if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"+DIR required");
        fd=$fopen({dir,"/recs.txt"},"r");void'($fscanf(fd,"%d",nrec));
        for(k=0;k<nrec;k=k+1) begin
            void'($fscanf(fd,"%d %d %d %d %d %d",ops[k],n[k],ab[k],ob[k],costs[k],blks[k]));
            ab[k]=ab[k]%65536;ob[k]=ob[k]%65536;total_cost+=costs[k];
        end
        $fclose(fd);
        for(k=0;k<nrec;k=k+1) total_beats+=n[k]/32;
        if(!$value$plusargs("PROGRAM=%s",programfile)) $fatal(1,"+PROGRAM required");
        $readmemh(programfile,program_image,0,nrec-1);
        $readmemh("results/hbm_static_quant_1015/SW_replica/SW_program.hex",nw_program_image,0,174);
        repeat(8) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);
        for(k=0;k<nrec;k=k+1) begin
            fn=$sformatf("%s/in_%0d.hex",dir,k);$readmemh(fn,gi,0,n[k]/8-1);
            fn=$sformatf("%s/out_%0d.hex",dir,k);$readmemh(fn,go,0,n[k]/8-1);
            for(s=0;s<n[k]/8;s=s+1) begin
                @(negedge clk);pwq=0;
                bankidx=(ab[k]/8+s)&7;
                pwq[bankidx*281+:281]={1'b1,16'(ab[k]/8+s),gi[s],8'hff};
                expect_word[ob[k]/8+s]=go[s];expect_valid[ob[k]/8+s]=1;
            end
            @(negedge clk);pwq=0;
        end
        repeat(16) @(negedge clk);
        // Real AXI F-window, actual loader CP doorbell, actual local target125.
        for(integer quadrant=0;quadrant<4;quadrant++) begin
            write32(12'hf00,32'(quadrant));
            for(integer pc=0;pc<175;pc++) begin
                reg [255:0] word_;
                word_=0;word_[255:240]=16'hc7a1;word_[233:224]=10'(pc);
                if(quadrant==0) word_=nw_program_image[pc];
                for(integer piece=0;piece<8;piece++) write32(12'hf04,word_[piece*32+:32]);
            end
            write32(12'hf08,32'(175<<10));write32(12'hf0c,1);
        end
        write32(12'hf20,32'(MUT==5?48:125));
        for(integer pc=0;pc<nrec;pc++) begin
            for(integer piece=0;piece<8;piece++) write32(12'hf24,program_image[pc][piece*32+:32]);
        end
        write32(12'hf28,32'(nrec<<12));write32(12'hf2c,MUT==6?2:1);
        repeat(8) @(negedge clk);
        if(MUT!=5 && !econfigured) $fatal(1,"Quant target125 not configured");
        nbeat=total_beats;preload=0;
        write32(12'hc10,1);
        repeat(160) @(negedge clk);
        repeat(64) @(negedge clk);
        if(nissue!=nbeat || nreturn!=nbeat || nrecord!=nrec || nwrite!=4*nbeat || ncommit!=4*nbeat || expect_valid!='0)
            $fatal(1,"accounting beats%0d/%0d records%0d/%0d writes%0d/%0d",nreturn,nbeat,nrecord,nrec,nwrite,4*nbeat);
        // Four cycles after last write pin = actual bank commit edge.
        if(last_commit > (total_cost*11)/10) $fatal(1,"throughput miss cycles%0d immutable%0d",last_commit,total_cost);
        preload=1;check_fault=1; // declared external readback owner; quant idle observer may flag these reads
        for(k=0;k<nrec;k=k+1) begin
            fn=$sformatf("%s/out_%0d.hex",dir,k);$readmemh(fn,go,0,n[k]/8-1);
            for(s=0;s<n[k]/8;s=s+1) begin
                @(negedge clk);prq=0;bankidx=(ob[k]/8+s)&7;
                prq[bankidx*17+:17]={1'b1,16'(ob[k]/8+s)};
                @(negedge clk);prq=0;
                repeat(6) @(negedge clk);
                if(!rr[bankidx*257+256] || rr[bankidx*257+:256]!==go[s])
                    $fatal(1,"SRAM readback mismatch rec%0d sec%0d v%b got%h want%h",k,s,rr[bankidx*257+256],rr[bankidx*257+:256],go[s]);
                ncheck++;
                @(negedge clk);
            end
        end
        $display("PASS HGI_QDQ_SW_TARGET125_NATIVE_HOST RG5_WG1 records=%0d beats=%0d sectors=%0d commit_cycles=%0d immutable_price=%0d historical_wq3_price_not_applied=1 programme_macros=5 data_macros=24 real_loaderCP_target125=1",nrec,nbeat,ncheck,last_commit,total_cost);
        $finish;
    end
    initial begin repeat(20000) @(negedge clk);$fatal(1,"watchdog: fixed component timeline exceeded");end
endmodule
