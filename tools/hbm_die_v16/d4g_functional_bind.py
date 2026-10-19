#!/usr/bin/env python3
"""HBM-WIRE 10-18: FUNCTIONAL connectivity check of the d4g die contract (complements the strict port bind).

The strict port bind (DIE_PORT_BIND) proves every input port has SOME producer and every port exists in RTL.  It does not
prove that a command/data consumer is driven by the producer the compiler schedules for it.  This check does: for every
compiled command/data path below (producer block.port -> consumer block.port, width, schedule slot) every consumer bit
must be driven -- directly or through die relays / landings (i -> o, same bit) -- by exactly the named producer bit.

    d4g_functional_bind.py CONTRACT.json[.gz] [--report R.json] [--spec-out SPEC.json] [--gaps strict|warn]

PATHS (one class per TOKEN-PASS-HBMDS gap; the producer/consumer pairs and slots come from the RTL headers named):
  INJ   G-CIL-INJ   hb_coll_<q>.inj_rd/hgi_inj_addr -> cic_<q> (ot_hgi_coll_inj_copy, +1 edge) -> cxij_<q> + cij_<q> + su_<q><k>;
                    su_<q><k>.inj_q -> cxij_<q>.inj_q<k>; cxij_<q>.inj_d -> cij_<q>.su_inj_d_r0/r1 (region split
                    r<r>[j*256+:256] = d[512j+256r+:256]); cij_<q>.inj_d_r<r> -> hb_coll_<q>.inj_d (same split);
                    hb_coll_<q>.inj_idx -> cij_<q>.inj_idx(_r1); hb_idx__link.tx(_v) -> cij_<q>.idx_tx_*.
                    Slot: inj_d answers INJLAT = 12 edges after inj_rd (cij #(INJLAT 12); SU word at P+9, cxij INJ_RET 9).
  DEL   G-CIL-DEL   hb_coll_<q>.del_valid[g]/del_flit[545g+:545]/hgi_del_obase[40g+:40] -> cxdl_<q><g>;
                    cxdl_<q><g>.dw_v/dw_row/dw_d -> su_<q><g>.dw_* (ot_hbm_su_static_cxport_split (c): lane g -> slice g).
  RC    G-CIL-RC    cxrc_<q>.rc_v/rc_tag/rc_d -> hb_coll_<q>.rc_*; hb_coll_<q>.rr_* -> cxrc_<q>.rr_*;
                    sucore_<q>.red_sv/red_tag/red_x -> cxrc_<q>; cxrc_<q>.rr_wv/rr_wa/rr_wd/sfu_x -> sucore_<q>;
                    sfucore_<q>.ro_v_/ro_x_{w,n,e,s} -> cxrc_<q>.ro_v/ro_x (faces w,n,e,s low to high).
  XCMD  G-SMVM-XCMD xc_<q><k>.cmd_ext[108:0] -> sm_<q><k>.command[191:83]; svg_<q><k>.sm_command -> sm.command[82:0];
                    xc.kv_desc -> sm.kv_desc; svg.sm_packet -> sm.packet; x-load issuer xl_<x>_ctl -> aq trees ->
                    xq_<x>_p<p>_{bd,bfq<i>,eg} -> sm.xw_* (SM k<4 of quadrant q from xq_<q>, k>=4 from the east
                    quadrant's xq; pair p = (k % 4) // 2).  Static: no x_rdy (ot_hgi_sm_xload_cl2_ctlx own calendar).
  HC    G-HC-ENG/G-HC hc_eng (ot_hbm_hc_root_static) <-> hc_<q> (ot_hbm_hc_qhub_static = hc_q + quarter centre):
                    qd_*/qi_* quarter q -> d_*/i_*; ps_v/ps/ps_f/eng_fault/gathered_mix_* -> qps*/q_fault/gathered_*;
                    result_v/result_position/result[768q+:768] -> hc_<q>.result*; centre -> bank ring hcb_<q>0..7
                    (bd_* -> bank 0 d_*, bank k o_*/sum_out/f_out -> bank k+1, chain exit hcb_<q>0.s_o -> hc_<q>.s_i,
                    x-wave slices xb_d<k>).  The quarter engine (root + 4 x (centre + 8 banks)) IS the HC engine.
  SFUJ  G-SFU-OPERAND-JOIN-<q> sfus_<q>.l<nn>_vi_q -> sfucore_<q>.vi_q_<face> (lanes 4f..4f+3 on face f = w,n,e,s).
  DMA   G-DMA/G-DMA-WB hb_dbk_<q>.wb_*/wd -> wbk_<q>; wbk_<q>.wb_ready/wa -> hb_dbk_<q> (write-back partner).
  LAT   G-VM-BANKLAT (HBM-BANKLAT 10-19, coordinator decision on the VEH-TOPKFIX2 audit): every fixed-latency VM bank
                    client's round-trip parameter == bank contract (read 6 / commit 3, + 1 when the bank master pin-
                    registers its inputs) + the die lane edges on its rq and rr lanes, EQUAL over every bank it reads
                    (d4g_bank_latency.py: rule table, landing latency ceil(N/2)+1+E with E from the K straps).
                    --lat strict (default) fails the bind on any mismatch; --lat warn reports it (physical-only
                    stand-in iterations; never for a qualifying GEN).
Every gap id the contract still lists whose paths ALL pass here is reported STALE (the netlist closed it, the contract's
gap list was never pruned -> layer_coverage.py grades the layer BLOCKED on a closed gap).  --gaps strict fails on that.
Output line: FUNCTIONAL_BIND PASS|FAIL paths=N bits=B fail_paths=F stale_gaps=S open_gaps=O.
"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import d4g_bank_latency

QS = ('SW', 'SE', 'NW', 'NE')
EAST = {'SW': 'SE', 'NW': 'NE'}
RELAY = re.compile(r'^hbfd_(rly|lh0?|lnd|land)[A-Za-z0-9_]*$')   # lane relays (i -> o) / landing hops + landings (a -> b), same bit
THRU = {'o': 'i', 'b': 'a'}


def P(gap, cls, kind, src, dst, w, slot='', note='', stages=None):
    """src/dst = (inst, port, lo); stages = (inst, param, default): the die relay stages on the path must equal that
    compiler-visible parameter (e.g. hc_eng XRD / XRU)."""
    return dict(gap=gap, cls=cls, kind=kind, src=list(src), dst=list(dst), w=w, slot=slot, note=note, stages=stages)


def spec():
    S = []
    for q in QS:
        g = 'G-CIL-INJ'
        S.append(P(g, 'INJ', 'cmd', (f'hb_coll_{q}', 'inj_rd', 0), (f'cic_{q}', 'inj_rd_i', 0), 2, 'P'))
        S.append(P(g, 'INJ', 'cmd', (f'hb_coll_{q}', 'hgi_inj_addr', 0), (f'cic_{q}', 'inj_addr_i', 0), 160, 'P'))
        for d, port in ((f'cxij_{q}', 'inj_rd'), (f'cij_{q}', 'inj_rd'), (f'cij_{q}', 'inj_rd_r1')):
            S.append(P(g, 'INJ', 'cmd', (f'cic_{q}', 'inj_rd_o', 0), (d, port, 0), 2, 'P+1 (INJ_COPY_EDGES 1)'))
        for d, port in ((f'cxij_{q}', 'inj_addr'), (f'cij_{q}', 'inj_addr'), (f'cij_{q}', 'inj_addr_r1')):
            S.append(P(g, 'INJ', 'cmd', (f'cic_{q}', 'inj_addr_o', 0), (d, port, 0), 160, 'P+1'))
        for k in range(4):
            S.append(P(g, 'INJ', 'cmd', (f'cic_{q}', 'inj_rd_o', 0), (f'su_{q}{k}', 'inj_rd', 0), 2, 'P+1'))
            S.append(P(g, 'INJ', 'cmd', (f'cic_{q}', 'inj_addr_o', 0), (f'su_{q}{k}', 'inj_addr', 0), 160, 'P+1'))
            S.append(P(g, 'INJ', 'data', (f'su_{q}{k}', 'inj_q', 0), (f'cxij_{q}', f'inj_q{k}', 0), 1024, 'SU port-5 word, P+9'))
        for p in ('inj_idx', 'inj_idx_r1'):
            S.append(P(g, 'INJ', 'cmd', (f'hb_coll_{q}', 'inj_idx', 0), (f'cij_{q}', p, 0), 32, 'P'))
        for r in (0, 1):
            for j in (0, 1):
                S.append(P(g, 'INJ', 'data', (f'cxij_{q}', 'inj_d', 512 * j + 256 * r), (f'cij_{q}', f'su_inj_d_r{r}', 256 * j),
                           256, 'SU answer (cxij INJ_RET 9)', 'region split r<r>[j*256+:256] = d[512j+256r+:256]'))
                S.append(P(g, 'INJ', 'data', (f'cij_{q}', f'inj_d_r{r}', 256 * j), (f'hb_coll_{q}', 'inj_d', 512 * j + 256 * r),
                           256, 'P+INJLAT 12', 'region split'))
        for a in range(4):
            for r in (0, 1):
                for p in (f'idx_tx_r{r}',):
                    S.append(P(g, 'INJ', 'data', ('hb_idx__link', 'tx', a * 545 + 256 * r), (f'cij_{q}', p, a * 256), 256,
                               'IDX tx flit a', 'idx_tx_r<r>[a*256+:256] = tx[a*545+256r+:256]'))
            for p in ('idx_tx_h', 'idx_tx_h_r1'):
                S.append(P(g, 'INJ', 'cmd', ('hb_idx__link', 'tx', a * 545 + 512), (f'cij_{q}', p, a * 33), 33, 'IDX tx header'))
        for p in ('idx_tx_v', 'idx_tx_v_r1'):
            S.append(P(g, 'INJ', 'cmd', ('hb_idx__link', 'tx_v', 0), (f'cij_{q}', p, 0), 4, 'IDX tx valid'))
        g = 'G-CIL-DEL'
        for k in range(4):
            S.append(P(g, 'DEL', 'cmd', (f'hb_coll_{q}', 'del_valid', k), (f'cxdl_{q}{k}', 'del_valid', 0), 1, 'D'))
            S.append(P(g, 'DEL', 'data', (f'hb_coll_{q}', 'del_flit', 545 * k), (f'cxdl_{q}{k}', 'del_flit', 0), 545, 'D'))
            S.append(P(g, 'DEL', 'cmd', (f'hb_coll_{q}', 'hgi_del_obase', 40 * k), (f'cxdl_{q}{k}', 'del_obase', 0), 40, 'D'))
            for p, w in (('dw_v', 2), ('dw_row', 18), ('dw_d', 1024)):
                S.append(P(g, 'DEL', 'data' if p == 'dw_d' else 'cmd', (f'cxdl_{q}{k}', p, 0), (f'su_{q}{k}', p, 0), w,
                           'serial slot of the delivery (cxport (c))'))
        g = 'G-CIL-RC'
        for p, w in (('rc_v', 1), ('rc_tag', 3), ('rc_d', 256)):
            S.append(P(g, 'RC', 'data', (f'cxrc_{q}', p, 0), (f'hb_coll_{q}', p, 0), w, 'RED_CARRY'))
        for p, w in (('rr_v', 1), ('rr_tag', 3), ('rr_d', 256)):
            S.append(P(g, 'RC', 'data', (f'hb_coll_{q}', p, 0), (f'cxrc_{q}', p, 0), w, 'reduce result'))
        for p, w in (('red_sv', 1), ('red_tag', 32), ('red_x', 32)):
            S.append(P(g, 'RC', 'data', (f'sucore_{q}', p, 0), (f'cxrc_{q}', p, 0), w, 'SU reducer'))
        for p, w in (('rr_wv', 1), ('rr_wa', 5), ('rr_wd', 256), ('sfu_x', 32)):
            S.append(P(g, 'RC', 'data', (f'cxrc_{q}', p, 0), (f'sucore_{q}', p, 0), w, 'serial write-back'))
        for f, face in enumerate('wnes'):
            S.append(P(g, 'RC', 'cmd', (f'sfucore_{q}', f'ro_v_{face}', 0), (f'cxrc_{q}', 'ro_v', 4 * f), 4, 'SFU reducer operand'))
            S.append(P(g, 'RC', 'data', (f'sfucore_{q}', f'ro_x_{face}', 0), (f'cxrc_{q}', 'ro_x', 128 * f), 128, 'SFU reducer operand'))
        g = f'G-SFU-OPERAND-JOIN-{q}'
        for f, face in enumerate('wnes'):
            for i in range(4):
                S.append(P(g, 'SFUJ', 'data', (f'sfus_{q}', f'l{4 * f + i:02d}_vi_q', 0), (f'sfucore_{q}', f'vi_q_{face}', 32 * i),
                           32, 'indexed-address read'))
        g = 'G-DMA-WB'
        for p, w in (('wb_reserve_v', 1), ('wb_reserve_bank', 1), ('wb_fill_bank', 1), ('wb_reserve_epoch', 16),
                     ('wb_fill_epoch', 16), ('wb_reserve_sectors', 12), ('wb_reserve_base', 32), ('wb_fill_start', 1), ('wd', 2312)):
            S.append(P(g, 'DMA', 'data' if p == 'wd' else 'cmd', (f'hb_dbk_{q}', p, 0), (f'wbk_{q}', p, 0), w, 'DMA write-back band'))
        S.append(P(g, 'DMA', 'cmd', (f'wbk_{q}', 'wb_ready', 0), (f'hb_dbk_{q}', 'wb_ready', 0), 1, 'WB partner'))
        S.append(P(g, 'DMA', 'cmd', (f'wbk_{q}', 'wa', 0), (f'hb_dbk_{q}', 'wa', 0), 12, 'posted sectors'))
        # HC: root <-> quadrant hub <-> bank ring
        g = 'G-HC-ENG'
        qi = QS.index(q)
        for p, rp, w in (('d_v', 'qd_v', 1), ('d_ss', 'qd_ss', 1), ('d_nv', 'qd_nv', 7), ('d_wa', 'qd_wa', 10), ('d_xa', 'qd_xa', 10),
                         ('i_v', 'qi_v', 1), ('i_kind', 'qi_kind', 1), ('i_slot', 'qi_slot', 2), ('i_lo', 'qi_lo', 5),
                         ('i_w', 'qi_w', 5), ('i_cnt', 'qi_cnt', 12), ('i_word', 'qi_word', 10)):
            S.append(P(g, 'HC', 'cmd', ('hc_eng', rp, w * qi), (f'hc_{q}', p, 0), w, 'root -> quarter (XRD relays)',
                       stages=('hc_eng', 'XRD', 0)))
        for p, rp, w in (('ps_v', 'qps_v', 1), ('ps', 'qps', 32), ('ps_f', 'qps_f', 1), ('eng_fault', 'q_fault', 1),
                         ('gathered_mix_v', 'gathered_mix_v', 1), ('gathered_mix_row', 'gathered_mix_row', 5),
                         ('gathered_mix_pos', 'gathered_mix_pos', 3), ('gathered_mix_data', 'gathered_mix_data', 32)):
            S.append(P(g, 'HC', 'data', (f'hc_{q}', p, 0), ('hc_eng', rp, w * qi), w, 'quarter -> root (XRU relays)',
                       stages=('hc_eng', 'XRU', 0)))
        for p, rp, w in (('result_v', 'result_v', 1), ('result_position', 'result_position', 3), ('result', 'result', 768)):
            S.append(P(g, 'HC', 'data', ('hc_eng', rp, w * qi), (f'hc_{q}', p, 0), w, 'tail result -> VM store'))
        for p, w in (('v', 1), ('ss', 1), ('nv', 7), ('wa', 10), ('xa', 10)):
            S.append(P(g, 'HC', 'cmd', (f'hc_{q}', f'bd_{p}', 0), (f'hcb_{q}0', f'd_{p}', 0), w, 'descriptor chain head'))
            for k in range(7):
                S.append(P(g, 'HC', 'cmd', (f'hcb_{q}{k}', f'o_{p}', 0), (f'hcb_{q}{k + 1}', f'd_{p}', 0), w, 'descriptor chain'))
        for k in range(7):
            S.append(P(g, 'HC', 'data', (f'hcb_{q}{k}', 'sum_out', 0), (f'hcb_{q}{k + 1}', 'sum_in', 0), 2048, 'partial-sum chain'))
            S.append(P(g, 'HC', 'cmd', (f'hcb_{q}{k}', 'f_out', 0), (f'hcb_{q}{k + 1}', 'f_in', 0), 1, 'fault chain'))
        S.append(P(g, 'HC', 'data', (f'hcb_{q}0', 's_o', 0), (f'hc_{q}', 's_i', 0), 2049, 'chain exit -> centre subtree'))
        for k, face in ((0, ''), (2, '_n'), (4, '_e'), (6, '_s')):   # direct banks: own slice xb_d<k>
            S.append(P(g, 'HC', 'data', (f'hc_{q}', f'xb_d{k}', 0), (f'hcb_{q}{k}', 'xb_d', 0), 256, 'x-wave beat slice'))
            S.append(P(g, 'HC', 'cmd', (f'hc_{q}', f'xb_v{face}', 0), (f'hcb_{q}{k}', 'xb_v', 0), 1, 'x-wave beat'))
        for k, c in ((2, 'a'), (2, 'b'), (6, 'a'), (6, 'b')):           # corner banks through the edge tile feed
            kk = {('2', 'a'): 1, ('2', 'b'): 3, ('6', 'a'): 5, ('6', 'b'): 7}[(str(k), c)]
            S.append(P(g, 'HC', 'data', (f'hc_{q}', f'xb_d{kk}', 0), (f'hcb_{q}{k}', f'f{c}_xb_d', 0), 256, 'corner x-wave slice (+1)'))
            S.append(P(g, 'HC', 'data', (f'hcb_{q}{k}', f'f{c}_xb_d_o', 0), (f'hcb_{q}{kk}', 'xb_d', 0), 256, 'corner feed'))
    # XCMD: SM command / KV descriptor / packet / x-load words (SMs live in SW and NW; k >= 4 fed by the east quadrant's xq)
    for q in ('SW', 'NW'):
        for k in range(8):
            g = 'G-SMVM-XCMD'
            S.append(P(g, 'XCMD', 'cmd', (f'xc_{q}{k}', 'cmd_ext', 0), (f'sm_{q}{k}', 'command', 83), 109, 'xcal run edge = svg run edge'))
            S.append(P(g, 'XCMD', 'cmd', (f'svg_{q}{k}', 'sm_command', 0), (f'sm_{q}{k}', 'command', 0), 83, 'svg issuer'))
            S.append(P(g, 'XCMD', 'cmd', (f'xc_{q}{k}', 'kv_desc', 0), (f'sm_{q}{k}', 'kv_desc', 0), 64, 'KV descriptor'))
            S.append(P(g, 'XCMD', 'data', (f'svg_{q}{k}', 'sm_packet', 0), (f'sm_{q}{k}', 'packet', 0), 1099, 'K packet'))
            x = q if k < 4 else EAST[q]
            pr = (k % 4) // 2
            for p, w in (('xw_en', 1), ('xw_addr', 7), ('xw_grp', 7), ('xw_data', 2048)):
                S.append(P(g, 'XCMD', 'data' if p == 'xw_data' else 'cmd', (f'xq_{x}_p{pr}_eg', p, 0), (f'sm_{q}{k}', p, 0), w,
                           'x-load write port'))
    for x in QS:
        g = 'G-SMVM-XCMD'
        for h in ('lo', 'hi'):
            S.append(P(g, 'XCMD', 'cmd', (f'xl_{x}_ctl', f'qv_{h}', 0), (f'xl_{x}_aq{h}', 'v', 0), 1, 'x quantiser issue'))
            S.append(P(g, 'XCMD', 'data', (f'xl_{x}_ctl', 'l_d_o', 0 if h == 'lo' else 1024), (f'xl_{x}_aq{h}', 'x', 0), 1024, 'x words'))
        for pr in (0, 1):
            for p, w in (('ed5', 8), ('ede', 17)):
                S.append(P(g, 'XCMD', 'cmd', (f'xl_{x}_ctl', f'eg_{p}', 0), (f'xq_{x}_p{pr}_eg', p, 0), w, 'egress schedule'))
            for p, cp, w in (('bq_v', 'eg_bqv', 1), ('bq_last', 'eg_bqlast', 1), ('bq_addr', 'eg_bqaddr', 7), ('bq_b', 'eg_bqb', 7)):
                S.append(P(g, 'XCMD', 'cmd', (f'xl_{x}_ctl', cp, 0), (f'xq_{x}_p{pr}_eg', p, 0), w, 'egress schedule'))
            S.append(P(g, 'XCMD', 'data', (f'xq_{x}_p{pr}_bd', 'bq_d', 0), (f'xq_{x}_p{pr}_eg', 'bq_d', 0), 2048, 'quantised x'))
            for h in ('lo', 'hi'):
                S.append(P(g, 'XCMD', 'data', (f'xl_{x}_aq{h}', 'q', 0), (f'xq_{x}_p{pr}_bd', f'qq_{h}', 0), 256, 'quantised x'))
                S.append(P(g, 'XCMD', 'data', (f'xl_{x}_aq{h}', 'e', 0), (f'xq_{x}_p{pr}_bd', f'qe_{h}', 0), 10, 'block exponents'))
            for i in range(4):
                S.append(P(g, 'XCMD', 'data', (f'xl_{x}_ctl', 'c_d', 0), (f'xq_{x}_p{pr}_bfq{i}', 'c_d', 0), 1024, 'x words to bfq'))
                S.append(P(g, 'XCMD', 'data', (f'xq_{x}_p{pr}_bfq{i}', 'rwq', 0), (f'xq_{x}_p{pr}_eg', 'rwq', 256 * i), 256, 'raw x'))
    return S


def param_rules():
    """Schedule-slot rules between producer/consumer parameters (the same compiled slot seen from both ends)."""
    R = []
    for q in QS:
        R.append(dict(gap='G-CIL-INJ', cls='INJ', id=f'INJ_RET.{q}', inst=f'cxij_{q}', param='INJ_RET',
                      expect=('cij', f'cij_{q}', 'INJLAT', -3),
                      why='ot_hgi_coll_inj_idx_join: the SU must update its inj_d register at P+INJLAT-3 (P+9 for INJLAT 12)'))
        R.append(dict(gap='G-CIL-INJ', cls='INJ', id=f'B39_NOOP.{q}', inst=f'cxij_{q}', param='B39_NOOP', expect=('const', 1),
                      why='addr_lo[39]=1 selects the cij IDX staging; bit 39 is reserved in the SU space (no SU read, no fault)'))
    return R


def check_params(c, R):
    I = c['instances']; out = []
    for r in R:
        x = dict(r, status='PASS', bad=[])
        if r['inst'] not in I:
            x['status'] = 'FAIL'; x['bad'].append(f'{r["inst"]} missing'); out.append(x); continue
        have = I[r['inst']].get('params', {}).get(r['param'])
        e = r['expect']
        if e[0] == 'const':
            want = e[1]
        else:
            ref = I.get(e[1])
            want = None if ref is None else ref.get('params', {}).get(e[2])
            want = None if want is None else int(want) + e[3]
        x['have'], x['want'] = have, want
        if want is None or have is None or int(have) != int(want):
            x['status'] = 'FAIL'; x['bad'].append(f'{r["inst"]}.{r["param"]} = {have}, slot needs {want} ({r["why"]})')
        out.append(x)
    return out


def load(f):
    return json.load(gzip.open(f) if str(f).endswith('.gz') else open(f))


def check(c, S):
    I = c['instances']
    drv = {}
    for e in c['edges']:
        si, sp, slo, shi = e['source']; ki, kp, klo, khi = e['sink']   # bit ranges are [lo, hi)
        assert shi - slo == khi - klo, e
        for b in range(khi - klo):
            drv[(ki, kp, klo + b)] = (si, sp, slo + b)
    strap = set()
    for s in c.get('straps', []):
        for b in range(s['lo'], s['hi']):
            strap.add((s['inst'], s['port'], b))

    landed = [False]

    def trace(i, p, b):
        st = 0
        while True:
            d = drv.get((i, p, b))
            if d is None:
                return ('STRAP' if (i, p, b) in strap else None), st
            si, sp, sb = d
            m = I.get(si, {}).get('master', '')
            if RELAY.match(m) and sp in THRU:
                if not m.startswith('hbfd_rly'):
                    landed[0] = True
                i, p, b = si, THRU[sp], sb; st += 1; continue
            return d, st
    res = []
    for x in S:
        si, sp, slo = x['src']; di, dp, dlo = x['dst']; w = x['w']
        r = dict(x, status='PASS', relay_stages=None, bad=[])
        for inst, port, lo, role in ((si, sp, slo, 'producer'), (di, dp, dlo, 'consumer')):
            if inst not in I:
                r['status'] = 'FAIL'; r['bad'].append(f'{role} instance {inst} missing'); continue
            pd = I[inst]['ports'].get(port)
            if pd is None:
                r['status'] = 'FAIL'; r['bad'].append(f'{role} port {inst}.{port} missing')
            elif lo + w > pd['bits']:
                r['status'] = 'FAIL'; r['bad'].append(f'{role} {inst}.{port}[{lo}+:{w}] beyond {pd["bits"]} b')
        if r['status'] == 'PASS':
            wrong = collections.Counter(); stages = set(); nbad = 0; landed[0] = False
            for b in range(w):
                d, st = trace(di, dp, dlo + b)
                if d == (si, sp, slo + b):
                    stages.add(st); continue
                nbad += 1
                wrong['undriven' if d is None else 'strap' if d == 'STRAP' else f'{d[0]}.{d[1]}'] += 1
            if nbad:
                r['status'] = 'FAIL'
                r['bad'].append(f'{nbad}/{w} consumer bits not from {si}.{sp}[{slo}+:{w}]: ' +
                                ', '.join(f'{k}:{v}' for k, v in wrong.most_common(4)))
            r['relay_stages'] = sorted(stages)
            r['landed'] = landed[0]
            if landed[0]:
                # half-cycle hops + landing: the latency is the land plan's (equal-age padding at the landing), not a
                # stage count -> slot rules are checked by the land plan / landing lockstep (HBM-LANDING), not here
                pass
            elif len(stages) > 1:
                r['status'] = 'FAIL'; r['bad'].append(f'unequal relay stages across bits {sorted(stages)}')
            if x.get('stages') and stages and not landed[0]:
                pi, pn, dflt = x['stages']
                want = int(I.get(pi, {}).get('params', {}).get(pn, dflt))
                if stages != {want}:
                    r['status'] = 'FAIL'; r['bad'].append(f'relay stages {sorted(stages)} != {pi}.{pn} = {want} (compiled slot)')
        res.append(r)
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('contract'); ap.add_argument('--report'); ap.add_argument('--spec-out')
    ap.add_argument('--gaps', choices=('strict', 'warn'), default='strict')
    ap.add_argument('--lat', choices=('strict', 'warn', 'off'), default='strict',
                    help='LAT class (bank-client latency): strict fails the bind on a mismatch')
    a = ap.parse_args()
    S = spec()
    if a.spec_out:
        Path(a.spec_out).write_text(json.dumps({'schema': 'opentallas.d4g_functional_paths.v1', 'paths': S}, indent=0))
    c = load(a.contract)
    res = check(c, S)
    pres = check_params(c, param_rules())
    for x in pres:   # a param rule counts as a 0-bit path of its class
        res.append(dict(x, src=[x['inst'], x['param'], 0], dst=[x['inst'], x['param'], 0], w=0, relay_stages=[], kind='slot'))
    lat_rows = []
    if a.lat != 'off':
        lat_rows, lat_sum = d4g_bank_latency.check(c)
        for r in lat_rows:
            if r['status'] == 'INFO':
                continue
            st = r['status'] if a.lat == 'strict' else 'PASS'
            res.append(dict(gap='G-VM-BANKLAT', cls='LAT', kind='latency', src=[r['client'], r['port'], 0],
                            dst=[r['client'], r.get('param', '-'), 0], w=0, relay_stages=[], status=st, bad=r['bad'],
                            have=r.get('have'), want=r.get('want'), rt=r.get('rt'), lat_status=r['status']))
    by_gap = collections.defaultdict(list)
    for r in res:
        by_gap[r['gap']].append(r['status'])
    listed = {g['id']: g for g in c.get('gaps', [])}
    stale = sorted(g for g in by_gap if g in listed and all(s == 'PASS' for s in by_gap[g])
                   and listed[g].get('status') != 'closed')
    open_ = sorted(g for g in by_gap if any(s != 'PASS' for s in by_gap[g]))
    unlisted_open = sorted(g for g in open_ if (g not in listed or listed[g].get('status') == 'closed')
                           and g != 'G-VM-BANKLAT')   # LAT fails are reported as fail_paths; not a contract gap id
    fails = [r for r in res if r['status'] != 'PASS']
    cls = collections.OrderedDict()
    for r in res:
        k = cls.setdefault(r['cls'], dict(paths=0, bits=0, fail=0, relay_stages=set()))
        k['paths'] += 1; k['bits'] += r['w']; k['fail'] += r['status'] != 'PASS'
        k['relay_stages'] |= set(r['relay_stages'] or [])
    ok = not fails and not unlisted_open and (a.gaps == 'warn' or not stale)
    for k, v in cls.items():
        print(f'  {k:5s} paths {v["paths"]:4d} bits {v["bits"]:7d} fail {v["fail"]:3d} relay_stages {sorted(v["relay_stages"])}')
    for r in fails[:40]:
        print('  FAIL', r['cls'], f'{r["src"][0]}.{r["src"][1]}[{r["src"][2]}+:{r["w"]}] -> {r["dst"][0]}.{r["dst"][1]}[{r["dst"][2]}]',
              '|', '; '.join(r['bad']))
    lat_bad = [r for r in lat_rows if r['status'] == 'FAIL']
    if lat_rows:
        print(f'  LAT   clients {sum(r["status"] != "INFO" for r in lat_rows):4d} fail {len(lat_bad):3d} (--lat {a.lat})'
              + ('' if a.lat == 'strict' or not lat_bad else '  WARN: bank-client latency mismatches NOT failing this bind'))
    for g in stale:
        print('  STALE_GAP', g, '(all functional paths bound; contract still lists it open)')
    for g in unlisted_open:
        print('  UNLISTED_OPEN_GAP', g, '(paths fail but the contract does not list the gap open)')
    print(f'FUNCTIONAL_BIND {"PASS" if ok else "FAIL"} paths={len(res)} bits={sum(r["w"] for r in res)} '
          f'fail_paths={len(fails)} stale_gaps={len(stale)} open_gaps={len(open_)}')
    if a.report:
        Path(a.report).write_text(json.dumps({
            'schema': 'opentallas.d4g_functional_bind.v1', 'contract': str(a.contract), 'verdict': 'PASS' if ok else 'FAIL',
            'classes': {k: dict(v, relay_stages=sorted(v['relay_stages'])) for k, v in cls.items()},
            'stale_gaps': stale, 'open_gaps': open_, 'unlisted_open_gaps': unlisted_open,
            'fails': fails, 'paths': len(res), 'lat_mode': a.lat,
            'lat_rows': [{k: v for k, v in r.items() if k != 'paths'} for r in lat_rows]}, indent=1))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
