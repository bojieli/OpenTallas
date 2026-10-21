#!/usr/bin/env python3
"""HD-CTL 10-21: write results/arch/s81_head_1021/ports.json from the RTL port lists of the head-die controller-side
masters (ot_s81hd_ctl, ot_s81hd_lep, ot_s81hd_lane) and ot_pdie_serdes, plus the die connection table (ctl <-> lep /
lanes / spines, lanes / lep <-> SerDes).  Roles: clk / rst / strap / bus / serdes_tx / serdes_rx.
usage: gen_ports.py REPO_ROOT"""
import json, re, sys, subprocess
from pathlib import Path

root = Path(sys.argv[1])
MASTERS = {
    'ot_s81hd_ctl': 'rtl/dsrom_sys/s81_head/ot_s81hd_ctl.sv',
    'ot_s81hd_lep': 'rtl/dsrom_sys/s81_head/ot_s81hd_lep.sv',
    'ot_s81hd_lane': 'rtl/dsrom_sys/s81_head/ot_s81hd_lane.sv',
    'ot_pdie_serdes': 'rtl/dsrom_sys/s81_link/ot_pdie_serdes.sv',
}


def ports(path, mod):
    t = re.sub(r'//[^\n]*', '', (root / path).read_text())
    m = re.search(r'module\s+' + mod + r'\s*(#\s*\((?:[^()]|\([^()]*\))*\))?\s*\((.*?)\);', t, re.S)
    out, d, w = [], None, 1
    for item in m.group(2).split(','):
        item = item.strip()
        mm = re.match(r'(input|output)?\s*(?:wire|reg)?\s*(\[[^\]]+\])?\s*(\w+)$', item)
        if not mm:
            raise SystemExit(f'cannot parse port "{item}" of {mod}')
        if mm.group(1):
            d = mm.group(1)
            w = 1
            if mm.group(2):
                hi, lo = mm.group(2)[1:-1].split(':')
                w = eval(hi.replace('$clog2', '')) - eval(lo) + 1
        elif mm.group(2):
            hi, lo = mm.group(2)[1:-1].split(':')
            w = eval(hi) - eval(lo) + 1
        out.append({'name': mm.group(3), 'dir': d, 'width': w})
    return out


def role(mod, p):
    n = p['name']
    if n in ('ck', 'clk', 'pma_tck', 'pma_rck'):
        return 'clk' if n in ('ck', 'clk') else ('serdes_tx' if n == 'pma_tck' else 'serdes_rx')
    if n in ('rst_n', 'rst'):
        return 'rst'
    if n in ('chb', 'ch_b'):
        return 'strap'
    if mod in ('ot_s81hd_lane', 'ot_s81hd_lep') and re.fullmatch(r'tx\d?', n):
        return 'serdes_tx'
    if mod in ('ot_s81hd_lane', 'ot_s81hd_lep') and re.fullmatch(r'rx\d?', n):
        return 'serdes_rx'
    if mod == 'ot_pdie_serdes':
        return {'tx': 'serdes_tx', 'rx': 'serdes_rx', 'st': 'serdes_rx', 'pma_tx': 'serdes_tx', 'pma_rx': 'serdes_rx'}[n]
    return 'bus'


NOTES = {
    ('ot_pdie_serdes', 'tx'): 'core side: from the lane / lep tx', ('ot_pdie_serdes', 'rx'): 'core side: to lane rx[511:0]',
    ('ot_pdie_serdes', 'st'): '{live, fault} -> lane rx[513:512]', ('ot_pdie_serdes', 'pma_tx'): 'die pads',
    ('ot_pdie_serdes', 'pma_rx'): 'die pads', ('ot_pdie_serdes', 'pma_tck'): 'die pad (forwarded clock)',
    ('ot_pdie_serdes', 'pma_rck'): 'die pad (recovered clock, separate CDR domain inside the macro)',
    ('ot_s81hd_lane', 'rx'): '{serdes st[1:0], serdes rx[511:0]}', ('ot_s81hd_lep', 'rx0'): '{serdes st, rx} lk_WN0 (pair A)',
    ('ot_s81hd_lep', 'rx1'): 'lk_WN1 (pair A)', ('ot_s81hd_lep', 'rx2'): 'lk_WN2 (pair B)', ('ot_s81hd_lep', 'rx3'): 'lk_WN3 (pair B)',
    ('ot_s81hd_lane', 'chb'): 'strap 1 = board lane (as the end-slice lanes, CH_BOARD 700)',
    ('ot_s81hd_lep', 'ch_b'): 'strap 1 = board lane',
}

out = {'schema': 'opentallas.s81_head.ports.v1', 'source': 'HD-CTL 10-21 (claude/s81-head-ctl-1021)',
       'generator': 'rtl/dsrom_sys/s81_head/test/gen_ports.py', 'masters': {}}
for mod, path in MASTERS.items():
    lst = []
    for p in ports(path, mod):
        e = dict(p, role=role(mod, p))
        if (mod, p['name']) in NOTES:
            e['note'] = NOTES[(mod, p['name'])]
        lst.append(e)
    out['masters'][mod] = {'source': path, 'ports': lst,
                           'hard_children': {'ot_s81hd_ctl': ['dsfd_mtp_seq (CLOSED 10-08 kit)', '4 x ot_sram_1r1w_64x512_m1_r2c2'],
                                             'ot_s81hd_lep': ['4 x dsfd_coll_lane_w_safe8_ntf', 'ot_s81sl_lep_mu_ab #(RX_SRAM 1, IN_PIPE 1, NATIVE32 1)', 'dsdv_mu_land #(W 1104, NB 80, NS 1, SRAM 1)'],
                                             'ot_s81hd_lane': ['dsfd_coll_lane_w_safe8_ntf'],
                                             'ot_pdie_serdes': ['hard PHY macro (slot 518.4 x 3844.8)']}[mod]}
FW = 553
inst = {'ctl': 'u_ctl', 'lep': 'u_lep'}
conn = []
def c(a, b, w, note=''):
    conn.append({'from': a, 'to': b, 'width': w, **({'note': note} if note else {})})
# ctl <-> lep (die-level land-plan row: fixed-latency landing ring, ctl region <-> lep region)
c('u_ctl.ro', 'u_lep.ro', 1104, 'pair A TX ring beats'); c('u_lep.ri', 'u_ctl.ri', 1104, 'pair A/B RX ring beats (XB in)')
c('u_ctl.mu_c', 'u_lep.mu_c', 34); c('u_lep.mu_rt', 'u_ctl.mu_rt', 32); c('u_ctl.mu_rc', 'u_lep.mu_rc', 11)
c('u_lep.lw', 'u_ctl.lw', 11); c('u_lep.fault', 'u_ctl.lep_f', 1); c('u_ctl.ctl_f', 'u_lep.sl_f', 1)
# spines
c('u_ctl.sn_o', 'u_spo_N0.i', 565, 'bus B to the bottom N spine-out node (HD-TILE / HD-FP name)')
c('u_spr_N0.o', 'u_ctl.sn_i', 565, 'bus B from the bottom N spine-return node')
c('u_ctl.ss_o', 'u_spo_S0.i', 565); c('u_spr_S0.o', 'u_ctl.ss_i', 565)
lanes = [('m', k, 'mtx', 'mrx', 'mflt', f'TP4 mesh lane {k} (peer pair {k // 2}, copy {k % 2})') for k in range(6)]
lanes += [('h', k, 'htx', 'hrx', 'hflt', ['host lane 0 (lk_HOST0): HFWD in / RESULT out', 'host lane 1 (lk_HOST1): CSRW in / STATUS out'][k]) for k in range(2)]
lanes += [('d', k, 'dtx', 'drx', 'dflt', f'draft fan-out lane {k} (SEED / DHSTEP out, DHRES / ROWS in)') for k in range(5)]
serdes = []
for cls, k, tx, rx, fl, note in lanes:
    u = f'u_ln{cls}{k}'
    c(f'u_ctl.{tx}_v[{k}]', f'{u}.tx_v', 1, note); c(f'u_ctl.{tx}_d[{FW*k+FW-1}:{FW*k}]', f'{u}.tx_d', FW)
    c(f'{u}.rx_v', f'u_ctl.{rx}_v[{k}]', 1); c(f'{u}.rx_d', f'u_ctl.{rx}_d[{FW*k+FW-1}:{FW*k}]', FW)
    c(f'{u}.flt', f'u_ctl.{fl}[{4*k+3}:{4*k}]', 4)
    s = f'u_sd{cls}{k}'
    serdes.append({'serdes': s, 'client': u, 'link': {'m': f'rank mesh {k}', 'h': f'lk_HOST{k}', 'd': f'draft {k}'}[cls]})
    c(f'{u}.tx', f'{s}.tx', 512); c(f'{s}.st', f'{u}.rx[513:512]', 2); c(f'{s}.rx', f'{u}.rx[511:0]', 512)
for k, lk in enumerate(['lk_WN0', 'lk_WN1', 'lk_WN2', 'lk_WN3']):
    s = f'u_sdl{k}'
    serdes.append({'serdes': s, 'client': f'u_lep lane {k}', 'link': lk + (' (pair A, TX side: forward / token return)' if k < 2 else ' (pair B: XB in)')})
    c(f'u_lep.tx{k}', f'{s}.tx', 512); c(f'{s}.st', f'u_lep.rx{k}[513:512]', 2); c(f'{s}.rx', f'u_lep.rx{k}[511:0]', 512)
out['instances'] = {'u_ctl': 'ot_s81hd_ctl', 'u_lep': 'ot_s81hd_lep',
                    **{f'u_ln{cls}{k}': 'ot_s81hd_lane' for cls, k, *_ in lanes},
                    **{x['serdes']: 'ot_pdie_serdes' for x in serdes}}
out['serdes_assignment'] = serdes
out['connections'] = conn
out['die_level'] = {'clocks': 'ck of every block from its regional root (ctl region, lep region, one region per lane block); '
                              'ot_pdie_serdes clk = its client lane region clock; pma_tck / pma_rck / pma_* = die pads',
                    'resets': 'rst_n / rst from the die reset tree (regional leaves); each master lands it in 2 stages inside',
                    'straps': 'chb / ch_b = 1 (board / cable lanes)',
                    'crossings': 'ctl <-> lep and ctl <-> each lane are region crossings: land-plan rows (fixed-latency '
                                 'landing ring, no flow control), owned by HD-CHAIN',
                    'frame_format': 'HSF0, documented in rtl/dsrom_sys/s81_head/ot_s81hd_ctl.sv header (S81-FIX2 owns the final choice)'}
dst = root / 'results/arch/s81_head_1021/ports.json'
dst.write_text(json.dumps(out, indent=1) + '\n')
print('wrote', dst, 'masters', {m: len(v['ports']) for m, v in out['masters'].items()}, 'connections', len(conn))
