#!/usr/bin/env python3
"""Two-row exact equivalence of the column return row (HC-COLUMN 10-16, option A, y-beat / cs relay).

Reference row = the cth_nt return path verbatim (monolithic ot_s81_hc_ctra / ctrb / ctrn, RLY 2, wiring copied from
ot_s81_hc_cth_nt) built with ctrs Y_LAG 1 / CS_LAG 1 and fed the y beat and cs one cycle late (the relay modelled in the
bench).  DUT row = ot_s81_hc_retrow (ot_s81_hc_ret_column_c0..3 = ctra+ctrb column leaf YB_STAGE 1 PAYLOAD_STAGE 0, +
ot_s81_hc_ctrn_col_e/_w slices) chained through the per-column bundles, the raw y beat / cs at its pins (relayed inside).
Every other input is identical.  PASS = the two-row chain output (cols2flat) and every per-column request equal the
reference in the same cycle, 3000 cycles incl. a mid-run reset.  Mutants: partner column c+1, header copy from a peer,
unrelayed own y lanes, cs not relayed, slices not replicating the partner ctrb chunk.
Runs on ot-run only.
"""
import argparse, hashlib, json, subprocess, shutil
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);a=ap.parse_args()
r=Path(__file__).resolve().parents[2];out=Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
cth=(r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv').read_text()
def module(src,name):
    b=src.index('module '+name+' #(');return src[b:src.index('\nendmodule',b)+len('\nendmodule')]
sup=(r/'rtl/hdc/ot_hdc_delay.sv').read_text(); vl=(r/'rtl/hdc/ot_hdc_sfu.sv').read_text(); vb=vl.index('module ot_hdc_vline')
sup+='\n'+vl[vb:vl.index('endmodule',vb)+9]
ref=sup+'\n'+'\n'.join(module(cth,n) for n in ('ot_s81_hc_ctq','ot_s81_hc_ctrs','ot_s81_hc_ctra','ot_s81_hc_ctrb','ot_s81_hc_ctrn'))
ref+='''
module ref_row(input wire clk, input wire rst_c, input wire [7:0] tid, input wire last, input wire [6:0] fv_local, input wire [103:0] fdx_local,
  input wire [7:0] rv_in, input wire [2155:0] rd_in, output wire [7:0] rv_out, output wire [2155:0] rd_out,
  output wire [15:0] rq0, rq1, rq2, rq3, output wire [3:0] hs_run_c, output wire [15:0] hs0, hs1, hs2, hs3,
  input wire [4095:0] hrq, input wire [255:0] yb, input wire [127:0] cs, input wire [15:0] nflt, input wire hov0,
  input wire [7:0] hnz_d, pflt_d);
  localparam integer S_RT=4, SH=2, P_D=108, RDW=2156, WA=1132;
  wire [S_RT+3:0] rvm; wire [RDW-1:0] rdm; wire [8*64*SH-1:0] hqa_n, hqa_s, hqb_n, hqb_s;
  genvar j,q;
  generate for (j = 0; j < 8; j = j + 1) begin : g_hq
    for (q = 0; q < SH; q = q + 1) begin : g_s
      assign hqa_n[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * j + 64 * q +: 64];
      assign hqa_s[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * (j + 8) + 64 * q +: 64];
      assign hqb_n[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * j + 64 * (q + SH) +: 64];
      assign hqb_s[64 * (SH * j + q) +: 64] = hrq[64 * S_RT * (j + 8) + 64 * (q + SH) +: 64];
    end
  end endgenerate
  wire [15:0] rq_q; wire hs_run; wire [15:0] hs_c; wire [15:0] rq_c1, rq_c2, rq_c3; wire hr1,hr2,hr3; wire [15:0] hc1,hc2,hc3;
  wire [7:0] hov_d = {7'd0, hov0};
  ot_s81_hc_ctra #(.NG(256),.D(5120),.NCOL(3),.GS(8),.S_RD(2),.S_RT(4),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1),.Y_LAG(2),.CS_LAG(2),.HQ_LAG(1)) u_ra (
    .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local), .rv_in(rv_in),
    .rd_in(rd_in[WA-1:0]), .rvm(rvm), .rdm(rdm[WA-1:0]), .rq_q(rq_q), .hs_run(hs_run), .hs_c(hs_c),
    .rq_q_c1(rq_c1), .rq_q_c2(rq_c2), .rq_q_c3(rq_c3), .hs_run_c1(hr1), .hs_run_c2(hr2), .hs_run_c3(hr3),
    .hs_c_c1(hc1), .hs_c_c2(hc2), .hs_c_c3(hc3),
    .hrq_n(hqa_n), .hrq_s(hqa_s), .yb_n(yb[0 +: 128]), .yb_s(yb[128 +: 128]), .cs(cs),
    .nflt_n(nflt[7:0]), .nflt_s(nflt[15:8]), .hov_d(hov_d[0]),
    .hnz_n({hnz_d[6], hnz_d[4], hnz_d[2], hnz_d[0]}), .hnz_s({hnz_d[7], hnz_d[5], hnz_d[3], hnz_d[1]}),
    .pflt_n({pflt_d[6], pflt_d[4], pflt_d[2], pflt_d[0]}), .pflt_s({pflt_d[7], pflt_d[5], pflt_d[3], pflt_d[1]}));
  ot_s81_hc_ctrb #(.NG(256),.D(5120),.NCOL(3),.GS(8),.S_RD(2),.S_RT(4),.ML(5),.AL(4),.CHAIN_STEP(6),.READ_STAGE(1),.Y_LAG(2),.CS_LAG(0),.HQ_LAG(1)) u_rb (
    .clk(clk), .rst_in(rst_c), .tid(tid), .last(last), .fv(fv_local), .fdx(fdx_local), .rv_in(rv_in),
    .rdh_in(rd_in[P_D-1:0]), .rdd_in(rd_in[RDW-1 -: 512 * SH + 128]), .rdm(rdm[RDW-1 -: 512 * SH]),
    .hrq_n(hqb_n), .hrq_s(hqb_s), .yb_n(yb[0 +: 128]), .yb_s(yb[128 +: 128]));
  ot_s81_hc_ctrn #(.S_RT(S_RT), .RDW(RDW), .RLY(2)) u_rn (.clk(clk), .rst_in(rst_c), .rvm(rvm), .rdm(rdm), .rv_out(rv_out), .rd_out(rd_out));
  assign rq0=rq_q; assign rq1=rq_c1; assign rq2=rq_c2; assign rq3=rq_c3; assign hs_run_c={hr3,hr2,hr1,hs_run};
  assign hs0=hs_c; assign hs1=hc1; assign hs2=hc2; assign hs3=hc3;
endmodule
'''
(out/'reference.sv').write_text(ref)
cols=(r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv').read_text()
ntc=(r/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth_ntc.sv').read_text()
_b=ntc.index('module ot_s81_hc_cth_ntc'); _e=ntc.index('\nendmodule',_b)+len('\nendmodule')
dut_src=cols+'\n'+ntc[:_b]+ntc[_e:]   # every module except the cth_ntc parent
bench='''module check;
  reg clk=0; reg [31:0] rng=32'h2545F491; integer cycle,j,k;
  reg rst; reg [7:0] tid1,tid2; reg last1,last2; reg [6:0] fv1,fv2; reg [103:0] fdx1,fdx2;
  reg [7:0] rv_x; reg [2155:0] rd_x; reg [7:0] rv_xd; reg [2155:0] rd_xd;
  reg [4095:0] hrq1,hrq2,hrq1d,hrq2d; reg [255:0] yb1,yb2,yb1d,yb2d,yb1e,yb2e; reg [127:0] cs1d,cs2d,cs1e,cs2e; reg [127:0] cs1,cs2;
  reg rrf; reg [6:0] fv1L,fv2L; /* a4: the reference sees ctfl's fv_local = the early fv registered (reset relay as ctfl) */ reg [15:0] nf1,nf2; reg hov1,hov2; reg [7:0] hz1,hz2,pf1,pf2;
  wire [7:0] r1_rv, r2_rv; wire [2155:0] r1_rd, r2_rd;
  wire [15:0] r1q0,r1q1,r1q2,r1q3,r2q0,r2q1,r2q2,r2q3,r1h0,r1h1,r1h2,r1h3,r2h0,r2h1,r2h2,r2h3; wire [3:0] r1hr,r2hr;
  ref_row ref1(.clk(clk),.rst_c(rst),.tid(tid1),.last(last1),.fv_local(fv1L),.fdx_local(fdx1),.rv_in(rv_x),.rd_in(rd_x),.rv_out(r1_rv),.rd_out(r1_rd),
    .rq0(r1q0),.rq1(r1q1),.rq2(r1q2),.rq3(r1q3),.hs_run_c(r1hr),.hs0(r1h0),.hs1(r1h1),.hs2(r1h2),.hs3(r1h3),.hrq(hrq1d),.yb(yb1e),.cs(cs1e),.nflt(nf1),.hov0(hov1),.hnz_d(hz1),.pflt_d(pf1));
  ref_row ref2(.clk(clk),.rst_c(rst),.tid(tid2),.last(last2),.fv_local(fv2L),.fdx_local(fdx2),.rv_in(r1_rv),.rd_in(r1_rd),.rv_out(r2_rv),.rd_out(r2_rd),
    .rq0(r2q0),.rq1(r2q1),.rq2(r2q2),.rq3(r2q3),.hs_run_c(r2hr),.hs0(r2h0),.hs1(r2h1),.hs2(r2h2),.hs3(r2h3),.hrq(hrq2d),.yb(yb2e),.cs(cs2e),.nflt(nf2),.hov0(hov2),.hnz_d(hz2),.pflt_d(pf2));
  localparam integer RBW=1140;
  wire [4*RBW-1:0] b0, b1, b2; wire [7:0] d_rv; wire [2155:0] d_rd;
  wire [15:0] d1q0,d1q1,d1q2,d1q3,d2q0,d2q1,d2q2,d2q3,d1h0,d1h1,d1h2,d1h3,d2h0,d2h1,d2h2,d2h3; wire [3:0] d1hr,d2hr;
  ot_s81_hc_rb_flat2cols #(.S_RT(4)) f2c(.rv(rv_x),.rd(rd_x),.rb(b0));
  ot_s81_hc_retrow #(.CHAIN_STEP(6),.READ_STAGE(1)) dut1(.clk(clk),.rst_in(rst),.tid(tid1),.last(last1),.fv(fv1),.fdx(fdx1),.rb_in(b0),.rb_out(b1),
    .rq_q0(d1q0),.rq_q1(d1q1),.rq_q2(d1q2),.rq_q3(d1q3),.hs_run_c(d1hr),.hs_c0(d1h0),.hs_c1(d1h1),.hs_c2(d1h2),.hs_c3(d1h3),
    .hrq(hrq1),.yb(yb1),.cs(cs1),.nflt(nf1),.hov_d(hov1),.hnz_d(hz1),.pflt_d(pf1));
  ot_s81_hc_retrow #(.CHAIN_STEP(6),.READ_STAGE(1)) dut2(.clk(clk),.rst_in(rst),.tid(tid2),.last(last2),.fv(fv2),.fdx(fdx2),.rb_in(b1),.rb_out(b2),
    .rq_q0(d2q0),.rq_q1(d2q1),.rq_q2(d2q2),.rq_q3(d2q3),.hs_run_c(d2hr),.hs_c0(d2h0),.hs_c1(d2h1),.hs_c2(d2h2),.hs_c3(d2h3),
    .hrq(hrq2),.yb(yb2),.cs(cs2),.nflt(nf2),.hov_d(hov2),.hnz_d(hz2),.pflt_d(pf2));
  ot_s81_hc_rb_cols2flat #(.S_RT(4)) c2f(.rb(b2),.rv(d_rv),.rd(d_rd));
  reg [7:0] p_rv; reg [2155:0] p_rd; reg [15:0] p1q0,p1q1,p1q2,p1q3,p2q0,p2q1,p2q2,p2q3,p1h0,p1h1,p1h2,p1h3,p2h0,p2h1,p2h2,p2h3; reg [3:0] p1hr,p2hr;
  task automatic rnd(inout reg [31:0] s); begin s=s^(s<<13); s=s^(s>>17); s=s^(s<<5); end endtask
  `define RB(v) for(j=0;j<$bits(v);j=j+1) begin rnd(rng); v[j]=rng[0]; end
  initial begin
    rst=0; rv_x=0; rd_x=0; yb1d=0; yb2d=0; cs1d=0; cs2d=0; yb1e=0; yb2e=0; cs1e=0; cs2e=0; hrq1d=0; hrq2d=0; rrf=0; fv1L=0; fv2L=0;
    for(cycle=0;cycle<3000;cycle=cycle+1) begin
      clk=0; #1;
      rst=(cycle>=6 && !(cycle>=1500 && cycle<1504));
      tid1=8'd3; tid2=8'd5; last1=(cycle<1000); last2=1'b0;
      `RB(fdx1) `RB(fdx2) `RB(hrq1) `RB(hrq2) `RB(yb1) `RB(yb2) `RB(cs1) `RB(cs2) `RB(rd_x)
      nf1=(cycle%211==0)?16'h0100:16'd0; nf2=(cycle%223==0)?16'h0002:16'd0; hz1=(cycle%97==0)?8'h10:8'd0; hz2=0; pf1=0; pf2=(cycle%151==0)?8'h04:8'd0;
      hov1=(cycle%61==0); hov2=(cycle%67==0);
      fv1='0; fv1[3]=(cycle%97==0); fv1[6]=(cycle%83==0); fv1[4]=(cycle%7==0); fv1[5]=(cycle%41==0); fdx1[63 +:8]=cycle%5;
      fv2='0; fv2[3]=(cycle%101==1); fv2[6]=(cycle%89==3); fv2[4]=(cycle%7==2); fv2[5]=(cycle%43==5); fdx2[63 +:8]=(cycle+1)%5;
      rv_x=0; rv_x[4]=(cycle%13==0); rv_x[5]=(cycle%17==0);
      for(j=0;j<4;j=j+1) begin rd_x[4+8*j +:8]=(cycle+j)%5; rd_x[4+32+16*j +:16]=(cycle+j)%640; end
      rd_x[4+96 +:8]=cycle%5;
      #1; clk=1;
      yb1d<=yb1; yb2d<=yb2; cs1d<=cs1; cs2d<=cs2; yb1e<=yb1d; yb2e<=yb2d; cs1e<=cs1d; cs2e<=cs2d; hrq1d<=hrq1; hrq2d<=hrq2;
      rrf<=rst; fv1L<=rrf ? fv1 : 7'd0; fv2L<=rrf ? fv2 : 7'd0;
      #1;
      p_rv=r2_rv; p_rd=r2_rd;
      p1q0=r1q0;p1q1=r1q1;p1q2=r1q2;p1q3=r1q3;p2q0=r2q0;p2q1=r2q1;p2q2=r2q2;p2q3=r2q3;p1hr=r1hr;p2hr=r2hr;
      p1h0=r1h0;p1h1=r1h1;p1h2=r1h2;p1h3=r1h3;p2h0=r2h0;p2h1=r2h1;p2h2=r2h2;p2h3=r2h3;
      if(cycle>16 && !(cycle>=1500 && cycle<1516)) begin
        if(d_rv!==p_rv) $fatal(1,"rv mismatch cycle=%0d",cycle);
        if(d_rd!==p_rd) $fatal(1,"rd mismatch cycle=%0d",cycle);
        if({d1q0,d1q1,d1q2,d1q3,d2q0,d2q1,d2q2,d2q3}!=={p1q0,p1q1,p1q2,p1q3,p2q0,p2q1,p2q2,p2q3}) $fatal(1,"request mismatch cycle=%0d",cycle);
        if({d1hr,d2hr,d1h0,d1h1,d1h2,d1h3,d2h0,d2h1,d2h2,d2h3}!=={p1hr,p2hr,p1h0,p1h1,p1h2,p1h3,p2h0,p2h1,p2h2,p2h3}) $fatal(1,"hs mismatch cycle=%0d",cycle);
      end
    end
    $display("PASS row 3000 cycles two-row chain output and all per-column requests exact (same cycle)");
    $finish;
  end
endmodule
'''
(out/'check.sv').write_text(bench)
MUT={'positive':[],
 'partner_c1':[('localparam integer B = RBW * c, PC = (c + 2) % 4;','localparam integer B = RBW * c, PC = (c + 1) % 4;'),('PC = (COLUMN + 2) % 4,','PC = (COLUMN + 1) % 4,')],
 'header_from_peer':[('.flg_hnz(flg_hnz), .hdr_c(hdr),','.flg_hnz(flg_hnz), .hdr_c(g_col[(c + 1) % 4].hdr ^ {107\'d0, g_col[(c + 1) % 4].rvm[0]}),')],
 'no_par_ctrb':[(".a_par(g_col[PC].a_rdm), .b_par(g_col[PC].b_rdm),",".a_par(g_col[PC].a_rdm), .b_par(b_rdm),")],
 'cs_relay_skipped':[('.cs_in(c == 3 ? cs : cs_net), .cs_fwd(csf),','.cs_in(cs), .cs_fwd(csf),')],
 'unrelayed_own_y':[('yb_o<=yb_r;','yb_o<=yb_loc;')],
 'hq_pin_reg_bypassed':[('assign hrq_use = hrq_q;','assign hrq_use = hrq_col;')],
 'fv_pin_reg_bypassed':[('assign fv_use = fv_q;','assign fv_use = fv;')],
 'yb_peer_reg_bypassed':[('assign yb_own=yb_o; assign yb_pv=yb_pq;','assign yb_own=yb_o; assign yb_pv=yb_peer;')],
 'yb_own_reg_bypassed':[('assign yb_own=yb_o; assign yb_pv=yb_pq;','assign yb_own=yb_r; assign yb_pv=yb_pq;')],
 'cs_reg_bypassed':[('assign cs_use=cs_o;','assign cs_use=(COLUMN==3) ? cs_q : cs_rel;')],
 'slice_flag_merge_dropped':[('rv_c[S_RT+2] | (|flg_fault)','rv_c[S_RT+2]')]}
res=[]
verilator=shutil.which('verilator') or str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator')
variants=list(MUT)
for v in variants:
    x=dut_src; b=bench
    for o,n in MUT.get(v,[]):
        assert o in x,(v,o); x=x.replace(o,n)
    (out/f'{v}.sv').write_text(x); (out/f'check_{v}.sv').write_text(b)
    build=out/('obj_'+v); log=out/(v+'.log')
    with log.open('w') as f:
        c=subprocess.run([verilator,'--binary','--timing','-Wno-fatal','--top-module','check','--Mdir',str(build),'-j','8',str(out/'reference.sv'),str(out/f'{v}.sv'),str(out/f'check_{v}.sv')],stdout=f,stderr=subprocess.STDOUT)
        if c.returncode: raise SystemExit('COMPILE FAIL '+str(log))
        run=subprocess.run([str(build/'Vcheck')],stdout=f,stderr=subprocess.STDOUT)
    ok=(run.returncode==0)==(v=='positive'); res.append(dict(variant=v,returncode=run.returncode,expected=ok,log=log.name))
    shutil.rmtree(build,ignore_errors=True)
    if not ok: raise SystemExit('UNEXPECTED VERDICT '+str(log))
rec={'status':'PASS','scope':'two-row return chain (ret_column leaves a4: YB_STAGE 2, HQ_LAG 1, FV_PIN 1, PAYLOAD_STAGE 0 + ctrn slices) vs cth_nt monolithic ctra/ctrb/ctrn at Y_LAG/CS_LAG 2, HQ_LAG 1 (reference fed y / cs two cycles late, hrq one cycle late, fv_local = registered early fv); component chain only, the system calendar is checked by the exact HC gate',
     'cycles':3000,'calendar':'a4: y returns +2 vs cth_nt (Y_LAG 2), cs captured +2 (CS_LAG 2), h-return merge +1 per row (HQ_LAG 1: rd relay +1 = chain +1 per row); requests unchanged; fv 0 (early fv + pin register)',
     'sources_sha256':{p:hashlib.sha256((r/p).read_bytes()).hexdigest() for p in ['rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_return_columns.sv','rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth_ntc.sv','rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv']},'results':res}
(out/'receipt.json').write_text(json.dumps(rec,indent=1)+'\n'); print(json.dumps(rec))
