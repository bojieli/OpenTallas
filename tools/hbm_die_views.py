#!/usr/bin/env python3
"""HBM accelerator DS die: hardened block views (LEF + SS/FF Liberty) for the real die placement (CLAUDE HBM-ABSTRACTS,
2026-10-06).

Every die block is a placeholder master of tools/hbm_accel_die_fp.py (round r16g, the adopted variant).  A real view of
a master is a routed block whose LEF has the SAME macro name, size, pin names, widths, layers and pin positions as
the generator's master, so the die netlist, the snap placer and the die-level route bind it unchanged.  Blocks whose
closed sub-blocks have other ports get a thin registered die wrapper (named as the master) around them; the wrapper,
not the generator, absorbs the mismatch.

Modes
  ports  --out DIR [--master M ...]     per master: ports.json (size, faces, per-bit directions from the
                                        die_top_lint DIRECTION MODEL, every pin rectangle), io_place.tcl (ORFS
                                        IO_CONSTRAINTS: place_pin at the generator's pin), ports.svh (port list)
  check  --master M --lef F             a view's LEF against the generator master (size, pin set, layer, position)
  reservation --master M --out DIR      outline + pins only view (reservation slabs: no logic, no nets)
  index                                 physical/hbm_accel_die_views/index.json from the per-kind view.json records
  die    --work DIR --case real|grt     die cases with every indexed real view in place of its generated master
                                        (real: legality / on-track / pin access at k = 1; grt: k-bundled global route,
                                        generator pins bundled with the REAL view's obstructions)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
import die_top_lint as L  # noqa: E402

H = L.H
S = L.S
Q = L.Q
VIEWS = 'physical/hbm_accel_die_views'
KIND_OF = {      # master prefix -> view kind directory
    'hfd_attn_tile': 'attn_tile', 'hfd_su': 'su', 'hfd_sfu': 'sfu', 'hfd_hc': 'hc', 'hfd_index_q': 'index_q',
    'hfd_svc_': 'svc', 'hfd_coll': 'coll', 'hfd_cmdproc': 'cmdproc', 'hfd_vm': 'vm', 'hfd_barrier': 'barrier',
    'hfd_loader': 'loader', 'hfd_router': 'router', 'hfd_quant': 'quant', 'hfd_sm': 'sm', 'hfd_stn_': 'stations',
    'hfd_mcast_': 'stations', 'hfd_gath_': 'stations', 'hfd_cdist_': 'stations', 'hfd_meso_': 'stations',
    'hfd_host_slab': 'host_slab', 'hfd_serdes_slab': 'serdes_slab'}


def kind_of(master):
    for p, k in KIND_OF.items():
        if master == p or (p.endswith('_') and master.startswith(p)):
            return k
    return None


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


_MODEL = {}


def model():
    """(m, pw, M, real): the r16g die model as die_top_lint builds it, generator masters at k = 1, real bindings."""
    if not _MODEL:
        m, pw, M, tool = L.build('hbm')
        real = L.real_blocks('hbm', m)
        L.CUR_M['_by'] = {it.name: it for it in m['insts']}
        L.CUR_M['_real'] = real
        _MODEL.update(m=m, pw=pw, M=M, real=real, tool=tool)
    return _MODEL['m'], _MODEL['pw'], _MODEL['M'], _MODEL['real']


def port_dirs():
    """master -> port -> per-bit direction ('in' / 'out' / 'x' conflicting / '?'), exactly as die_top_lint's stubs."""
    m, pw, M, real = model()
    by = {it.name: it for it in m['insts']}
    pdir = defaultdict(dict)
    narrow = set()
    for bus in m['buses']:
        bid, cls, bits, eps = bus
        for j, (inst, port) in enumerate(eps):
            if inst == 'TOP':
                continue
            mst = by[inst].master
            if mst in real and mst != 'hfd_sm':
                continue
            seg, _ = L.endpoint_dirs('hbm', real, by, bus, j)
            if seg is None:
                continue
            w = pw.get((mst, port), bits)
            cur = pdir[mst].setdefault(port, ['?'] * w)
            if bits < w:
                narrow.add((mst, port))
            for a, b, d in seg:
                for i in range(a, b):
                    cur[i] = d if cur[i] in ('?', d) else 'x'
    return pdir, narrow


def segs(arr):
    out, i = [], 0
    while i < len(arr):
        j = i
        while j < len(arr) and arr[j] == arr[i]:
            j += 1
        out.append([i, j, arr[i]])
        i = j
    return out


def master_record(name):
    m, pw, M, real = model()
    mst = M[name]
    wmap = {p: pw.get((name, p), 0) for p in mst.order}
    rects = S.pin_rects(mst, 1, wmap)
    pdir, narrow = port_dirs()
    insts = [it for it in m['insts'] if it.master == name]
    ports = {}
    for nm, layer, r in rects:
        base, idx = re.match(r'^(.*)\[(\d+)\]$', nm).groups()
        p = ports.setdefault(base, dict(bits=0, layer=layer, pins=[]))
        p['bits'] = max(p['bits'], int(idx) + 1)
        p['pins'].append([nm, layer] + [round(v, 4) for v in r])
    for base, p in ports.items():
        spec = mst.ports.get(base)
        p['face'] = spec[2] if spec and spec[0] == 'face' else ('xy' if spec and spec[0] == 'xy' else '?')
        arr = pdir.get(name, {}).get(base)
        p['dir_segments'] = segs(arr) if arr else []
        kinds = set(arr or ['?'])
        p['direction'] = ('input' if kinds <= {'in', '?'} or (len(kinds - {'?'}) > 1 and (name, base) in narrow)
                          else 'output' if kinds <= {'out'} else 'inout')
    return dict(master=name, kind=kind_of(name), w_um=round(mst.w, 4), h_um=round(mst.h, 4), obs_top=mst.obs_top,
                note=mst.note, instances=len(insts), orients=sorted({it.orient for it in insts}),
                inst_names=[it.name for it in insts], ports=ports,
                generator=dict(file='tools/hbm_accel_die_fp.py', sha256=sha(ROOT / 'tools/hbm_accel_die_fp.py'),
                               round=H.FINAL_ROUND))


def io_tcl(rec):
    L_ = [f"# {rec['master']}: every die pin at the generator's position (tools/hbm_die_views.py ports, "
          f"{rec['generator']['round']})"]
    for p in sorted(rec['ports']):
        for nm, layer, x0, y0, x1, y1 in rec['ports'][p]['pins']:
            L_.append(f'place_pin -pin_name {{{nm}}} -layer {layer} -location {{{(x0 + x1) / 2:.4f} {(y0 + y1) / 2:.4f}}} '
                      f'-pin_size {{{x1 - x0:.4f} {y1 - y0:.4f}}}')
    return '\n'.join(L_) + '\n'


def svh(rec):
    return ',\n'.join(f"    {rec['ports'][p]['direction']} wire [{rec['ports'][p]['bits'] - 1}:0] {p}"
                      for p in sorted(rec['ports'])) + '\n'


def cmd_ports(a):
    m, pw, M, real = model()
    names = a.master or sorted(n for n in M if n.startswith('hfd_') and n != 'hfd_sm' or n == 'hfd_sm')
    out = Path(a.out)
    summary = {}
    for n in names:
        if n not in M:
            raise SystemExit(f'no generator master {n}')
        rec = master_record(n)
        d = out / n
        d.mkdir(parents=True, exist_ok=True)
        (d / 'ports.json').write_text(json.dumps(rec, indent=0) + '\n')
        (d / 'io_place.tcl').write_text(io_tcl(rec))
        (d / 'ports.svh').write_text(svh(rec))
        summary[n] = dict(kind=rec['kind'], w=rec['w_um'], h=rec['h_um'], instances=rec['instances'],
                          ports={p: (v['bits'], v['face'], v['direction']) for p, v in rec['ports'].items()})
    (out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    print(json.dumps({k: (v['kind'], v['w'], v['h'], v['instances']) for k, v in summary.items()}))


# ------------------------------------------------------------------------------------------------ LEF parsing
def parse_lef(path):
    t = Path(path).read_text()
    name = re.search(r'^MACRO (\S+)', t, re.M).group(1)
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', t).groups())
    pins, pg = {}, {}
    for pm in re.finditer(r'\n\s*PIN (\S+)\n(.*?)\n\s*END \1[ \t]*(?=\n)', t, re.S):
        body = pm.group(2)
        rects = []
        cur = None
        for ln in body.split('\n'):
            mm = re.match(r'\s*LAYER (\S+)', ln)
            if mm:
                cur = mm.group(1)
            mr = re.match(r'\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', ln)
            if mr and cur:
                rects.append((cur, tuple(float(v) for v in mr.groups())))
        dm = re.search(r'DIRECTION (\S+)', body)
        rec = dict(dir=(dm.group(1) if dm else None), rects=rects)
        if 'USE POWER' in body or 'USE GROUND' in body:
            pg[pm.group(1)] = rec
        else:
            pins[pm.group(1)] = rec
    obs = defaultdict(int)
    om = re.search(r'\n\s*OBS\n(.*?)\n\s*END\n', t, re.S)
    if om:
        cur = None
        for ln in om.group(1).split('\n'):
            mm = re.match(r'\s*LAYER (\S+)', ln)
            if mm:
                cur = mm.group(1)
            elif cur and 'RECT' in ln:
                obs[cur] += 1
    return dict(name=name, w=w, h=h, pins=pins, pg=pg, obs_rects=dict(obs), text=t)


def face_of(rects, w, h, eps=0.5):
    b = rects[0][1]
    if b[1] <= eps:
        return 'S'
    if b[3] >= h - eps:
        return 'N'
    if b[0] <= eps:
        return 'W'
    if b[2] >= w - eps:
        return 'E'
    return 'xy'


def check_lef(master, lef, tol=0.0125):
    """compare a view LEF to the generator master: returns dict(verdict, ...)."""
    rec = master_record(master)
    r = parse_lef(lef)
    out = dict(master=master, lef=str(lef), macro=r['name'], size_view=[r['w'], r['h']],
               size_gen=[rec['w_um'], rec['h_um']])
    problems = []
    if r['name'] != master:
        problems.append(f"macro name {r['name']} != {master}")
    if abs(r['w'] - rec['w_um']) > 0.01 or abs(r['h'] - rec['h_um']) > 0.01:
        problems.append(f"size {r['w']} x {r['h']} != {rec['w_um']} x {rec['h_um']}")
    gen = {}
    for p, v in rec['ports'].items():
        for nm, layer, x0, y0, x1, y1 in v['pins']:
            gen[nm] = (p, layer, (x0 + x1) / 2, (y0 + y1) / 2)
    missing = sorted(set(gen) - set(r['pins']))
    extra = sorted(set(r['pins']) - set(gen))
    moved, layer_bad, face_bad = [], [], []
    for nm in set(gen) & set(r['pins']):
        _, layer, cx, cy = gen[nm]
        rs = r['pins'][nm]['rects']
        if not any(ly == layer for ly, _ in rs):
            layer_bad.append(nm)
            continue
        ok = any(ly == layer and b[0] - tol <= cx <= b[2] + tol and b[1] - tol <= cy <= b[3] + tol for ly, b in rs)
        if not ok:
            moved.append(nm)
        gface = rec['ports'][gen[nm][0]]['face']
        vf = face_of(rs, r['w'], r['h'])
        if gface in 'NSEW' and vf != gface:
            face_bad.append(nm)
    out.update(gen_pins=len(gen), view_pins=len(r['pins']), missing=len(missing), extra=len(extra),
               moved=len(moved), wrong_layer=len(layer_bad), wrong_face=len(face_bad),
               wrong_face_examples=sorted(face_bad)[:8], missing_examples=missing[:8], extra_examples=extra[:8],
               moved_examples=sorted(moved)[:8], wrong_layer_examples=sorted(layer_bad)[:8],
               pg_pins={k: sorted({ly for ly, _ in v['rects']}) for k, v in r['pg'].items()},
               obs_layers=sorted(r['obs_rects']))
    obs_hi = [ly for ly in r['obs_rects'] if re.fullmatch(r'M(\d+)', ly) and int(ly[1:]) > rec['obs_top']]
    out['obs_above_generator'] = obs_hi
    if missing or extra or layer_bad or face_bad:
        problems.append(f'pins: {len(missing)} missing, {len(extra)} extra, {len(face_bad)} wrong face, '
                        f'{len(layer_bad)} wrong layer')
    out['positions'] = 'exact' if not moved else f'{len(moved)} pins off the generator position (same face)'
    out['problems'] = problems
    out['verdict'] = 'MATCH' if not problems else 'MISMATCH'
    return out


def cmd_check(a):
    print(json.dumps(check_lef(a.master, a.lef), indent=1))


def cmd_reservation(a):
    m, pw, M, real = model()
    mst = M[a.master]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    t, n = S.lef_text(mst, 1, {p: pw.get((a.master, p), 0) for p in mst.order})
    t = t.replace('tools/dsrom_s81_fulldie.py', 'tools/hbm_accel_die_fp.py via tools/hbm_die_views.py reservation')
    (out / f'{a.master}.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + t + 'END LIBRARY\n')
    rec = master_record(a.master)
    view = dict(schema='opentallas.hbm_die_view.v1', master=a.master, kind=rec['kind'], status='reservation',
                lef=f'{a.master}.lef', lib=None, size_um=[rec['w_um'], rec['h_um']], instances=rec['instances'],
                pins=n, note='reservation slab: outline + obstruction M1-M7 only, no logic, no die nets, no timing '
                'view (nothing to time); the die route crosses it on M8/M9 as in r16g')
    (out / 'view.json').write_text(json.dumps(view, indent=1) + '\n')
    print(json.dumps(view))


def cmd_index(a):
    base = ROOT / VIEWS
    m, pw, M, real = model()
    rows = {}
    for vj in sorted(base.glob('*/view*.json')):
        v = json.loads(vj.read_text())
        v['dir'] = str(vj.parent.relative_to(ROOT))
        rows[v['master']] = v
    need = sorted({it.master for it in m['insts'] if it.master.startswith('hfd_')})
    idx = dict(schema='opentallas.hbm_die_views_index.v1', die='HBM accelerator DS die', round=H.FINAL_ROUND,
               generator_sha256=sha(ROOT / 'tools/hbm_accel_die_fp.py'),
               status_values=['closed', 'interim-not-closed', 'reservation', 'missing'],
               masters={}, counts=defaultdict(int))
    for n in need:
        v = rows.get(n)
        st = v['status'] if v else 'missing'
        idx['masters'][n] = dict(kind=kind_of(n), status=st, instances=sum(it.master == n for it in m['insts']),
                                 **({k: v[k] for k in ('dir', 'lef', 'lib', 'check', 'source') if k in v} if v else {}))
        idx['counts'][st] += 1
    idx['counts'] = dict(idx['counts'])
    (base / 'index.json').write_text(json.dumps(idx, indent=1) + '\n')
    print(json.dumps(idx['counts']))


# ------------------------------------------------------------------------------------------------ die with real views
def real_views(index_path):
    idx = json.loads(Path(index_path).read_text())
    out = {}
    for n, v in idx['masters'].items():
        if v['status'] in ('closed', 'interim-not-closed', 'reservation') and v.get('lef'):
            out[n] = ROOT / v['dir'] / v['lef']
    return out


def cmd_die(a):
    m, pw, M, real = model()
    views = real_views(a.index)
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    gen_text = {}
    if a.case == 'real':
        H.case_real(m, work)
        # replace the generated macros that have a real view by the view's LEF
        el = (work / 'elements.lef').read_text()
        for n, lef in views.items():
            el, k = re.subn(r'(# [^\n]*\n)?MACRO ' + re.escape(n) + r'\n.*?\nEND ' + re.escape(n) + r'\n', '', el,
                            flags=re.S)
            assert k == 1, (n, k)
            gen_text[n] = lef
        (work / 'elements.lef').write_text(el)
        lefs = []
        for n, lef in views.items():
            t = parse_lef(lef)['text']
            body = re.search(r'(MACRO .*?END ' + re.escape(n) + r')', t, re.S).group(1)
            lefs.append(body)
        (work / 'views.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lefs)
                                        + '\nEND LIBRARY\n')
        run = (work / 'run.tcl').read_text().replace('foreach f {phy.lef serdes.lef ucie.lef elements.lef}',
                                                     'foreach f {phy.lef serdes.lef ucie.lef elements.lef views.lef}')
        (work / 'run.tcl').write_text(run)
    else:
        cov = dict(H.COV)
        H.case_grt(m, work, a.k, a.tag, a.iters, cov)
        el = (work / 'elements.lef').read_text()
        for n, lef in views.items():
            r = parse_lef(lef)
            om = re.search(r'\n(\s*OBS\n.*?\n\s*END)\n', r['text'], re.S)
            obs = om.group(1) if om else '  OBS\n  END'
            # bundled tech LEF (k > 1) defines the metal layers only: keep the view's metal obstructions
            keep, cur = [], True
            for ln in obs.split('\n'):
                mm = re.match(r'\s*LAYER (\S+)', ln)
                if mm:
                    cur = bool(re.fullmatch(r'M[1-9]', mm.group(1)))
                if cur or not ln.strip().startswith(('LAYER', 'RECT', 'POLYGON')):
                    if cur or not mm:
                        keep.append(ln)
            obs = '\n'.join(keep)
            pat = r'(MACRO ' + re.escape(n) + r'\n.*?)\n  OBS\n.*?\n  END\n(END ' + re.escape(n) + r'\n)'
            el, k = re.subn(pat, lambda mm: mm.group(1) + '\n' + obs + '\n' + mm.group(2), el, flags=re.S)
            assert k == 1, (n, k)
        (work / 'elements.lef').write_text(el)
    man = json.loads((work / 'manifest.json').read_text())
    man['real_views'] = {n: dict(lef=str(p.relative_to(ROOT)), sha256=sha(p)) for n, p in views.items()}
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(dict(case=a.case, real_views=len(views), work=str(work))))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='mode', required=True)
    p = sp.add_parser('ports')
    p.add_argument('--out', required=True)
    p.add_argument('--master', action='append')
    p.set_defaults(fn=cmd_ports)
    p = sp.add_parser('check')
    p.add_argument('--master', required=True)
    p.add_argument('--lef', required=True)
    p.set_defaults(fn=cmd_check)
    p = sp.add_parser('reservation')
    p.add_argument('--master', required=True)
    p.add_argument('--out', required=True)
    p.set_defaults(fn=cmd_reservation)
    p = sp.add_parser('index')
    p.set_defaults(fn=cmd_index)
    p = sp.add_parser('die')
    p.add_argument('--work', required=True)
    p.add_argument('--case', choices=['real', 'grt'], required=True)
    p.add_argument('--index', default=str(ROOT / VIEWS / 'index.json'))
    p.add_argument('--k', type=int, default=16)
    p.add_argument('--iters', type=int, default=50)
    p.add_argument('--tag', default='views')
    p.set_defaults(fn=cmd_die)
    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == '__main__':
    raise SystemExit(main())
