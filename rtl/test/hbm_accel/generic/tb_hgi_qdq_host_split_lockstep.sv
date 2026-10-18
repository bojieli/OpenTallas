`timescale 1ns/1ps
// OWNERS-HBM/QDQ 2026-10-18: lockstep of the d4g split composition ot_hgi_qdq_host_split against the monolith
// ot_hgi_qdq_host_static #(RL7,WC4,COMPACT1) as GEN0 binds hb_quant_NW.  Both receive the SAME target48 configuration,
// descriptor and launch from one real AXI host window + loader CP doorbell (ot_vms_calendar_host_static / ot_hgi_loader_cp,
// as tb_hgi_qdq_compact_host_pin_boundary).  Each drives its own fixed-latency VM model (RL edges at the pins, no ready),
// preloaded with the qdqvec input sectors.  Every cycle, after the launch:
//   split rq                         == monolith rq,                         delayed RQ_OFF=1 edge
//   split wq / beat_done / record_done == monolith wq / beat_done / record_done, delayed WQ_OFF=5 edges
//   split program_active/done/configured == monolith, same edge;  neither raises fault
// and every bank write of each DUT matches the golden output sector.  MUT (bench): 1 = split built with LGMUT=1
// (quant_NW0/quant_NW1 write ports crossed); 2 = split built with RL=5 (LG/transport edges not priced).
module tb_hgi_qdq_host_split_lockstep #(parameter integer MUT=0,RQ_OFF=1,WQ_OFF=5,L=7);
    reg clk=0; always #5 clk=~clk;
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
    wire loader_fault,host_fault;
    wire ext_cfg_v,ext_desc_v,ext_launch_v;
    wire [7:0] ext_target;
    wire [11:0] ext_cfg_addr,ext_base;
    wire [255:0] ext_cfg_data;
    wire [12:0] ext_limit;
    wire [15:0] ext_loops;
    ot_vms_calendar_host_static host(
        .clk(clk),.rst_n(rst_n),.s_awvalid(s_awvalid),.s_awready(s_awready),.s_awaddr(s_awaddr),
        .s_wvalid(s_wvalid),.s_wready(s_wready),.s_wdata(s_wdata),.s_wstrb(4'hf),
        .s_bvalid(s_bvalid),.s_bready(1'b1),.s_arvalid(s_arvalid),.s_arready(s_arready),.s_araddr(s_araddr),
        .s_rvalid(s_rvalid),.s_rready(1'b1),.s_rdata(s_rdata),
        .c_awvalid(c_awvalid),.c_awready(c_awready),.c_awaddr(c_awaddr),
        .c_wvalid(c_wvalid),.c_wready(c_wready),.c_wdata(c_wdata),.c_wstrb(c_wstrb),
        .c_bvalid(c_bvalid),.c_bready(c_bready),.c_arvalid(c_arvalid),.c_arready(c_arready),.c_araddr(c_araddr),
        .c_rvalid(c_rvalid),.c_rready(c_rready),.c_rdata(c_rdata),.lcp_doorbell(lcp_full[71]),
        .program_active(4'd0),.program_done(4'd0),.program_fault(4'd0),
        .cfg_we(),.cfg_addr(),.cfg_data(),.start_v(),.start_base(),.start_limit(),.start_loops(),
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

    // ---- DUT A: the monolith as GEN0 binds it; DUT B: the d4g split composition
    wire [135:0] rqA,rqB; wire [2055:0] rrA,rrB; wire [2247:0] wqA,wqB;
    wire actA,actB,pdA,pdB,cfgA,cfgB,bdA,bdB,rdA,rdB,fA,fB;
    ot_hgi_qdq_host_static #(.RL(7),.WC(4),.COMPACT(1)) mono(
        .clk_program(clk),.clk_transport(clk),.clk_dxl(clk),.clk_dbq(clk),.clk_daq(clk),.rst_n(rst_n),
        .cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(actA),.program_done(pdA),.configured(cfgA),
        .rq(rqA),.rr(rrA),.wq(wqA),.beat_done(bdA),.record_done(rdA),.fault(fA));
    ot_hgi_qdq_host_split #(.RL(MUT==2?5:7),.WC(4),.COMPACT(1),.LGMUT(MUT==1?1:0)) split(
        .clk_program(clk),.clk_transport(clk),.clk_dxl(clk),.clk_dbq(clk),.clk_daq(clk),.rst_n(rst_n),
        .cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(actB),.program_done(pdB),.configured(cfgB),
        .rq(rqB),.rr(rrB),.wq(wqB),.beat_done(bdB),.record_done(rdB),.fault(fB));

    // ---- fixed-latency VM models: rr of bank b = {1, mem[addr]} exactly L edges after rq of bank b at the pins
    reg [255:0] memA[0:65535], memB[0:65535];
    reg [2055:0] pA[0:L-1], pB[0:L-1];
    reg [2055:0] lkA,lkB;
    always @* begin
        lkA='0; lkB='0;
        for(integer b=0;b<8;b=b+1) begin
            if(rqA[b*17+16]) lkA[b*257+:257]={1'b1,memA[rqA[b*17+:16]]};
            if(rqB[b*17+16]) lkB[b*257+:257]={1'b1,memB[rqB[b*17+:16]]};
        end
    end
    always @(posedge clk) begin
        pA[0]<=lkA; pB[0]<=lkB;
        for(integer i=1;i<L;i=i+1) begin pA[i]<=pA[i-1]; pB[i]<=pB[i-1]; end
    end
    assign rrA=pA[L-1]; assign rrB=pB[L-1];

    // ---- monolith delay lines (posedge), compared at negedge
    reg [135:0] rqA_d[1:RQ_OFF];
    reg [2247:0] wqA_d[1:WQ_OFF];
    reg [WQ_OFF:1] bdA_d, rdA_d;
    always @(posedge clk) begin
        rqA_d[1]<=rqA; wqA_d[1]<=wqA; bdA_d[1]<=bdA; rdA_d[1]<=rdA;
        for(integer i=2;i<=RQ_OFF;i=i+1) rqA_d[i]<=rqA_d[i-1];
        for(integer i=2;i<=WQ_OFF;i=i+1) begin wqA_d[i]<=wqA_d[i-1]; bdA_d[i]<=bdA_d[i-1]; rdA_d[i]<=rdA_d[i-1]; end
    end

    reg [255:0] gi[0:127],go[0:127];
    reg [255:0] program_image[0:1023];
    reg [255:0] expect_word[0:65535];
    reg [65535:0] expA='0, expB='0;
    integer fd,nrec,k,s,n[0:15],ab[0:15],ob[0:15],ops[0:15],blks[0:15],costs[0:15];
    integer cyc=0,t0=0,total_cost=0,total_beats=0;
    integer nrqA=0,nrqB=0,nwA=0,nwB=0,nbA=0,nbB=0,nrA=0,nrB=0,lastA=0,lastB=0,ncmp=0;
    reg launched=0, armed=0;
    string dir,programfile;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(lcp_full[71] && !launched) begin launched=1;t0=cyc-1;end
    end
    task automatic chk_writes(input [2247:0] w, inout reg [65535:0] ex, inout integer nw, inout integer last, input string who);
        for(integer b=0;b<8;b=b+1) if(w[b*281+280]) begin
            integer a;
            a=int'(w[b*281+264+:16]);
            if(a[2:0]!=3'(b) || !ex[a]) $fatal(1,"LOCKSTEP_FAIL %s unexpected bank write b%0d address%0d cycle%0d",who,b,a,cyc-t0);
            if(w[b*281+8+:256]!==expect_word[a]) $fatal(1,"LOCKSTEP_FAIL %s gold mismatch addr%0d",who,a);
            if(w[b*281+:8]!==8'hff) $fatal(1,"LOCKSTEP_FAIL %s write mask",who);
            ex[a]=0; nw=nw+1; last=cyc-t0;
        end
    endtask
    always @(negedge clk) if(rst_n && armed) begin
        if(host_fault || loader_fault) $fatal(1,"LOCKSTEP_FAIL host/loader fault host%b loader%b cycle%0d",host_fault,loader_fault,cyc);
        if(fA) $fatal(1,"LOCKSTEP_FAIL monolith unexpected static fault cycle%0d",cyc-t0);
        if(fB) $fatal(1,"LOCKSTEP_FAIL split unexpected static fault cycle%0d",cyc-t0);
        if({actA,pdA,cfgA}!=={actB,pdB,cfgB}) $fatal(1,"LOCKSTEP_FAIL programme status A%b B%b cycle%0d",{actA,pdA,cfgA},{actB,pdB,cfgB},cyc-t0);
        for(integer b=0;b<8;b=b+1) begin
            if(rqB[b*17+16]!==rqA_d[RQ_OFF][b*17+16] || (rqB[b*17+16] && rqB[b*17+:16]!==rqA_d[RQ_OFF][b*17+:16]))
                $fatal(1,"LOCKSTEP_FAIL rq bank%0d cycle%0d split %h monolith+%0d %h",b,cyc-t0,rqB[b*17+:17],RQ_OFF,rqA_d[RQ_OFF][b*17+:17]);
            if(wqB[b*281+280]!==wqA_d[WQ_OFF][b*281+280] || (wqB[b*281+280] && wqB[b*281+:280]!==wqA_d[WQ_OFF][b*281+:280]))
                $fatal(1,"LOCKSTEP_FAIL wq bank%0d cycle%0d split v%b a%h monolith+%0d v%b a%h",b,cyc-t0,wqB[b*281+280],wqB[b*281+264+:16],
                    WQ_OFF,wqA_d[WQ_OFF][b*281+280],wqA_d[WQ_OFF][b*281+264+:16]);
            if(rqA[b*17+16]) nrqA++;
            if(rqB[b*17+16]) nrqB++;
        end
        if(bdB!==bdA_d[WQ_OFF] || rdB!==rdA_d[WQ_OFF]) $fatal(1,"LOCKSTEP_FAIL done cycle%0d split %b%b monolith+%0d %b%b",cyc-t0,bdB,rdB,WQ_OFF,bdA_d[WQ_OFF],rdA_d[WQ_OFF]);
        if(bdA) nbA++; if(bdB) nbB++; if(rdA) nrA++; if(rdB) nrB++;
        chk_writes(wqA,expA,nwA,lastA,"monolith");
        chk_writes(wqB,expB,nwB,lastB,"split");
        ncmp++;
    end
    task automatic host_step; begin @(posedge clk);#1;end endtask
    task automatic write32(input [11:0] addr,input [31:0] data_);
        begin
            @(negedge clk);s_awaddr=addr;s_wdata=data_;s_awvalid=1;s_wvalid=1;
            #1;while(!s_awready || !s_wready)begin host_step();@(negedge clk);#1;end
            host_step();@(negedge clk);s_awvalid=0;s_wvalid=0;host_step();
        end
    endtask
    initial begin
        if(!$value$plusargs("DIR=%s",dir)) $fatal(1,"+DIR required");
        if(!$value$plusargs("PROGRAM=%s",programfile)) $fatal(1,"+PROGRAM required");
        fd=$fopen({dir,"/recs.txt"},"r");void'($fscanf(fd,"%d",nrec));
        for(k=0;k<nrec;k=k+1) begin
            void'($fscanf(fd,"%d %d %d %d %d %d",ops[k],n[k],ab[k],ob[k],costs[k],blks[k]));
            ab[k]=ab[k]%65536;ob[k]=ob[k]%65536;total_cost+=costs[k];total_beats+=n[k]/32;
        end
        $fclose(fd);
        $readmemh(programfile,program_image,0,nrec-1);
        for(integer a=0;a<65536;a++) begin memA[a]=256'd0; memB[a]=256'd0; end
        for(k=0;k<nrec;k=k+1) begin
            $readmemh($sformatf("%s/in_%0d.hex",dir,k),gi,0,n[k]/8-1);
            $readmemh($sformatf("%s/out_%0d.hex",dir,k),go,0,n[k]/8-1);
            for(s=0;s<n[k]/8;s=s+1) begin
                memA[ab[k]/8+s]=gi[s]; memB[ab[k]/8+s]=gi[s];
                expect_word[ob[k]/8+s]=go[s]; expA[ob[k]/8+s]=1; expB[ob[k]/8+s]=1;
            end
        end
        repeat(8) @(negedge clk);rst_n=1;repeat(8) @(negedge clk);
        armed=1;
        // the four quadrant VM descriptors must be valid before the doorbell (host rule); one idle canonical word each
        for(integer quadrant=0;quadrant<4;quadrant++) begin
            reg [255:0] word_;
            word_=0;word_[255:240]=16'hc7a1;
            write32(12'hf00,32'(quadrant));
            for(integer piece=0;piece<8;piece++) write32(12'hf04,word_[piece*32+:32]);
            write32(12'hf08,32'(1<<10));write32(12'hf0c,1);
        end
        write32(12'hf20,32'd48);
        for(integer pc=0;pc<nrec;pc++) for(integer piece=0;piece<8;piece++) write32(12'hf24,program_image[pc][piece*32+:32]);
        write32(12'hf28,32'(nrec<<12));write32(12'hf2c,1);
        for(integer w=0;w<64 && !cfgA;w++) @(negedge clk);
        if(!cfgA || !cfgB) $fatal(1,"LOCKSTEP_FAIL target48 not configured A%b B%b",cfgA,cfgB);
        write32(12'hc10,1);
        repeat(260) @(negedge clk);
        if(nbA!=total_beats || nbB!=total_beats || nrA!=nrec || nrB!=nrec || nwA!=4*total_beats || nwB!=4*total_beats ||
           expA!='0 || expB!='0 || nrqA!=4*total_beats || nrqB!=4*total_beats)
            $fatal(1,"LOCKSTEP_FAIL accounting beats A%0d B%0d /%0d records A%0d B%0d /%0d writes A%0d B%0d reads A%0d B%0d",
                nbA,nbB,total_beats,nrA,nrB,nrec,nwA,nwB,nrqA,nrqB);
        if(lastB-lastA!=WQ_OFF) $fatal(1,"LOCKSTEP_FAIL last write offset %0d",lastB-lastA);
        $display("PASS HGI_QDQ_HOST_SPLIT_LOCKSTEP records=%0d beats=%0d reads=%0d writes=%0d cycles_compared=%0d monolith_last_write=%0d split_last_write=%0d rq_offset=%0d wq_done_offset=%0d immutable_price=%0d VM_latency_at_pins=%0d",
            nrec,total_beats,nrqB,nwB,ncmp,lastA,lastB,RQ_OFF,WQ_OFF,total_cost,L);
        $finish;
    end
    initial begin repeat(30000) @(negedge clk);$fatal(1,"LOCKSTEP_FAIL watchdog");end
endmodule
