#!/usr/bin/env python3
"""TOK-ALL-17: check tb_dense_gb_slice logs (six u_s_0S frames, die return cone, capc5r) against the checkpoint rows of
each frame's lower_xs vectors.  Per frame: return words == the frame plan at ONE common shift; landed words (LND) ==
returned words in order at ONE constant latency; CAP words == the union of the six frames' checkpoint rows.
Measured: XS go edge, per-frame first/last return, landed latency, last capture, GO -> last capture."""
import argparse, hashlib, json, re
from pathlib import Path
FR = ['u_f_0L01', 'u_f_0L02', 'u_f_0L03', 'u_f_0R01', 'u_f_0R02', 'u_f_0R03']


def expected_caps(v):
    m = json.loads((v/'meta.json').read_text())
    cfg = int((v/'capture.hex').read_text(), 16); rbase = (cfg >> 29) & 65535; obase = cfg & 4095
    out = []
    for row, val in m['rows'].items():
        relative = ((1 << 14)+int(row))-rbase
        column, elem = divmod(relative, 64); leaf, block = column % 5, column//5
        addr = obase+64*block+elem; face = 'S' if leaf < 3 else 'N'
        port = 2*(leaf if face == 'S' else leaf-3)+((addr >> 2) & 1)
        out.append((face, port, addr, int(val['bf16']) << 16))
    return m, out


def check(vecs, log, byp):
    text = log.read_text(); errors = []; frames = {}
    cap = [(f, int(e), int(p), int(a), int(d, 16)) for f, e, p, a, d in
           re.findall(r'^CAP ([SN]) (\d+) (\d+) (\d+) ([0-9a-f]+)$', text, re.M)]
    ctrl = [(int(e), int(c), int(g)) for e, c, g in re.findall(r'^XCTRL (\d+) cfg=(\d) go=(\d)', text, re.M)]
    go = next((e for e, c, g in ctrl if g), None)
    allexp = []
    for j, f in enumerate(FR):
        m, exp = expected_caps(vecs[f]); allexp += exp
        ret = [(int(e), int(w, 16)) for e, w in re.findall(rf'^RET {j} (\d+) ([0-9a-f]+)$', text, re.M)]
        lnd = [(int(e), int(w, 16)) for e, w in re.findall(rf'^LND {j} (\d+) ([0-9a-f]+)$', text, re.M)]
        want = m['plan']['ret']
        rr = [[e, (w >> 1) & 0xffffffff, (w >> 33) & 0xffffffff, (w >> 65) & 1] for e, w in ret]
        if any(not w & 1 for _, w in ret): errors.append(f"{f}: return word missing valid")
        shift = rr[0][0]-want[0][0] if rr and want else None
        if len(rr) != len(want): errors.append(f'{f}: return count {len(rr)} != {len(want)}')
        elif any(r != [w[0]+shift]+w[1:] for r, w in zip(rr, want)):
            errors.append(f'{f}: returns differ from plan at common shift {shift}')
        lat = sorted({b[0]-a[0] for a, b in zip(ret, lnd)})
        if [w for _, w in lnd] != [w for _, w in ret]: errors.append(f'{f}: landed words != returned words')
        if len(lat) > 1: errors.append(f'{f}: landed latency not constant {lat}')
        keys = {(fa, p, a) for fa, p, a, _ in exp}
        mine = [e for fa, e, p, a, d in cap if (fa, p, a) in keys]
        frames[f] = dict(master=m['die_master'], rows=[int(x) for x in m['rows']], return_words=len(rr), plan_shift=shift,
                         first_return=ret[0][0] if ret else None, last_return=ret[-1][0] if ret else None,
                         landed_latency=lat[0] if len(lat) == 1 else lat, last_landed=lnd[-1][0] if lnd else None,
                         last_capture=max(mine) if mine else None,
                         go_to_last_capture=(max(mine)-go) if mine and go is not None else None)
    actual = [(f, p, a, d) for f, e, p, a, d in cap]
    if sorted(actual) != sorted(allexp):
        errors.append(f'CAP words: {len(actual)} actual vs {len(allexp)} checkpoint; missing {len(set(allexp)-set(actual))}, extra {len(set(actual)-set(allexp))}')
    end = re.search(r'^SLICE_END cycles=(\d+) events=(\d+) consumed=(\d+) xs_fault=(\d) frame_fault=(\d+) land_fault=(\d) cap_fault=(\d) mutant=(\d) byp=(\d)', text, re.M)
    lf = re.search(r'^LAND_FAULT (\d+)', text, re.M)
    if not end: errors.append('missing terminal marker')
    else:
        if end[2] != end[3] or int(end[4]) or int(end[5]) or int(end[7]): errors.append('unconsumed input or component fault: '+end[0])
    return dict(status='PASS' if not errors else 'FAIL', errors=errors, byp=byp, xs_go=go, ctrl=ctrl, frames=frames,
                capture_words=len(cap), checkpoint_words=len(allexp), last_capture=max((e for _, e, *_ in cap), default=None),
                land_fault_first=int(lf[1]) if lf else None, log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())


def main():
    p = argparse.ArgumentParser(); p.add_argument('--vec-root', type=Path, required=True); p.add_argument('--run', type=Path, required=True)
    a = p.parse_args()
    vecs = {f: a.vec_root/f for f in FR}
    d = {}
    for n, b in (('landed', 0), ('bypass', 1), ('mut_input', 0), ('swapimg', 0)):
        lg = a.run/f'run_{n}.log'
        if lg.exists(): d[n] = check(vecs, lg, b)
    (a.run/'check.json').write_text(json.dumps(d, indent=1)+'\n')
    for n, r in d.items():
        print(n, r['status'], r['errors'][:3], 'go', r['xs_go'], 'last_cap', r['last_capture'], 'land_fault', r['land_fault_first'])
        for f, x in r['frames'].items():
            print('  ', f, x['master'], 'ret', x['return_words'], x['first_return'], x['last_return'], 'shift', x['plan_shift'],
                  'lat', x['landed_latency'], 'last_cap', x['last_capture'], 'go->cap', x['go_to_last_capture'])


if __name__ == '__main__':
    main()
