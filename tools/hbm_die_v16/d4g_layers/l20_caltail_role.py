#!/usr/bin/env python3
"""LH-UNREAD 10-19 l20: universal-calendar capacity tail -> role-width calendars (epcal_<q>, vmfc_<q>).

Each epcal_* / vmfc_* hfd_hgi_vm_calendar_f20 instance is re-mastered to hfd_hgi_vm_calendar_f20_role #(W) where W is
derived from the contract (the used universal payload prefix; asserted 19 / 38 (epcal_SW) / 89 (vmfc)).  Every edge
leaving a universal payload field (client_seq .. lg_local_write) is remapped bit-exactly to payload[off+lo, off+hi):
same consumer bits, same edge timing (role payload = universal calendar[W-1:0] on the same edge).  The universal
capacity tail calendar[186:W] has no port any more, and the role core REJECTS a nonzero tail row with its existing
sticky fault (bench run_calendar_f20_role.sh).  calendar_v / done / ordinal / fault / tgt_* ports are unchanged.
No hard view is admitted: the role master needs its own physical closure (hv16_vm_cal_f20_ww stays the universal view).
"""
import argparse, copy, gzip, hashlib, json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
OLD = 'hfd_hgi_vm_calendar_f20'
NEW = 'hfd_hgi_vm_calendar_f20_role'
SRC = 'rtl/hbm_accel/generic/vm/static/' + NEW + '.sv'
UNI = 'rtl/hbm_accel/generic/vm/static/hfd_hgi_vm_calendar.sv'
DEPS = ['rtl/hbm_accel/generic/vm/static/ot_vms_calendar_static_xcap.sv',
        'rtl/hbm_accel/generic/vm/static/ot_static_program_target.sv']
EXPECT = {'epcal_SW': 38}


def layout():
    lay = {n: (int(lo), int(w)) for n, lo, w in
           re.findall(r'assign\s+(\w+)=calendar\[(\d+)\+:(\d+)\];', (ROOT / UNI).read_text())}
    assert len(lay) == 17 and sum(w for _, w in lay.values()) == 187, lay
    return lay


def apply(original):
    c = copy.deepcopy(original); lay = layout(); rep = []
    names = sorted(n for n in c['instances'] if n.startswith(('epcal_', 'vmfc_')))
    assert len(names) == 8, names
    for n in names:
        v = c['instances'][n]
        if v['master'] != OLD:
            raise ValueError(f'{n}: unexpected master {v["master"]}')
        used, moved = set(), 0
        for e in c['edges']:
            s = e['source']
            if s[0] == n and s[1] in lay:
                off, w = lay[s[1]]; assert 0 <= s[2] < s[3] <= w, (n, s)
                used.update(range(off + s[2], off + s[3]))
        W = max(used) + 1
        if used != set(range(W)):
            raise ValueError(f'{n}: used payload is not a dense prefix')
        if W != EXPECT.get(n, 19 if n.startswith('epcal_') else 89):
            raise ValueError(f'{n}: unexpected role width {W}')
        for e in c['edges']:
            s = e['source']
            if s[0] == n and s[1] in lay:
                off, _ = lay[s[1]]
                e['source'] = [n, 'payload', off + s[2], off + s[3]]
                e['basis'] = e.get('basis', '') + f' | l20: role calendar payload[{off + s[2]}+:{s[3] - s[2]}] (= universal {s[1]}[{s[2]}+:{s[3] - s[2]}])'
                moved += 1
        for e in c['edges']:
            if e['sink'][0] == n:
                assert e['sink'][1] not in lay, e
        ports = {p: d for p, d in v['ports'].items() if p not in lay}
        ports['payload'] = {'direction': 'output', 'bits': W}
        v.update(master=NEW, source=SRC, rtl_deps=list(DEPS), params={'W': W}, ports=ports)
        v['note'] = v.get('note', '') + f' | l20: role calendar W{W}; tail [186:{W}] removed and rejected by the existing sticky fault'
        for s in c['straps']:
            if s.get('inst') == n:
                s['master'] = NEW
        # whole universal tail ports were recorded as open outputs: they no longer exist on the role master
        oo = [x for x in c.get('open_outputs', []) if x[0] == n and x[1] in lay]
        for x in oo:
            off, w = lay[x[1]]
            if x[2] != w or off < W:
                raise ValueError(f'{n}: open output {x} overlaps the used payload')
        c['open_outputs'] = [x for x in c.get('open_outputs', []) if not (x[0] == n and x[1] in lay)]
        rep.append(dict(instance=n, W=W, removed_tail_bits=187 - W, edges_remapped=moved, open_output_records_dropped=len(oo)))
    if isinstance(c.get('masters'), dict):
        m = c['masters']
        for k, d in ((OLD, -8), (NEW, 8)):
            if isinstance(m.get(k, 0), int):
                m[k] = m.get(k, 0) + d
                if m[k] == 0: m.pop(k)
    r = dict(layer='l20_caltail_role', master=NEW, source=SRC, instances=rep,
             removed_tail_bits=sum(x['removed_tail_bits'] for x in rep),
             universal_sha256=hashlib.sha256((ROOT / UNI).read_bytes()).hexdigest(),
             role_sha256=hashlib.sha256((ROOT / SRC).read_bytes()).hexdigest(),
             successful_edges_added=0, bench='rtl/hbm_accel/generic/vm/static/fill_universal_0600/run_calendar_f20_role.sh',
             qualification='SOURCE_ONLY_NEEDS_TILE_CLOSURE (role master; universal hard view hv16_vm_cal_f20_ww not reused)')
    return c, r


def main():
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('inp'); p.add_argument('out'); p.add_argument('--report', required=True)
    a = p.parse_args()
    with (gzip.open(a.inp, 'rt') if a.inp.endswith('.gz') else open(a.inp)) as f:
        c = json.load(f)
    c, r = apply(c)
    Path(a.out).write_text(json.dumps(c, separators=(',', ':')) + '\n'); Path(a.report).write_text(json.dumps(r, indent=1) + '\n')
    print(f"L20_CALTAIL_ROLE removed_tail_bits={r['removed_tail_bits']} instances={len(r['instances'])}")


if __name__ == '__main__':
    main()
