`timescale 1ns/1ps
// Persistent four-rank link, collective DMA and behavioral VM for the exact
// ShapeBuilder TP layer-0 COLL sequence. Images/descriptors come from Python.
module tb_v41_tp_layer0_collectives;
    localparam integer N=4, FW=512, PW=547, RB=2, WA=15;
    localparam integer OPS=12, MAXW=320, MEMW=32768;
    reg clk=0, rst_n=0, go=0, check_go=0;
    always #5 clk=~clk;
    integer cyc=0, op=-1;
    always @(posedge clk) cyc<=cyc+1;
    reg [31:0] desc [0:OPS-1];
    reg [FW-1:0] part [0:OPS*N*MAXW-1];
    reg [FW-1:0] expected [0:OPS*N*MAXW-1];
    reg images_ready=0;
    reg [N-1:0] vm_loaded=0;
    wire [N-1:0] check_done;
    integer first_tx [0:N-1],last_tx [0:N-1],first_vm [0:N-1],last_vm [0:N-1];
    integer txstall [0:N-1],outstall [0:N-1],peak_fifo [0:N-1],writes [0:N-1];
    reg [WA-1:0] src=0, dst=0, n=0;
    reg mode=0, rnd=0;
    reg [31:0] tag=0;
    wire [N-1:0] busy, dma_fault, efault, oerr;
    wire [N*3-1:0] ecode;
    wire [N-1:0] ev, er, el, em, ov, ory, ol;
    wire [N*FW-1:0] ed;
    wire [N*32-1:0] etag;
    wire [N*PW-1:0] txrec;
    wire [N*N-1:0] txv, txready, rxv, relaytxv, relayrxv;
    wire [N*N*PW-1:0] rxrec, relaytxrec, relayrxrec;
    wire [N*GW*FW-1:0] od;
    wire [N*RB-1:0] orank;
    wire [2*N*N-1:0] crin, crout;
    localparam integer GW=4;

    genvar s,t;
    generate for (s=0;s<N;s=s+1) begin : g_die
        reg [FW-1:0] vm [0:MEMW-1];
        wire re,we,ready4;
        wire [WA-1:0] raddr,waddr;
        wire [FW-1:0] wdata;
        reg [FW-1:0] rq=0;
        wire [3:0] we4;
        wire [4*WA-1:0] waddr4;
        wire [4*FW-1:0] wdata4;
        wire [31:0] words_out, words_in;
        reg [N*MAXW-1:0] seen=0;
        reg checked=0;
        assign check_done[s]=checked;
        initial begin
            for (integer k=0;k<MEMW;k=k+1) vm[k]='0;
            wait(images_ready);
            for (integer o=0;o<OPS;o=o+1)
                for (integer k=0;k<MAXW;k=k+1)
                    vm[o*512+k]=part[(o*N+s)*MAXW+k];
            vm_loaded[s]=1'b1;
        end
        always @(posedge clk) if (re) rq <= vm[raddr];
        always @(posedge clk) begin
            if(go) checked<=0;
            else if(check_go && !checked) begin
                for(integer j=0;j<(mode?4*integer'(n):integer'(n));j=j+1)
                    if(vm[integer'(dst)+j]!==expected[(op*N)*MAXW+j])
                        $fatal(1,"final VM readback mismatch op=%0d die=%0d j=%0d",op,s,j);
                checked<=1;
            end
        end
        assign ready4=1'b1;
        ot_chip_v41x_coll_dma #(.WA(WA),.FW(FW),.TAGW(32),.N(N),.GW(GW),.VM_ALWAYS_READY(1)) u_dma (
            .clk(clk),.rst_n(rst_n),.go(go),.mode(mode),.rnd(rnd),.tag(tag),
            .src(src),.n(n),.dst(dst),.busy(busy[s]),.fault(dma_fault[s]),
            .words_out(words_out),.words_in(words_in),
            .vm_re(re),.vm_raddr(raddr),.vm_rq(rq),.vm_we(we),.vm_waddr(waddr),.vm_wdata(wdata),
            .vm_ready4(ready4),.vm_we4(we4),.vm_waddr4(waddr4),.vm_wdata4(wdata4),
            .e_valid(ev[s]),.e_ready(er[s]),.e_data(ed[s*FW+:FW]),.e_last(el[s]),
            .e_mode(em[s]),.e_tag(etag[s*32+:32]),.o_valid(ov[s]),.o_ready(ory[s]),
            .o_data(od[s*GW*FW+:GW*FW]),.o_last(ol[s]),.o_rank(orank[s*RB+:RB]),
            .o_err(oerr[s]),.engine_fault(efault[s]));
        ot_rom_oneshot_die_px #(.N(N),.RANK(s),.LANES(16),.TAGW(32),.DEPTH(256),
                                .PKG_DIES(2),.RELAY(1),.ADD_LAT(3),.PAIRWISE(1),.GW(4),.OUT_BP(1)) u_coll (
            .clk(clk),.rst_n(rst_n),.in_valid(ev[s]),.in_ready(er[s]),.in_data(ed[s*FW+:FW]),
            .in_last(el[s]),.in_mode(em[s]),.in_tag(etag[s*32+:32]),
            .tx_valid(txv[s*N+:N]),.tx_rec(txrec[s*PW+:PW]),.tx_ready(txready[s*N+:N]),
            .cr_in(crin[2*s*N+:2*N]),.rx_valid(rxv[s*N+:N]),.rx_rec(rxrec[s*N*PW+:N*PW]),
            .cr_out(crout[2*s*N+:2*N]),.rl_tx_valid(relaytxv[s*N+:N]),
            .rl_tx_rec(relaytxrec[s*N*PW+:N*PW]),.rl_rx_valid(relayrxv[s*N+:N]),
            .rl_rx_rec(relayrxrec[s*N*PW+:N*PW]),.out_valid(ov[s]),.out_ready(ory[s]),
            .out_data(od[s*GW*FW+:GW*FW]),.out_last(ol[s]),.out_rank(orank[s*RB+:RB]),
            .out_err(oerr[s]),.fault(efault[s]),.fault_code(ecode[s*3+:3]));
        for(t=0;t<N;t=t+1) begin : g_link
            if(t==s) begin : g_self
                assign txready[s*N+t]=1'b1;
                assign crin[2*(s*N+t)+:2]=0;
                assign rxv[s*N+t]=0;
                assign rxrec[(s*N+t)*PW+:PW]=0;
            end else begin : g_remote
                localparam integer SAME=(s/2)==(t/2);
                ot_v41px_link #(.PW(PW),.CW(2),.LAT(SAME?11:142),.COST(64),
                                .BPC_NUM(SAME?3864:15758),.BPC_DEN(SAME?1:100)) u_link (
                    .clk(clk),.rst_n(rst_n),.in_valid(txv[s*N+t]),.in_rec(txrec[s*PW+:PW]),
                    .in_ready(txready[s*N+t]),.out_valid(rxv[t*N+s]),
                    .out_rec(rxrec[(t*N+s)*PW+:PW]),.cr_in(crout[2*(t*N+s)+:2]),
                    .cr_out(crin[2*(s*N+t)+:2]));
            end
            localparam integer PEER=s^1;
            ot_v41px_link #(.PW(PW),.CW(1),.LAT(11),.RATED(0)) u_relay (
                .clk(clk),.rst_n(rst_n),.in_valid(relaytxv[s*N+t]),
                .in_rec(relaytxrec[(s*N+t)*PW+:PW]),.in_ready(),
                .out_valid(relayrxv[PEER*N+t]),.out_rec(relayrxrec[(PEER*N+t)*PW+:PW]),
                .cr_in(1'b0),.cr_out());
        end

        always @(posedge clk) if(rst_n && op>=0) begin : observe
            integer wc, occ, a, j;
            wc=0;occ=0;
            if(go) begin
                seen='0;writes[s]=0;first_tx[s]=-1;last_tx[s]=-1;
                first_vm[s]=-1;last_vm[s]=-1;txstall[s]=0;outstall[s]=0;peak_fifo[s]=0;
            end
            for(integer f=0;f<2*N;f=f+1) occ+=integer'(u_coll.cnt[f]);
            if(occ>peak_fifo[s]) peak_fifo[s]=occ;
            if(ev[s]&&!er[s]) txstall[s]++;
            if(ov[s]&&!ory[s]) outstall[s]++;
            if(ev[s]&&er[s]) begin
                if(first_tx[s]<0) first_tx[s]=cyc;
                if(el[s]) last_tx[s]=cyc;
            end
            for(integer k=0;k<4;k=k+1) if(we4[k]) begin
                a=integer'(waddr4[k*WA+:WA]);
                j=a-integer'(dst);
                if(j<0 || j>=(mode?4*integer'(n):integer'(n))) $fatal(1,"VM address op=%0d die=%0d addr=%0d",op,s,a);
                if(seen[j]) $fatal(1,"duplicate VM write op=%0d die=%0d j=%0d",op,s,j);
                if(wdata4[k*FW+:FW]!==expected[(op*N)*MAXW+j])
                    $fatal(1,"VM mismatch op=%0d die=%0d j=%0d",op,s,j);
                seen[j]=1'b1;
                vm[a]<=wdata4[k*FW+:FW];
                wc++;
            end
            if(wc>0) begin
                if(first_vm[s]<0) first_vm[s]=cyc;
                last_vm[s]=cyc;
                writes[s]+=wc;
            end
        end
    end endgenerate

    task automatic run_op(input integer oi);
        integer nn, limit, begin_cycle, end_cycle;
        begin
            @(negedge clk);
            op=oi;mode=desc[oi][31];rnd=desc[oi][30];tag={24'd0,desc[oi][22:15]};
            nn=integer'(desc[oi][14:0]);n=WA'(nn);
            src=WA'(oi*512);dst=WA'(8192+oi*1536);
            begin_cycle=cyc;
            go=1;
            @(negedge clk);go=0;
            wait(&busy);
            wait(!( |busy));
            @(negedge clk);
            end_cycle=cyc;
            check_go=1;
            wait(&check_done);
            @(negedge clk);
            check_go=0;
            if((|dma_fault)||(|efault)||(|oerr))
                $fatal(1,"collective fault op=%0d dma=%b engine=%b out=%b",oi,dma_fault,efault,oerr);
            for(integer d=0;d<N;d=d+1) begin
                if(writes[d]!=(mode?4*nn:nn))
                    $fatal(1,"write count op=%0d die=%0d got=%0d",oi,d,writes[d]);
                $display("OP op=%0d die=%0d mode=%0d words=%0d tag=%0d start=%0d first_tx=%0d last_tx=%0d first_vm=%0d last_vm=%0d finish=%0d txstall=%0d outstall=%0d peak_fifo=%0d writes=%0d",
                         oi,d,mode,nn,tag,begin_cycle,first_tx[d],last_tx[d],
                         first_vm[d],last_vm[d],end_cycle,txstall[d],
                         outstall[d],peak_fifo[d],writes[d]);
            end
        end
    endtask
    string vecdir;
    initial begin
        if(!$value$plusargs("VEC=%s",vecdir)) $fatal(1,"missing VEC");
        $readmemh({vecdir,"/desc.hex"},desc);
        $readmemh({vecdir,"/part.hex"},part);
        $readmemh({vecdir,"/expected.hex"},expected);
        images_ready=1;
        wait(&vm_loaded);
        repeat(8)@(negedge clk);rst_n=1;
        for(integer i=0;i<OPS;i=i+1) run_op(i);
        $display("L0_COLLECTIVES_PASS ops=%0d cycles=%0d",OPS,cyc);
        $finish;
    end
    initial begin #1000000; $fatal(1,"layer0 collective sequence timeout"); end
endmodule
