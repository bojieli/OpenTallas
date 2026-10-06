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
    'hfd_attn_tile': 'attn_tile', 'hfd_su': 'su', 'hfd_sfu': 'sfu', 'hfd_hc': 'hc', 'hfd_index_q': 'index_q', 'hfd_index_q_': 'index_q',
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


def derived_record(name):
    """a derived master (a generator master split into separately hardened views, tools/hbm_die_split.py): its
    committed ports.json under physical/hbm_accel_die_views/*/split/<name>/, else None."""
    for f in sorted((ROOT / 'physical/hbm_accel_die_views').glob(f'*/split/{name}/ports.json')):
        return json.loads(f.read_text())
    return None


def master_record(name):
    d = derived_record(name)
    m, pw, M, real = model()
    if d is not None and name not in M:     # a split the generator does not place yet
        return d
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
    if d is not None:       # generator-placed band: directions / forwarded-clock bits from the split record
        for p_, v_ in ports.items():
            if p_ in d['ports']:
                for k_ in ('direction', 'dir_segments'):
                    if k_ in d['ports'][p_]:
                        v_[k_] = d['ports'][p_][k_]
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
        if n not in M and derived_record(n) is None:
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


def check_lef(master, lef, tol=0.0125, allow_extra=()):
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
    allowed = sorted(p for p in extra if re.sub(r'\[\d+\]$', '', p) in set(allow_extra))
    extra = [p for p in extra if p not in allowed]
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
               die_top_io_pins=allowed,
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
    if moved:       # the die GRT / pricing use the generator pin plan: a moved pin is a mismatch
        problems.append(out['positions'])
    out['problems'] = problems
    out['verdict'] = 'MATCH' if not problems else 'MISMATCH'
    return out


def cmd_check(a):
    print(json.dumps(check_lef(a.master, a.lef, allow_extra=a.allow_extra or ()), indent=1))


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


def _slacks(v):
    """(SS setup, FF hold) block slack in ps from a view record (the forks' field spellings)."""
    t = json.dumps(v)
    ss = re.findall(r'"(?:ss_setup_ps|ss_worst_setup_ps|setup_ss_ps)": (-?[\d.]+)', t)
    ff = re.findall(r'"(?:ff_hold_ps|ff_worst_hold_ps|ff_worst_hold_slack_ps|hold_ff_ps)": (-?[\d.]+)', t)
    return (float(ss[0]) if ss else None, float(ff[0]) if ff else None)


def cmd_index(a):
    base = ROOT / VIEWS
    m, pw, M, real = model()
    rows = {}
    for vj in sorted(base.rglob('view*.json')):
        v = json.loads(vj.read_text())
        if not isinstance(v, dict) or 'master' not in v or 'status' not in v:
            continue
        v['dir'] = str(vj.parent.relative_to(ROOT))
        rows[v['master']] = v
    need = sorted({it.master for it in m['insts'] if it.master.startswith('hfd_')})
    idx = dict(schema='opentallas.hbm_die_views_index.v1', die='HBM accelerator DS die', round=H.FINAL_ROUND,
               generator_sha256=sha(ROOT / 'tools/hbm_accel_die_fp.py'),
               status_values=['closed', 'closed-below-margin', 'interim-not-closed', 'reservation', 'missing'],
               masters={}, counts=defaultdict(int))
    for n in need:
        v = rows.get(n)
        st = v['status'] if v else 'missing'
        margin = None
        if st == 'closed':      # owner UPDATE 2 (2026-10-06): closed only at SS >= +40 ps and FF >= +15 ps
            ss_, ff_ = _slacks(v)
            margin = dict(ss_setup_ps=ss_, ff_hold_ps=ff_, rule='SS >= +40 ps, FF >= +15 ps (owner 2026-10-06)')
            if ss_ is None or ff_ is None or ss_ < 40.0 or ff_ < 15.0:
                st = 'closed-below-margin'
        idx['masters'][n] = dict(kind=kind_of(n), status=st, instances=sum(it.master == n for it in m['insts']),
                                 **({k: v[k] for k in ('dir', 'lef', 'lib', 'check', 'source') if k in v} if v else {}))
        if margin:
            idx['masters'][n]['margin'] = margin
        if v and v.get('lef'):     # re-check against the CURRENT generator round (a view routed on an older outline)
            c_ = check_lef(n, ROOT / v['dir'] / v['lef'], allow_extra=v.get('die_top_io', ()))
            idx['masters'][n]['check'] = {k: c_[k] for k in ('verdict', 'problems', 'positions', 'size_view',
                                                                 'size_gen', 'die_top_io_pins')}
        idx['counts'][st] += 1
    idx['counts'] = dict(idx['counts'])
    (base / 'index.json').write_text(json.dumps(idx, indent=1) + '\n')
    print(json.dumps(idx['counts']))


# ------------------------------------------------------------------------------------------------ die with real views
def real_views(index_path):
    idx = json.loads(Path(index_path).read_text())
    out = {}
    for n, v in idx['masters'].items():
        if v['status'] in ('closed', 'closed-below-margin', 'interim-not-closed', 'reservation') and v.get('lef'):
            out[n] = ROOT / v['dir'] / v['lef']
    return out


def sta_tcl(m, work, index):
    """die-context STA (owner addendum 2026-10-06: a block counts as closed only after die-context STA with the real
    abstract): the real-abstract die placement (case real, k = 1) with every indexed view that has SS / FF Liberty,
    wires from placement (estimate_parasitics -placement, ASAP7 setRC), one ideal clock per die clock net on the lib
    views' clock pins at 833.333 ps, setup at SS with 60 ps and with 60 + 150 ps (the die clock-arrival difference the
    owner rule budgets), hold at FF with 25 ps.  Reports every die path between two timed views (tile <-> tile chains,
    tile <-> stations) and the unconstrained pins of timed views (forwarded-clock station links are source-synchronous
    and checked inside the station views)."""
    idx = json.loads(Path(index).read_text())['masters']
    libs = {n: v for n, v in idx.items() if v.get('lib') and v['status'] in ('closed', 'closed-below-margin',
                                                                            'interim-not-closed')}
    run = (work / 'run.tcl').read_text()
    head = run.split('set t0 [clock seconds]\nsource /work/place.tcl')[0]
    lib_lines = []
    for n, v in sorted(libs.items()):
        d = ROOT / v['dir']
        (work / f'{n}_ss.lib').write_bytes((d / v['lib']['ss']).read_bytes())
        (work / f'{n}_ff.lib').write_bytes((d / v['lib']['ff']).read_bytes())
        lib_lines += [f'read_liberty -corner ss /work/{n}_ss.lib', f'read_liberty -corner ff /work/{n}_ff.lib']
    timed = [it for it in m['insts'] if it.master in libs]
    clk_nets = {'stream': 'n_clk_stream', 'serial': 'n_clk_serial', 'hbm': 'n_clk_hbm', 'link': 'n_clk_link'}
    head = head.replace('read_verilog /work/die.v', 'define_corners ss ff\n' + '\n'.join(lib_lines) + '\nread_verilog /work/die.v')
    tcl = head + 'source /work/place.tcl\n' + f"""
source /OpenROAD-flow-scripts/flow/platforms/asap7/setRC.tcl
set_wire_rc -signal -layer M7
set_wire_rc -clock -layer M7
estimate_parasitics -placement
set_cmd_units -time ns -capacitance fF
set timed_insts {{{' '.join(it.name for it in timed)}}}
foreach {{dom net}} {{{' '.join(f'{k} {v}' for k, v in clk_nets.items())}}} {{
  set ck {{}}
  foreach p [get_pins -quiet -of_objects [get_nets -quiet "$net $net\\[0\\]"]] {{
    set i [lindex [split [get_full_name $p] /] 0]
    if {{[lsearch -exact $timed_insts $i] >= 0}} {{ lappend ck $p }}
  }}
  puts "OT_STA_CLKNET $dom pins=[llength [get_pins -quiet -of_objects [get_nets -quiet \"$net $net\\[0\\]\"]]] timed=[llength $ck]"
  if {{[llength $ck]}} {{ create_clock -name clk_$dom -period 0.833333 $ck; puts "OT_STA_CLOCK $dom sinks=[llength $ck]" }}
}}
set_propagated_clock [all_clocks]
set tp {{}}
foreach i $timed_insts {{ foreach p [get_pins -quiet $i/*] {{ lappend tp $p }} }}
foreach u {{0.060 0.210}} {{
  set_clock_uncertainty -setup $u [all_clocks]
  set_clock_uncertainty -hold 0.025 [all_clocks]
  puts "OT_STA_SETUP uncertainty=$u wns=[sta::format_time [sta::worst_slack -max] 3] tns=[sta::format_time [sta::total_negative_slack -max] 3]"
  report_checks -path_delay max -corner ss -group_path_count 5 -format end -digits 3
}}
puts "OT_STA_HOLD wns=[sta::format_time [sta::worst_slack -min] 3]"
report_checks -path_delay min -corner ff -group_path_count 5 -format end -digits 3
report_checks -path_delay max -corner ss -digits 3 -fields {{slew cap input_pins}}
set ti [get_pins -quiet at_*/*]
if {{[llength $ti]}} {{
  set_clock_uncertainty -setup 0.210 [all_clocks]
  puts "OT_STA_ATTN_SETUP_U210 [sta::format_time [sta::worst_slack -max] 3]"
  report_checks -path_delay max -corner ss -through $ti -group_path_count 10 -format end -digits 3
  report_checks -path_delay max -corner ss -through $ti -digits 3 -fields {{slew cap input_pins}}
  report_checks -path_delay min -corner ff -through $ti -group_path_count 10 -format end -digits 3
}}
puts "OT_STA_DONE timed_insts=[llength $timed_insts]"
"""
    (work / 'run.tcl').write_text(tcl)


def pad_mirror(body, orients, P=48, R=24):
    """a view whose instances are mirrored keeps its on-track pins on track only if the mirrored dimension is
    R mod P nm (the generator convention, ot_macro_track_snap.tcl): pad the outline up to the next such value (< P nm
    of empty edge) and extend the pin shapes that touch the moved edge to it.  Returns (body, pad record or None)."""
    mm = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', body)
    w, h = (round(float(v) * 1000) for v in mm.groups())
    nw = w + (R - w) % P if orients & {'MY', 'R180'} else w
    nh = h + (R - h) % P if orients & {'MX', 'R180'} else h
    if (nw, nh) == (w, h):
        return body, None
    body = body.replace(mm.group(0), f'SIZE {nw / 1000:.3f} BY {nh / 1000:.3f}', 1)
    head, sep, rest = body.partition('\n  OBS')  # pins precede OBS in every exported view
    moved = 0

    def fix(r):
        nonlocal moved
        x0, y0, x1, y1 = (float(v) for v in r.groups())
        X1 = nw / 1000 if nw != w and abs(x1 * 1000 - w) < 1 else x1
        Y1 = nh / 1000 if nh != h and abs(y1 * 1000 - h) < 1 else y1
        if (X1, Y1) == (x1, y1):
            return r.group(0)
        moved += 1
        return (f'RECT  {r.group(1)} {r.group(2)} {r.group(3) if X1 == x1 else f"{X1:.3f}"} '
                f'{r.group(4) if Y1 == y1 else f"{Y1:.3f}"}')
    head = re.sub(r'RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', fix, head)
    return head + sep + rest, dict(size_nm=[w, h], padded_nm=[nw, nh], edge_pin_shapes_extended=moved,
                                   orients=sorted(orients))


def bundle_real_pins(macro_text, view, k):
    """GRT (k-bundled) master with the REAL view's pin plan: bundle pin port[j] (bits j*k .. j*k+k-1) moves to the
    centroid of those bits' pins in the view, on the view's face for them (N/S on M5, E/W on M4), snapped to the
    bundled track grid; bundles of one face and layer that would share a track take the nearest free track.
    Returns (macro text, record)."""
    from chip_assembly import v41_die as VD
    trk = {n: (off * k, p * k) for n, d, p, wd, sp, off in VD.ASAP7_LAYERS}
    w, h = map(float, re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', macro_text).groups())
    bits = defaultdict(dict)
    for nm, pr in view['pins'].items():
        mm = re.match(r'^(.*)\[(\d+)\]$', nm)
        if not mm or not pr['rects']:
            continue
        ly, b = pr['rects'][0]
        bits[mm.group(1)][int(mm.group(2))] = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2, face_of(pr['rects'], view['w'], view['h']))
    want = []        # (face, layer, desired coordinate along the face, pin name)
    for pm in re.finditer(r'  PIN (\S+)\n.*?\n  END \1\n', macro_text, re.S):
        nm = pm.group(1)
        base, j = re.match(r'^(.*)\[(\d+)\]$', nm).groups()
        j = int(j)
        pts = [bits[base][i] for i in range(j * k, (j + 1) * k) if i in bits[base]]
        if not pts:
            continue
        faces = defaultdict(int)
        for _, _, f in pts:
            faces[f] += 1
        f = max(faces, key=faces.get)
        f = f if f in 'NSEW' else min('NSEW', key=lambda q: dict(N=h - pts[0][1], S=pts[0][1], E=w - pts[0][0],
                                                                    W=pts[0][0])[q])
        c = sum(pt[0] if f in 'NS' else pt[1] for pt in pts) / len(pts)
        want.append((f, 'M5' if f in 'NS' else 'M4', c, nm))
    hw, depth = 0.012 * k, 0.192 * k
    place, moved = {}, 0
    groups = defaultdict(list)
    for f, ly, c, nm in want:
        groups[(f, ly)].append((c, nm))
    for (f, ly), grp in groups.items():
        off, p = trk[ly]
        along = w if f in 'NS' else h
        lo, hi = math.ceil((2 * p - off) / p), math.floor((along - 2 * p - off) / p)
        used = set()
        dense = len(grp) > (hi - lo) // 2      # more bundles than 2-track slots: 1-track spacing (the generator's)
        for c, nm in sorted(grp):
            t = min(max(round((c - off) / p), lo), hi)
            d = 0
            while True:      # nearest free track (2-track pitch keeps bundled pins spaced like the generator's)
                cand = [t + d, t - d] if d else [t]
                ok = [q for q in cand if lo <= q <= hi and q not in used and (dense or (q - 1 not in used and q + 1 not in used))]
                if ok:
                    t = ok[0]
                    break
                d += 1
                if d > hi - lo:
                    raise ValueError(f'{nm}: no free bundled track on face {f}')
            used.add(t)
            pos = off + t * p
            r = {'S': (pos - hw, 0.0, pos + hw, depth), 'N': (pos - hw, h - depth, pos + hw, h),
                 'W': (0.0, pos - hw, depth, pos + hw), 'E': (w - depth, pos - hw, w, pos + hw)}[f]
            place[nm] = (ly, r)
    def fix(pm):
        nonlocal moved
        nm = pm.group(1)
        if nm not in place:
            return pm.group(0)
        ly, r = place[nm]
        moved += 1
        return (f'  PIN {nm}\n    DIRECTION INOUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER {ly} ;\n'
                f'        RECT {r[0]:.3f} {r[1]:.3f} {r[2]:.3f} {r[3]:.3f} ;\n    END\n  END {nm}\n')
    out = re.sub(r'  PIN (\S+)\n.*?\n  END \1\n', fix, macro_text, flags=re.S)
    return out, dict(bundle_pins_moved=moved, bundle_pins=len(re.findall(r'\n  PIN ', macro_text)),
                     faces={f'{f}/{ly}': len(g) for (f, ly), g in groups.items()})


def cmd_die(a):
    m, pw, M, real = model()
    views = real_views(a.index)
    work = Path(a.work).resolve()
    work.mkdir(parents=True, exist_ok=True)
    gen_text = {}
    if a.case in ('real', 'sta'):
        H.case_real(m, work)
        # replace the generated macros that have a real view by the view's LEF
        el = (work / 'elements.lef').read_text()
        for n, lef in views.items():
            el, k = re.subn(r'(# [^\n]*\n)?MACRO ' + re.escape(n) + r'\n.*?\nEND ' + re.escape(n) + r'\n', '', el,
                            flags=re.S)
            assert k == 1, (n, k)
            gen_text[n] = lef
        (work / 'elements.lef').write_text(el)
        lefs, pads = [], {}
        orients = defaultdict(set)
        for it in m['insts']:
            orients[it.master].add(it.orient)
        for n, lef in views.items():
            t = parse_lef(lef)['text']
            body = re.search(r'(MACRO .*?END ' + re.escape(n) + r')', t, re.S).group(1)
            body, pad = pad_mirror(body, orients[n])
            if pad:
                pads[n] = pad
            lefs.append(body)
        (work / 'views.lef').write_text('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n' + '\n'.join(lefs)
                                        + '\nEND LIBRARY\n')
        run = (work / 'run.tcl').read_text().replace('foreach f {phy.lef serdes.lef ucie.lef elements.lef}',
                                                     'foreach f {phy.lef serdes.lef ucie.lef elements.lef views.lef}')
        (work / 'run.tcl').write_text(run)
        if a.case == 'sta':
            sta_tcl(m, work, a.index)
    else:
        cov = dict(H.COV)
        H.case_grt(m, work, a.k, a.tag, a.iters, cov)
        idx = json.loads(Path(a.index).read_text())['masters']
        mismatched = {n for n in views if idx[n].get('check', {}).get('verdict') == 'MISMATCH'}
        pinrec, regadj, contract_assumed = {}, [], []
        el = (work / 'elements.lef').read_text()
        for n, lef in views.items():
            r = parse_lef(lef)
            om = re.search(r'\n(\s*OBS\n.*?\n\s*END)\n', r['text'], re.S)
            obs = om.group(1) if om else '  OBS\n  END'
            # bundled tech LEF (k > 1) defines the metal layers only: keep the view's metal obstructions
            # M8 / M9 obstructions become GRT region adjustments instead (measured r6_attn: a macro OBS on M8/M9
            # makes GRT drop the die's M8/M9 layer adjustments, capacity x10 and overflow not comparable)
            keep, cur, hi = [], True, defaultdict(list)
            for ln in obs.split('\n'):
                mm = re.match(r'\s*LAYER (\S+)', ln)
                if mm:
                    cur = bool(re.fullmatch(r'M[1-7]', mm.group(1)))
                    hil = mm.group(1) if mm.group(1) in ('M8', 'M9') else None
                mr = re.match(r'\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', ln)
                if mr and not cur and hil:
                    hi[hil].append(tuple(float(v) for v in mr.groups()))
                if cur or not ln.strip().startswith(('LAYER', 'RECT', 'POLYGON')):
                    if cur or not mm:
                        keep.append(ln)
            obs = '\n'.join(keep)
            if n in (a.contract_m89 or ()):   # decided re-hardening to the die contract (PG <= M7): M8/M9 free
                contract_assumed.append(n)
                hi = {}
            for ly, rs in hi.items():
                if len(rs) > 16:        # a reduced outline-minus-pins OBS: its bounding box
                    rs = [(min(r_[0] for r_ in rs), min(r_[1] for r_ in rs), max(r_[2] for r_ in rs),
                           max(r_[3] for r_ in rs))]
                for it in m['insts']:
                    if it.master != n:
                        continue
                    for r_ in rs:
                        x0_, y0_, x1_, y1_ = _xf(r_, it, r['w'], r['h'])
                        regadj.append(f'set_global_routing_region_adjustment {{{x0_:.3f} {y0_:.3f} {x1_:.3f} '
                                      f'{y1_:.3f}}} -layer {ly} -adjustment 1.0')
            pat = r'(MACRO ' + re.escape(n) + r'\n.*?)\n  OBS\n.*?\n  END\n(END ' + re.escape(n) + r'\n)'
            el, k = re.subn(pat, lambda mm: mm.group(1) + '\n' + obs + '\n' + mm.group(2), el, flags=re.S)
            assert k == 1, (n, k)
            if a.real_pins and n in mismatched:
                mpat = r'MACRO ' + re.escape(n) + r'\n.*?\nEND ' + re.escape(n) + r'\n'
                body = re.search(mpat, el, re.S).group(0)
                nb, rec = bundle_real_pins(body, r, a.k)
                el = el.replace(body, nb)
                pinrec[n] = rec
        (work / 'elements.lef').write_text(el)
        if regadj:
            t_ = (work / 'run.tcl').read_text()
            t_ = t_.replace('set_routing_layers -signal M2-M9', '\n'.join(regadj) + '\nset_routing_layers -signal M2-M9', 1)
            (work / 'run.tcl').write_text(t_)
    man = json.loads((work / 'manifest.json').read_text())
    man['real_views'] = {n: dict(lef=str(p.relative_to(ROOT)), sha256=sha(p)) for n, p in views.items()}
    if a.case in ('real', 'sta') and pads:
        man['mirror_pads'] = pads
    if a.case == 'grt':
        man['m8_m9_view_blockages'] = len(regadj)
        man['m8_m9_contract_assumed'] = contract_assumed
        man['real_pin_plan'] = pinrec if a.real_pins else 'generator pins (views MATCH or --real-pins off)'
    (work / 'manifest.json').write_text(json.dumps(man, indent=1))
    print(json.dumps(dict(case=a.case, real_views=len(views), work=str(work))))


def parse_case_log(t):
    """legality / on-track / pin access / GRT figures of one die case log."""
    r = {}
    m_ = re.search(r'OT_LEGAL instances=(\d+) overlaps=(\d+) outside=(\d+)', t)
    if m_:
        r.update(instances=int(m_.group(1)), overlaps=int(m_.group(2)), outside=int(m_.group(3)))
    if 'OT_ASSERT' in t:
        r['on_track'] = 'PASS' if 'OT_ASSERT PASS' in t else 'FAIL'
    if 'OT_PA' in t:
        r['pin_access'] = 'DONE' if 'OT_PA DONE' in t else 'FAIL'
        r['pa_errors'] = len(re.findall(r'\[ERROR DRT', t))
        mm = re.search(r'#macroNoAp\s*=\s*(\d+)', t)
        r['macro_no_access'] = int(mm.group(1)) if mm else None
    tot = re.findall(r'^Total\s+(\d+)\s+(\d+)\s+([\d.]+)%\s+(\d+) /\s+(\d+) /\s+(\d+)', t, re.M)
    if tot:
        a, b, u, h, v, o = tot[-1]
        r.update(grt_capacity=int(a), grt_demand=int(b), grt_usage_pct=float(u), overflow_h=int(h), overflow_v=int(v),
                 overflow=int(o))
    err = re.search(r'^Error: .*$', t, re.M)
    if err:
        r['error'] = err.group(0)
    for k in ('place_s', 'pa_s', 'grt_s'):
        mm = re.search(r'OT_TIME ' + k + r'=(\d+)', t)
        if mm:
            r[k] = int(mm.group(1))
    return r


def cmd_die_record(a):
    rd = Path(a.round)
    out = dict(schema='opentallas.hbm_die_views_round.v1', round=rd.name, cases={})
    for c in sorted(p for p in rd.iterdir() if p.is_dir()):
        lg = c / 'run.log'
        if not lg.exists():
            continue
        rec = parse_case_log(lg.read_text(errors='replace'))
        ex = c / 'run.log.exit'
        rec['exit'] = ex.read_text().strip() if ex.exists() else None
        man = c / 'manifest.json'
        if man.exists():
            mj = json.loads(man.read_text())
            rec['real_views'] = sorted(mj.get('real_views', {}))
            rec['bundle_k'] = mj.get('bundle_k')
            rec['iterations'] = mj.get('congestion_iterations')
        out['cases'][c.name] = rec
    sc = rd / 'SOURCE_COMMIT'
    out['source_commit'] = sc.read_text().strip() if sc.exists() else None
    txt = json.dumps(out, indent=1) + '\n'
    if a.out:
        Path(a.out).write_text(txt)
    print(txt)


# ------------------------------------------------------------------------------------------------ IR: attention-tile PDN exception
ATTN = 'hfd_attn_tile'


def _xf(rect, it, w, h):
    a, b, c, d = rect
    if it.orient in ('MY', 'R180'):
        a, c = w - c, w - a
    if it.orient in ('MX', 'R180'):
        b, d = h - d, h - b
    return (it.x + a, it.y + b, it.x + c, it.y + d)


def _cut(iv, holes):
    """interval iv minus holes -> list of intervals"""
    out = [iv]
    for h0, h1 in holes:
        nxt = []
        for a, b in out:
            if h1 <= a or h0 >= b:
                nxt.append((a, b))
                continue
            if h0 > a:
                nxt.append((a, h0))
            if h1 < b:
                nxt.append((h1, b))
        out = nxt
    return [(a, b) for a, b in out if b - a > 1.0]


QUAD_LEF = 'physical/hbm_attn_tile_r/quad/ot_attn_tile_m6h1q/ot_attn_tile_m6h1q.lef'
QW = 514.89
QUAD_PLACE = ((70.014, 40.032, 'MY'), (765.504, 40.032, 'R0'), (70.014, 763.632, 'MY'), (765.504, 763.632, 'R0'))
_QPG = {}


def QUAD_PG():
    """the closed quad's PG: M9 straps (its PG pins) and M8 PG strap segments (its 0.474 um M8 OBS shapes on the y
    tracks of its M8 PG edge stubs, per net), quad-local.  Placement: attn_tile/flow/macro_placement.tcl."""
    if not _QPG:
        r = parse_lef(ROOT / QUAD_LEF)
        t = r['text']
        o = t[t.index('\n  OBS'):]
        cur, m8 = None, []
        for ln in o.split('\n'):
            mm = re.match(r'\s*LAYER (\S+)', ln)
            if mm:
                cur = mm.group(1)
                continue
            mr = re.match(r'\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', ln)
            if mr and cur == 'M8':
                b = tuple(float(v) for v in mr.groups())
                if abs(b[3] - b[1] - 0.474) < 1e-3:
                    m8.append(b)
        for net in ('VDD', 'VSS'):
            ys = {round((b[1] + b[3]) / 2, 3) for ly, b in r['pg'][net]['rects'] if ly == 'M8'}
            _QPG[net] = dict(M9=[b for ly, b in r['pg'][net]['rects'] if ly == 'M9'],
                             M8=[b for b in m8 if round((b[1] + b[3]) / 2, 3) in ys])
    return _QPG


def cmd_ir_attn(a):
    """IR window with the OWNER PDN EXCEPTION for hfd_attn_tile (2026-10-06): the die's M9 straps land on the tile's
    M8 PG pins (the tile consumes M8 everywhere and M9 over its four closed quads); M9 is blocked over the quads, no
    die M8 inside a tile.  Built on the r16g IR window (method c, tools/dsrom_s81_fulldie.py case_ir): die M8 removed
    inside every tile, the tile's real M8 PG straps (view LEF, per orientation) added, die M9 cut over every quad, M9 ->
    tile M8 vias at every same-net crossing outside the quads, no power bump over a quad (its M9 is the quad's own),
    the tile's power re-hosted: cells over the tile's open area on its M8 straps, cells over a quad as loads on the
    quad's M8 edge stubs (the strap ends the tile bridges to the quad, flow/bridge_quad_m8.tcl)."""
    m, pw, M, real = model()
    work = Path(a.work).resolve()
    cov = dict(H.COV)
    meta = H.case_ir(m, work, a.window, cov)
    X0, Y0 = meta['window_um'][0], meta['window_um'][1]
    Wn, Hn = meta['size_um']
    view = parse_lef(ROOT / VIEWS / 'attn_tile' / f'{ATTN}.lef')
    vw, vh = view['w'], view['h']
    quads_v, cur = [], None
    om = re.search(r'\n\s*OBS\n(.*?)\n\s*END\n', view['text'], re.S)
    for ln in om.group(1).split('\n'):
        mm = re.match(r'\s*LAYER (\S+)', ln)
        if mm:
            cur = mm.group(1)
            continue
        mr = re.match(r'\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)', ln)
        if mr and cur == 'M9':
            quads_v.append(tuple(float(v) for v in mr.groups()))
    straps_v = {net: [b for ly, b in view['pg'][net]['rects'] if ly == 'M8'] for net in ('VDD', 'VSS')}
    tiles = [it for it in m['insts'] if it.master == ATTN and it.x < X0 + Wn and it.x + it.w > X0
             and it.y < Y0 + Hn and it.y + it.h > Y0]
    loc = lambda r: (r[0] - X0, r[1] - Y0, r[2] - X0, r[3] - Y0)  # noqa: E731
    trects, quads, tstraps = [], [], {'VDD': [], 'VSS': []}
    for it in tiles:
        trects.append(loc((it.x, it.y, it.x + it.w, it.y + it.h)))
        for q in quads_v:
            qq = loc(_xf(q, it, vw, vh))
            if qq[0] < Wn and qq[2] > 0 and qq[1] < Hn and qq[3] > 0:
                quads.append((it.name, qq))
        for net, rs in straps_v.items():
            for r in rs:
                x0_, y0_, x1_, y1_ = loc(_xf(r, it, vw, vh))
                x0_, x1_ = max(x0_, 0.0), min(x1_, Wn)
                if x1_ - x0_ > 1.0 and 0.5 < (y0_ + y1_) / 2 < Hn - 0.5:
                    tstraps[net].append((x0_, y0_, x1_, y1_))
    qpg = {'M9': {'VDD': [], 'VSS': []}, 'M8': {'VDD': [], 'VSS': []}}
    if a.quad_pg:
        for it in tiles:
            for qx, qy, qo in QUAD_PLACE:
                for net in ('VDD', 'VSS'):
                    for ly, rs in QUAD_PG()[net].items():
                        for r_ in rs:
                            x0q, x1q = (QW - r_[2], QW - r_[0]) if qo == 'MY' else (r_[0], r_[2])
                            rr = loc(_xf((qx + x0q, qy + r_[1], qx + x1q, qy + r_[3]), it, vw, vh))
                            c0, c1 = max(rr[0], 0.0), min(rr[2], Wn)
                            d0, d1 = max(rr[1], 0.0), min(rr[3], Hn)
                            xc_, yc_ = (rr[0] + rr[2]) / 2, (rr[1] + rr[3]) / 2
                            if (ly == 'M9' and d1 - d0 > 1.0 and 0.5 < xc_ < Wn - 0.5) or \
                                    (ly == 'M8' and c1 - c0 > 0.5 and 0.5 < yc_ < Hn - 0.5):
                                qpg[ly][net].append((c0, d0, c1, d1) if ly == 'M8' else (rr[0], d0, rr[2], d1))
    inq = lambda x, y: any(q[0] <= x <= q[2] and q[1] <= y <= q[3] for _, q in quads)  # noqa: E731
    intile = lambda x, y: any(t[0] <= x <= t[2] and t[1] <= y <= t[3] for t in trects)  # noqa: E731
    # ---- die grid from the method-c DEF
    d = (work / 'top.def').read_text()
    head, sn = d.split('SPECIALNETS 2 ;\n')
    s9, s8, vias = [], [], []
    for net in ('VDD', 'VSS'):
        blk = re.search(r'- ' + net + r' \( \* ' + net + r' \).*?;\n', sn, re.S).group(0)
        for mm in re.finditer(r'M9 480 \+ SHAPE STRIPE \( (-?\d+) (-?\d+) \) \( \* (-?\d+) \)', blk):
            s9.append((net, int(mm.group(1)) / 1e3, int(mm.group(2)) / 1e3, int(mm.group(3)) / 1e3))
        for mm in re.finditer(r'M8 480 \+ SHAPE STRIPE \( (-?\d+) (-?\d+) \) \( (-?\d+) \* \)', blk):
            s8.append((net, int(mm.group(1)) / 1e3, int(mm.group(2)) / 1e3, int(mm.group(3)) / 1e3))
        for mm in re.finditer(r'NEW M8 0 \( (-?\d+) (-?\d+) \) via89', blk):
            vias.append((net, int(mm.group(1)) / 1e3, int(mm.group(2)) / 1e3))
    n9 = []
    for net, x, y0_, y1_ in s9:       # M9 cut over the quads
        holes = [(q[1] - 0.24, q[3] + 0.24) for _, q in quads if q[0] - 0.24 <= x <= q[2] + 0.24]
        n9 += [(net, x, a_, b_) for a_, b_ in _cut((y0_, y1_), holes)]
    n8 = []
    for net, x0_, y, x1_ in s8:       # no die M8 inside a tile
        holes = [(t[0], t[2]) for t in trects if t[1] - 0.24 <= y <= t[3] + 0.24]
        n8 += [(net, a_, y, b_) for a_, b_ in _cut((x0_, x1_), holes)]
    nv = [(net, x, y) for net, x, y in vias if not intile(x, y)]
    # M9 -> tile M8 vias at every same-net crossing outside the quads
    m9x = defaultdict(list)
    for net, x, y0_, y1_ in n9:
        m9x[net].append((x, y0_, y1_))
    added = 0
    for net, rs in tstraps.items():
        for x0_, y0_, x1_, y1_ in rs:
            yc = round((y0_ + y1_) / 2 * 1e3) / 1e3     # the DEF stripe centre, to the nm
            for x, a_, b_ in m9x[net]:
                if x0_ + 0.25 <= x <= x1_ - 0.25 and a_ <= yc <= b_ and not inq(x, yc):
                    nv.append((net, x, yc))
                    added += 1
    qvias, qdrop, qpads = 0, {}, {}
    if a.quad_pg:       # quad M8 PG segments x quad M9 PG straps (the quad's own internal vias)
        for net in ('VDD', 'VSS'):
            m9s = sorted(qpg['M9'][net])
            xs = [round((r_[0] + r_[2]) / 2 * 1e3) / 1e3 for r_ in m9s]   # the DEF stripe centre, to the nm
            import bisect
            used9, keep8 = set(), []
            for x0_, y0_, x1_, y1_ in qpg['M8'][net]:
                yc = (y0_ + y1_) / 2
                hit = 0
                for k_ in range(bisect.bisect_left(xs, x0_ + 0.25), bisect.bisect_right(xs, x1_ - 0.25)):
                    if m9s[k_][1] <= yc <= m9s[k_][3]:
                        nv.append((net, xs[k_], round(yc * 1e3) / 1e3))
                        qvias += 1
                        hit += 1
                        used9.add(k_)
                if hit:
                    keep8.append((x0_, y0_, x1_, y1_))
            # bump-pad vias: a bump over a quad lands on every same-net quad M9 strap under its 20 um pad (the
            # AP / pad-layer vias of a real bump; the die grid's own bumps reach its M9 the same way in PSM)
            other = qpg['M8']['VSS' if net == 'VDD' else 'VDD']
            for row in (work / f'vsrc_{net}.loc').read_text().splitlines():
                if not row.strip():
                    continue
                bx, by = (float(v) for v in row.split(',')[:2])
                if not inq(bx, by):
                    continue
                for k_ in range(bisect.bisect_left(xs, bx - 9.5), bisect.bisect_right(xs, bx + 9.5)):
                    if not (m9s[k_][1] + 0.5 <= by <= m9s[k_][3] - 0.5):
                        continue
                    yy = None
                    for dy in (0.0, 0.6, -0.6, 1.2, -1.2, 1.8, -1.8, 2.4, -2.4):
                        y_ = round((by + dy) * 1e3) / 1e3
                        if all(not (abs((o[1] + o[3]) / 2 - y_) < 0.6 and o[0] - 0.4 < xs[k_] < o[2] + 0.4) for o in other):
                            yy = y_
                            break
                    if yy is None:
                        continue
                    keep8.append((xs[k_] - 0.24, yy - 0.237, xs[k_] + 0.24, yy + 0.237))
                    nv.append((net, xs[k_], yy))
                    qpads[net] = qpads.get(net, 0) + 1
                    used9.add(k_)
            # a shape with no via is an isolated PSM node (IRSolver::checkOpen connections_map.at -> map::at)
            qdrop[net] = (len(qpg['M8'][net]) - len(keep8), len(m9s) - len(used9))
            qpg['M8'][net] = keep8
            qpg['M9'][net] = [m9s[k_] for k_ in sorted(used9)]
    L = ['SPECIALNETS 2 ;']
    for net in ('VDD', 'VSS'):
        seg = []
        for x0_, y0_, x1_, y1_ in qpg['M9'][net]:
            seg.append(f'M9 474 + SHAPE STRIPE ( {round((x0_ + x1_) / 2 * 1e3)} {round(y0_ * 1e3)} ) ( * {round(y1_ * 1e3)} )')
        for x0_, y0_, x1_, y1_ in qpg['M8'][net]:
            seg.append(f'M8 474 + SHAPE STRIPE ( {round(x0_ * 1e3)} {round((y0_ + y1_) / 2 * 1e3)} ) ( {round(x1_ * 1e3)} * )')
        for nn, x, y0_, y1_ in n9:
            if nn == net:
                seg.append(f'M9 480 + SHAPE STRIPE ( {round(x * 1e3)} {round(y0_ * 1e3)} ) ( * {round(y1_ * 1e3)} )')
        for nn, x0_, y, x1_ in n8:
            if nn == net:
                seg.append(f'M8 480 + SHAPE STRIPE ( {round(x0_ * 1e3)} {round(y * 1e3)} ) ( {round(x1_ * 1e3)} * )')
        for x0_, y0_, x1_, y1_ in tstraps[net]:
            wd = round((y1_ - y0_) * 1e3)
            wd += wd % 2
            seg.append(f'M8 {wd} + SHAPE STRIPE ( {round(x0_ * 1e3)} {round((y0_ + y1_) / 2 * 1e3)} ) '
                       f'( {round(x1_ * 1e3)} * )')
        seg += [f'M8 0 ( {round(x * 1e3)} {round(y * 1e3)} ) via89' for nn, x, y in nv if nn == net]
        L.append(f'- {net} ( * {net} ) + USE ' + ('POWER' if net == 'VDD' else 'GROUND'))
        L += [('  + ROUTED ' if i == 0 else '    NEW ') + s_ for i, s_ in enumerate(seg)]
        L[-1] += ' ;'
    L += ['END SPECIALNETS', 'END DESIGN', '']
    # ---- loads: re-host the cells over the tiles
    comps = re.findall(r'- (L_\d+_\d+) (\S+) \+ FIXED \( (\d+) (\d+) \) N ;', head)
    tcl = (work / 'run.tcl').read_text()
    power = {mm.group(1): float(mm.group(2)) for mm in re.finditer(r'set_pdnsim_inst_power -inst (\S+) -power (\S+)', tcl)}
    kinds = json.loads((work / 'kinds.json').read_text())
    lefs = (work / 'loads.lef').read_text()
    cell = meta['cell_um']
    keep, newc, pool, tile_open_moved, quad_cells = [], [], defaultdict(float), 0, 0
    srt = {net: sorted(rs, key=lambda r: (r[1] + r[3]) / 2) for net, rs in tstraps.items()}

    def strap_in(net, cx0, cy0):
        best = None
        for x0_, y0_, x1_, y1_ in srt[net]:
            yc = (y0_ + y1_) / 2
            if cy0 + 0.3 <= yc <= cy0 + cell - 0.3 and x0_ <= cx0 + 0.6 and x1_ >= cx0 + cell - 0.6:
                if best is None or abs(yc - cy0 - cell / 2) < abs(best - cy0 - cell / 2):
                    best = yc
        return best
    newm = {}
    for n, mst, xs, ys in comps:
        cx0, cy0 = int(xs) / 1e3, int(ys) / 1e3
        cx, cy = cx0 + cell / 2, cy0 + cell / 2
        if not intile(cx, cy):
            keep.append((n, mst, cx0, cy0))
            continue
        p_ = power.pop(n, 0.0)
        kinds.pop(n, None)
        if inq(cx, cy) and a.quad_pg:
            pins = {}
            for net in ('VDD', 'VSS'):
                cand = [((r_[0] + r_[2]) / 2) for r_ in qpg['M9'][net] if cx0 + 0.6 <= (r_[0] + r_[2]) / 2 <= cx0 + cell - 0.6
                        and r_[1] <= cy0 + 0.6 and r_[3] >= cy0 + cell - 0.6]
                pins[net] = min(cand, key=lambda x: abs(x - cx)) if cand else None
            if pins['VDD'] is not None and pins['VSS'] is not None:
                key = (round(pins['VDD'] - cx0, 3), round(pins['VSS'] - cx0, 3))
                mn = f'qir_q9_{int(key[0] * 1000)}_{int(key[1] * 1000)}'
                if mn not in newm:
                    newm[mn] = '\n'.join([f'MACRO {mn}', '  CLASS BLOCK ;', f'  FOREIGN {mn} 0 0 ;', '  SYMMETRY X Y ;',
                                          f'  SIZE {cell:.3f} BY {cell:.3f} ;', '  PIN VDD', '    DIRECTION INOUT ;',
                                          '    USE POWER ;', '    PORT', '      LAYER M9 ;',
                                          f'        RECT {key[0] - 0.237:.3f} 0.600 {key[0] + 0.237:.3f} {cell - 0.6:.3f} ;',
                                          '    END', '  END VDD', '  PIN VSS', '    DIRECTION INOUT ;', '    USE GROUND ;',
                                          '    PORT', '      LAYER M9 ;',
                                          f'        RECT {key[1] - 0.237:.3f} 0.600 {key[1] + 0.237:.3f} {cell - 0.6:.3f} ;',
                                          '    END', '  END VSS', '  OBS'] +
                                         [f'    LAYER M{q} ;\n      RECT 0 0 {cell:.3f} {cell:.3f} ;' for q in range(2, 8)] +
                                         ['  END', f'END {mn}', ''])
                nn = n + '_q'
                newc.append((nn, mn, cx0, cy0))
                power[nn] = p_
                kinds[nn] = 'attn_quad'
                quad_cells += 1
                continue
        if inq(cx, cy):
            qn = min(quads, key=lambda q: max(q[1][0] - cx, 0, cx - q[1][2]) + max(q[1][1] - cy, 0, cy - q[1][3]))
            pool[qn[0] + '|' + str(qn[1])] += p_
            continue
        pv, ps_ = strap_in('VDD', cx0, cy0), strap_in('VSS', cx0, cy0)
        if pv is None or ps_ is None:     # no full-width tile strap pair over this cell: nearest quad's edge stubs
            qn = min(quads, key=lambda q: max(q[1][0] - cx, 0, cx - q[1][2]) + max(q[1][1] - cy, 0, cy - q[1][3]))
            pool[qn[0] + '|' + str(qn[1])] += p_
            continue
        key = (round(pv - cy0, 3), round(ps_ - cy0, 3))
        mn = f'qir_load_{int(key[0] * 1000)}_{int(key[1] * 1000)}'
        if f'MACRO {mn}\n' not in lefs and mn not in newm:
            newm[mn] = '\n'.join([f'MACRO {mn}', '  CLASS BLOCK ;', f'  FOREIGN {mn} 0 0 ;', '  SYMMETRY X Y ;',
                                  f'  SIZE {cell:.3f} BY {cell:.3f} ;', '  PIN VDD', '    DIRECTION INOUT ;', '    USE POWER ;',
                                  '    PORT', '      LAYER M8 ;', f'        RECT 0.600 {key[0] - 0.237:.3f} {cell - 0.6:.3f} {key[0] + 0.237:.3f} ;',
                                  '    END', '  END VDD', '  PIN VSS', '    DIRECTION INOUT ;', '    USE GROUND ;', '    PORT',
                                  '      LAYER M8 ;', f'        RECT 0.600 {key[1] - 0.237:.3f} {cell - 0.6:.3f} {key[1] + 0.237:.3f} ;',
                                  '    END', '  END VSS', '  OBS'] + [f'    LAYER M{q} ;\n      RECT 0 0 {cell:.3f} {cell:.3f} ;' for q in range(2, 8)] +
                                 ['  END', f'END {mn}', ''])
        nn = n + '_t'
        newc.append((nn, mn, cx0, cy0))
        power[nn] = p_
        kinds[nn] = 'attn_open'
        tile_open_moved += 1
    # quad edge stubs: every tile M8 strap segment ending at a quad's W / E edge, VDD/VSS pairs (2.7 um apart)
    stubs, orphan = [], {}
    for key, p_ in list(pool.items()):
        tn, qs = key.split('|', 1)
        q = eval(qs)  # noqa: S307  (our own tuple repr)
        ends = {'VDD': [], 'VSS': []}
        for net, rs in tstraps.items():
            for x0_, y0_, x1_, y1_ in rs:
                yc = (y0_ + y1_) / 2
                if not (q[1] <= yc <= q[3]):
                    continue
                if abs(x1_ - q[0]) < 12.0:
                    ends[net].append(('W', x1_, yc))
                elif abs(x0_ - q[2]) < 12.0:
                    ends[net].append(('E', x0_, yc))
        pairs = []
        for side, xe, yv in ends['VDD']:
            cand = [e for e in ends['VSS'] if e[0] == side and abs(e[1] - xe) < 0.5 and 0 < abs(e[2] - yv) <= 2.8]
            if cand:
                ss = min(cand, key=lambda e: abs(e[2] - yv))
                pairs.append((side, xe, yv, ss[2]))
        if not pairs:      # the quad's stub edges lie outside the window: its in-window power goes to the nearest
            orphan[key] = p_    # in-window quad that has stubs (recorded)
            continue
        for side, xe, yv, ysv in pairs:
            stubs.append((side, xe, yv, ysv, p_ / len(pairs), tn))
    if orphan:
        if not stubs:
            raise SystemExit('no quad edge stubs in the window')
        extra = sum(orphan.values()) / len(stubs)
        stubs = [(sd, xe, yv, ysv, p_ + extra, tn) for sd, xe, yv, ysv, p_, tn in stubs]
    for i, (side, xe, yv, ysv, p_, tn) in enumerate(stubs):
        yb = min(yv, ysv) - 0.6
        key = (round(yv - yb, 3), round(ysv - yb, 3))
        mn = f'qir_stub_{int(key[0] * 1000)}_{int(key[1] * 1000)}'
        if mn not in newm:
            newm[mn] = '\n'.join([f'MACRO {mn}', '  CLASS BLOCK ;', f'  FOREIGN {mn} 0 0 ;', '  SYMMETRY X Y ;',
                                  f'  SIZE 1.200 BY {max(key) + 0.6:.3f} ;', '  PIN VDD', '    DIRECTION INOUT ;', '    USE POWER ;',
                                  '    PORT', '      LAYER M8 ;', f'        RECT 0.100 {key[0] - 0.2:.3f} 1.100 {key[0] + 0.2:.3f} ;',
                                  '    END', '  END VDD', '  PIN VSS', '    DIRECTION INOUT ;', '    USE GROUND ;', '    PORT',
                                  '      LAYER M8 ;', f'        RECT 0.100 {key[1] - 0.2:.3f} 1.100 {key[1] + 0.2:.3f} ;',
                                  '    END', '  END VSS', '  OBS', '    LAYER M7 ;', '      RECT 0 0 1.200 1.000 ;', '  END',
                                  f'END {mn}', ''])
        x = xe - 1.5 if side == 'W' else xe + 0.3
        nn = f'Q_{i}'
        newc.append((nn, mn, x, yb))
        power[nn] = p_
        kinds[nn] = 'attn_quad_stub'
    allc = keep + newc
    head = re.sub(r'COMPONENTS \d+ ;\n.*?END COMPONENTS\n', lambda _: f'COMPONENTS {len(allc)} ;\n' + ''.join(
        f'- {n} {mst} + FIXED ( {round(x * 1e3)} {round(y * 1e3)} ) N ;\n' for n, mst, x, y in allc) + 'END COMPONENTS\n',
        head, flags=re.S)
    (work / 'top.def').write_text(head + '\n'.join(L))
    (work / 'loads.lef').write_text(lefs.replace('END LIBRARY', '\n'.join(newm.values()) + 'END LIBRARY'))
    tcl = re.sub(r'(set_pdnsim_inst_power [^\n]*\n)+', lambda _: ''.join(
        f'set_pdnsim_inst_power -inst {n} -power {p_:.9f}\n' for n, p_ in power.items() if p_ > 0), tcl, count=1)
    (work / 'run.tcl').write_text(tcl)
    (work / 'kinds.json').write_text(json.dumps(kinds))
    nb = {}
    for net in ('VDD', 'VSS'):
        f = work / f'vsrc_{net}.loc'
        rows = [r for r in f.read_text().splitlines() if r.strip()]
        if a.quad_pg:     # bumps over a quad stay: they land on the quad's M9 through the bump-pad vias
            ok = rows
        else:
            ok = [r for r in rows if not inq(float(r.split(',')[0]), float(r.split(',')[1]))]
        nb[net] = len(rows) - len(ok)
        f.write_text('\n'.join(ok) + '\n')
    meta.update(method=('c + attn-tile PDN exception (owner 2026-10-06): die M9 -> tile M8 PG pins, M9 blocked over '
                        'the quads, no die M8 in a tile' + (', the quads\' own M9 PG straps exposed (bump-landable) with '
                        'their M8 PG segments and M8-M9 vias, quad power on its M9 straps, bumps kept over the quads'
                        if a.quad_pg else ', quad power on its M8 edge stubs, no bump over a quad')),
                tiles=len(tiles), quads=len(quads), tile_m8_straps={k: len(v) for k, v in tstraps.items()},
                m9_to_tile_m8_vias=added, tile_open_cells=tile_open_moved, quad_stub_loads=len(stubs),
                quad_power_w=round(sum(pool.values()), 4), bumps_removed_over_quads=nb,
                quad_pg=bool(a.quad_pg), quad_m9_straps={k: len(v) for k, v in qpg['M9'].items()},
                quad_m8_segments={k: len(v) for k, v in qpg['M8'].items()}, quad_m8_m9_vias=qvias, quad_isolated_dropped_m8_m9=qdrop, quad_bump_pad_vias=qpads,
                quad_load_cells_on_m9=quad_cells,
                quad_power_without_in_window_stubs_w=round(sum(orphan.values()), 4),
                power_w=round(sum(power.values()), 4), view_lef_sha256=sha(ROOT / VIEWS / 'attn_tile' / f'{ATTN}.lef'))
    (work / 'manifest.json').write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: meta[k] for k in ('window', 'tiles', 'quads', 'tile_m8_straps', 'm9_to_tile_m8_vias',
                                           'tile_open_cells', 'quad_stub_loads', 'quad_power_w', 'power_w',
                                           'bumps_removed_over_quads')}))


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
    p.add_argument('--allow-extra', action='append', help='a port the view carries that the die netlist does not '
                   'connect yet because it is die top I/O (H11, tape-out scope: e.g. hfd_coll refclk / por of the '
                   'PLL owner); reported as die_top_io_pins, not as a mismatch')
    p.set_defaults(fn=cmd_check)
    p = sp.add_parser('reservation')
    p.add_argument('--master', required=True)
    p.add_argument('--out', required=True)
    p.set_defaults(fn=cmd_reservation)
    p = sp.add_parser('index')
    p.set_defaults(fn=cmd_index)
    p = sp.add_parser('die')
    p.add_argument('--work', required=True)
    p.add_argument('--case', choices=['real', 'grt', 'sta'], required=True)
    p.add_argument('--index', default=str(ROOT / VIEWS / 'index.json'))
    p.add_argument('--k', type=int, default=16)
    p.add_argument('--iters', type=int, default=50)
    p.add_argument('--tag', default='views')
    p.add_argument('--contract-m89', action='append', help='grt: treat this view\'s M8/M9 as free (a decided '
                   're-hardening to the die PG <= M7 contract, e.g. hfd_attn_tile option B); recorded in the manifest')
    p.add_argument('--real-pins', action='store_true', help='grt: bundle a MISMATCH view\'s pins at its real '
                   'positions (default: generator positions + the view\'s obstructions)')
    p.set_defaults(fn=cmd_die)
    p = sp.add_parser('ir-attn')
    p.add_argument('--work', required=True)
    p.add_argument('--window', required=True)
    p.add_argument('--quad-pg', action='store_true', help='expose the quads\' own M9 PG grid (bump-landable), keep '
                   'the bumps over the quads (owner approval 2026-10-06)')
    p.set_defaults(fn=cmd_ir_attn)
    p = sp.add_parser('die-record')
    p.add_argument('--round', required=True)
    p.add_argument('--out')
    p.set_defaults(fn=cmd_die_record)
    a = ap.parse_args(argv)
    return a.fn(a) or 0


if __name__ == '__main__':
    raise SystemExit(main())
