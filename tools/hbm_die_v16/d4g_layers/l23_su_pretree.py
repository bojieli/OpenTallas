#!/usr/bin/env python3
"""HBM-PRETREE3 10-20 GEN2e5 layer (after l22): bind the closed HH-6 SU reducer pre-tree (H.STA.BLK.16.6).

Why: on GEN2e4 the SU reducer takes ONE lane operand per edge per quarter, so SU reductions are ingress bound (Qwen softmax
22.3k vs 590/399 priced -> 417.5 tok/s).  With the pre-tree (bench-bound, claude/hbm-pretree2-1020 @a5cc6f083 +
codex/hbm-pretree-pickup-1020) the measured re-composition is DS 1148.8 / Qwen 1000.7 tok/s (claude/hbm-pretree3-1020,
results/token_pass/measured_hbm_1019/pretree2/recompose_pt3.json).

Per quarter q in NW/NE/SW/SE, slice g 0..3 (placement (a): the leaf is a HARD CHILD inside the su cluster):
 (1) su_<q><g> (ot_hbm_su_static_pgslice_lg): params PRETREE=1; new ports tree_cmd[11:0] (in), tree_o[66:0] (out).
     The child u_slice/g_pretree.u_pt = ot_hbm_su_red_pretree_s #(LAT 6, OPR 1) = CLOSED view
     hbm_su_pretree_s_1018-p3-1dad69123 (172.8 x 302.4; clk = the cluster's clk_ctl, rst_n landed in the tile).
     The pretree source must NOT enter the scoped pgslice family (l14 would rename ot_hbm_su_red_pretree_s and break the
     hard-view binding): it is an external module, added here as an rtl_dep.
 (2) sucore_<q> (ot_hbm_su_static_qcore): params PRETREE=1; new port slice_t[267:0] (in) + ot_hbm_su_red_pretree_j
     (join, 7 adders, inside the core).  Release qcore = r6n (ot_hbm_su_static_qcore_r5 PRETREE=1,
     hbm_su_qcore_r6n_1019) when it closes; this layer keeps the current master and sets PRETREE.
 (3) pgp_<q> (ot_hbm_su_programme_pslice_c5): SB 2422 -> 2470.  NC stays 10 (column 9 = bits 2304..2559 already
     exists; its leaf outputs 256 b): NO leaf/head master change.  command[2422 + 12g +: 12] = slice g's
     {v, max, cntB5, cntA5} (su_pretree_lower.tree_cmd_word), emitted on the SAME programme edge as the red_sel bits of
     the block (bench: tools/hbm_static/toksim_su/suvop/pt_prog_field_run.sh, pslice_c5 SB 2470 lockstep/golden PASS).
 (4) edges: pgp_<q>.command[2422+12g +:12] -> su_<q><g>.tree_cmd   (serial, region su_sfu, MUST carry the same relay
     stage count as pgp_<q>.command[0:8] -> su_<q><g>.red_sel; a difference changes compiler constant TREE_LEAD)
     su_<q><g>.tree_o[0:67] -> sucore_<q>.slice_t[67g +:67]  (serial; every relay stage on it ADDS to PT_RED 80)
No other edge changes.  Needs synthesis of the changed masters (su cluster with hard child, qcore PRETREE, pslice SB)."""
import argparse, copy, hashlib, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
QS = ('NW', 'NE', 'SW', 'SE')
PT_SRC = 'rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_red_pretree.sv'
SB0, SB1, TW, SW = 2422, 2470, 12, 67
VIEW = 'hbm_su_pretree_s_1018-p3-1dad69123'


def _edge(name, bits, src, snk, basis):
    return dict(name=name, bits=bits, source=src, sink=snk, clock='serial', ready_or_credit=False, allowed_exception=None,
                basis=basis, region='su_sfu')


def apply(original):
    c = copy.deepcopy(original); I = c['instances']; E = c['edges']
    rep = dict(layer='l23_su_pretree', view=VIEW, pretree_source_sha256=hashlib.sha256((ROOT / PT_SRC).read_bytes()).hexdigest(),
               added_edges=0, added_edge_bits=0, instances={})
    names = {e['name'] for e in E}
    for q in QS:
        pg, co = I[f'pgp_{q}'], I[f'sucore_{q}']
        if pg['master'] != 'ot_hbm_su_programme_pslice_c5' or pg['ports']['command']['bits'] != SB0:
            raise ValueError(f'pgp_{q}: expected pslice_c5 command {SB0}')
        if co['master'] not in ('ot_hbm_su_static_qcore', 'ot_hbm_su_static_qcore_r5') or 'slice_t' in co['ports']:
            raise ValueError(f'sucore_{q}: unexpected master/ports')
        used = [e for e in E if e['source'][0] == f'pgp_{q}' and e['source'][1] == 'command' and e['source'][3] > SB0]
        if used:
            raise ValueError(f'pgp_{q}: command bits >= {SB0} already used')
        pg['params'] = dict(pg.get('params') or {}, SB=SB1)
        pg['ports']['command']['bits'] = SB1
        pg['note'] += f' | l23: SB {SB0}->{SB1}: command[{SB0}+12g+:12] = slice g pre-tree tree_cmd (NC 10, leaves unchanged)'
        co['params'] = dict(co.get('params') or {}, PRETREE=1)
        co['ports']['slice_t'] = dict(direction='input', bits=4 * SW)
        co['rtl_deps'] = sorted(set(co.get('rtl_deps') or []) | {PT_SRC})
        co['note'] += ' | l23: PRETREE=1 (ot_hbm_su_red_pretree_j join; red_cmd osel1 lane[5] takes the quarter subtree at E+PT_RED 80)'
        rep['instances'][f'pgp_{q}'] = dict(SB=SB1); rep['instances'][f'sucore_{q}'] = dict(PRETREE=1, slice_t=4 * SW)
        for g in range(4):
            s = I[f'su_{q}{g}']
            if s['master'] != 'ot_hbm_su_static_pgslice_lg' or 'tree_cmd' in s['ports']:
                raise ValueError(f'su_{q}{g}: unexpected master/ports')
            rs = [e for e in E if e['sink'][0] == f'su_{q}{g}' and e['sink'][1] == 'red_sel']
            if sum(e['bits'] for e in rs) != 12 or any(e['source'][0] != f'pgp_{q}' for e in rs):
                raise ValueError(f'su_{q}{g}: red_sel not fed 12 b from pgp_{q}')
            s['params'] = dict(s['params'], PRETREE=1)
            s['ports']['tree_cmd'] = dict(direction='input', bits=TW)
            s['ports']['tree_o'] = dict(direction='output', bits=SW)
            s['rtl_deps'] = sorted(set(s.get('rtl_deps') or []) | {PT_SRC})
            s['hard_children'] = sorted(set(s.get('hard_children') or []) | {f'u_slice/g_pretree.u_pt={VIEW}'})
            s['note'] += (f' | l23: PRETREE=1, hard child u_slice/g_pretree.u_pt = ot_hbm_su_red_pretree_s (CLOSED {VIEW}); '
                          'tree_cmd/tree_o faces; slot grows by the leaf (172.8 x 302.4)')
            lo = SB0 + TW * g
            for n, b, src, snk, basis in (
                (f'su_pt_{q}{g}_tree_cmd', TW, [f'pgp_{q}', 'command', lo, lo + TW], [f'su_{q}{g}', 'tree_cmd', 0, TW],
                 f'l23 pre-tree: slice {g} tree_cmd = pslice_c5 SB{SB1} command[{lo}+:{TW}] (su_pretree_lower.tree_cmd_word, '
                 'same programme edge and relay depth as red_sel)'),
                (f'su_pt_{q}{g}_tree_o', SW, [f'su_{q}{g}', 'tree_o', 0, SW], [f'sucore_{q}', 'slice_t', SW * g, SW * (g + 1)],
                 f'l23 pre-tree: ot_hbm_su_static_quarter .tree_o(slice_t[g*67+:67]) (relay stages add to PT_RED 80)')):
                if n in names:
                    raise ValueError('edge exists: ' + n)
                E.append(_edge(n, b, src, snk, basis)); rep['added_edges'] += 1; rep['added_edge_bits'] += b
            rep['instances'][f'su_{q}{g}'] = dict(PRETREE=1, tree_cmd=TW, tree_o=SW)
    # coverage check: every new sink bit driven exactly once, every new source bit read
    for q in QS:
        cov = [0] * (4 * SW)
        for e in E:
            if e['sink'][:2] == [f'sucore_{q}', 'slice_t']:
                for i in range(e['sink'][2], e['sink'][3]): cov[i] += 1
        if cov != [1] * (4 * SW):
            raise ValueError(f'sucore_{q}.slice_t coverage {set(cov)}')
        rd = [0] * (SB1 - SB0)
        for e in E:
            if e['source'][:2] == [f'pgp_{q}', 'command'] and e['source'][2] >= SB0:
                for i in range(e['source'][2], e['source'][3]): rd[i - SB0] += 1
        if rd != [1] * (SB1 - SB0):
            raise ValueError(f'pgp_{q}.command[{SB0}:{SB1}] read coverage {set(rd)}')
    s = c.get('summary') or {}
    if 'edges' in s:
        s['edges'] = len(E); s['edge_bits'] = s.get('edge_bits', 0) + rep['added_edge_bits']
    return c, rep


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True)
    a = p.parse_args()
    c = json.load(open(a.inp)); c, r = apply(c)
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n'); Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print('L23_SU_PRETREE edges +%d (%d b), 16 su clusters PRETREE=1, 4 qcores PRETREE=1, 4 pslice SB %d' % (
        r['added_edges'], r['added_edge_bits'], SB1))


if __name__ == '__main__':
    main()
