`timescale 1ns/1ps
// Minimum actual TP4 participant. No VM, clock generator or host gather.
// Existing elastic transpose retains outputs when the SAME publisher stalls.
module DsromTp4Gather (
    input wire clk, rst_n, go, command,
    input wire [2047:0] vm_rq,
    input wire [3:0] vm_ready,
    output wire [3:0] vm_re, busy, fault,
    output wire [59:0] vm_raddr,
    output wire [15:0] vm_we,
    output wire [239:0] vm_waddr,
    output wire [8191:0] vm_wdata
);
    localparam integer N=4, FW=512, PW=547;
    wire [14:0] src = command ? 15'(420096 >> 4) : 15'(419776 >> 4);
    wire [14:0] dst = command ? 15'(54208 >> 4) : 15'(51648 >> 4);
    wire [14:0] n = command ? 15'(128 >> 4) : 15'(320 >> 4);
    wire [31:0] tag = command ? 32'd1 : 32'd0;
    wire [3:0] ev, er, el, em, ov, ore, ol, oe, ef, df;
    wire [2047:0] ed;
    wire [127:0] et;
    wire [8191:0] od;
    wire [7:0] ranks;
    wire [15:0] txv, txready, rxv, relaytxv, relayrxv;
    wire [4*PW-1:0] txrec;
    wire [16*PW-1:0] rxrec, relaytxrec, relayrxrec;
    wire [31:0] crin, crout;
    assign fault = ef | df | oe;
    genvar s,t;
    generate for(s=0;s<N;s=s+1) begin : g_rank
        ot_w15_coll_dma #(.WA(15),.FW(FW),.TAGW(32),.N(N),.GW(4),
                         .VM_ALWAYS_READY(0),.TOPK(0)) u_dma (
            .clk(clk),.rst_n(rst_n),.go(go),.mode(1'b1),.rnd(1'b0),
            .tag(tag),.src(src),.n(n),.dst(dst),.topk(1'b0),.ibase(15'd0),
            .tk_k(16'd0),.tk_stride(32'd0),.busy(busy[s]),.fault(df[s]),
            .words_out(),.words_in(),.vm_re(vm_re[s]),.vm_raddr(vm_raddr[s*15+:15]),
            .vm_rq(vm_rq[s*FW+:FW]),.vm_we(),.vm_waddr(),.vm_wdata(),
            .vm_ready4(vm_ready[s]),.vm_we4(vm_we[s*4+:4]),
            .vm_waddr4(vm_waddr[s*60+:60]),.vm_wdata4(vm_wdata[s*2048+:2048]),
            .e_valid(ev[s]),.e_ready(er[s]),.e_data(ed[s*FW+:FW]),
            .e_last(el[s]),.e_mode(em[s]),.e_tag(et[s*32+:32]),
            .o_valid(ov[s]),.o_ready(ore[s]),.o_data(od[s*2048+:2048]),
            .o_last(ol[s]),.o_rank(ranks[s*2+:2]),.o_err(oe[s]),.engine_fault(ef[s]));
        ot_rom_oneshot_die_px #(.N(4),.RANK(s),.LANES(16),.TAGW(32),
            .DEPTH(1024),.PKG_DIES(2),.RELAY(1),.ADD_LAT(3),
            .PAIRWISE(1),.GW(4),.OUT_BP(1)) u_coll (
            .clk(clk),.rst_n(rst_n),.in_valid(ev[s]),.in_ready(er[s]),
            .in_data(ed[s*FW+:FW]),.in_last(el[s]),.in_mode(em[s]),.in_tag(et[s*32+:32]),
            .tx_valid(txv[s*4+:4]),.tx_rec(txrec[s*PW+:PW]),.tx_ready(txready[s*4+:4]),
            .cr_in(crin[s*8+:8]),.rx_valid(rxv[s*4+:4]),.rx_rec(rxrec[s*4*PW+:4*PW]),
            .cr_out(crout[s*8+:8]),.rl_tx_valid(relaytxv[s*4+:4]),
            .rl_tx_rec(relaytxrec[s*4*PW+:4*PW]),.rl_rx_valid(relayrxv[s*4+:4]),
            .rl_rx_rec(relayrxrec[s*4*PW+:4*PW]),.out_valid(ov[s]),.out_ready(ore[s]),
            .out_data(od[s*2048+:2048]),.out_last(ol[s]),.out_rank(ranks[s*2+:2]),
            .out_err(oe[s]),.fault(ef[s]),.fault_code());
        for(t=0;t<N;t=t+1) begin : g_link
            if(t==s) begin : g_self
                assign txready[s*4+t]=1'b1;
                assign crin[2*(s*4+t)+:2]=0;
                assign rxv[s*4+t]=0;
                assign rxrec[(s*4+t)*PW+:PW]=0;
            end else begin : g_remote
                localparam integer SAME=(s/2)==(t/2);
                ot_v41px_link #(.PW(PW),.CW(2),.LAT(SAME?11:142),.COST(64),
                    .BPC_NUM(SAME?3864:15758),.BPC_DEN(SAME?1:100)) u_link (
                    .clk(clk),.rst_n(rst_n),.in_valid(txv[s*4+t]),.in_rec(txrec[s*PW+:PW]),
                    .in_ready(txready[s*4+t]),.out_valid(rxv[t*4+s]),
                    .out_rec(rxrec[(t*4+s)*PW+:PW]),.cr_in(crout[2*(t*4+s)+:2]),
                    .cr_out(crin[2*(s*4+t)+:2]));
            end
            localparam integer PEER=s^1;
            ot_v41px_link #(.PW(PW),.CW(1),.LAT(11),.RATED(0)) u_relay (
                .clk(clk),.rst_n(rst_n),.in_valid(relaytxv[s*4+t]),
                .in_rec(relaytxrec[(s*4+t)*PW+:PW]),.in_ready(),
                .out_valid(relayrxv[PEER*4+t]),.out_rec(relayrxrec[(PEER*4+t)*PW+:PW]),
                .cr_in(1'b0),.cr_out());
        end
    end endgenerate
endmodule
