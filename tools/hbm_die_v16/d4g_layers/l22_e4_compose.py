#!/usr/bin/env python3
"""L2H-GEN2E 10-19 GEN2e4 compose layer (after l21): two source-only re-masterings, no edge added or removed.

(f) col_idx FAN32=1: the IDX256R collar (l20p packed face) on the FAN32 banked structure (L2H-PAD 944b0ceb2; kits
    hdie_col_idx256r_a/_b set FAN32=1).  Ports identical to FAN32=0 (packed prm 769, pw_addr 8).
(m) RELEASE PC controller stand-in: every ot_hbm_svc_pc_ctrl_leaf_cfg_h9b -> ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face with
    the HBM-MC3 kit parameters (hdie_pc_ctrl_mc3_p540: RST_FOREST=1 PCID_LOCAL=1, RESET_LANDING 2, SRAM_P192, PURE_FACE).
    Same port names / widths / directions as h9b (checked against the RTL headers below); h9b-only QREG dropped.
    LABELLED STAND-IN: the die binds the SYNTH view until hdie_pc_ctrl_mc3_p540 (or _q648) is CLOSED.
Both changes need synthesis (new master / parameter set); no hard view is admitted here."""
import argparse, copy, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
COL = 'ot_hbm_static_cfg_collar_idx256r'
COL_SRC = 'rtl/hbm_accel/host_static_20261015/' + COL + '.sv'
OLD_PC = 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b'
NEW_PC = 'ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face'
SN = 'rtl/hbm_accel/loader/service_native/'
NEW_PC_SRC = SN + NEW_PC + '.sv'
NEW_PC_DEPS = ['rtl/lib/ot_rst_relay.sv', 'rtl/lib/ot_rst_forest.sv', SN + 'ot_hbm_svc_pc_ctrl_leaf_cfg_safe.sv',
               SN + 'ot_hbm_svc_ring_h9b.sv', SN + 'ot_hbm_svc_pin_skid2_h9.sv', 'rtl/model_ready_hbm_r14/ot_hbm_r14_aq_pc_safe.sv',
               SN + 'ot_hbm_svc_ring_bw_safe.sv', SN + 'ot_hbm_svc_pin_skid2_bw_safe.sv', SN + 'ot_hbm_svc_sram128_n64.sv']
MC3_PARAMS = {'OREG': 1, 'KREG': 1, 'KRREG': 1, 'RREG': 1, 'WPAY': 1, 'RESET_LANDING': 2, 'SRAM_P192': 1, 'PURE_FACE': 1,
              'RST_FOREST': 1, 'PCID_LOCAL': 1}


def header_ports(src, mod, ports_too=True):
    t = (ROOT / src).read_text()
    m = re.search(r'\bmodule\s+' + mod + r'\b\s*#\((.*?)\)\s*\((.*?)\);', t, re.S)
    if not m:
        raise ValueError('no header for ' + mod)
    params = set(re.findall(r'parameter\s+integer\s+(\w+)', m[1]))
    ports, d, w = {}, None, 1
    if not ports_too:
        return params, ports
    for tok in re.sub(r'//[^\n]*', '', m[2]).replace('\n', ' ').split(','):
        tok = tok.strip()
        mm = re.match(r'(input|output)?\s*(?:wire|reg)?\s*(\[(\d+):0\])?\s*(\w+)$', tok)
        if not mm:
            raise ValueError(f'{mod}: unparsed port token {tok!r}')
        if mm[1]:
            d, w = mm[1], (int(mm[3]) + 1 if mm[2] else 1)
        elif mm[2]:
            w = int(mm[3]) + 1
        ports[mm[4]] = (d, w)
    return params, ports


def apply(original, fan32=True, mc3=True):
    c = copy.deepcopy(original); rep = dict(layer='l22_e4_compose', successful_data_added_edges=0, edges_changed=0)
    if fan32:
        v = c['instances']['col_idx']
        if v['master'] != COL:
            raise ValueError('l22f requires the l20p IDX256R collar on col_idx')
        if 'FAN32' not in header_ports(COL_SRC, COL, False)[0]:
            raise ValueError('collar RTL has no FAN32 parameter (944b0ceb2 source missing)')
        v['params'] = dict(v['params'], FAN32=1)
        v['note'] += ' | l22f: FAN32=1 banked structure (kits hdie_col_idx256r_a/_b), SYNTH stand-in until one CLOSES'
        rep['col_idx'] = dict(params=v['params'], source_sha256=hashlib.sha256((ROOT / COL_SRC).read_bytes()).hexdigest())
    if mc3:
        npar, nports = header_ports(NEW_PC_SRC, NEW_PC)
        bad = [p for p in MC3_PARAMS if p not in npar]
        if bad:
            raise ValueError('MC3 params not in RTL: %s' % bad)
        n = 0
        for name, v in c['instances'].items():
            if v['master'] != OLD_PC:
                continue
            for p, q in v['ports'].items():
                if p not in nports or nports[p][1] != q['bits']:
                    raise ValueError(f'{name}.{p}: port differs on {NEW_PC} ({nports.get(p)} vs {q["bits"]})')
            missing = set(nports) - set(v['ports'])
            if missing:
                raise ValueError(f'{name}: {NEW_PC} has extra ports {sorted(missing)}')
            v.update(master=NEW_PC, source=NEW_PC_SRC, rtl_deps=list(NEW_PC_DEPS), params=dict(MC3_PARAMS))
            v['note'] += (' | l22m: RELEASE controller HBM-MC3 SAFE face (per-bank open row, ACT lookahead, reset forest,'
                          ' local pc_id) as LABELLED SYNTH STAND-IN until hdie_pc_ctrl_mc3_p540/_q648 is CLOSED')
            n += 1
        for s in c.get('straps', []):
            if s.get('master') == OLD_PC:
                s['master'] = NEW_PC
        if n != 64:
            raise ValueError(f'expected 64 PC controllers, found {n}')
        rep['pc_controllers'] = dict(count=n, master=NEW_PC, params=MC3_PARAMS, stand_in=True,
                                     source_sha256=hashlib.sha256((ROOT / NEW_PC_SRC).read_bytes()).hexdigest())
    return c, rep


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True)
    p.add_argument('--no-fan32', action='store_true'); p.add_argument('--no-mc3', action='store_true'); a = p.parse_args()
    c = json.load(open(a.inp)); c, r = apply(c, not a.no_fan32, not a.no_mc3)
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n'); Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print('L22_E4_COMPOSE fan32=%s mc3=%s 0 added edges' % ('col_idx' in r, r.get('pc_controllers', {}).get('count', 0)))


if __name__ == '__main__':
    main()
