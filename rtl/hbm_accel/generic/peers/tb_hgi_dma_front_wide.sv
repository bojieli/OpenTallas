`timescale 1ns/1ps
module tb_hgi_dma_front_wide;
    parameter integer MUT = 0;
    parameter integer LDEPTH=256, DATA_HOPS=96, CREDIT_HOPS=96, RESPONSE_LATENCY=208, SERVICE_SLOTS=64;
    localparam integer NS = 4, NL = 32, NIN = 128;
    localparam integer SBIT = 21; localparam longint SB = 2097152;   // 1 MiB stacks in the bench
    reg clk = 0; always #1 clk = ~clk; reg rst_n = 0;
    reg mv_v = 0; reg [226:0] mv = 0; wire mv_rdy, mv_done, mv_fault;
    wire [NS*53-1:0] dq; reg [NS-1:0] dq_rdy = 0; reg [NIN*272-1:0] dd_src = 0; wire [NIN*272-1:0] dd; wire [NIN-1:0] dd_cr; wire [NIN-1:0] cr_arrived;
    reg [NIN*272-1:0] data_pipe [0:DATA_HOPS];
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
    wire [512*283-1:0] wl; wire [511:0] wl_done; wire [511:0] wl_ready;
    ot_hgi_dma_front_wide #(.ENABLE(1),.NS(NS), .NL(NL), .SBIT(SBIT), .STACK_BYTES(36'(SB)), .LDEPTH(LDEPTH)) dut (.clk(clk), .rst_n(rst_n), .mv_v(mv_v),
        .mv_rdy(mv_rdy), .mv(mv), .mv_done(mv_done), .mv_fault(mv_fault), .dq(dq), .dq_rdy(dq_rdy), .dd(dd), .dd_cr(dd_cr),
        .wl(wl), .wl_done(wl_done),.wl_ready(wl_ready));
    // ---- memories
    function automatic [7:0] hb(input longint a); hb = 8'((a * 2654435761 + (a >> 7) * 40503) >> 3); endfunction
    localparam integer VM_WORDS = 2097152;
    reg [31:0] vm [0:VM_WORDS-1];
    reg vm_written [0:VM_WORDS-1];
    // Qualified real bank/body mechanism is measured separately on sixteen macros.
    // This full-control shape retains exact phase-II2 admission and commit ACK delay.
    reg [1023:0]cool=0;reg[511:0]ack_pipe[0:5];
    integer firstVM,lastVM,VMwrites,firstSource,lastSource,sourceBytes,firstReq;
    initial for(integer e=0;e<6;e=e+1)ack_pipe[e]=0;
    assign wl_done=ack_pipe[5];
    generate for(genvar p=0;p<512;p=p+1)begin
      wire phase=wl[p*283+273];
      assign wl_ready[p]=!cool[p*2+phase];
    end endgenerate
    always @(posedge clk)begin
       cool<=0;ack_pipe[0]<=0;
       for(integer e=1;e<6;e=e+1)ack_pipe[e]<=ack_pipe[e-1];
       for(integer p=0;p<512;p=p+1)if(wl[p*283+282]&&wl_ready[p])begin
         integer sec,address;sec=wl[p*283+264+:18];
         if(sec%512!=p)$fatal(1,"wrong logical bank");
         cool[p*2+((sec>>9)&1)]<=1;ack_pipe[0][p]<=1;
         if(firstVM<0)firstVM=cyc;lastVM=cyc;VMwrites=VMwrites+1;
         for(integer w=0;w<8;w=w+1)if(wl[p*283+w])begin
           address=sec*8+w;
           if(address>=VM_WORDS||vm_written[address])$fatal(1,"VM duplicate or bounds %0d",address);
           vm_written[address]=1;vm[address]=wl[p*283+8+w*32+:32];
         end
       end
    end
    // ---- svc model: per stack a request queue; per lane a beat queue in idx order; credit 4 a lane
    integer rq_n [0:NS-1]; reg [51:0] rq [0:NS-1][0:63]; integer rq_h [0:NS-1];
    integer cr [0:NIN-1]; integer nxt [0:NS-1];               // next idx of the head request to schedule
    reg [271:0] lb [0:NIN-1][0:1023]; integer lh [0:NIN-1]; integer lt [0:NIN-1];
    integer lb_ready [0:NIN-1][0:1023];
    integer service_used [0:NS-1],service_left [0:NS-1][0:63];
    initial for (integer i = 0; i < NIN; i = i + 1) begin cr[i] = LDEPTH; lh[i] = 0; lt[i] = 0; end
    initial for (integer s = 0; s < NS; s = s + 1) begin rq_n[s] = 0; rq_h[s] = 0; nxt[s] = 0; service_used[s]=0;
        for(integer tag=0;tag<64;tag=tag+1)service_left[s][tag]=0; end
    always @(posedge clk) if (rst_n) begin
        dd_src <= 0;
        for (integer s = 0; s < NS; s = s + 1) begin

            if (dq[s*53 + 52] && dq_rdy[s]) begin
                if(firstReq<0)firstReq=cyc;
                if(service_used[s]>=SERVICE_SLOTS)$fatal(1,"service descriptor window exceeded");
                if(service_left[s][dq[s*53+46+:6]]!=0)$fatal(1,"service tag reused before completion");
                service_used[s]=service_used[s]+1;service_left[s][dq[s*53+46+:6]]=dq[s*53+37+:9];
                rq[s][(rq_h[s] + rq_n[s]) % 64] = dq[s*53 +: 52]; rq_n[s] = rq_n[s] + 1;
            end
            // schedule up to 8 sectors of the head request into the lane queues (the svc reading its PCs)
            for (integer k = 0; k < 32 && rq_n[s] > 0; k = k + 1) begin : sch
                reg [51:0] r; reg [255:0] sd; longint a; integer l;
                r = rq[s][rq_h[s] % 64];
                a = longint'(r[36:0]) + 32 * nxt[s];
                for (integer b = 0; b < 32; b = b + 1) sd[8*b +: 8] = hb(a + b);
                l = s * NL + (nxt[s] % 32);
                lb[l][lt[l] % 1024] = {1'b1, 1'b0, r[51:46], 8'(nxt[s]), sd}; lb_ready[l][lt[l] % 1024]=cyc+RESPONSE_LATENCY; lt[l] = lt[l] + 1;
                nxt[s] = nxt[s] + 1;
                if (nxt[s] == int'(r[45:37])) begin nxt[s] = 0; rq_h[s] = rq_h[s] + 1; rq_n[s] = rq_n[s] - 1; end
            end
        end
        for (integer i = 0; i < NIN; i = i + 1) begin
            if (cr_arrived[i]) cr[i] = cr[i] + 1;
            if (lt[i] > lh[i] && cyc>=lb_ready[i][lh[i]%1024] && cr[i] > 0 && (full ? (cyc%30<23) : (($urandom % 5) != 0))) begin dd_src[i*272 +: 272] <= lb[i][lh[i] % 1024]; begin : release_service
                    integer tag, stack; tag=lb[i][lh[i]%1024][269:264];stack=i/NL;
                    service_left[stack][tag]=service_left[stack][tag]-1;
                    if(service_left[stack][tag]==0)service_used[stack]=service_used[stack]-1;
                end
                if(firstSource<0)firstSource=cyc;lastSource=cyc;sourceBytes=sourceBytes+32;
                lh[i] = lh[i] + 1; cr[i] = cr[i] - 1; end
        end
        for(integer s=0;s<NS;s=s+1)dq_rdy[s]<=(service_used[s]<SERVICE_SLOTS)&&(full||($urandom%4)!=0);
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
            firstVM=-1;lastVM=-1;VMwrites=0;firstSource=-1;lastSource=-1;sourceBytes=0;firstReq=-1;
            es = (f == 0 || f == 5) ? 4 : (f == 1) ? 2 : 1; e0 = errs;
            if(dbase<0||dbase+(m-1)*dstr+n>VM_WORDS)$fatal(1,"bench move exceeds actual18bit VM sector ABI");
            for (i = 0; i < VM_WORDS; i = i + 1)begin vm[i] = 32'hA5A5_0000 + i;vm_written[i]=0;end
            mv = 0; mv[1:0] = 0; mv[4:2] = f; mv[44:5] = 40'(sbase); mv[76:45] = 32'(sstr); mv[92:77] = 1;
            mv[94:93] = 1; mv[97:95] = 0; mv[137:98] = 40'(dbase); mv[169:138] = 32'(dstr); mv[185:170] = 1;
            mv[205:186] = 20'(m); mv[226:206] = 21'(n);
            @(negedge clk); mv_v = 1; while (!mv_rdy) @(negedge clk); @(negedge clk); mv_v = 0; t0 = cyc;
            while (!mv_done && !mv_fault && cyc - t0 < 200000) @(negedge clk);
            if (!mv_done) begin $display("FAIL load f %0d m %0d n %0d: done %0d fault %0d", f, m, n, mv_done, mv_fault); errs = errs + 1; end
            else begin
                $display("WIDE_TIMING format=%0d request=%0d source=%0d VM=%0d lastsource=%0d lastVM=%0d rawbytes=%0d decodedbytes=%0d payload_raw_Bpc=%0.3f cold_raw_Bpc=%0.3f",f,firstReq,firstSource,firstVM,lastSource,lastVM,sourceBytes,VMwrites*32,sourceBytes*1.0/(lastVM-firstVM+1),sourceBytes*1.0/(cyc-firstReq+1));
                if(full && sourceBytes*1.0/(lastVM-firstVM+1)<3000.0)$fatal(1,"wide raw payload BW below3000");
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
                $display("LOAD f %0d m %0d n %0d: %0d cycles, %0.1f destination B / cycle", f, m, n, cyc - t0, (m * n * 4.0) / (cyc - t0));
            end
        end
    endtask
    initial begin
      repeat(4)@(negedge clk);rst_n=1;
      load(0,0,SB,0,524288,4,524288);
      load(1,0,SB,0,524288,4,524288);
      load(2,0,SB,0,524288,4,524288);
      if(errs!=0)$fatal(1,"wide exact errors%0d",errs);
      $display("PASS widefront fullshape128rawlanes512logicalbanks allformats exact +real II2/ACK timing model");$finish;
    end
endmodule
