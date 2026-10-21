#!/usr/bin/env python3
"""HBM-OWN/DIE2-BIND 10-21: r17 GEN binds for the 4 MISSING rows of the r16 bind table (lanes/HBM-OWN.md "DIE/BIND 12:19").

Contract in -> contract out (+ optional grants in -> grants out) + report, like l26/l29/l30.  Source/view selection only:
the parent die still needs S2 synthesis of the changed masters, GEN geometry, S4 stations and S11 STA/IR.

 1 cxport ij   cxij_<q> (ot_hbm_su_static_cxport_ij, SOFT) -> abutted halves cxij_<q>_q (W) + cxij_<q>_s (E), split exactly as
               l9 split_cx does for cxdl/cxrc (wrapper nets -> seam edges, split_parents port map).  Source
               claude/hbm-own-cxij-bind-1021 df472fefc (ij_q SAFE_GATHER body == CLOSED 5a6486280).
               cxij_<q>_q <- physical/ref_tile/hbm_su_cx_ijq_1019t/views/ot_hbm_su_static_cxport_ij_q (SAFE_GATHER=1, record
               25f839df7; ij_q has no QID/INJ_RET/B39 parameters -> one view for all 4).
               cxij_<q>_s stays SYNTH: the CLOSED ij_s view (hbm_su_cx_ijs_1018) is QID 2 / B39_NOOP 0 / INJ_RET 11 / OBR 1;
               the die needs QID q / B39_NOOP 1 / INJ_RET 9 (cij INJLAT 12, functional_bind INJ_RET rule) and INJ_RET 9 leaves
               no spare stage for OBR 1 (X = INJ_RET-1-RQ-LMAX = 0) -> OBR 0.  v16_views.real_view refuses the view on the
               spec-param mismatch anyway; binding it would alias another parameterisation.
 2 hb_quant_NW ot_hgi_qdq_host_split -> CLOSED QDQ r3 leaves via l32q_qdq_split.py (= Codex 7d6b45a59 l27_qdq_split); needs
               the fleet netmap (qdq_split_netmap.py OUT --rl RL --wc 4 --xr XR, yosys elaboration).  Applied only with
               --qdq-netmap; otherwise reported BLOCKED.
 3 ot_hidx_s3_q binds inside the hidx_sel_s3p parent only; reported NOT-BINDABLE-YET while the contract has no s3p parent.
 4 ot_hgi_coll_link_e1 binds only as a hard child of an hb_coll master that instantiates it; r16 hb_coll_* =
               ot_hfd_coll_q_hard_v8g.sv (ot_hgi_coll_link_e, 5 entry clocks) -> NOT-APPLICABLE.
"""
import argparse, collections, copy, json, re, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / 'tools/hbm_die_v15'))
import l9_gen2c_views as L9          # noqa: E402
import full_die_v16 as F             # noqa: E402
from v16_views import lef_ports      # noqa: E402

REGION = 'd4g_l32_r17'
QS = ('SW', 'SE', 'NW', 'NE')
IJ = 'ot_hbm_su_static_cxport_ij'
IJQ_VIEW = 'physical/ref_tile/hbm_su_cx_ijq_1019t/views/ot_hbm_su_static_cxport_ij_q'
IJQ_REC = ('hbm_su_cx_ijq_1019t-t1-5a6486280 CLOSED TT +67.13/FF +26.92 DRC 0 (record 25f839df7, SAFE_GATHER=1); '
           'source claude/hbm-own-cxij-bind-1021 df472fefc')
IJS_VIEW = 'physical/ref_tile/hbm_su_cx_ijs_1018/views/ot_hbm_su_static_cxport_ij_s'
IJ_DEFAULTS = dict(RQ=0, RQC=0, SD=0, OBR=0, SAFE_GATHER=1)


def spec_params(view):
    return json.loads((ROOT / view).parent.parent.joinpath('spec.json').read_text()).get('params') or {}


def bind_cxij(c, problems, rep):
    I = c['instances']
    names = [f'cxij_{q}' for q in QS]
    for n in names:
        i = I.get(n)
        if i is None or i['master'] != IJ:
            problems.append(f'{n}: expected {IJ}, have {None if i is None else i["master"]}'); return
        i['params'] = dict(i['params'], **{k: v for k, v in IJ_DEFAULTS.items() if k not in i['params']})
        if i['params']['OBR'] != 0 or i['params']['SAFE_GATHER'] != 1:
            problems.append(f'{n}: params {i["params"]}')
    src = (ROOT / L9.CX_SRC).read_text()
    if 'SAFE_GATHER' not in re.search(r'module\s+ot_hbm_su_static_cxport_ij_q\b.*?\)\(', src, re.S).group(0):
        problems.append('cxport_split.sv lacks the SAFE_GATHER ij_q (need df472fefc)'); return
    L9.CX = {IJ: 'ij'}; L9.REGION = REGION
    sub = dict(cx=[])
    L9.split_cx(c, F.Rtl(), problems, sub)
    rep['cxij']['split'] = sub['cx']
    lq = lef_ports(ROOT / IJQ_VIEW / 'ot_hbm_su_static_cxport_ij_q.lef')
    ijs_sp = spec_params(IJS_VIEW); ijq_sp = spec_params(IJQ_VIEW)
    for q in QS:
        nq, ns = f'cxij_{q}_q', f'cxij_{q}_s'
        if nq not in I or ns not in I:
            problems.append(f'cxij_{q}: halves missing after split'); continue
        x = I[nq]
        mism = {p: (lq.get(p), d['bits']) for p, d in x['ports'].items() if lq.get(p) != d['bits']}
        pmiss = {k: (v, x['params'].get(k)) for k, v in ijq_sp.items() if str(x['params'].get(k)) != str(v)}
        if mism or pmiss:
            problems.append(f'{nq}: ij_q view port {mism} / param {pmiss} mismatch'); continue
        x.update(physical_view=IJQ_VIEW, closed_record=IJQ_REC, region=REGION,
                 note=x['note'] + ' | l32: CLOSED ij_q view, abutted W of ' + ns)
        s = I[ns]
        smiss = {k: (v, s['params'].get(k)) for k, v in ijs_sp.items() if str(s['params'].get(k)) != str(v)}
        s['note'] += (f' | l32: SYNTH; CLOSED ij_s view {IJS_VIEW} is hardened for {ijs_sp} (mismatch {smiss}) -> '
                      f'needs an ij_s re-harden at QID {s["params"].get("QID")} B39_NOOP 1 INJ_RET 9 OBR 0')
        rep['cxij']['bound'].append(nq)
        rep['cxij']['synth'].append(dict(inst=ns, params=s['params'], view_param_mismatch=smiss))


def split_grants(g, c, problems, rep):
    """cxij_<q> grant slot -> abutted pair: ij_q (LEF 216 x 388.8) W at the slot origin, ij_s (LEF 108 x 388.8) E of it."""
    slots = {s['name']: s for s in g['slots']}
    lq = (ROOT / IJQ_VIEW / 'ot_hbm_su_static_cxport_ij_q.lef').read_text()
    ls = (ROOT / IJS_VIEW / 'ot_hbm_su_static_cxport_ij_s.lef').read_text()
    wq, hq = map(float, re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', lq).groups())
    ws, hs = map(float, re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', ls).groups())
    new = []
    for q in QS:
        old = slots.get(f'cxij_{q}')
        if old is None:
            problems.append(f'grant cxij_{q} missing'); continue
        for nm, dx, w, h, view in ((f'cxij_{q}_q', 0.0, wq, hq, IJQ_VIEW), (f'cxij_{q}_s', wq, ws, hs, None)):
            s = copy.deepcopy(old)
            s.update(name=nm, instance=nm, cell=c['instances'][nm]['master'], outline=dict(w=w, h=h), grant=REGION,
                     notes=f'l32 abutted cxport ij pair (ij_q W | ij_s E), pair {wq + ws} x {max(hq, hs)}; '
                           + ('CLOSED LEF outline' if view else 'ij_s SYNTH at the CLOSED ij_s LEF outline'))
            s['origin'] = dict(old['origin'], x=round(old['origin']['x'] + dx, 3))
            if view:
                s['physical_view'] = view
            new.append(s)
        rep['cxij']['grants'].append(dict(slot=f'cxij_{q}', old_outline=old.get('outline'), pair=[wq + ws, max(hq, hs)]))
    g['slots'] = [s for s in g['slots'] if s['name'] not in {f'cxij_{q}' for q in QS}] + new


def check_s3q(c, rep):
    I = c['instances']
    hit = [n for n, i in I.items() if i['master'] in ('ot_hidx_s3_q', 'ot_hidx_sel_s3p') or 'hidx_sel_s3p' in n]
    rep['hidx_s3_q'] = dict(status='NOT-BINDABLE-YET' if not hit else 'PRESENT', instances=hit,
                            reason='r16 hb_idx__selector = ot_hbm_idx_selector_static_sel; ot_hidx_s3_q (view hidx_sel_s3u_b, '
                                   'record 5bd53e4cb) binds only inside the hidx_sel_s3p parent, which has no CLOSED view '
                                   '(no daemon job, not in closed_archive)')


def check_coll_link(c, rep):
    I = c['instances']; uses = {}
    for n, i in I.items():
        if n.startswith('hb_coll_'):
            t = (ROOT / i['source']).read_text() if (ROOT / i['source']).is_file() else ''
            uses[n] = dict(master=i['master'], source=i['source'], link_e1=bool(re.search(r'\bot_hgi_coll_link_e1\b', t)),
                           link_e=bool(re.search(r'\bot_hgi_coll_link_e\b', t)))
    app = any(u['link_e1'] for u in uses.values())
    rep['coll_link_e1'] = dict(status='APPLICABLE' if app else 'NOT-APPLICABLE', hb_coll=uses,
                               reason=None if app else 'r16 hb_coll_* masters instantiate ot_hgi_coll_link_e (5 entry clocks), '
                               'not ot_hgi_coll_link_e1; e2u view (claude/collq8-link-1021 4e35e168c) binds only with a '
                               'lp_ars/lpf_ars collq8 parent')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('input', type=Path); ap.add_argument('output', type=Path); ap.add_argument('--report', required=True, type=Path)
    ap.add_argument('--grants', type=Path); ap.add_argument('--out-grants', type=Path)
    ap.add_argument('--qdq-netmap', type=Path, help='fleet output of qdq_split_netmap.py (RL/WC/XR of this die)')
    a = ap.parse_args()
    c = json.loads(a.input.read_text()); problems = []
    rep = dict(schema='opentallas.hbm_d4g_l32_r17_binds.v1', input=str(a.input), cxij=dict(bound=[], synth=[], grants=[]))
    n0 = len(c['instances'])
    dup_before = frozenset(k for k, v in collections.Counter(e['name'] for e in c['edges']).items() if v > 1)
    bind_cxij(c, problems, rep)
    if a.qdq_netmap:
        import l32q_qdq_split as Q
        c, rq = Q.apply(c, json.loads(a.qdq_netmap.read_text()))
        rep['qdq'] = dict(status='BOUND', **rq)
    else:
        rep['qdq'] = dict(status='BLOCKED', reason='needs fleet netmap: python3 tools/hbm_die_v16/d4g_layers/qdq_split_netmap.py '
                          'OUT.json --rl <l12 lat_rows RL, 54> --wc 4 --xr <equal quant_NW<k><->quant_NW_xp stages from the r17 '
                          'grant geometry (12 today, 8 with xp at the LG centroid)> (yosys elaboration on the fleet)')
    check_s3q(c, rep); check_coll_link(c, rep)
    L9.validate(c, problems, dup_before)
    c['masters'] = dict(sorted(collections.Counter(i['master'] for i in c['instances'].values()).items()))
    c.setdefault('summary', {}).update(instances=len(c['instances']), masters=len(c['masters']), edges=len(c['edges']),
                                       edge_bits=sum(e['bits'] for e in c['edges']), clock_reset_ports=len(c['clock_resets']))
    if isinstance(c.get('notes'), list):
        c['notes'].append(f'{REGION}: cxij abutted pairs (ij_q CLOSED x{len(rep["cxij"]["bound"])}, ij_s SYNTH), qdq {rep["qdq"]["status"]}')
    if a.grants:
        if not a.out_grants:
            ap.error('--grants requires --out-grants')
        g = json.loads(a.grants.read_text()); split_grants(g, c, problems, rep)
        if a.qdq_netmap:
            g = Q.bind_grants(g, c)
        a.out_grants.write_text(json.dumps(g, indent=1) + '\n')
    rep.update(instances_before=n0, instances_after=len(c['instances']), problems=problems,
               verdict='PASS' if not problems else 'FAIL',
               qualification='SOURCE/VIEW SELECTION; S2 re-synth of cxij_<q>_s (+hb_quant_NW children), GEN geometry, '
                             'S4 stations and S11 STA/IR remain')
    a.report.write_text(json.dumps(rep, indent=1) + '\n')
    for p in problems[:40]:
        print('PROBLEM', p)
    print(f'L32_R17_BINDS {rep["verdict"]} inst {n0} -> {len(c["instances"])} ij_q_closed {len(rep["cxij"]["bound"])} '
          f'ij_s_synth {len(rep["cxij"]["synth"])} qdq {rep["qdq"]["status"]} s3q {rep["hidx_s3_q"]["status"]} '
          f'link_e1 {rep["coll_link_e1"]["status"]}')
    if problems:
        sys.exit(1)
    a.output.write_text(json.dumps(c, indent=1) + '\n')


if __name__ == '__main__':
    main()
