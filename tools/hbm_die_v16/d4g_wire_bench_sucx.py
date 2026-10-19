#!/usr/bin/env python3
"""HBM-WIRE 10-18: SU <-> COLL exchange WIRING bench for one d4g quadrant (gaps G-CIL-INJ, G-CIL-DEL, G-CIL-RC).

    d4g_wire_bench_sucx.py --die die.v --contract pre.json[.gz] --q SW --out DIR [--mut N]

DUT = the die slice {cic_<q>, cxij_<q>, cij_<q>, cxdl_<q>0..3, cxrc_<q>} cut VERBATIM from die.v (d4g_die_slice.py), with
the die's own connection expressions into hb_coll_<q>, su_<q>0..3 and sucore_<q> as observe ports.
REFERENCE = the RTL composition the compiler's INJ / DEL / RC schedule assumes, written from the RTL port contracts (no
die text): ot_hgi_coll_inj_copy (INJ_COPY_EDGES 1) -> ot_hbm_su_static_cxport_split (the hub-shaped composition of the
same six leaves: inj_q = {su3..su0}, del lane g = del_flit[545g+:545], ro_v/ro_x faces w,n,e,s low -> high) ->
ot_hgi_coll_inj_idx_join_rg_flat (flat su_inj_d / inj_d, INJLAT as the die); the reference inject leaf takes the
compiled slot INJ_RET = INJLAT - 3 and B39_NOOP 1 (never the die's own parameter).  Same random stimulus on every boundary
net (stream 3 / serial 4 lattice, phase-zero bridge reset), every observed consumer pin compared (!==) at every edge of
both clocks: COLL inj_d (answer slot P + INJLAT), COLL rc_*, SU slice dw_* and inj_rd/inj_addr, SU core rr_w*/sfu_x,
and the leaf faults.  Non-vacuity counters must be > 0.  Prints SUCX_WIRE PASS|FAIL Q=<q> MUT=<n> ...
MUT (die slice only, must FAIL): 1 cij su_inj_d_r0 word halves swapped; 2 cxdl lane 1 fed from lane 2; 3 cxrc SFU
operand data faces n/e swapped; 4 cxij slice inputs 1/2 swapped.
"""
import argparse, re, subprocess, sys
from pathlib import Path

H = Path(__file__).resolve().parent
RTL = ['rtl/hbm_accel/generic/adapters/static_su/collport/ot_hbm_su_static_cxport_split.sv',
       'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_inj_copy.sv',
       'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_inj_idx_join_rg.sv',
       'rtl/hbm_accel/generic/collective/p2p/ot_hgi_coll_inj_idx_join.sv']


def mutate(txt, q, mut):
    def sub(inst, old, new):
        nonlocal txt
        i = txt.index(f' {inst} (')
        j = txt.index('\n  );', i)
        blk = txt[i:j]
        assert old in blk, (inst, old)
        txt = txt[:i] + blk.replace(old, new, 1) + txt[j:]
    if mut == 1:
        sub(f'cij_{q}', f'.su_inj_d_r0({{cxij_{q}__inj_d[767:512], cxij_{q}__inj_d[255:0]}})',
            f'.su_inj_d_r0({{cxij_{q}__inj_d[255:0], cxij_{q}__inj_d[767:512]}})')
    elif mut == 2:
        sub(f'cxdl_{q}1', f'.del_flit(hb_coll_{q}__del_flit[1089:545])', f'.del_flit(hb_coll_{q}__del_flit[1634:1090])')
    elif mut == 3:
        sub(f'cxrc_{q}', f'sfucore_{q}__ro_x_e[127:0], sfucore_{q}__ro_x_n[127:0]', f'sfucore_{q}__ro_x_n[127:0], sfucore_{q}__ro_x_e[127:0]')
    elif mut == 4:
        sub(f'cxij_{q}', f'.inj_q1(su_{q}1__inj_q[1023:0])', f'.inj_q1(su_{q}2__inj_q[1023:0])')
    return txt


def conn(die, inst, port):
    t = Path(die).read_text()
    i = t.index(f' {inst} (')
    m = re.search(r'\.' + port + r'\((.*)\),?\n', t[i:])
    return m.group(1)


def params(die, inst):
    t = Path(die).read_text()
    m = re.search(r'\n  [A-Za-z0-9_]+ #\((.*)\) ' + inst + r' \(', t)
    return dict(re.findall(r'\.([A-Za-z0-9_]+)\(([^()]*)\)', m.group(1))) if m else {}


def tb(q, die, meta):
    pij = params(die, f'cxij_{q}'); pcij = params(die, f'cij_{q}')
    # REFERENCE parameters come from the compiled slot, NOT from the die: behind the cij join (INJLAT) the SU inj_d register
    # must update at P+INJLAT-3 and addr bit 39 is the IDX-staging select (ot_hgi_coll_inj_idx_join.sv header)
    qid = pij.get('QID', '0'); injlat = pcij.get('INJLAT', '12'); b39 = '1'; iret = str(int(injlat) - 3)
    red_sel = conn(die, f'cxrc_{q}', 'red_sel')
    ins = meta['inputs']
    decl = '\n'.join(f' reg [{w - 1}:0] {n};' for n, w in ins.items())
    zero = ' '.join(f'{n}=0;' for n in ins)
    outs = {**meta['outputs'], **meta['observe']}
    wdecl = '\n'.join(f' wire [{w - 1}:0] {n};' for n, w in outs.items())
    ports = ', '.join(f'.{n}({n})' for n in list(ins) + list(outs))
    C = f'hb_coll_{q}__'
    pairs = [(f'obs__hb_coll_{q}__inj_d', 'r_ij'), (f'obs__hb_coll_{q}__rc_v', 'r_rcv'), (f'obs__hb_coll_{q}__rc_tag', 'r_rct'),
             (f'obs__hb_coll_{q}__rc_d', 'r_rcd'), (f'obs__sucore_{q}__rr_wv', 'r_rrv'), (f'obs__sucore_{q}__rr_wa', 'r_rra'),
             (f'obs__sucore_{q}__rr_wd', 'r_rrd'), (f'obs__sucore_{q}__sfu_x', 'r_sfu')]
    for k in range(4):
        pairs += [(f'obs__su_{q}{k}__dw_v', f'r_dwv[{2 * k + 1}:{2 * k}]'), (f'obs__su_{q}{k}__dw_row', f'r_dwr[{18 * k + 17}:{18 * k}]'),
                  (f'obs__su_{q}{k}__dw_d', f'r_dwd[{1024 * k + 1023}:{1024 * k}]'),
                  (f'obs__su_{q}{k}__inj_rd', 'r_crd'), (f'obs__su_{q}{k}__inj_addr', 'r_cad')]
    for a, _ in pairs:
        assert a in outs, a
    cmp = '\n'.join(f'  if({a}!=={b}) begin errors=errors+1; if(errors<8) $display("MISMATCH t=%0t {a}", $time); end' for a, b in pairs)
    dfault = ' | '.join([f'cxdl_{q}{k}__fault[0]' for k in range(4)] + [f'cxij_{q}__fault[0]', f'cxrc_{q}__fault[0]'])
    return f'''`timescale 1ps/1ps
`default_nettype none
// generated by tools/hbm_die_v16/d4g_wire_bench_sucx.py (HBM-WIRE 10-18): die slice slice_sucx_{q} vs the RTL composition.
module tb_d4g_wire_sucx;
 parameter integer NRST=3, EDGES=3000;
 localparam integer TS=1200, TP=900, T0=600;
 reg clk_q=0, clk_s=0;
 initial begin #(T0); forever begin clk_q=1; #(TS/2); clk_q=0; #(TS/2); end end
 initial begin #(T0); forever begin clk_s=1; #(TP/2); clk_s=0; #(TP/2); end end
{decl}
 initial begin {zero} end
 always @* begin hb_ckgen__pll_stream = clk_s; hb_ckgen__pll_serial = clk_q; end
 reg rst_n=0, por=0, active=0, viol=0, legal=0;
 always @* begin subr_{q}__bridge_rst_n = rst_n; hb_ckgen__por_stream = por; end
{wdecl}
 slice_sucx_{q} dut({ports});
 // ---------------- reference composition (RTL port contracts)
 wire [159:0] r_cad; wire [1:0] r_crd;
 ot_hgi_coll_inj_copy ref_cic(.clk(clk_s),.rst_n(por),.inj_addr_i({C}hgi_inj_addr),.inj_rd_i({C}inj_rd),.inj_addr_o(r_cad),.inj_rd_o(r_crd));
 wire [1023:0] r_sij, r_ij; wire r_rcv, r_rrv, r_f, r_jf; wire [2:0] r_rct; wire [255:0] r_rcd, r_rrd; wire [7:0] r_dwv;
 wire [71:0] r_dwr; wire [4095:0] r_dwd; wire [4:0] r_rra; wire [31:0] r_sfu;
 wire [11:0] r_red_sel = {red_sel};
 ot_hbm_su_static_cxport_split #(.QID({qid}),.B39_NOOP({b39}),.INJ_RET({iret})) ref_spl(.clk_s(clk_s),.clk_q(clk_q),.rst_n(rst_n),
  .inj_rd(r_crd),.inj_addr(r_cad),.inj_d(r_sij),.del_valid({C}del_valid),.del_flit({C}del_flit),.del_obase({C}hgi_del_obase),
  .rc_v(r_rcv),.rc_tag(r_rct),.rc_d(r_rcd),.rr_v({C}rr_v),.rr_tag({C}rr_tag),.rr_d({C}rr_d),
  .inj_q({{su_{q}3__inj_q, su_{q}2__inj_q, su_{q}1__inj_q, su_{q}0__inj_q}}),.dw_v(r_dwv),.dw_row(r_dwr),.dw_d(r_dwd),
  .red_sv(sucore_{q}__red_sv),.red_tag(sucore_{q}__red_tag),.red_x(sucore_{q}__red_x),.rr_wv(r_rrv),.rr_wa(r_rra),.rr_wd(r_rrd),
  .ro_v({{sfucore_{q}__ro_v_s, sfucore_{q}__ro_v_e, sfucore_{q}__ro_v_n, sfucore_{q}__ro_v_w}}),
  .ro_x({{sfucore_{q}__ro_x_s, sfucore_{q}__ro_x_e, sfucore_{q}__ro_x_n, sfucore_{q}__ro_x_w}}),
  .red_sel(r_red_sel),.sfu_x(r_sfu),.fault(r_f));
 ot_hgi_coll_inj_idx_join_rg_flat #(.INJLAT({injlat})) ref_join(.clk_r0(clk_s),.clk_r1(clk_s),.rst_n(por),.inj_rd(r_crd),
  .inj_idx({C}inj_idx),.inj_addr(r_cad),.su_inj_d(r_sij),.idx_tx_v(hb_idx__link__tx_v),.idx_tx(hb_idx__link__tx),.inj_d(r_ij),.fault(r_jf));
 // ---------------- stimulus (compiler calendar shape of tb_hbm_su_cxport_split; IDX tx as tb_hgi_coll_inj_idx_join_rg_lockstep)
 integer sph=0; always @(posedge clk_s) sph <= rst_n ? (sph+1)%4 : 0;
 function automatic [39:0] saddr(input integer g, input integer bad);
  reg [39:0] a; begin a=0; a[3]=$urandom; a[5:4]=g; a[6]=$urandom; a[15:7]=$urandom; a[17:16]={qid};
   if({b39} && ($urandom%5)==0) a[39]=1; if(bad) a[17:16]={qid}^1; saddr=a; end endfunction
 function automatic [39:0] daddr(input integer j, input integer bad);
  reg [39:0] a; begin a=0; a[5:4]=j; a[6]=$urandom; a[15:7]=$urandom; a[17:16]={qid}; if(bad) a[3:0]=1; daddr=a; end endfunction
 integer i;
 always @(negedge clk_s) begin
  if(active && (sph!=1 || viol)) begin   // the copy adds one edge: the leaves see phase sph+1 (never 2)
   {C}inj_rd=$urandom; for(i=0;i<4;i=i+1) begin {C}hgi_inj_addr[40*i+:40]=saddr($urandom%4, viol && ($urandom%50)==0); if(i%2) {C}hgi_inj_addr[40*i+39]=1'b0; end
  end else {C}inj_rd=0;
  if(active && (sph!=2 || viol)) begin
   {C}del_valid=$urandom;
   for(i=0;i<4;i=i+1) begin {C}hgi_del_obase[40*i+:40]=daddr(i, viol && ($urandom%50)==0);
    {C}del_flit[545*i+:545]={{1'b1,32'($urandom),{{16{{32'($urandom)}}}}}}; if(viol && ($urandom%60)==0) {C}del_flit[545*i+544]=0; end
   {C}rr_v=!legal && ($urandom%3)==0; {C}rr_tag=$urandom; for(i=0;i<8;i=i+1) {C}rr_d[32*i+:32]=$urandom;
   {{sfucore_{q}__ro_v_s,sfucore_{q}__ro_v_e,sfucore_{q}__ro_v_n,sfucore_{q}__ro_v_w}}=legal ? 16'd0 : 16'($urandom);
   for(i=0;i<4;i=i+1) begin sfucore_{q}__ro_x_w[32*i+:32]=$urandom; sfucore_{q}__ro_x_n[32*i+:32]=$urandom;
    sfucore_{q}__ro_x_e[32*i+:32]=$urandom; sfucore_{q}__ro_x_s[32*i+:32]=$urandom; end
  end else begin {C}del_valid=0; {C}rr_v=0; {{sfucore_{q}__ro_v_s,sfucore_{q}__ro_v_e,sfucore_{q}__ro_v_n,sfucore_{q}__ro_v_w}}=0; end
  if(active) begin
   {C}inj_idx=$urandom & 32'h00070007;
   for(i=0;i<2180;i=i+32) hb_idx__link__tx[i+:32]=$urandom;
   hb_idx__link__tx_v = ($urandom%8==0) ? 4'($urandom) : (($urandom%3==0) ? 4'hf : 4'h0);
   for(i=0;i<4;i=i+1) begin hb_idx__link__tx[i*545+544]=($urandom%50)!=0; if(($urandom%20)!=0) hb_idx__link__tx[i*545+512+:3]=3'(i+4*(sph%2)); end
  end else hb_idx__link__tx_v=0;
 end
 always @(negedge clk_q) begin
  if(active) begin
   for(i=0;i<32;i=i+1) begin su_{q}0__inj_q[32*i+:32]=$urandom; su_{q}1__inj_q[32*i+:32]=$urandom; su_{q}2__inj_q[32*i+:32]=$urandom; su_{q}3__inj_q[32*i+:32]=$urandom; end
   sucore_{q}__red_sv=!legal && ($urandom%3)==0; sucore_{q}__red_x=$urandom;
   sucore_{q}__red_tag=0; sucore_{q}__red_tag[9]=$urandom; sucore_{q}__red_tag[12:10]=$urandom; sucore_{q}__red_tag[13]=($urandom%4)==0;
   sucore_{q}__red_tag[16:14]=$urandom; sucore_{q}__red_tag[17]=$urandom; sucore_{q}__red_tag[22:18]=$urandom; sucore_{q}__red_tag[23]=$urandom;
   for(i=0;i<2422;i=i+32) pgp_{q}__command[i+:32]= legal ? 32'd0 : $urandom;
  end else begin sucore_{q}__red_sv=0; pgp_{q}__command=0; end
 end
 // ---------------- compare
 integer checks=0, errors=0, cmp=0, dwn=0, ijn=0, rcn=0, rrn=0, sfn=0, fn=0;
 always @(posedge clk_s or posedge clk_q) if(cmp) begin
  #1; checks=checks+1; dwn=dwn+((|r_dwv)===1'b1); ijn=ijn+((|r_ij)===1'b1); rcn=rcn+(r_rcv===1'b1); rrn=rrn+(r_rrv===1'b1);
  sfn=sfn+((|r_sfu)===1'b1); fn=fn+(r_f===1'b1);
{cmp}
  if(({dfault})!==r_f) begin errors=errors+1; if(errors<8) $display("MISMATCH t=%0t leaf faults %b ref %b", $time, ({dfault}), r_f); end
  if(cij_{q}__fault[0]!==r_jf) begin errors=errors+1; if(errors<8) $display("MISMATCH t=%0t cij fault", $time); end
 end
 integer k;
 initial begin
  repeat(6) @(posedge clk_s); por=1;
  for(k=0;k<NRST;k=k+1) begin
   rst_n=0; cmp=0; active=0; viol=(k==NRST-1); legal=(k==0);
   repeat(4) @(posedge clk_q);
   while((($time-T0)%(3*TS)) != 2*TS) @(posedge clk_q);
   #(TS-150); rst_n=1;
   repeat(2) @(negedge clk_q); cmp=1; active=1;
   repeat(EDGES) @(negedge clk_q);
   active=0; repeat(30) @(negedge clk_q);
  end
  if(errors==0 && checks>NRST*EDGES && dwn>0 && ijn>0 && rcn>0 && rrn>0 && sfn>0)
   $display("SUCX_WIRE PASS Q={q} MUT=%0d checks=%0d dw=%0d inj=%0d rc=%0d rr=%0d sfu=%0d fault_edges=%0d", `MUTN, checks, dwn, ijn, rcn, rrn, sfn, fn);
  else $display("SUCX_WIRE FAIL Q={q} MUT=%0d errors=%0d checks=%0d dw=%0d inj=%0d rc=%0d rr=%0d sfu=%0d fault_edges=%0d", `MUTN, errors, checks, dwn, ijn, rcn, rrn, sfn, fn);
  $finish;
 end
endmodule
`default_nettype wire
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--die', required=True); ap.add_argument('--contract', required=True)
    ap.add_argument('--q', required=True); ap.add_argument('--out', required=True); ap.add_argument('--mut', type=int, default=0)
    a = ap.parse_args()
    q = a.q; O = Path(a.out); O.mkdir(parents=True, exist_ok=True)
    sl = O / f'slice_sucx_{q}.sv'
    subprocess.run([sys.executable, str(H / 'd4g_die_slice.py'), '--die', a.die, '--contract', a.contract,
                    '--keep', f'(cic|cxij|cij|cxrc)_{q}|cxdl_{q}[0-3]', '--observe', f'hb_coll_{q}|su_{q}[0-3]|sucore_{q}',
                    '--top', f'slice_sucx_{q}', '--out', str(sl)], check=True)
    import json
    meta = json.loads(sl.with_suffix('.json').read_text())
    if a.mut:
        sl.write_text(mutate(sl.read_text(), q, a.mut))
    (O / 'tb_d4g_wire_sucx.sv').write_text(tb(q, a.die, meta))
    (O / 'files.txt').write_text('\n'.join(RTL) + '\n')
    (O / 'run.sh').write_text(f'''#!/bin/bash
# HBM-WIRE SUCX wiring bench Q={q} MUT={a.mut}: run from a source tree root (SRC) holding the RTL files of files.txt.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd); SRC=${{SRC:?SRC}}; cd "$SRC"
vl=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$vl" --version
"$vl" --binary --timing -j 8 -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN +define+MUTN={a.mut} --top-module tb_d4g_wire_sucx \\
  -Mdir "$here/obj" -o Vsucx "$here/tb_d4g_wire_sucx.sv" "$here/slice_sucx_{q}.sv" $(cat "$here/files.txt") > "$here/build.log" 2>&1 || {{ tail -30 "$here/build.log"; echo "SUCX_WIRE BUILD_FAIL Q={q} MUT={a.mut}"; exit 2; }}
"$here/obj/Vsucx" > "$here/run.log" 2>&1; rc=$?
grep -E "SUCX_WIRE|MISMATCH" "$here/run.log" | head -12
rm -rf "$here/obj"
grep -q "SUCX_WIRE PASS" "$here/run.log"
''')
    print('BENCH', O)


if __name__ == '__main__':
    main()
