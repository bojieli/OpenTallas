#!/usr/bin/env python3
"""mk_tb72.py (S81-RTLGAP/RG-IDX 10-21): the L2 index-transport bench on the 72-frame die RTL.

Generated from the reader bench of record rtl/dsrom_sys/s81_dv/idx/test/tb_dsdv_idx_rg3.sv (S81-IDX3R / S81-IDXRD):
same HBM model (ot_hdc_v41x_idx_hbm + per-PC adapters), same independent reference engine, same selector V-ingress
decode and word checks, same slice-traffic / slot-hit checks, same plusargs.  Only the DUT section changes: instead of
8 readers + 16 controllers wired by bench delay lines (tb_idx3_dly, SD 3..18 / XD 21), the DUT is idx72_top, cut
VERBATIM from the G3 die netlist (claude/s81-die72-g3-1021 die.v) by tools/s81_dv/dv_slice_cut.py: u_iqf, u_irg_00..07,
u_ctrl_00..15 and every relay station / landing / forwarded-clock cell / reset station of their die lanes:
  query  : bench -> i__w_iq_src_l{0,1}_src (= s_3S iq output register) -> 45 stations -> landing -> iqf qs ->
           iqf (type-4 job frames pass, 3 edges) -> qr -> 35/36 stations -> landing -> irg_00 qi -> reader chain
           (iq_03_04 W->E: 0/1 station + landing)
  scores : irg_07 so -> is_tail 41 stations -> landing at the bk_sel vi_idx pin -> o__w_is_tail_lnd -> bench decode
  HBM    : irg_p rqo -> hrrq_{2p,2p+1} (70..74 stations) -> ctrl rrq landing; ctrl rrd -> hrrd (71..74) -> reader rri
           landing; ctrl k_* / kr_* = the PHY face (bench HBM model, as the record bench)
  svc    : i__w_hrq_k_src (= rsv_k rq output register) -> 4 stations -> landing -> ctrl rq; ctrl rd -> hrd -> rsv landing
           (o__w_hrd_k_lnd; 2 unlanded lanes o__w_hrd_k_src)
Checks added: every landing fault bit of the slice (o__land_fault) and the iqf status stay 0; the qo forwarding check of
the record bench is dropped (the chain end irg_07 is dsdv_idx_rg3_nq: no qo on the die).
Usage: mk_tb72.py <tb_dsdv_idx_rg3.sv> <slice_ports.json> <out tb_idx72.sv>
"""
import json
import re
import sys

src, ports_f, out = sys.argv[1:4]
t = open(src).read()
P = json.load(open(ports_f))['ports']
a = t.index('    // ------------------------------------------------------------------ DUT chain')
b = t.index('    // ------------------------------------------------------------------ PC adapters + HBM model')
R = 16
hrd = {}
for k in range(R):
    for suf in ('lnd', 'src'):
        n = f'o__w_hrd_{k:02d}_{suf}'
        if n in P:
            hrd[k] = n
    assert k in hrd, k
    assert f'i__w_hrq_{k:02d}_src' in P, k
dut = ['    // ------------------------------------------------------------------ DUT: idx72_top (cut from the G3 die netlist)',
       '    reg  [512:0] qin = 0;',
       '    wire [275:0] s_tail;                    // is_tail at the bk_sel vi_idx landing',
       '    wire [561:0] rd_c [0:R-1], rd_s [0:R-1];',
       '    wire [9:0]   st [0:NRD-1];',
       '    reg  [681:0] rq_tb [0:R-1];',
       '    wire [227:0] land_fault; wire [3:0] iqf_st; wire [512:0] iqf_qc0, iqf_qc1;',
       '    wire [31:0] k_v, k_rdy, k_we, k_wr_done, kr_v, kr_rdy;',
       '    wire [32*30-1:0] k_addr; wire [32*4-1:0] k_len, kr_beat; wire [32*17-1:0] k_tag, kr_tag;',
       '    wire [32*256-1:0] k_wdata, kr_data; wire [32*32-1:0] k_wstrb;']
conn = []
for n, p in P.items():
    if p['kind'] == 'clock':
        conn.append(f'.{n}(ck)')
    elif n == 'i__ck_hbm':
        conn.append(f'.{n}(ckh)')
    elif n == 'i__rst_n':
        conn.append(f'.{n}(rst)')
    elif n == 'i__iqf_ql':
        conn.append(f'.{n}(513\'d0)')          # parent tree link: a single-die L2 shard has no parent (die pad)
    elif n == 'i__w_iq_src_l0_src':
        conn.append(f'.{n}(qin[275:0])')
    elif n == 'i__w_iq_src_l1_src':
        conn.append(f'.{n}({{39\'d0, qin[512:276]}})')
    elif n == 'o__w_is_tail_lnd':
        conn.append(f'.{n}(s_tail)')
    elif (m := re.fullmatch(r'i__w_hrq_(\d\d)_src', n)):
        conn.append(f'.{n}(rq_tb[{int(m.group(1))}])')
    elif (m := re.fullmatch(r'o__w_hrd_(\d\d)_(lnd|src)', n)):
        conn.append(f'.{n}(rd_c[{int(m.group(1))}])')
    elif (m := re.fullmatch(r'o__irg_(\d\d)_st', n)):
        conn.append(f'.{n}(st[{int(m.group(1))}])')
    elif (m := re.fullmatch(r'[io]__a_phy_hbm_(\w+)', n)):
        conn.append(f'.{n}({m.group(1)})')
    elif n in ('o__land_fault', 'o__iqf_st', 'o__iqf_qc0', 'o__iqf_qc1'):
        conn.append(f'.{n}({n[3:]})')
    elif p['dir'] == 'output':
        conn.append(f'.{n}()')                 # reset-tree branches leaving the slice (rs_*, rsg_*, rsl_*)
    else:
        raise SystemExit(f'unmapped input port {n}')
dut.append('    idx72_top u_die (' + ', '.join(conn) + ');')
dut.append('    generate for (genvar r = 0; r < R; r = r + 1) begin : g_rs assign rd_s[r] = rd_c[r]; end endgenerate')
dut.append('')
t = t[:a] + '\n'.join(dut) + '\n' + t[b:]
# decode the die's is_tail landing instead of the record chain end
t = t.replace('.dl_nv(sch[NRD][0]),\n        .dl_n(sch[NRD])', '.dl_nv(s_tail[0]),\n        .dl_n(s_tail)')
assert 's_tail[0]' in t
# qo forwarding check: no chain-end qo on the die
qa = t.index('    // ------------------------------------------------------------------ qo forwarding check')
qb = t.index('    // ------------------------------------------------------------------ slice traffic')
t = t[:qa] + '    integer qerr = 0;   // (record qo forwarding check dropped: the die chain end irg_07 has no qo)\n\n' + t[qb:]
# the die reset tree is deep (reset stations): settle before the reference / slice phases
t = t.replace('        rst = 1;\n        repeat (40) @(posedge ck);', '        rst = 1;\n        repeat (400) @(posedge ck);')
# window wait: + the die lane latency (iq_src 45 + iq_qf 36 + is_tail 41 stations, landings, 2 x 74 HBM lane stations)
t = t.replace('P * nw + 200 && lw_n[0] <= nw)', 'P * nw + 900 && lw_n[0] <= nw)')
# landing faults + iqf status
t = t.replace('        if (vin_f) begin fail = 1;',
              '        if (|land_fault) begin fail = 1; $display("TB_IDXRD die landing fault %h", land_fault); end\n'
              '        if (iqf_st != 4\'d0) begin fail = 1; $display("TB_IDXRD iqf status %b", iqf_st); end\n'
              '        if (vin_f) begin fail = 1;')
t = t.replace('module tb_dsdv_idx_rg3;', 'module tb_idx72;')
t = '// GENERATED by results/rtl/s81_rtlgap_idx_1021/mk_tb72.py from tb_dsdv_idx_rg3.sv -- do not edit\n' + t
for bad in ('qch[', 'sch[', 'tb_idx3_dly #'):
    assert bad not in t.split('// registered hops')[0], bad
open(out, 'w').write(t)
print('mk_tb72: ports', len(P), '->', out)
