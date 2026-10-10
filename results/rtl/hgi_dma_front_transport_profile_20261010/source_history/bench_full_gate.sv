`timescale 1ns/1ps
// hgi-takeover 2026-10-10: ot_hgi_dma_front against an svc-stream MODEL per the hgi-takeover.log interface spec (per
// stack: requests {tag, nsec, addr}; 8 lanes, lane l = idx % 8 in order, credit 4 a lane, random lane latencies and
// gaps) and a VM wide-port model.  Every LOAD's VM destination words are compared with an independent decode of the
// HBM model (BF16 << 16, E4M3 exact / NaN -> 0x7FC00000, INT8 exact, FP32 / U32 the word); no other VM word may change.
// Reports cycles and destination bytes a cycle.  +MUT via parameter MUT (1 BF16 lane mirror, 2 early tag free): FAIL.
module tb_hgi_dma_front;
    parameter integer MUT = 0;
    parameter integer LDEPTH = 4, DATA_HOPS = 0, CREDIT_HOPS = 0, RESPONSE_LATENCY=0, STACK_LOCAL_TAGS=0, SERVICE_SLOTS=64, BW_SCOPE=0;
    localparam integer NS = 4, NL = 8, NIN = 32;
    localparam integer SBIT = 20; localparam longint SB = 1048576;   // 1 MiB stacks in the bench
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    reg mv_v = 0; reg [226:0] mv = 0; wire mv_rdy, mv_done, mv_fault;
    wire [NS*51-1:0] dq; reg [NS-1:0] dq_rdy = 0; reg [NIN*270-1:0] dd_src = 0; wire [NIN*270-1:0] dd; wire [NIN-1:0] dd_cr; wire [NIN-1:0] cr_arrived;
    reg [NIN*270-1:0] data_pipe [0:DATA_HOPS];
    reg [NIN-1:0] credit_pipe [0:CREDIT_HOPS];
    initial begin
        for (integer d=0; d<=DATA_HOPS; d=d+1) data_pipe[d]=0;
        for (integer d=0; d<=CREDIT_HOPS; d=d+1) credit_pipe[d]=0;
    end
    always @(posedge clk) begin
        data_pipe[0] <= dd_src; credit_pipe[0] <= dd_cr;
        for (integer d=1; d<=DATA_HOPS; d=d+1) data_pipe[d]<=data_pipe[d-1];
        for (integer d=1; d<=CREDIT_HOPS; d=d+1) credit_pipe[d]<=credit_pipe[d-1];
    end
    assign dd = DATA_HOPS==0 ? dd_src : data_pipe[(DATA_HOPS>0)?DATA_HOPS-1:0];
    assign cr_arrived = CREDIT_HOPS==0 ? dd_cr : credit_pipe[(CREDIT_HOPS>0)?CREDIT_HOPS-1:0];
    wire [32*280-1:0] wl; reg [31:0] wl_done = 0;
    ot_hgi_dma_front #(.NS(NS), .NL(NL), .SBIT(SBIT), .STACK_BYTES(36'(SB)), .LDEPTH(LDEPTH), .STACK_LOCAL_TAGS(STACK_LOCAL_TAGS), .MUT(MUT)) dut (.clk(clk), .rst_n(rst_n), .mv_v(mv_v),
        .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
        .wl(wl), .wl_done(wl_done));
    // ---- memories
    function automatic [7:0] hb(input longint a); hb = 8'((a * 2654435761 + (a >> 7) * 40503) >> 3); endfunction
    localparam integer VM_WORDS = 262144;
    reg [31:0] vm [0:VM_WORDS-1];
    reg vm_written [0:VM_WORDS-1];
    reg [31:0] wl_d1 = 0;
    always @(posedge clk) begin
        wl_d1 <= 0; wl_done <= wl_d1;
        for (integer p = 0; p < 32; p = p + 1) if (wl[p*280 + 279]) begin
            if (wl[p*280 + 264 +: 5] != 5'(p)) $fatal(1, "wide lane %0d carries bank %0d", p, wl[p*280 + 264 +: 5]);
            for (integer w = 0; w < 8; w = w + 1) if (wl[p*280 + w])begin
                integer address;address={wl[p*280 + 264 +: 15], 3'(w)};
                if(vm_written[address])begin if(errs<8)$display("FAIL duplicate VM word %0d",address);errs=errs+1;end
                vm_written[address]=1;vm[address] = wl[p*280 + 8 + 32*w +: 32];
            end
            wl_d1[p] <= 1'b1;
        end
    end
    // ---- svc model: per stack a request queue; per lane a beat queue in idx order; credit 4 a lane
    integer rq_n [0:NS-1]; reg [49:0] rq [0:NS-1][0:63]; integer rq_h [0:NS-1];
    integer cr [0:NIN-1]; integer nxt [0:NS-1];               // next idx of the head request to schedule
    reg [269:0] lb [0:NIN-1][0:1023]; integer lh [0:NIN-1]; integer lt [0:NIN-1];
    integer lb_ready [0:NIN-1][0:1023];
    integer service_used [0:NS-1],service_left [0:NS-1][0:15];
    initial for (integer i = 0; i < NIN; i = i + 1) begin cr[i] = LDEPTH; lh[i] = 0; lt[i] = 0; end
    initial for (integer s = 0; s < NS; s = s + 1) begin rq_n[s] = 0; rq_h[s] = 0; nxt[s] = 0; service_used[s]=0;
        for(integer tag=0;tag<16;tag=tag+1)service_left[s][tag]=0; end
    always @(posedge clk) if (rst_n) begin
        dd_src <= 0;
        for (integer s = 0; s < NS; s = s + 1) begin

            if (dq[s*51 + 50] && dq_rdy[s]) begin
                if(service_used[s]>=SERVICE_SLOTS)$fatal(1,"service descriptor window exceeded");
                if(service_left[s][dq[s*51+46+:4]]!=0)$fatal(1,"service tag reused before completion");
                service_used[s]=service_used[s]+1;service_left[s][dq[s*51+46+:4]]=dq[s*51+37+:9];
                rq[s][(rq_h[s] + rq_n[s]) % 64] = dq[s*51 +: 50]; rq_n[s] = rq_n[s] + 1;
            end
            // schedule up to 8 sectors of the head request into the lane queues (the svc reading its PCs)
            for (integer k = 0; k < 8 && rq_n[s] > 0; k = k + 1) begin : sch
                reg [49:0] r; reg [255:0] sd; longint a; integer l;
                r = rq[s][rq_h[s] % 64];
                a = longint'(r[36:0]) + 32 * nxt[s];
                for (integer b = 0; b < 32; b = b + 1) sd[8*b +: 8] = hb(a + b);
                l = s * NL + (nxt[s] % 8);
                lb[l][lt[l] % 1024] = {1'b1, 1'b0, r[49:46], 8'(nxt[s]), sd}; lb_ready[l][lt[l] % 1024]=cyc+RESPONSE_LATENCY; lt[l] = lt[l] + 1;
                nxt[s] = nxt[s] + 1;
                if (nxt[s] == int'(r[45:37])) begin nxt[s] = 0; rq_h[s] = rq_h[s] + 1; rq_n[s] = rq_n[s] - 1; end
            end
        end
        for (integer i = 0; i < NIN; i = i + 1) begin
            if (cr_arrived[i]) cr[i] = cr[i] + 1;
            if (lt[i] > lh[i] && cyc>=lb_ready[i][lh[i]%1024] && cr[i] > 0 && (full || ($urandom % 5) != 0)) begin dd_src[i*270 +: 270] <= lb[i][lh[i] % 1024]; begin : release_service
                    integer tag, stack; tag=lb[i][lh[i]%1024][267:264];stack=i/NL;
                    service_left[stack][tag]=service_left[stack][tag]-1;
                    if(service_left[stack][tag]==0)service_used[stack]=service_used[stack]-1;
                end
                lh[i] = lh[i] + 1; cr[i] = cr[i] - 1; end
        end
        for(integer s=0;s<NS;s=s+1)dq_rdy[s]<=(service_used[s]<SERVICE_SLOTS)&&(full||($urandom%4)!=0);
    end
    integer profile_on=0;integer profile_move=0;
    integer pa,p_issue,p_tagstall,p_ingress,p_grants,p_ack,p_creditstall,p_lqpeak,p_lqmax,p_ovpeak;
    integer p_firstrequest,p_firstsource,p_firstdata,p_firstVM,p_lastsource,p_lastdata,p_lastVM;
    initial profile_on=(BW_SCOPE!=0)||$test$plusargs("DMA_PROFILE");
    always @(posedge clk) if(profile_on&&rst_n)begin:prof
        integer tagcount,inc,gc,ack,oq,lqn,issuedq,blocked,maxq;
        if(dut.cv_q)begin
            profile_move=profile_move+1;pa=0;p_issue=0;p_tagstall=0;p_ingress=0;p_grants=0;p_ack=0;p_creditstall=0;p_lqpeak=0;p_lqmax=0;p_ovpeak=0;
            p_firstrequest=-1;p_firstsource=-1;p_firstdata=-1;p_firstVM=-1;p_lastsource=-1;p_lastdata=-1;p_lastVM=-1;
        end
        if(dut.busy)begin
            tagcount=0;inc=0;gc=0;ack=0;oq=0;lqn=0;issuedq=0;blocked=0;maxq=0;
            for(integer t=0;t<dut.NT;t=t+1)tagcount=tagcount+dut.tag_busy[t];
            for(integer i=0;i<32;i=i+1)begin
                inc=inc+dd[i*270+269];gc=gc+dut.bsel_v[i];ack=ack+wl_done[i];
                lqn=lqn+dut.lq_n[i];if(dut.lq_n[i]>maxq)maxq=dut.lq_n[i];
                for(integer j=0;j<4;j=j+1)oq=oq+dut.ov[i][j];
                if(lt[i]>lh[i]&&cyc>=lb_ready[i][lh[i]%1024]&&cr[i]==0)blocked=blocked+1;
            end
            for(integer s=0;s<NS;s=s+1)issuedq=issuedq+(dq[s*51+50]&&dq_rdy[s]);
            if(issuedq>0&&p_firstrequest<0)p_firstrequest=cyc;
            if(inc>0)begin if(p_firstdata<0)p_firstdata=cyc;p_lastdata=cyc;end
            for(integer i=0;i<32;i=i+1)begin
                if(dd_src[i*270+269])begin if(p_firstsource<0)p_firstsource=cyc;p_lastsource=cyc;end
                if(wl[i*280+279])begin if(p_firstVM<0)p_firstVM=cyc;p_lastVM=cyc;end
            end
            pa=pa+1;p_issue=p_issue+issuedq;p_tagstall=p_tagstall+(!dut.r_done&&dut.ft==16);
            p_ingress=p_ingress+inc;p_grants=p_grants+gc;p_ack=p_ack+ack;p_creditstall=p_creditstall+blocked;
            if(lqn>p_lqpeak)p_lqpeak=lqn;if(maxq>p_lqmax)p_lqmax=maxq;if(oq>p_ovpeak)p_ovpeak=oq;
            if($test$plusargs("DMA_PROFILE_CSV"))$display("DMA_PROFILE_CYCLE move=%0d cycle=%0d tags=%0d issue=%0d ingress=%0d grants=%0d ack=%0d lq=%0d maxlane=%0d ov=%0d creditblocked=%0d",profile_move,cyc,tagcount,issuedq,inc,gc,ack,lqn,maxq,oq,blocked);
        end
        if(mv_done)begin
            $display("DMA_TIMING move=%0d firstrequest=%0d firstsource=%0d firstdata=%0d firstVM=%0d lastsource=%0d lastdata=%0d lastVM=%0d source_span=%0d data_span=%0d VM_span=%0d VM_bytes=%0d VM_steady_Bpc=%0.3f",profile_move,p_firstrequest,p_firstsource,p_firstdata,p_firstVM,p_lastsource,p_lastdata,p_lastVM,p_lastsource-p_firstsource+1,p_lastdata-p_firstdata+1,p_lastVM-p_firstVM+1,p_grants*32,p_grants*32.0/(p_lastVM-p_firstVM+1));
            $display("DMA_PROFILE move=%0d cycles=%0d requests=%0d tagstall=%0d ingress=%0d grants=%0d ack=%0d creditstall_lane_cycles=%0d peak_lq=%0d max_lane_lq=%0d peak_ov=%0d",profile_move,pa,p_issue,p_tagstall,p_ingress,p_grants,p_ack,p_creditstall,p_lqpeak,p_lqmax,p_ovpeak);
        end
    end
    // ---- reference decode
    // binary32 bits of an exactly representable normal / zero double (Verilator's $shortrealtobits is not reliable)
    function automatic [31:0] f32(input real v);
        reg [63:0] d;
        begin
            d = $realtobits(v);
            f32 = (d[62:0] == 63'd0) ? {d[63], 31'd0} : {d[63], 8'(d[62:52] - 11'd1023 + 11'd127), d[51:29]};
        end
    endfunction
    function automatic [31:0] e4(input [7:0] c);
        real v; integer e, m; reg [31:0] r;
        begin
            e = c[6:3]; m = c[2:0];
            if (e == 15 && m == 7) e4 = 32'h7FC00000;
            else begin
                v = (e == 0) ? (m / 8.0) * (2.0 ** -6) : (1.0 + m / 8.0) * (2.0 ** (e - 7));
                r = f32(v); r[31] = c[7];
                if (v == 0.0) r = {c[7], 31'd0};
                e4 = r;
            end
        end
    endfunction
    function automatic [31:0] i8(input [7:0] c); i8 = f32(real'($signed(c))); if (c == 0) i8 = 0; endfunction
    integer full = 0; initial full = $test$plusargs("FULL");     // +FULL: the svc model at its full rate (no gaps)
    integer errs = 0, cyc = 0, tbytes = 0, tcyc = 0;
    always @(posedge clk) cyc <= cyc + 1;
    task automatic load(input [2:0] f, input longint sbase, input longint sstr, input integer dbase, input integer dstr,
                        input integer m, input integer n);
        integer es, t0, o, i, e0; longint a; reg [31:0] want;
        begin
            es = (f == 0 || f == 5) ? 4 : (f == 1) ? 2 : 1; e0 = errs;
            if(dbase<0||dbase+(m-1)*dstr+n>VM_WORDS)$fatal(1,"bench move exceeds actual15bit VM sector ABI");
            for (i = 0; i < VM_WORDS; i = i + 1)begin vm[i] = 32'hA5A5_0000 + i;vm_written[i]=0;end
            mv = 0; mv[1:0] = 0; mv[4:2] = f; mv[44:5] = 40'(sbase); mv[76:45] = 32'(sstr); mv[92:77] = 1;
            mv[94:93] = 1; mv[97:95] = 0; mv[137:98] = 40'(dbase); mv[169:138] = 32'(dstr); mv[185:170] = 1;
            mv[205:186] = 20'(m); mv[226:206] = 21'(n);
            @(negedge clk); mv_v = 1; while (!mv_rdy) @(negedge clk); @(negedge clk); mv_v = 0; t0 = cyc;
            while (!mv_done && !mv_fault && cyc - t0 < 200000) @(negedge clk);
            if (!mv_done) begin $display("FAIL load f %0d m %0d n %0d: done %0d fault %0d", f, m, n, mv_done, mv_fault); errs = errs + 1; end
            else begin
                tcyc = tcyc + (cyc - t0); tbytes = tbytes + m * n * 4;
                for (o = 0; o < m; o = o + 1) for (i = 0; i < n; i = i + 1) begin
                    a = sbase + o * sstr + i * es;
                    case (f)
                        1: want = {hb(a + 1), hb(a), 16'd0};
                        2: want = e4(hb(a));
                        4: want = i8(hb(a));
                        default: want = {hb(a + 3), hb(a + 2), hb(a + 1), hb(a)};
                    endcase
                    if (!vm_written[dbase + o*dstr+i] || vm[dbase + o * dstr + i] !== want) begin
                        if (errs < 8) $display("FAIL f %0d row %0d elem %0d: vm %h want %h", f, o, i, vm[dbase + o * dstr + i], want);
                        errs = errs + 1;
                    end
                end
                begin : untouched
                    integer w, o2, hit, bad; bad = 0;
                    for (w = 0; w < VM_WORDS; w = w + 1) begin
                        hit = 0;
                        for (o2 = 0; o2 < m; o2 = o2 + 1) if (w >= dbase + o2 * dstr && w < dbase + o2 * dstr + n) hit = 1;
                        if (!hit && vm[w] !== 32'hA5A5_0000 + w) bad = bad + 1;
                    end
                    if (bad != 0) begin $display("FAIL f %0d: %0d words outside the destination changed", f, bad); errs = errs + 1; end
                end
                if (errs != e0) $display("  load f %0d: %0d errors", f, errs - e0);
                if (LDEPTH >= 64 && f == 0 && m == 4 && n == 65536 && ((BW_SCOPE==0)?(m * n * 4.0) / (cyc-t0):(m*n*4.0)/(p_lastVM-p_firstVM+1)) < 0.9*1024)
                    begin $display("FAIL physical-credit bandwidth scope=%0d below90pct",BW_SCOPE); errs=errs+1; end
                $display("LOAD f %0d m %0d n %0d: %0d cycles, %0.1f destination B / cycle", f, m, n, cyc - t0, (m * n * 4.0) / (cyc - t0));
            end
        end
    endtask
    initial begin
        repeat (4) @(negedge clk); rst_n = 1; repeat (4) @(negedge clk);
        load(0, 64'h0000, 2048, 1024, 512, 4, 512);                      // FP32 rows, one stack
        load(1, 64'h1000, 8192, 8192, 4096, 3, 4096);                    // BF16
        load(2, 64'h4000, 4096, 40000, 4096, 2, 4096);                   // FP8
        load(4, 64'h8000, 1024, 100000, 1024, 5, 1024);                  // INT8
        load(0, 64'h0, 64'(SB), 150000, 2048, 4, 2048);                  // FP32 rows striped over the 4 stacks
        load(2, 64'h100, 64'(SB), 200000, 8192, 4, 8192);                // FP8 striped (4 x 32 KB raw -> 128 KB VM)
        load(0, 64'h2000, 32, 250000, 8, 64, 8);                         // 64 one-sector rows
        load(0, 64'h0, 64'(SB), 0, 16384, 4, 16384);                    // FP32 striped, 4 x 64 KB (steady state)
        load(1, 64'h0, 64'(SB), 100000, 32768, 4, 32768);               // BF16 striped, 4 x 64 KB raw -> 512 KB VM
        if (LDEPTH >= 64) load(0, 64'h0, 64'(SB), 0, 65536, 4, 65536); // full-capacity steady window prices transport fill
        repeat(2)@(negedge clk);
        if (errs == 0) $display("PASS HGI_DMA_FRONT %0d B in %0d cycles (%0.1f B / cycle overall)", tbytes, tcyc, (1.0 * tbytes) / tcyc);
        else $display("FATAL HGI_DMA_FRONT errors=%0d", errs);
        $finish;
    end
endmodule
