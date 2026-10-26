`timescale 1ns/1ps
// HBM-P4-QUANT 2026-10-23 (COORD R6(3)): lockstep of ONE quadrant's replicated QUANT + VM write-merge group
// ot_hbm_quant_vmm_q #(Q) (hb_quant_Q = ot_hgi_qdq_host_split_q, idx_share_Q = ot_hbm_idx_vm_share2_static_r,
// vmm_Q0..7 = hfd_vms_wq2_merge) against the golden monolith ot_hgi_qdq_host_static #(RL=L,WC4,COMPACT1), derived from
// tb_hgi_qdq_host_split_r2_lockstep (same real AXI host window + loader CP doorbell, same qdqvec records and golden
// output sectors).  The host programmes target 8'h30+Q; the monolith (hard target 48) sees that id renamed to 48.
// Every cycle after the launch:
//   group vm_rq (bank face, share pin flop)   == monolith rq   delayed RQ_OFF+1 edges
//   group wq_m  (bank wq1, after the merge)   == monolith wq   delayed WQ_OFF+2 edges   (SM writer idle)
//   group wq_done2[k] == bank k done (model: wq_m valid + DONE_LAT) +1 edge, wq_done1 never; no fault, no flt
//   programme active/done/configured equal; every bank write matches the golden sector; accounting exact.
// Isolation: a NEIGHBOUR group #(Q+1 mod 4) on the same configuration broadcast must never configure, read or write.
// MUT 1: DUT strap of quadrant Q^1 (wrong quadrant id); 2: vmm bank pair 0/1 crossed; 3: vmm done steering one edge late.
module tb_hbm_quant_vmm_q_lockstep #(parameter integer Q=0,MUT=0,L=54,BANK_RT=51,LB=52,DONE_LAT=5,RING_RAND=1,
                                     RQ_OFF=3+1,WQ_OFF=9+2);
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

    // ---- DUT A: golden monolith (target 48); DUT B: the quadrant group; NB: the neighbour quadrant group
    localparam [7:0] TGT=8'h30+8'(Q);
    localparam integer QN=(Q+1)%4;
    wire [7:0] mono_target=(ext_target==TGT)?8'd48:((ext_target==8'd48)?8'hff:ext_target);
    wire [135:0] rqA,vrqB,vrqN; wire [2055:0] rrA,vrrB; wire [2247:0] wqA,wqB,wqN;
    wire actA,actB,actN,pdA,pdB,pdN,cfgA,cfgB,cfgN,bdA,bdB,bdN,rdA,rdB,rdN,fA,fB,fN,sfB,sfN;
    wire [2055:0] idx_rrB,idx_rrN;
    wire [7:0] d1B,d2B,flB,d1N,d2N,flN;
    reg  [7:0] done_m;
    ot_hgi_qdq_host_static #(.RL(L),.WC(4),.COMPACT(1)) mono(
        .clk_program(clk),.clk_transport(clk),.clk_dxl(clk),.clk_dbq(clk),.clk_daq(clk),.rst_n(rst_n),
        .cfg_v(ext_cfg_v),.cfg_target(mono_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(actA),.program_done(pdA),.configured(cfgA),
        .rq(rqA),.rr(rrA),.wq(wqA),.beat_done(bdA),.record_done(rdA),.fault(fA));
    ot_hbm_quant_vmm_q #(.Q(Q),.RL(L),.WC(4),.BANK_RT(BANK_RT),.DONE_LAT(DONE_LAT),.MUT(MUT)) dut(
        .clk_program(clk),.clk_transport(clk),.clk_dec(clk),.rst_n(rst_n),.clk_lg({4{clk}}),.clk_share({4{clk}}),.clk_vmm({8{clk}}),
        .cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(actB),.program_done(pdB),.configured(cfgB),
        .idx_rq(136'd0),.idx_rr(idx_rrB),.vm_rq(vrqB),.vm_rr(vrrB),.wq_sm(2248'd0),.wq_m(wqB),.done_m(done_m),
        .wq_done1(d1B),.wq_done2(d2B),.vmm_flt(flB),.beat_done(bdB),.record_done(rdB),.fault(fB),.share_fault(sfB));
    ot_hbm_quant_vmm_q #(.Q(QN),.RL(L),.WC(4),.BANK_RT(BANK_RT),.DONE_LAT(DONE_LAT)) nbr(
        .clk_program(clk),.clk_transport(clk),.clk_dec(clk),.rst_n(rst_n),.clk_lg({4{clk}}),.clk_share({4{clk}}),.clk_vmm({8{clk}}),
        .cfg_v(ext_cfg_v),.cfg_target(ext_target),.cfg_addr(ext_cfg_addr),.cfg_data(ext_cfg_data),
        .desc_v(ext_desc_v),.desc_base(ext_base),.desc_limit(ext_limit),.desc_loops(ext_loops),.launch_v(ext_launch_v),
        .program_active(actN),.program_done(pdN),.configured(cfgN),
        .idx_rq(136'd0),.idx_rr(idx_rrN),.vm_rq(vrqN),.vm_rr(2056'd0),.wq_sm(2248'd0),.wq_m(wqN),.done_m(8'd0),
        .wq_done1(d1N),.wq_done2(d2N),.vmm_flt(flN),.beat_done(bdN),.record_done(rdN),.fault(fN),.share_fault(sfN));
    if(RING_RAND!=0) begin: ring_rand   // power-up: random ctl_r4 ring contents and pointer (as the r3 gate)
        initial begin
            #1;
            for(integer i=0;i<128;i=i+1) dut.hb_quant_Q.quant_Q_xp.ctl.u_ctl.ring.arr[i]={$random,$random};
            for(integer i=0;i<64;i=i+1) dut.hb_quant_Q.quant_Q_xp.ctl.u_ctl.commit.arr[i]=16'($random);
            dut.hb_quant_Q.quant_Q_xp.ctl.u_ctl.wp=7'($random);
        end
    end

    // ---- fixed-latency VM models: monolith rr exactly L edges after its rq; group bank face answers LB edges after vm_rq
    reg [255:0] memA[0:65535], memB[0:65535];
    reg [2055:0] pA[0:L-1], pB[0:LB-1];
    reg [2055:0] lkA,lkB;
    always @* begin
        lkA='0; lkB='0;
        for(integer b=0;b<8;b=b+1) begin
            if(rqA[b*17+16]) lkA[b*257+:257]={1'b1,memA[rqA[b*17+:16]]};
            if(vrqB[b*17+16]) lkB[b*257+:257]={1'b1,memB[vrqB[b*17+:16]]};
        end
    end
    always @(posedge clk) begin
        pA[0]<=lkA; pB[0]<=lkB;
        for(integer i=1;i<L;i=i+1) pA[i]<=pA[i-1];
        for(integer i=1;i<LB;i=i+1) pB[i]<=pB[i-1];
    end
    assign rrA=pA[L-1]; assign vrrB=pB[LB-1];
    // bank wq_done1 model: DONE_LAT edges after the merged write reaches the bank
    reg [7:0] wv_d[1:DONE_LAT]; reg [7:0] done_exp;
    wire [7:0] wvB; for(genvar b=0;b<8;b=b+1) begin: wv assign wvB[b]=wqB[b*281+280]; end
    always @(posedge clk) begin
        wv_d[1]<=wvB; for(integer i=2;i<=DONE_LAT;i=i+1) wv_d[i]<=wv_d[i-1];
        done_exp<=wv_d[DONE_LAT];
    end
    always @* done_m=wv_d[DONE_LAT];
    // ---- monolith delay lines (posedge), compared at negedge
    reg [135:0] rqA_d[1:RQ_OFF];
    reg [2247:0] wqA_d[1:WQ_OFF];
    reg [WQ_OFF:1] bdA_d, rdA_d;
    always @(posedge clk) begin
        rqA_d[1]<=rqA; wqA_d[1]<=wqA; bdA_d[1]<=bdA; rdA_d[1]<=rdA;
        for(integer i=2;i<=RQ_OFF;i=i+1) rqA_d[i]<=rqA_d[i-1];
        for(integer i=2;i<=WQ_OFF;i=i+1) begin wqA_d[i]<=wqA_d[i-1]; bdA_d[i]<=bdA_d[i-1]; rdA_d[i]<=rdA_d[i-1]; end
    end
    wire [135:0] rqB=vrqB;
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
    integer ndone=0;
    always @(negedge clk) if(rst_n && armed) begin
        if(d2B!==done_exp || d1B!==8'd0) $fatal(1,"LOCKSTEP_FAIL vmm done steering cycle%0d done2 %b exp %b done1 %b",cyc-t0,d2B,done_exp,d1B);
        if(|flB || sfB) $fatal(1,"LOCKSTEP_FAIL vmm/share fault flt %b share %b",flB,sfB);
        if(cfgN || actN || fN || sfN || |flN || |d1N || |d2N || bdN || rdN) $fatal(1,"LOCKSTEP_FAIL neighbour Q%0d reacted cycle%0d",QN,cyc-t0);
        for(integer b=0;b<8;b=b+1) if(vrqN[b*17+16] || wqN[b*281+280]) $fatal(1,"LOCKSTEP_FAIL neighbour Q%0d bank%0d access",QN,b);
        for(integer b=0;b<8;b=b+1) if(d2B[b]) ndone++;
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
        if(fB) $fatal(1,"LOCKSTEP_FAIL group unexpected static fault cycle%0d",cyc-t0);
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
        if(bdB!==bdA_d[WQ_OFF-2] || rdB!==rdA_d[WQ_OFF-2]) $fatal(1,"LOCKSTEP_FAIL done cycle%0d split %b%b monolith+%0d %b%b",cyc-t0,bdB,rdB,WQ_OFF-2,bdA_d[WQ_OFF-2],rdA_d[WQ_OFF-2]);
        if(bdA) nbA++; if(bdB) nbB++; if(rdA) nrA++; if(rdB) nrB++;
        chk_writes(wqA,expA,nwA,lastA,"monolith");
        chk_writes(wqB,expB,nwB,lastB,"group");
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
        write32(12'hf20,32'(TGT));
        for(integer pc=0;pc<nrec;pc++) for(integer piece=0;piece<8;piece++) write32(12'hf24,program_image[pc][piece*32+:32]);
        write32(12'hf28,32'(nrec<<12));write32(12'hf2c,1);
        for(integer w=0;w<64 && !cfgA;w++) @(negedge clk);
        if(!cfgA || !cfgB) $fatal(1,"LOCKSTEP_FAIL target %0h not configured A%b B%b",TGT,cfgA,cfgB);
        write32(12'hc10,1);
        repeat(260) @(negedge clk);
        if(nbA!=total_beats || nbB!=total_beats || nrA!=nrec || nrB!=nrec || nwA!=4*total_beats || nwB!=4*total_beats ||
           expA!='0 || expB!='0 || nrqA!=4*total_beats || nrqB!=4*total_beats)
            $fatal(1,"LOCKSTEP_FAIL accounting beats A%0d B%0d /%0d records A%0d B%0d /%0d writes A%0d B%0d reads A%0d B%0d",
                nbA,nbB,total_beats,nrA,nrB,nrec,nwA,nwB,nrqA,nrqB);
        if(lastB-lastA!=WQ_OFF) $fatal(1,"LOCKSTEP_FAIL last write offset %0d",lastB-lastA);
        if(ndone!=nwB) $fatal(1,"LOCKSTEP_FAIL vmm wq_done2 count %0d writes %0d",ndone,nwB);
        $display("PASS HBM_QUANT_VMM_Q_LOCKSTEP Q=%0d target=%0h neighbour=Q%0d silent wq_done2=%0d records=%0d beats=%0d reads=%0d writes=%0d cycles_compared=%0d monolith_last_write=%0d split_last_write=%0d rq_offset=%0d wq_done_offset=%0d immutable_price=%0d VM_latency_at_split_pins=%0d bank_face_latency=%0d",
            Q,TGT,QN,ndone,nrec,total_beats,nrqB,nwB,ncmp,lastA,lastB,RQ_OFF,WQ_OFF,total_cost,L,LB);
        $finish;
    end
    initial begin repeat(30000) @(negedge clk);$fatal(1,"LOCKSTEP_FAIL watchdog");end
endmodule
