#!/usr/bin/env python3
"""c_ctl_prog: the compiled tt_ctlm deployment image on the cut die slice qwc_slice_ctl (dv2f14bn netlist: qfd_sys_face +
qfd_tt_ctlm_dv + the die relays between them), QLB-PROG 10-18 (G-C3).

  prep IMG_DIR OUT_DIR   -> OUT_DIR/prog_status.txt (the neighbours' compiled status, relative to each decode stage's
                            edge 0, already shifted by the die relays from the slice-edge pins to tt_ctlm: what the bench
                            drives at the slice edge), OUT_DIR/prog_expect.json (the compiled events at the slice pins)
  check IMG_DIR LOG      -> CPROG PASS / FAIL: every slice command at the dvs_W5 cmd_wi pin (slice output, after the die's
                            R_CMD relays), every ROM command go / XPF arm at the dvs_W5 hr_wi pin, every native command at
                            native59, every head issue and LOCAL start on its compiled edge relative to the stage's edge
                            0 (the edge tt_ctlm's dh pin register captures h_start), the BOOT SETID after the seal; no
                            tt_ctlm fault.  The slice's own reset / programme-load checks stay in the smoke bench.
The die relay ages used are the compiled relay table's (ctlm_image.json relay); a die whose landed lanes add age shows
up here as every event of that lane off by the same number of edges (reported).
"""
import json
import sys
from collections import Counter
from pathlib import Path


def prep(img_dir, out):
    img = json.loads((Path(img_dir) / 'ctlm_image.json').read_text())
    R = img['relay']
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    ag = dict(su_busy=0, stn_busy=0)
    lines = []
    for s in img['status']:
        e, f, v = s['edge'], s['field'], s['value']
        if f in ag:
            ag[f] = v
            lines.append((e - R['R_AG'], 7, (ag['stn_busy'] << 9) | (ag['su_busy'] << 1)))
        elif f == 'su_prog':
            lines.append((e - R['R_SS'], 8, (v << 45) | (v << 29)))
        else:                                 # native59.native_ret -> tt_ctlm.native_ret: 0 relays
            lines.append((e, 9, (v << 1) | 1))
    lines.sort(key=lambda x: x[0])
    if lines[0][0] < 1:
        raise SystemExit('status before the stage edge 0 at the slice edge')
    (out / 'prog_status.txt').write_text(f'{len(lines)}\n' + ''.join(f'{e} {k} {v:x}\n' for e, k, v in lines))
    (out / 'prog_expect.json').write_text(json.dumps(img['expected'], indent=1) + '\n')
    print(f'c_ctl_prog prep: {len(lines)} status events -> {out}')


def check(img_dir, log):
    img = json.loads((Path(img_dir) / 'ctlm_image.json').read_text())
    X, R, C = img['expected'], img['relay'], img['constants']
    e0s, dw7, got, errs, info = [], None, [], [], Counter()
    cmdi, hri, ages = [], [], {}
    for line in open(log):
        p = line.split()
        if len(p) < 2 or not p[0].isdigit():
            continue
        cy, k = int(p[0]), p[1]
        if k == 'E0':
            e0s.append((cy, int(p[2])))
        elif k == 'PEND':
            info['pend'] = cy
        elif k == 'DW7':
            dw7 = cy
        elif k == 'CMD':
            got.append((cy, 'CMD', int(p[2], 16)))
        elif k == 'HRROM':
            got.append((cy, 'HRROM', None))
        elif k == 'HRXPF':
            got.append((cy, 'HRXPF', int(p[2], 16)))
        elif k == 'NAT':
            got.append((cy, 'NAT', None))
        elif k == 'ISSUE':
            got.append((cy, 'ISSUE', (int(p[2]), int(p[3]))))
        elif k == 'LOC':
            got.append((cy, 'LOC', (p[2], int(p[3]))))
        elif k == 'CF':
            errs.append(f'tt_ctlm fault rise at {cy}: {" ".join(p[2:])}')
        elif k == 'CMDI':
            cmdi.append((cy, int(p[2], 16)))
        elif k == 'HRI':
            hri.append(cy)
        elif k == 'AGE':
            ages['R_AG'], ages['R_SS'] = int(p[3]), int(p[5])
        elif k == 'SFF':
            info['sys_face_fault'] += 1
            info['sys_face_fault_first'] = info['sys_face_fault_first'] or cy
    if dw7 is None:
        errs.append('DW7 never reached tt_ctlm (no programme load)')
    # die lane ages measured on this slice vs the ages the image was compiled with
    cmdo = [(cy, v) for cy, k, v in got if k == 'CMD']
    hro = [cy for cy, k, v in got if k == 'HRROM']
    if cmdi and len(cmdi) == len(cmdo) and all(a[1] == b[1] for a, b in zip(cmdi, cmdo)):
        ages['R_CMD'] = sorted({b[0] - a[0] for a, b in zip(cmdi, cmdo)})
    if hri and len(hri) == len(hro):
        ages['R_HR'] = sorted({b - a for a, b in zip(hri, hro)})
    for key, v in ages.items():
        want = R[key]
        if (v if isinstance(v, int) else (v[0] if len(v) == 1 else None)) != want:
            errs.append(f'die lane age {key}: measured {v}, image compiled with {want} ({R.get("source", "relay table")})')
    info['ages'] = ages
    exp = []
    if dw7 is not None:
        for x in X['boot_cmd_after_seal']:
            exp.append((dw7 + 1 + x['edge'] + R['R_CMD'], 'CMD', int(x['cmd'], 16)))
    # decode stages whose whole compiled window lies inside the run (the run ends at PEND)
    span = max([x['edge'] for v in X.values() for x in v] + [s['edge'] for s in img['status']])
    pend = info.get('pend', 0)
    dec = [(e, s) for e, s in e0s if 1 <= s <= 36 and e + span <= pend]
    info['partial_stages'] = len([1 for e, s in e0s if 1 <= s <= 36 and e + span > pend])
    for e0, s in e0s:
        if s == 0:
            for x in X['stage0_local']:
                exp.append((e0 + x['edge'], 'LOC', ('EMB', 0)))
    for e0, s in dec:
        exp += [(e0 + x['edge'], 'CMD', int(x['cmd'], 16)) for x in X['cmd_at_w5_pin']]
        exp += [(e0 + x['edge'], 'HRROM', None) for x in X['hr_rom_go_at_w5_pin']]
        exp += [(e0 + x['edge'], 'HRXPF', int(x['xpf72'], 16)) for x in X['hr_xpf_arm_at_w5_pin']]
        exp += [(e0 + x['edge'], 'NAT', None) for x in X['native_go_at_tt_ctlm']]
        exp += [(e0 + x['edge'], 'ISSUE', (x['pc'], x['unit'])) for x in X['me_issue']]
        exp += [(e0 + x['edge'], 'LOC', (x['kind'], x['base'])) for x in X['local_at_tt_ctlm']]
    cut = min([e for e, s in e0s if 1 <= s <= 36 and e + span > pend] + [pend + 1])
    got = [g for g in got if g[0] < cut]        # events of a stage cut by the end of the run are not judged
    se, sg = set(exp), set(got)
    miss, extra = sorted(se - sg, key=lambda x: x[0]), sorted(sg - se, key=lambda x: x[0])
    # a uniformly shifted lane (die landing age differs from the relay table) is reported as one offset
    for kind in ('CMD', 'HRROM', 'HRXPF'):
        m = [e for e in miss if e[1] == kind]
        x = [g for g in extra if g[1] == kind]
        if m and len(m) == len(x):
            offs = sorted({g[0] - e[0] for e, g in zip(m, x)})
            errs.append(f'{kind}: {len(m)} events off by {offs} edges vs the compiled relay age')
    for e in miss[:10]:
        errs.append(f'missing {e[1]} at {e[0]} {e[2] if not isinstance(e[2], int) else hex(e[2])[:36]}')
    for g in extra[:10]:
        errs.append(f'unexpected {g[1]} at {g[0]} {g[2] if not isinstance(g[2], int) else hex(g[2])[:36]}')
    if len(dec) < 2:
        errs.append(f'only {len(dec)} complete decode stages in the run (need >= 2)')
    v = 'PASS' if not errs else 'FAIL'
    print(f'CPROG {v}: {len(se & sg)}/{len(se)} compiled events on their edges, {len(dec)} complete decode stages '
          f'(+{info["partial_stages"]} cut by the run end) '
          f'(E0 {[e for e, _ in e0s]}), unexpected {len(extra)}, sys_face faults {info["sys_face_fault"]} '
          f'(first @{info["sys_face_fault_first"] or "-"}), lane ages measured {info["ages"]}')
    for e in errs[:16]:
        print('   ', e)
    return 0 if v == 'PASS' else 1


if __name__ == '__main__':
    if sys.argv[1] == 'prep':
        prep(sys.argv[2], sys.argv[3])
    else:
        sys.exit(check(sys.argv[2], sys.argv[3]))
