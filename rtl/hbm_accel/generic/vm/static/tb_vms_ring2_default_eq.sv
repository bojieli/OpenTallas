`timescale 1ns/1ps
`default_nettype none
// HBM-BIND 2026-10-24: default-parameter bit-exactness of the NSTOP change. The edited ot_vms_rstop_static,
// ot_vms_hub_static and ot_vms_slice_static_glue (through the unchanged four-stop wrappers) run in lockstep with the
// ORIGINAL modules (git show <base>:..., renamed *_ref by run_vms_ring2_static.sh) on random pins, with a reset
// pulse every 256 cycles; every output is compared on every cycle (4-state ===). MUT>0 applies the module's bench
// mutant to the edited copies only (rstop MUT 1, hub MUT 2, glue RMUT 1) and must FAIL.
module tb_vms_ring2_default_eq;
parameter integer MUT=0, CYCLES=20000, SEED=5;
reg clk=0; always #5 clk=~clk;
reg rst_n=0;
integer seed=SEED, checks=0, errors=0, cyc;
reg [2223:0] r0,r1,r2,r3;
// ---------------- ring stop: two parameter sets
reg [1:0] sid; reg dir, txe, ack_i; reg [2:0] txs, wki; reg [2223:0] l_in; reg [289:0] pi; reg [2207:0] eg; reg [7:0] xd; reg [265:0] ri;
wire [2223:0] lo_n[0:1], lo_r[0:1]; wire [2207:0] xq_n[0:1], xq_r[0:1]; wire [287:0] rce_n[0:1], rce_r[0:1];
wire [2:0] wko_n[0:1], wko_r[0:1]; wire [263:0] cco_n[0:1], cco_r[0:1]; wire ack_n[0:1], ack_r[0:1], mb_n[0:1], mb_r[0:1], f_n[0:1], f_r[0:1];
for(genvar g=0;g<2;g=g+1) begin:RS
    localparam integer PR=(g==0)?1:0, CDV=(g==0)?6:5;
    ot_vms_rstop_static #(.PHYSICAL_RING(PR),.COMMIT_DELAY(CDV),.MUT(MUT==1?1:0)) n_(.clk(clk),.rst_n(rst_n),.sid(sid),.dir(dir),.tx_enable(txe),.tx_source(txs),
        .l_in(l_in),.l_out(lo_n[g]),.pi(pi),.eg(eg),.xq(xq_n[g]),.xq_done(xd),.rce(rce_n[g]),.ri(ri),.wko(wko_n[g]),.wki(wki),.cco(cco_n[g]),
        .ack_o(ack_n[g]),.ack_i(ack_i),.mirror_busy(mb_n[g]),.fault(f_n[g]));
    ot_vms_rstop_static_ref #(.PHYSICAL_RING(PR),.COMMIT_DELAY(CDV)) r_(.clk(clk),.rst_n(rst_n),.sid(sid),.dir(dir),.tx_enable(txe),.tx_source(txs),
        .l_in(l_in),.l_out(lo_r[g]),.pi(pi),.eg(eg),.xq(xq_r[g]),.xq_done(xd),.rce(rce_r[g]),.ri(ri),.wko(wko_r[g]),.wki(wki),.cco(cco_r[g]),
        .ack_o(ack_r[g]),.ack_i(ack_i),.mirror_busy(mb_r[g]),.fault(f_r[g]));
end
// ---------------- hub: NC=2 (CW 2) and NC=0 (CW 1)
reg [3*338-1:0] hcq; reg [5:0] hseq; reg [7:0] hbe; reg [15:0] hbc; reg hce, hcce; reg [1:0] hcs, hccs; reg [2127:0] hpr; reg [263:0] hc0, hc1;
reg [2:0] hre; reg [5:0] hrs;
wire [3*274-1:0] hcr_n, hcr_r; wire [2279:0] hpq_n, hpq_r, hpq0_n, hpq0_r; wire [289:0] hcw_n, hcw_r, hcc_n, hcc_r, hcw0_n, hcw0_r, hcc0_n, hcc0_r;
wire [2:0] hst_n, hst_r, hst0_n, hst0_r; wire [273:0] hcr0_n, hcr0_r;
ot_vms_hub_static #(.NC(2),.MUT(MUT==2?2:0)) hub_n(.clk(clk),.rst_n(rst_n),.sid(sid),.cq(hcq),.client_seq(hseq),.bank_enable(hbe),.bank_client(hbc),
    .cw_enable(hce),.cw_client(hcs),.ccw_enable(hcce),.ccw_client(hccs),.cr(hcr_n),.pq(hpq_n),.pr(hpr),.cwi(hcw_n),.cci(hcc_n),.cco0(hc0),.cco1(hc1),
    .response_enable(hre),.response_seq(hrs),.status(hst_n));
ot_vms_hub_static_ref #(.NC(2)) hub_r(.clk(clk),.rst_n(rst_n),.sid(sid),.cq(hcq),.client_seq(hseq),.bank_enable(hbe),.bank_client(hbc),
    .cw_enable(hce),.cw_client(hcs),.ccw_enable(hcce),.ccw_client(hccs),.cr(hcr_r),.pq(hpq_r),.pr(hpr),.cwi(hcw_r),.cci(hcc_r),.cco0(hc0),.cco1(hc1),
    .response_enable(hre),.response_seq(hrs),.status(hst_r));
ot_vms_hub_static #(.NC(0),.MUT(MUT==2?2:0)) hub0_n(.clk(clk),.rst_n(rst_n),.sid(sid),.cq(hcq[337:0]),.client_seq(hseq[1:0]),.bank_enable(hbe),.bank_client(hbc[7:0]),
    .cw_enable(hce),.cw_client(hcs[0]),.ccw_enable(hcce),.ccw_client(hccs[0]),.cr(hcr0_n),.pq(hpq0_n),.pr(hpr),.cwi(hcw0_n),.cci(hcc0_n),.cco0(hc0),.cco1(hc1),
    .response_enable(hre[0]),.response_seq(hrs[1:0]),.status(hst0_n));
ot_vms_hub_static_ref #(.NC(0)) hub0_r(.clk(clk),.rst_n(rst_n),.sid(sid),.cq(hcq[337:0]),.client_seq(hseq[1:0]),.bank_enable(hbe),.bank_client(hbc[7:0]),
    .cw_enable(hce),.cw_client(hcs[0]),.ccw_enable(hcce),.ccw_client(hccs[0]),.cr(hcr0_r),.pq(hpq0_r),.pr(hpr),.cwi(hcw0_r),.cci(hcc0_r),.cco0(hc0),.cco1(hc1),
    .response_enable(hre[0]),.response_seq(hrs[1:0]),.status(hst0_r));
// ---------------- glue through the unchanged four-stop wrappers (SW: NC 2; NE: NC 0)
reg [2223:0] gcw, gccw; reg [1:0] gte; reg [5:0] gts; reg grpe, grps; reg [143:0] gbs; reg [7:0] gxd0, gxd1; reg [2207:0] geg;
`define GLUE_OUT(p) wire [547:0] p``cr; wire [2223:0] p``cwo, p``ccwo; wire [2207:0] p``xq, p``xq2; wire [2279:0] p``pq; wire [2:0] p``hs, p``rf; wire [1:0] p``mb; wire [18:0] p``vm;
`GLUE_OUT(sn_) `GLUE_OUT(sr_) `GLUE_OUT(en_) `GLUE_OUT(er_)
`define GLUE_PINS(p) .clk_hub(clk),.clk_ring({clk,clk}),.clk_replay(clk),.rst_n(rst_n),.bank_enable(hbe),.cw_in(gcw),.ccw_in(gccw),.cw_out(p``cwo),.ccw_out(p``ccwo), \
    .ring_tx_enable(gte),.ring_tx_source(gts),.replay_enable(grpe),.replay_source(grps),.bank_status(gbs),.bk_xq(p``xq),.bk_xq2(p``xq2), \
    .bk_xq_done(gxd0),.bk_xq2_done(gxd1),.bk_eg(geg),.bk_pq(p``pq),.bk_pr(hpr),.hub_status(p``hs),.mirror_busy(p``mb),.vmstat(p``vm),.ring_fault(p``rf)
`define SW_PINS(p) .cq(hcq[675:0]),.cr(p``cr),.client_seq(hseq),.response_enable(hre),.response_seq(hrs),.bank_client(hbc),.hub_ring_enable({hcce,hce}),.hub_ring_client({hccs,hcs}),
`define NE_PINS .client_seq(hseq[1:0]),.response_enable(hre[0]),.response_seq(hrs[1:0]),.bank_client(hbc[7:0]),.hub_ring_enable({hcce,hce}),.hub_ring_client({hccs[0],hcs[0]}),
hfd_hgi_vms_static_SW_glue     sw_n(`SW_PINS(sn_) `GLUE_PINS(sn_));
hfd_hgi_vms_static_SW_glue_ref sw_r(`SW_PINS(sr_) `GLUE_PINS(sr_));
// NE glue (NC 0) through the generic slice so the edited copy can take the RMUT mutant
ot_vms_slice_static_glue #(.NC(0),.RG(4),.WG(2),.NATIVE_SHAPE(1),.BANK_PIN_IN(1),.RMUT(MUT==3?1:0)) ne_n(.sid(2'd3),.cq(338'd0),.cr(en_cr[273:0]),`NE_PINS `GLUE_PINS(en_));
hfd_hgi_vms_static_NE_glue_ref ne_r(`NE_PINS `GLUE_PINS(er_));
assign en_cr[547:274]=0; assign er_cr=0;
task automatic cmp(input bit ok, input string what);
    begin checks=checks+1; if(!ok) begin errors=errors+1; if(errors<=10) $display("VMS_RING2_EQ mismatch cyc%0d %0s",cyc,what); end end
endtask
task automatic rnd(output [2223:0] v, input integer dens);
    begin for(integer i=0;i<70;i=i+1) v[i*32+:32]=$random(seed); if(($unsigned($random(seed))%dens)!=0) v=0; end
endtask
initial begin
    {sid,dir,txe,ack_i,txs,wki,l_in,pi,eg,xd,ri}=0; {hcq,hseq,hbe,hbc,hce,hcce,hcs,hccs,hpr,hc0,hc1,hre,hrs}=0;
    {gcw,gccw,gte,gts,grpe,grps,gbs,gxd0,gxd1,geg}=0;
    repeat(2) @(negedge clk); rst_n=1;
    for(cyc=0;cyc<CYCLES;cyc=cyc+1) begin
        @(negedge clk);
        rst_n=(cyc%256)!=255;
        sid=$random(seed); dir=$random(seed); txe=$random(seed); txs=$unsigned($random(seed))%6; ack_i=($unsigned($random(seed))%4)==0; wki=$random(seed);
        rnd(r0,2); l_in=r0; rnd(r0,3); pi=r0[289:0]; rnd(r0,3); eg=r0[2207:0]; rnd(r0,3); ri=r0[265:0]; xd=$random(seed);
        rnd(r0,2); hcq=r0[3*338-1:0]; rnd(r1,1); hseq=r1[5:0]; hbe=r1[13:6]&{8{r1[14]}}; hbc=r1[30:15]; hce=r1[31]&r1[32]; hcce=r1[33]&r1[34];
        hcs=r1[36:35]; hccs=r1[38:37]; hre=r1[41:39]&{3{r1[42]}}; hrs=r1[48:43];
        rnd(r2,2); hpr=r2[2127:0]; rnd(r2,3); hc0=r2[263:0]; rnd(r3,3); hc1=r3[263:0];
        rnd(r0,2); gcw=r0; rnd(r0,2); gccw=r0; rnd(r1,1); gte=r1[1:0]; gts=r1[7:2]; grpe=r1[8]; grps=r1[9]; gbs={r1[143:10],10'd0}&{144{r1[200]}};
        gxd0=r1[215:208]; gxd1=r1[223:216]; rnd(r0,3); geg=r0[2207:0];
        @(posedge clk); #1;
        for(integer g=0;g<2;g=g+1) begin
            cmp(lo_n[g]===lo_r[g],"rstop l_out"); cmp(xq_n[g]===xq_r[g],"rstop xq"); cmp(rce_n[g]===rce_r[g],"rstop rce");
            cmp(wko_n[g]===wko_r[g],"rstop wko"); cmp(cco_n[g]===cco_r[g],"rstop cco"); cmp({ack_n[g],mb_n[g],f_n[g]}==={ack_r[g],mb_r[g],f_r[g]},"rstop ack/busy/fault");
        end
        cmp(hcr_n===hcr_r,"hub2 cr"); cmp(hpq_n===hpq_r,"hub2 pq"); cmp({hcw_n,hcc_n}==={hcw_r,hcc_r},"hub2 ring"); cmp(hst_n===hst_r,"hub2 status");
        cmp(hcr0_n===hcr0_r,"hub0 cr"); cmp(hpq0_n===hpq0_r,"hub0 pq"); cmp({hcw0_n,hcc0_n}==={hcw0_r,hcc0_r},"hub0 ring"); cmp(hst0_n===hst0_r,"hub0 status");
        cmp({sn_cr,sn_cwo,sn_ccwo,sn_xq,sn_xq2,sn_pq,sn_hs,sn_rf,sn_mb,sn_vm}==={sr_cr,sr_cwo,sr_ccwo,sr_xq,sr_xq2,sr_pq,sr_hs,sr_rf,sr_mb,sr_vm},"SW glue");
        cmp({en_cr,en_cwo,en_ccwo,en_xq,en_xq2,en_pq,en_hs,en_rf,en_mb,en_vm}==={er_cr,er_cwo,er_ccwo,er_xq,er_xq2,er_pq,er_hs,er_rf,er_mb,er_vm},"NE glue");
    end
    if(errors==0) $display("VMS_RING2_EQ PASS MUT=%0d checks=%0d errors=0 cycles=%0d",MUT,checks,CYCLES);
    else $display("VMS_RING2_EQ FAIL MUT=%0d checks=%0d errors=%0d",MUT,checks,errors);
    $finish;
end
endmodule
`default_nettype wire
