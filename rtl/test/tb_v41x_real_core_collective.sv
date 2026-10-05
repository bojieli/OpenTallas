`timescale 1ns/1ps
// Reduced representative stage: one adopted V4.1x vector core produces rank-0
// partials, four real one-shot dies fold them, and the same core consumes each
// committed result. Other ranks use deterministic, source-pinned partials.
// The producer's VM is the full local result buffer; QTX is the bounded DMA
// queue. The one-shot engine has no out_ready: its result store holds WORDS.
module tb_v41x_real_core_collective #(
    parameter integer LAT_X = 142,
    parameter integer DEPTH = 2,
    parameter integer QTX = 2
) (input wire clk);
    localparam integer N=4, WORDS=8, LANES=16, FW=512, PW=546, RB=2, AW=24;
    localparam integer IN_BASE=0, PRODUCED=256, REDUCED=512, CONSUMED=768;
    reg [31:0] vm [0:1023];
    reg [1535:0] prog [0:17];
    reg [FW-1:0] part [0:N*WORDS-1], reduced_expect [0:WORDS-1];
    reg [31:0] consume_expect [0:WORDS*LANES-1];
    reg [FW-1:0] produced [0:WORDS-1];
    string dir;
    initial begin
        if (!$value$plusargs("VEC=%s",dir)) dir=".";
        for (integer i=0;i<1024;i=i+1) vm[i]=0;
        $readmemh({dir,"/init.hex"},vm,0,WORDS*LANES-1);
        $readmemh({dir,"/program.hex"},prog);
        $readmemh({dir,"/part.hex"},part);
        $readmemh({dir,"/expect.hex"},reduced_expect);
        $readmemh({dir,"/consumed.hex"},consume_expect);
    end
    reg [4:0] rcnt=0;
    wire rst_n=(rcnt==5'd16);
    always @(posedge clk) if(!rst_n) rcnt<=rcnt+1'b1;
    integer cyc=0, bad=0, rbw=0, produced_count=0, sum_count=0, consumed_count=0;
    always @(posedge clk) cyc<=cyc+1;
    reg core_start=0;
    reg [13:0] core_entry=0;
    wire core_done, core_fault, prog_re;
    wire [13:0] prog_addr;
    reg [1535:0] prog_q;
    wire [63:0] xs_rd_re;
    wire [1535:0] xs_rd_addr;
    wire [127:0] xs_rd_src;
    reg [2047:0] xs_rd_q;
    wire [15:0] xs_vm_we;
    wire [383:0] xs_vm_waddr;
    wire [511:0] xs_vm_wdata;
    always @(posedge clk) if(prog_re) prog_q<=prog[prog_addr];
    ot_hdc_core_v41x #(.X_HE(1),.X_SU(1),.SUN(16),.SUM(8)) u_core (
        .clk(clk),.rst_n(rst_n),.start(core_start),.token(16'd1),.pos(16'd0),
        .entry(core_entry),.done(core_done),.fault(core_fault),
        .prime_v(1'b0),.prime_first(1'b0),.prime_cid(12'd0),
        .prog_re(prog_re),.prog_addr(prog_addr),.prog_q(prog_q),
        .cfg_ik_base(24'd0),.idx_user_base_sec(28'd0),.cfg_me_xs(4'd0),
        .xs_vi_q('0),.xs_rd_re(xs_rd_re),.xs_rd_addr(xs_rd_addr),
        .xs_rd_src(xs_rd_src),.xs_rd_q(xs_rd_q),
        .xs_vm_we(xs_vm_we),.xs_vm_waddr(xs_vm_waddr),.xs_vm_wdata(xs_vm_wdata)
    );
    always @(posedge clk) begin : memory_step
        integer a,k,l;
        for(integer i=0;i<64;i=i+1) if(xs_rd_re[i]) begin
            a=xs_rd_addr[i*AW+:AW];
            xs_rd_q[i*32+:32]<=vm[a];
            if(a>=REDUCED && a<REDUCED+WORDS*LANES && a>=REDUCED+sum_count*LANES) begin
                rbw=rbw+1;
                if(rbw<4) $display("READ_BEFORE_WRITE addr=%0d committed=%0d",a,sum_count);
            end
        end
        for(integer i=0;i<16;i=i+1) if(xs_vm_we[i]) begin
            a=xs_vm_waddr[i*AW+:AW];
            vm[a]<=xs_vm_wdata[i*32+:32];
            if(a>=PRODUCED && a<PRODUCED+WORDS*LANES) begin
                k=(a-PRODUCED)/LANES; l=(a-PRODUCED)%LANES;
                produced[k][l*32+:32]<=xs_vm_wdata[i*32+:32];
                if(xs_vm_wdata[i*32+:32]!==part[k][l*32+:32]) begin
                    bad=bad+1;
                    if(bad<4) $display("PRODUCER_MISMATCH word=%0d lane=%0d",k,l);
                end
            end
        end
        if(&xs_vm_we && xs_vm_waddr[0+:AW]>=PRODUCED && xs_vm_waddr[0+:AW]<PRODUCED+WORDS*LANES)
            produced_count<=produced_count+1;
        if(ov[0]) begin
            for(integer i=0;i<LANES;i=i+1)
                vm[REDUCED+sum_count*LANES+i]<=od[i*32+:32];
            sum_count<=sum_count+1;
        end
    end
    // Core starts each consumer word only after that complete reduced word is committed.
    integer state=0;
    always @(posedge clk) begin
        core_start<=0;
        if(rst_n) case(state)
            0: begin core_entry<=0; core_start<=1; state<=1; end
            1: if(core_done && produced_count==WORDS) state<=2;
            2: if(consumed_count<WORDS && sum_count>consumed_count) begin
                   core_entry<=2+2*consumed_count; core_start<=1; state<=3;
               end
            3: if(!core_done) state<=4;
            4: if(core_done) begin
                   for(integer j=0;j<LANES;j=j+1)
                       if(vm[CONSUMED+consumed_count*LANES+j]!==consume_expect[consumed_count*LANES+j]) begin
                           bad=bad+1;
                           if(bad<4) $display("CONSUMER_MISMATCH word=%0d lane=%0d",consumed_count,j);
                       end
                   $display("CONSUMED word=%0d cyc=%0d",consumed_count,cyc);
                   consumed_count<=consumed_count+1; state<=2;
               end
        endcase
    end
    // Four rank-order one-shot engines and bounded input queues.
    wire [N-1:0] iv,ir,il,ov,ol,oe,flt,txv;
    wire [N*FW-1:0] id,od;
    wire [N*PW-1:0] txr;
    wire [N*RB-1:0] orank;
    wire [N*3-1:0] fc;
    wire [N*N-1:0] txrdy,crin,rxv,crout;
    wire [N*N*PW-1:0] rxr;
    integer out_count [0:N-1];
    wire [31:0] sent_count [0:N-1], stall_count [0:N-1], hold_count [0:N-1], qmax_count [0:N-1];
    initial for(integer i=0;i<N;i=i+1) out_count[i]=0;
    genvar s,t;
    generate for(s=0;s<N;s=s+1) begin:g_die
        ot_rom_oneshot_die #(.N(N),.RANK(s),.LANES(LANES),.DEPTH(DEPTH)) u_die (
            .clk(clk),.rst_n(rst_n),.in_valid(iv[s]),.in_ready(ir[s]),
            .in_data(id[s*FW+:FW]),.in_last(il[s]),.in_mode(1'b0),.in_tag(32'd7),
            .tx_valid(txv[s]),.tx_rec(txr[s*PW+:PW]),.tx_ready(txrdy[s*N+:N]),.cr_in(crin[s*N+:N]),
            .rx_valid(rxv[s*N+:N]),.rx_rec(rxr[s*N*PW+:N*PW]),.cr_out(crout[s*N+:N]),
            .out_valid(ov[s]),.out_data(od[s*FW+:FW]),.out_last(ol[s]),.out_rank(orank[s*RB+:RB]),
            .out_err(oe[s]),.fault(flt[s]),.fault_code(fc[s*3+:3]));
        for(t=0;t<N;t=t+1) begin:g_to
            if(t==s) begin:g_self
                assign txrdy[s*N+t]=1'b1;
                assign crin[s*N+t]=1'b0;
                assign rxv[t*N+s]=1'b0;
                assign rxr[(t*N+s)*PW+:PW]='0;
            end else begin:g_link
                localparam integer SAME=(s/2)==(t/2);
                ot_v41sb_link #(.PW(PW),.LAT(SAME?11:LAT_X),.COST(FW/8),
                                  .BPC_NUM(SAME?3864:15758),.BPC_DEN(SAME?1:100)) u_link (
                    .clk(clk),.rst_n(rst_n),.in_valid(txv[s]),.in_rec(txr[s*PW+:PW]),
                    .in_ready(txrdy[s*N+t]),.out_valid(rxv[t*N+s]),
                    .out_rec(rxr[(t*N+s)*PW+:PW]),.cr_in(crout[t*N+s]),.cr_out(crin[s*N+t]));
            end
        end
        reg [FW-1:0] q [0:QTX-1];
        integer k=0,qh=0,qt=0,qn=0,sent=0,stall=0,hold=0,qmax=0;
        assign sent_count[s]=sent; assign stall_count[s]=stall;
        assign hold_count[s]=hold; assign qmax_count[s]=qmax;
        wire take=iv[s]&&ir[s];
        wire can_push=rst_n && k<WORDS && (s==0 ? produced_count>k : cyc>=20+s*3) && qn<QTX;
        always @(posedge clk) if(rst_n) begin
            if(can_push) begin
                q[qt]<=s==0?produced[k]:part[s*WORDS+k];
                qt<=(qt==QTX-1)?0:qt+1;
                k<=k+1;
            end
            if(k<WORDS && qn==QTX) stall<=stall+1;
            if(qn>0 && !take) hold<=hold+1;
            if(take) begin qh<=(qh==QTX-1)?0:qh+1; sent<=sent+1; end
            qn<=qn+(can_push?1:0)-(take?1:0);
            if(qn+(can_push?1:0)-(take?1:0)>qmax) qmax<=qn+(can_push?1:0)-(take?1:0);
            if(ov[s]) begin
                if(out_count[s]>=WORDS || od[s*FW+:FW]!==reduced_expect[out_count[s]] || oe[s] ||
                   ol[s]!=(out_count[s]==WORDS-1)) begin
                    bad=bad+1;
                    if(bad<4) $display("COLLECTIVE_MISMATCH rank=%0d word=%0d err=%0d",s,out_count[s],oe[s]);
                end
                $display("REDUCED rank=%0d word=%0d cyc=%0d",s,out_count[s],cyc);
                out_count[s]<=out_count[s]+1;
            end
        end
        assign iv[s]=qn>0;
        assign id[s*FW+:FW]=q[qh];
        assign il[s]=(sent==WORDS-1);
    end endgenerate
    reg finished=0;
    always @(posedge clk) if(rst_n && !finished) begin
        if(cyc>20000 || (consumed_count==WORDS && out_count[0]==WORDS && out_count[1]==WORDS &&
                         out_count[2]==WORDS && out_count[3]==WORDS)) begin
            finished<=1;
            $display("REAL_STAGE_SUMMARY cyc=%0d produced=%0d reduced=%0d consumed=%0d bad=%0d rbw=%0d core_fault=%0d collective_fault=%b timeout=%0d",
                     cyc,produced_count,sum_count,consumed_count,bad,rbw,core_fault,flt,cyc>20000);
            for(integer i=0;i<N;i=i+1)
                $display("RANK rank=%0d accepted=%0d delivered=%0d stall=%0d hold=%0d qmax=%0d fault=%0d code=%0d",
                         i,sent_count[i],out_count[i],stall_count[i],hold_count[i],qmax_count[i],flt[i],fc[i*3+:3]);
            if(cyc<=20000 && bad==0 && rbw==0 && core_fault==0 && flt==0 && produced_count==WORDS &&
               sum_count==WORDS && consumed_count==WORDS && stall_count[0]>0) $display("REAL_STAGE PASS");
            else $display("REAL_STAGE FAIL");
            $finish;
        end
    end
endmodule
