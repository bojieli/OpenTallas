#!/usr/bin/env python3
"""HBM-H9R11 10-20: bind the CLOSED h9c PC-controller fallback on a GEN2e4 die contract (parameterised
results/arch/hbm_die11_portage_1020/prepare_fallback.py, admitted by LEAD9-HBM as manifest ea87fbac on the r10 contract).

  l25_h9c_fallback.py swap   CONTRACT_IN CONTRACT_OUT --report R.json
      re-masters exactly 64 ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face instances (+ their straps) to ot_hbm_svc_pc_ctrl_leaf_cfg_h9b
      with params OREG/KREG/KRREG/RREG/WPAY/QREG=1 (= the closed view hdie_pc_ctrl_cfg_h9c-h9c-cts-155-1aa2ec44b spec params);
      asserts sha256 of the 7 closed sources against fallback_source_identity.json; port sets/directions/widths equal the
      h9b header; edges and every port map unchanged.  Fail-closed: any deviation exits non-zero, nothing written.
  l25_h9c_fallback.py review TRANSFERRED_REVIEW OUT --admitted results/arch/hbm_die11_portage_1020/h9bind/review_h9bind.json
      renews the transferred L21 unread review for the l24 sources by REUSING the admitted H9BIND delta review (543ecfcb):
      only its re-pinned sources are re-pinned, and only when this review's old pin equals H9BIND's old pin and the
      current source equals H9BIND's reviewed new pin.  Every other pin must equal the current bytes (any other drift
      REFUSED -> a new semantic delta review is owed).  Entries/bits are never changed.
Run from the repository root (worktree)."""
import argparse, copy, gzip, hashlib, json, sys
from pathlib import Path

ROOT = Path.cwd()
SN = 'rtl/hbm_accel/loader/service_native/'
OLD, NEW = 'ot_hbm_svc_pc_ctrl_leaf_cfg_safe_face', 'ot_hbm_svc_pc_ctrl_leaf_cfg_h9b'
PARAMS = dict(OREG=1, KREG=1, KRREG=1, RREG=1, WPAY=1, QREG=1)
SRCS = ['rtl/lib/ot_rst_relay.sv', SN + 'ot_hbm_svc_ring_h9b.sv', SN + NEW + '.sv', SN + 'ot_hbm_svc_pc_ctrl_leaf.sv',
        'rtl/model_ready_hbm_r14/ot_hbm_r14_stream_pc_strap_h9.sv',
        'physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2_bb.v',
        SN + 'ot_hbm_svc_pin_skid2_h9.sv']
IDENT = 'results/arch/hbm_die11_portage_1020/fallback_source_identity.json'
VIEW_LEF = 'physical/ref_tile/hdie_pc_ctrl_cfg_h9c/views/' + NEW + '/' + NEW + '.lef'
N_INST = 64


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def swap(a):
    ident = json.loads((ROOT / IDENT).read_text())
    for p in SRCS:
        assert sha(ROOT / p) == ident['sources'][p]['closed_sha256'], ('closed source differs', p)
    assert (ROOT / VIEW_LEF).is_file(), ('closed h9c view missing in this checkout (sparse?)', VIEW_LEF)
    spec = json.loads((ROOT / 'physical/ref_tile/hdie_pc_ctrl_cfg_h9c/spec.json').read_text())
    assert spec.get('params') == PARAMS and spec.get('top') == NEW, ('h9c spec params/top', spec.get('params'))
    sys.path.insert(0, str(ROOT / 'tools/hbm_die_v16/d4g_layers'))
    from l22_e4_compose import header_ports
    np_, ports = header_ports(SN + NEW + '.sv', NEW)
    assert set(PARAMS) <= np_, np_
    c = load(a.contract_in)
    edges0 = hashlib.sha256(json.dumps(c['edges'], sort_keys=True).encode()).hexdigest()
    ports0 = {}
    names = []
    for n, v in c['instances'].items():
        if v['master'] != OLD:
            continue
        assert set(v['ports']) == set(ports), (n, 'port set', sorted(set(v['ports']) ^ set(ports)))
        for port, meta in v['ports'].items():
            assert ports[port] == (meta['direction'], meta['bits']), (n, port, ports[port], meta)
        ports0[n] = copy.deepcopy(v['ports'])
        v.update(master=NEW, source=SN + NEW + '.sv', rtl_deps=[f for f in SRCS if f != SN + NEW + '.sv'], params=dict(PARAMS))
        v['note'] = v.get('note', '') + (' | HBM-H9R11 l25: accepted h9c fallback (closed view hdie_pc_ctrl_cfg_h9c-h9c-cts-155-1aa2ec44b,'
                                         ' exact closed source 1aa2ec44b); legacy pre-BW-safe rate model; no T242 eligibility')
        names.append(n)
    assert len(names) == N_INST, ('instances', len(names))
    nstrap = 0
    for s in c.get('straps', []):
        if s.get('master') == OLD:
            s['master'] = NEW; nstrap += 1
    assert not any(i['master'] == OLD for i in c['instances'].values())
    assert hashlib.sha256(json.dumps(c['edges'], sort_keys=True).encode()).hexdigest() == edges0, 'edges changed'
    assert all(c['instances'][n]['ports'] == ports0[n] for n in names), 'ports changed'
    out = Path(a.contract_out)
    tmp = out.with_name(out.name + '.tmp')
    json.dump(c, open(tmp, 'w')); tmp.replace(out)
    rep = dict(layer='l25_h9c_fallback', status='SOURCE_BOUND_FALLBACK (LEAD admitted ea87fbac pattern)', contract_in=str(a.contract_in),
               contract_in_sha256=sha(a.contract_in), contract_out_sha256=sha(out), instances=names, straps_remastered=nstrap,
               params=PARAMS, closed_view=ident['closed_job'], view_lef=VIEW_LEF, edges_sha256=edges0,
               source_sha256={p: ident['sources'][p]['closed_sha256'] for p in SRCS}, oldrate_model_required=True)
    Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print('L25_H9C_SWAP PASS instances', len(names), 'straps', nstrap, 'EXACT_SOURCE7_PARAMS6_PORTS_AND_EDGES_PRESERVED out', rep['contract_out_sha256'][:16])


def review(a):
    r = json.loads(Path(a.review_in).read_text())
    pred = sha(a.review_in)
    adm = json.loads(Path(a.admitted).read_text())
    d = adm['delta_review_h9bind']
    rec = []
    for x in d['repinned_sources']:
        p = x['path']; cur = sha(ROOT / p)
        assert p in r['source_sha256'], ('pin absent', p)
        assert cur == x['new_sha256'], ('current source is not the H9BIND-reviewed bytes', p)
        if r['source_sha256'][p] == cur:
            continue
        assert r['source_sha256'][p] == x['old_sha256'], ('old pin differs from H9BIND old pin', p)
        r['source_sha256'][p] = cur
        rec.append(dict(path=p, old_sha256=x['old_sha256'], new_sha256=cur, reused_review=x['review']))
    drift = [p for p, s in r['source_sha256'].items() if sha(ROOT / p) != s]
    if drift:
        raise SystemExit(f'L25_REVIEW REFUSED: unreviewed drift {drift} -> new semantic delta review owed')
    r['delta_review_h9r11'] = dict(predecessor_review_sha256=pred, admitted_review=a.admitted, admitted_review_sha256=sha(a.admitted),
                                  admitted_manifest='ea87fbac3af9bb682d93d98d14fcbdd8588275708461d4dac91f26caa65aad4e',
                                  repinned_sources=rec, entries_changed=0, approved_bits=r['approved_bits'],
                                  scope='reuse of the LEAD-admitted H9BIND delta review: identical old->new source bytes; '
                                        'h9c fallback controller has no reviewed entry; no physical/native/token qualification granted')
    r['reviewer'] = r.get('reviewer', '') + ' | HBM-H9R11: H9BIND delta review (543ecfcb, admitted) re-applied, identical source deltas'
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print('L25_REVIEW PASS repinned', len(rec), 'entries', len(r['approved_entries']), 'bits', r['approved_bits'], 'sha', sha(a.out))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    s = sp.add_parser('swap'); s.add_argument('contract_in'); s.add_argument('contract_out'); s.add_argument('--report', required=True)
    s = sp.add_parser('review'); s.add_argument('review_in'); s.add_argument('out')
    s.add_argument('--admitted', default='results/arch/hbm_die11_portage_1020/h9bind/review_h9bind.json')
    a = ap.parse_args()
    (swap if a.cmd == 'swap' else review)(a)


if __name__ == '__main__':
    main()
