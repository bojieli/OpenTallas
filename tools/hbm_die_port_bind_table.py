#!/usr/bin/env python3
"""HBM die port-bind table (OWNER NO STUBS 2026-10-14): tools/hbm_die_port_bind.py JSON (run with --check-glue and the
die kit's generated station / glue RTL) -> a markdown table by master family with the owner of each open row.

    python3 tools/hbm_die_port_bind_table.py PORT_BIND.json --out results/arch/hbm_die_v14/port_bind_v14.md
"""
import argparse, collections, json, re
from pathlib import Path

OWNER = [  # (prefix, owner)
    ('hfd_coll_q', 'die lead (wrappers) + COLL agent (ot_hfd_coll_q, el1014-hbm-p2p-coll.log)'),
    ('hfd_ckgen', 'die lead (PLL macro: vendor views)'),
    ('hfd_attn_half', 'attention halves (hbm-phys-1010 / group B)'), ('hfd_svc', 'stream service (svc)'),
    ('hfd_sm', 'SM compaction (VM/SM 2240)'), ('hfd_lk_ep', 'LKEP (el1013-lkep-split)'),
    ('ot_pdie_serdes', 'die lead (PHY link-layer RTL)'), ('hfd_hc_eng', 'HC engine (hgi-1010/b)'), ('hfd_hc', 'HC/norm'),
    ('hfd_hgi_vms', 'VM/SM 2240 (slices)'), ('hfd_idx_score', 'native IDX'), ('hfd_idx_sel', 'native IDX'),
    ('hfd_sfu', 'SFU (el1013-hbm-sfu)'), ('hfd_su', 'SU.VOP stream'), ('hfd_vm_', 'VM8 CP (vm8)'),
    ('ot_hbm3e_phy', 'die lead (PHY hard IP: DFI controller RTL)'), ('ot_hgi_dma_back', 'DMA back (dbk)'),
    ('hfd_serdes_slab', 'die lead (link/PHY ctrl RTL)'), ('hfd_cmdproc', 'cmdproc (hgi)'), ('hfd_hgi_am', 'MTP'),
    ('hgi_mtp_native', 'MTP'), ('hfd_hgi_idx', 'HGI IDX top-k'), ('hfd_host_slab', 'die lead (host PHY ctrl RTL)'),
    ('ot_hbm_host_phy', 'die lead (PHY hard IP)'), ('hfd_loader', 'DMA/loader (el1011-hbm-dmafs)'), ('hfd_quant', 'quant/QDQ'),
    ('hfd_', 'die lead (generated glue)'), ('ot_', '?')]
GLUE = ('hfd_rrl', 'hfd_ckb', 'hfd_rly', 'hfd_stn', 'hfd_meso', 'hfd_mcast', 'hfd_gath', 'hfd_cdist', 'hfd_att_su_relay')


def owner(m):
    return next(o for p, o in OWNER if m.startswith(p))


def fam(m):
    if m.startswith(GLUE):
        return 'glue:' + re.sub(r'\d+\w*$', '', m).rstrip('_')
    return re.sub(r'_(NE|NW|SE|SW|s\d|lo|hi|q\d|ne|nw|se|sw)$', '', m)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('bind', type=Path)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--title', default='HBM die contract v14 port-bind audit')
    a = ap.parse_args()
    d = json.loads(a.bind.read_text())
    F = collections.defaultdict(lambda: collections.Counter())
    ex = {}
    for mst, r in d['masters'].items():
        f = fam(mst)
        n = r['n_instances']
        ok = bool(r.get('rtl')) and not r.get('die_ports_not_in_rtl') and not r.get('rtl_inputs_unconnected') \
            and not r.get('width_mismatch') and r.get('rtl_header') != 'unparsed'
        F[f]['masters'] += 1
        F[f]['instances'] += n
        F[f]['rtl'] += bool(r.get('rtl'))
        F[f]['bound_masters'] += ok
        F[f]['bound_instances'] += n if ok else 0
        F[f]['die_not_rtl'] += len(r.get('die_ports_not_in_rtl') or [])
        F[f]['in_unconn'] += len(r.get('rtl_inputs_unconnected') or [])
        F[f]['wmis'] += len(r.get('width_mismatch') or [])
        if not ok and f not in ex:
            ex[f] = (mst, {k: (r.get(k) or [])[:4] for k in ('die_ports_not_in_rtl', 'rtl_inputs_unconnected', 'width_mismatch')},
                     r.get('rtl'))
    tm, ti = sum(v['masters'] for v in F.values()), sum(v['instances'] for v in F.values())
    bm, bi = sum(v['bound_masters'] for v in F.values()), sum(v['bound_instances'] for v in F.values())
    L = [f'# {a.title}', '', f'Source: `{d["die_v"]}` (tools/hbm_die_port_bind.py --check-glue, generated station + glue RTL '
         'included). A master is BOUND when RTL exists under its die name, every die port is an RTL port of the same width '
         'and no RTL input is left unconnected.', '',
         f'**{"PASS" if bm == tm else "FAIL"}**: {bm} of {tm} die masters bound ({bi:,} of {ti:,} instances).', '',
         '| family | masters | instances | RTL | bound masters | bound inst | die ports not in RTL | RTL inputs unconn | width mis | owner | example |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|']
    for f, v in sorted(F.items(), key=lambda t: (t[1]['bound_masters'] == t[1]['masters'], -t[1]['instances'])):
        e = ex.get(f)
        es = '' if not e else f"{e[0]}: " + '; '.join(f"{k} {v_}" for k, v_ in e[1].items() if v_) + ('' if e[2] else ' (no RTL)')
        mst0 = f.split(':', 1)[-1]
        L.append(f"| {f} | {v['masters']} | {v['instances']:,} | {v['rtl']} | {v['bound_masters']} | {v['bound_instances']:,} | "
                 f"{v['die_not_rtl']} | {v['in_unconn']} | {v['wmis']} | {owner(mst0)} | {es[:160]} |")
    a.out.write_text('\n'.join(L) + '\n')
    a.out.with_suffix('.json').write_text(json.dumps(dict(bound_masters=bm, masters=tm, bound_instances=bi, instances=ti,
                                                          families={k: dict(v) for k, v in F.items()}), indent=1) + '\n')
    print(json.dumps(dict(bound_masters=bm, masters=tm, bound_instances=bi, instances=ti)))


if __name__ == '__main__':
    main()
