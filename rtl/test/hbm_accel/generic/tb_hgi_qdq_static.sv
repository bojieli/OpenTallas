`timescale 1ns/1ps
// Actual QDQ decoder + eight actual VM bank pipelines and 24 mapped SRAM macros.
// Golden vectors and external preload are declared component-boundary stimuli.
// This does not claim native whole-chip programme execution.
module tb_hgi_qdq_static #(parameter integer MUT=0,IO_REGS=0,LG=0,TSPLIT=0);
    reg clk=0; always #1 clk=~clk;
    reg rst_n=0, cv=0, last=0;
    reg [5:0] op=0; reg [7:0] block_n=0;
    reg [15:0] src=0,dst=0;
    reg cfg_we=0,start_v=0; reg [9:0] cfg_addr=0; reg [255:0] cfg_data=0;
    reg [10:0] start_limit=0; wire program_active,program_done;
    wire [135:0] rq; wire [2055:0] rr; wire [2055:0] rr_bank;
    reg [2055:0] rr_late; always @(posedge clk) rr_late<=rr_bank;
    assign rr=(MUT==3)?rr_late:rr_bank; wire [2247:0] wq;
    wire done,rdone,fault; wire [7:0] bankdone;
    reg preload=1;
    reg [2247:0] pwq=0;
    reg [135:0] prq=0;
    wire [143:0] status;
    ot_hgi_qdq_program_static #(.IO_REGS(IO_REGS),.LG(LG),.TSPLIT(TSPLIT),.LGMUT(MUT==4?1:0),.MUT(MUT==1?1:MUT==2?2:0)) dut(
        .clk_program(clk),.clk_lg({4{clk}}),.clk_transport(clk),.clk_dxl(clk),.clk_dbq(clk),.clk_daq(clk),.rst_n(rst_n),
        .cfg_we(cfg_we),.cfg_addr(cfg_addr),.cfg_data(cfg_data),
        .start_v(start_v),.start_base(10'd0),.start_limit(start_limit),.start_loops(16'd1),
        .program_active(program_active),.program_done(program_done),
        .rq(rq),.rr(rr),.wq(wq),.beat_done(done),.record_done(rdone),.fault(fault));
    // Fault-cause probes into the transport control (monolith or split control leaf).
    wire tr_bad,tr_dv24; wire [7:0] tr_expected;
    generate if(TSPLIT!=0) begin: probe_split
        assign tr_bad=dut.engine.split_transport.transport.ctl.bad;
        assign tr_dv24=dut.engine.split_transport.transport.ctl.dv[24];
        assign tr_expected=dut.engine.split_transport.transport.ctl.expected;
    end else begin: probe_mono
        assign tr_bad=dut.engine.monolith_transport.transport.bad;
        assign tr_dv24=dut.engine.monolith_transport.transport.dv[24];
        assign tr_expected=dut.engine.monolith_transport.transport.expected;
    end endgenerate
    for(genvar g=0;g<8;g=g+1) begin: banks
        wire [16:0] arq=preload?prq[g*17+:17]:rq[g*17+:17];
        wire [280:0] awq=preload?pwq[g*281+:281]:wq[g*281+:281];
        wire [17:0] st;
        wire [7*257-1:0] fullrr;wire [2:0] fulldone;
        assign rr_bank[g*257+:257]=fullrr[4*257+:257];
        assign bankdone[g]=fulldone[2];
        ot_vms_bank_static #(.RG(7),.WG(3)) bank(.clk(clk),.rst_n(rst_n),.bid(3'(g)),.sid(2'd0),
            .rslot_v(arq[16]),.rslot(3'd4),.wslot_v(awq[280]),.wslot(3'd2),.rq({34'd0,arq,68'd0}),.rr(fullrr),
            .wq({awq,562'd0}),.wq_done(fulldone),.dq(281'd0),.dq_done(),.kq(281'd0),.kq_done(),
            .xq(276'd0),.xq_done(),.xq2(276'd0),.xq2_done(),.eg(),.pq(285'd0),.pr(),.status(st));
        assign status[g*18+:18]=st;
    end
    reg [255:0] gi[0:127],go[0:127];
    reg [255:0] program_image[0:1023];
    integer fd,nrec,k,s,j,n[0:15],ab[0:15],ob[0:15],ops[0:15],blks[0:15],costs[0:15];
    integer cyc=0,t0,total_cost=0,nbeat=0,nreturn=0,nrecord=0,nwrite=0,nissue=0,total_beats=0,ncheck=0,bad=0,exp_commit,last_write=0,last_commit=0,ncommit=0;
    reg check_fault=0; string dir,fn,programfile;
    // Independent scoreboard: compare every actual bank write to immutable golden sectors,
    // then read the physically mapped macro output back after commit.
    reg [255:0] expect_word[0:32767]; reg [32767:0] expect_valid='0;
    integer bankidx,secidx;
    always @(posedge clk) begin
        cyc<=cyc+1;
        if(!preload && dut.command_v && dut.command[0]) begin
            if(dut.ordinal!=nissue || cyc-t0!=nissue+5) $fatal(1,"programme fixed issue expected%0d actualordinal%0d cycle%0d",nissue,dut.ordinal,cyc-t0);
            nissue++;
        end
        if(!preload && (tr_bad || dut.engine.decode_fault || (dut.engine.vo&&dut.engine.qfault) || dut.engine.vo!=tr_dv24))
            $display("FAULT_CAUSE cycle=%0d bad=%b decode=%b qfault=%b vo=%b expected=%b rr_mask=%b",cyc-t0,tr_bad,dut.engine.decode_fault,dut.engine.qfault,dut.engine.vo,tr_dv24,tr_expected);
    end
    always @(negedge clk) if(!preload && rst_n) begin
        if(fault && !check_fault) $fatal(1,"unexpected static fault at cycle %0d vo=%b expected=%b",cyc-t0,dut.engine.vo,tr_dv24);
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
        $readmemh(programfile,program_image,0,total_beats-1);
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
        // The compiler configures real programme macro words before global launch.
        for(k=0;k<nrec;k=k+1) for(s=0;s<n[k]/32;s=s+1) begin
            cfg_we=1;cfg_addr=10'(nbeat);cfg_data=program_image[nbeat];
            if(cfg_data[47:0]!=={(s==n[k]/32-1),16'(ob[k]/8+4*s),16'(ab[k]/8+4*s),8'(blks[k]),6'(ops[k]),1'b1})
                $fatal(1,"compiler programme command differs from production record%0d beat%0d",k,s);
            nbeat++;@(negedge clk);
        end
        cfg_we=0;start_limit=11'(nbeat);repeat(8) @(negedge clk);
        preload=0;t0=cyc;start_v=1;
        @(negedge clk);start_v=0;
        repeat(nbeat) @(negedge clk);
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
        $display("PASS HGI_QDQ_STATIC_PROGRAM RG4_WG2 records=%0d beats=%0d sectors=%0d commit_cycles=%0d immutable_price=%0d historical_wq3_price=184 programme_macros=1 data_macros=24",nrec,nbeat,ncheck,last_commit,total_cost);
        $finish;
    end
    initial begin repeat(20000) @(negedge clk);$fatal(1,"watchdog: fixed component timeline exceeded");end
endmodule
