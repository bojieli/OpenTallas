#!/usr/bin/env python3
"""Qwen TP8 die: REAL view binding (owner 2026-10-13: a design is released only with die timing closed on a die built
from REAL views).

Keyed by MASTER name, so it re-runs on any die case (it2, it2+delay, it3 ...):

    real_bind.py --case CASE_DIR [--netlist die.v] --repo SRC_ROOT [--status STATUS.txt] [--prev-libs LIBS_DIR]
                 --bind OUT.json [--out LIBS_REAL_DIR] [--log SLOT_FIT.log]

For every master the die netlist instantiates that is a case LEF macro (CASE_DIR/*.lef) or has a view:

  class real         a view found BY NAME (a directory under SRC_ROOT/physical holding <master>.lef + <master>_tt.lib,
                     the shape ref_tile export / the closure loop write; the same rule as die_real_census.py), whose
                     LEF outline and pin set fit the case slot, whose job is CLOSED (when --status is given) and whose
                     ETM was exported with the routed-verdict SDC replay (abstract.json "verdict", main >= abc334b14)
  class provisional  the same, but the ETM is a PRE-FIX export (kit signoff.sdc instead of the routed verdict sequence:
                     input setup arcs ~30..50 ps too tight, input hold arcs ~30..50 ps too loose)
  class hard_macro   a memory / PHY macro abstract found by name (view path matches die_real_census MACRO_RE) that fits
  class placeholder  everything else; "reason" says why.  A closed view that exists but does not fit the slot is
                     "view exists, slot mismatch" with both outlines / the pin difference: a slot change request for
                     the contract agent (or a die-generator change), never forced in.

The case slot is the case LEF macro (SIZE + pins); a master the case LEF does not carry (tiles added to the netlist
from their own view, e.g. the tree delay tiles) is checked on the netlist port names only.
Candidate views that are not named after the master ("alias": physical/qwen_die_masters/views/<master>_<rev>, kits
<master stem>_m5 ...) are compared and reported, but never bound: their macro / cell is another name, so a die that
binds them is binding by role, which the census does not count as real.

--out writes the die view set (nothing from the previous libs is modified):
  elements_real.lef       the case LEF with every bound macro replaced by the view's macro (verbatim), bound masters the
                          case LEF lacks appended, and a generated outline for instantiated masters with no LEF at all
                          (kit outline, pins at the centre; marked placeholder)
  real/<master>_<c>.lib   the view's Liberty, verbatim
  qfd_*_<c>.lib           the previous libs (symlink; rewritten without the bound cells when they define one)
  libs_<c>.txt            the Liberty list of the corner
"""
import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hier_contract'))
from die_real_census import lef_macros, view_index, KEYWORDS, MACRO_RE  # noqa: E402

SCHEMA = 'opentallas.qwen_tp8.real_bind.v1'
PG = {'VDD', 'VSS'}
CORNERS = ('tt', 'ff', 'ss')
STEM = re.compile(r'_(n|s|e|w|g|f1|m)$')


def netlist(path):
    """({master: count}, {master: sorted port names of its first instance})"""
    inst, ports = Counter(), {}
    rx = re.compile(r'^\s*([A-Za-z_]\w*)\s+(?:#\s*\(.*?\)\s*)?(\\\S+\s|[A-Za-z_][\w$]*(?:\[\d+\])?)\s*\((.*)')
    with open(path, errors='replace') as fh:
        for ln in fh:
            m = rx.match(ln)
            if m and m.group(1) not in KEYWORDS:
                inst[m.group(1)] += 1
                if m.group(1) not in ports:
                    ports[m.group(1)] = sorted(set(re.findall(r'\.(\w+)\s*\(', m.group(3))))
    return inst, ports


def bases(pins):
    c = Counter(re.sub(r'\[\d+\]$', '', p) for p in pins)
    return {k: v for k, v in c.items() if k not in PG}


def view_files(vd, name=None):
    """(lef path, cell name, {corner: lib path}) of a view directory; name = the cell expected"""
    lefs = sorted(vd.glob('*.lef'))
    if name and (vd / f'{name}.lef').exists():
        lef = vd / f'{name}.lef'
    elif lefs:
        lef = lefs[0]
    else:
        return None, None, {}
    stem = lef.stem
    return lef, stem, {c: vd / f'{stem}_{c}.lib' for c in CORNERS if (vd / f'{stem}_{c}.lib').exists()}


def provenance(vd):
    """(closed_job, export class, ok flag) from abstract.json (ref_tile export) / export.json (w18 export)"""
    job, exp, ok = None, 'pre-fix', None
    for f in ('abstract.json', 'export.json'):
        p = vd / f
        if not p.exists():
            continue
        try:
            a = json.loads(p.read_text())
        except ValueError:
            continue
        m = re.search(r'closure-loop/([^/]+)/routes/', str(a.get('orfs_dir', '')))
        job = m.group(1) if m else job
        ok = a.get('ok', ok)
        v = a.get('verdict')
        if isinstance(v, dict) and v.get('expect_ps') and a.get('ok', True):
            exp = 'corrected'
        break
    return job, exp, ok


def status_map(path):
    out = {}
    if path:
        for ln in Path(path).read_text(errors='replace').splitlines():
            t = ln.split()
            if len(t) >= 2 and re.match(r'^[A-Za-z_]', t[0]):
                out[t[0]] = t[1]
    return out


def alias_views(repo, master):
    """views that may implement the master under another cell name (reported, never bound)"""
    out, stem = [], STEM.sub('', master)
    for vd in sorted(list((repo / 'physical/ref_tile').glob('*/views/*')) + list((repo / 'physical/qwen_die_masters/views').glob('*'))):
        if not vd.is_dir():
            continue
        v = vd.name
        kit = vd.parts[-3] if vd.parts[-2] == 'views' and vd.parts[-4] == 'ref_tile' else ''
        if v == master:
            continue                                         # by name: found by view_index
        if v.startswith(master + '_') or v in (stem,) or v.startswith(stem + '_') or kit == master or \
                kit.startswith(master + '_') or kit.startswith(stem + '_'):
            out.append(vd)
    return out


def fit(slot, ports, vmac):
    """(verdict, detail) of a view macro against the case slot (case macro dict or None) / the netlist ports"""
    vb = bases(vmac['pins'])
    if slot is None:
        want = {p for p in ports if p not in PG}
        if want == set(vb):
            return 'ok', {'case': 'no case macro (netlist ports only)', 'view_size': vmac['size']}
        return 'pin mismatch', {'case': 'no case macro (netlist ports only)', 'view_size': vmac['size'],
                                'only_case': sorted(want - set(vb))[:12], 'only_view': sorted(set(vb) - want)[:12]}
    d = {'case_size': slot['size'], 'view_size': vmac['size']}
    if slot['size'] != vmac['size']:
        cb = bases(slot['pins'])
        d.update(case_pins=cb if len(cb) <= 30 else len(cb), view_pins=vb if len(vb) <= 30 else len(vb))
        return (f"outline mismatch (case {slot['size'][0]:g}x{slot['size'][1]:g} vs view "
                f"{vmac['size'][0]:g}x{vmac['size'][1]:g})"), d
    if set(slot['pins']) - PG != set(vmac['pins']) - PG:
        cb = bases(slot['pins'])
        d.update(case_pins=cb if len(cb) <= 30 else len(cb), view_pins=vb if len(vb) <= 30 else len(vb),
                 case_bits=sum(cb.values()), view_bits=sum(vb.values()))
        return 'pin mismatch', d
    return 'ok', d


def case_macros(case_lefs, inst):
    macros = {}
    for p in case_lefs:
        macros.update(lef_macros(p, set(inst)))
    return macros


def bind(case_lefs, inst, ports, repo, status):
    macros = case_macros(case_lefs, inst)
    named = view_index([repo], set(inst))
    out = {}
    for m in sorted(inst, key=lambda k: (-inst[k], k)):
        slot = macros.get(m)
        def exact(vd):                                       # the view the case macro was copied from goes first
            x = lef_macros(vd / f'{m}.lef', {m}).get(m)
            return not (x and slot and x['hash'] == slot['hash'])
        cands = [(vd, True) for vd in sorted(named.get(m, []), key=exact)] + [(vd, False) for vd in alias_views(repo, m)]
        if slot is None and not cands:
            if m in macros or not re.match(r'^(ot_|qfd_|qkd_|qkh_)', m):
                continue
        rec = {'class': 'placeholder', 'instances': inst[m], 'lef': None, 'export': None, 'closed_job': None,
               'slot_fit': None, 'reason': 'no closed view of this master on the source tree',
               'case_size': slot['size'] if slot else None, 'candidates': []}
        for vd, by_name in cands:
            lef, cell, libs = view_files(vd, m if by_name else None)
            if lef is None:
                continue
            macs = lef_macros(lef)
            mname = cell if cell in macs else next(iter(macs), None)
            if mname is None:
                continue
            vmac = macs[mname]
            verdict, detail = fit(slot, ports.get(m, []), vmac)
            job, exp, ok = provenance(vd)
            st = status.get(job) if status else None
            hard = bool(re.search(MACRO_RE, str(vd)))
            c = {'view': str(vd.relative_to(repo)), 'cell': mname, 'by_name': by_name, 'slot_fit': verdict,
                 'closed_job': job, 'job_status': st, 'export': exp, 'detail': detail}
            rec['candidates'].append(c)
            closed = (st == 'CLOSED') if status else True
            if hard and by_name and verdict == 'ok' and 'tt' in libs and rec['class'] == 'placeholder':
                rec.update({'class': 'hard_macro', 'lef': str(lef.relative_to(repo)), 'export': 'n/a', 'slot_fit': 'ok',
                            'view': c['view'], 'reason': 'memory / PHY macro abstract by name (not a routed element)'})
                for k in CORNERS:
                    rec[f'lib_{k}'] = str(libs[k].relative_to(repo)) if k in libs else None
            if by_name and verdict == 'ok' and closed and 'tt' in libs and rec['class'] == 'placeholder':
                rec.update({'class': 'real' if exp == 'corrected' else 'provisional', 'lef': str(lef.relative_to(repo)),
                            'export': exp, 'closed_job': job, 'slot_fit': 'ok', 'view': c['view'],
                            'reason': 'closed view by name, outline and pins fit' +
                                      ('' if exp == 'corrected' else '; PROVISIONAL: pre-fix ETM export (kit signoff.sdc, not the routed verdict SDC)')})
                for k in CORNERS:
                    rec[f'lib_{k}'] = str(libs[k].relative_to(repo)) if k in libs else None
        if rec['class'] == 'placeholder' and rec['candidates']:
            best = sorted(rec['candidates'], key=lambda c: (c['slot_fit'] != 'ok', not c['by_name'],
                                                            c['job_status'] != 'CLOSED', not c['slot_fit'].startswith('pin')))[0]
            rec.update(slot_fit=best['slot_fit'], closed_job=best['closed_job'], export=best['export'])
            if best['slot_fit'] != 'ok':
                rec['reason'] = f"view exists, slot mismatch: {best['slot_fit']} ({best['view']}, cell {best['cell']})"
                rec['view_size'] = best['detail'].get('view_size')
            elif not best['by_name']:
                rec['reason'] = (f"view fits but is cell {best['cell']} ({best['view']}): republish under the master "
                                 "name or instantiate the cell; a by-role bind is not real")
            else:
                rec['reason'] = f"view by name fits but its job is {best['job_status']} ({best['closed_job']})"
        out[m] = rec
    return out


def macro_text(lef, name):
    buf, on = [], False
    with open(lef, errors='replace') as fh:
        for ln in fh:
            if not on and re.match(rf'\s*MACRO\s+{re.escape(name)}\s*$', ln):
                on = True
            if on:
                buf.append(ln)
                if re.match(rf'\s*END\s+{re.escape(name)}\s*$', ln):
                    break
    return ''.join(buf)


def gen_macro(name, w, h, ports):
    """generated outline (placeholder): pins at the centre on M4"""
    s = [f'MACRO {name}\n  CLASS BLOCK ;\n  ORIGIN 0 0 ;\n  SIZE {w:g} BY {h:g} ;\n  SYMMETRY X Y ;\n']
    for p in ports:
        s.append(f'  PIN {p}\n    DIRECTION INOUT ;\n    USE SIGNAL ;\n    PORT\n      LAYER M4 ;\n        RECT {w / 2 - 0.012:.3f} '
                 f'{h / 2 - 0.012:.3f} {w / 2 + 0.012:.3f} {h / 2 + 0.012:.3f} ;\n    END\n  END {p}\n')
    s.append(f'END {name}\n')
    return ''.join(s)


def kit_outline(repo, master):
    for sp in sorted((repo / 'physical/ref_tile').glob('*/spec.json')):
        try:
            s = json.loads(sp.read_text())
        except ValueError:
            continue
        if s.get('top') == master and isinstance(s.get('outline'), dict):
            return float(s['outline']['w']), float(s['outline']['h']), sp.parent.name
    return None


def strip_cells(src, dst, cells):
    text = src.read_text(errors='replace')
    ms = list(re.finditer(r'^[ \t]*cell\s*\(\s*"?([^")\s]+)"?\s*\)\s*\{', text, re.M))
    keep, pos = [], 0
    for i, m in enumerate(ms):
        if m.group(1) in cells:
            end = ms[i + 1].start() if i + 1 < len(ms) else text.rstrip().rfind('}')
            keep.append(text[pos:m.start()])
            pos = end
    keep.append(text[pos:])
    dst.write_text(''.join(keep))


def copy_without(src, fo, bound, end_library):
    skip = None
    with open(src, errors='replace') as fh:
        for ln in fh:
            if skip is None:
                m = re.match(r'\s*MACRO\s+(\S+)\s*$', ln)
                if m and m.group(1) in bound:
                    skip = m.group(1)
                    continue
                if not end_library and re.match(r'\s*END\s+LIBRARY', ln):
                    continue
                fo.write(ln)
            elif re.match(rf'\s*END\s+{re.escape(skip)}\s*$', ln):
                skip = None


def build(out, case_lefs, binds, inst, ports, repo, prev):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'real').mkdir(exist_ok=True)
    bound = {m: b for m, b in binds.items() if b['class'] in ('real', 'provisional', 'hard_macro')}
    have = set(case_macros(case_lefs, inst))
    gen, lef_out = {}, []
    for p in case_lefs:                                      # the other case LEFs (PHY ...), bound macros removed
        if p.name != 'elements.lef':
            with open(out / p.name, 'w') as fo:
                copy_without(p, fo, bound, True)
            lef_out.append(str(out / p.name))
    with open(out / 'elements_real.lef', 'w') as fo:
        el = [p for p in case_lefs if p.name == 'elements.lef']
        if el:
            copy_without(el[0], fo, bound, False)
        else:
            fo.write('VERSION 5.8 ;\nBUSBITCHARS "[]" ;\nDIVIDERCHAR "/" ;\n')
        for m, b in sorted(bound.items()):
            fo.write(macro_text(repo / b['lef'], m))
        for m in sorted(binds):
            if m not in bound and m not in have:
                k = kit_outline(repo, m)
                if k:
                    fo.write(gen_macro(m, k[0], k[1], [p for p in ports.get(m, [])]))
                    gen[m] = {'outline': [k[0], k[1]], 'kit': k[2]}
                    binds[m]['generated_lef'] = f'kit {k[2]} outline {k[0]:g}x{k[1]:g}, pins at the centre'
        fo.write('END LIBRARY\n')
    lists = {}
    for c in CORNERS:
        lst = []
        for p in sorted(prev.glob(f'*_{c}.lib')) if prev else []:
            dst = out / p.name
            if dst.exists() or dst.is_symlink():
                dst.unlink()
            head = set()
            with open(p, errors='replace') as fh:
                for ln in fh:
                    m = re.match(r'[ \t]*cell\s*\(\s*"?([^")\s]+)', ln)
                    if m:
                        head.add(m.group(1))
            if head & set(bound):
                strip_cells(p, dst, set(bound))
            else:
                os.symlink(p.resolve(), dst)
            lst.append(str(dst))
        for m, b in sorted(bound.items()):
            if b.get(f'lib_{c}'):
                dst = out / 'real' / f'{m}_{c}.lib'
                dst.write_bytes((repo / b[f'lib_{c}']).read_bytes())
                lst.append(str(dst))
        if lst:
            (out / f'libs_{c}.txt').write_text('\n'.join(lst) + '\n')
            lists[c] = len(lst)
    return {'dir': str(out), 'lef': [str(out / 'elements_real.lef')] + lef_out, 'lib_files': lists, 'generated_outlines': gen}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--case', type=Path, required=True, help='die case dir (elements.lef, die.v)')
    ap.add_argument('--netlist', type=Path, help='die netlist (default CASE/die.v)')
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    ap.add_argument('--status', type=Path, help='text of `closure_loop.py status` (a bound view must be CLOSED)')
    ap.add_argument('--prev-libs', type=Path, help='previous die libs dir (placeholder timing of everything else)')
    ap.add_argument('--bind', type=Path, required=True, help='bind JSON to write')
    ap.add_argument('--out', type=Path, help='libs_real dir to build')
    ap.add_argument('--log', type=Path, help='slot-fit log (append only)')
    ap.add_argument('--case-id', default=None)
    a = ap.parse_args(argv)
    repo = a.repo.resolve()
    nl = a.netlist or a.case / 'die.v'
    inst, ports = netlist(nl)
    case_lefs = sorted(a.case.glob('*.lef'))
    binds = bind(case_lefs, inst, ports, repo, status_map(a.status))
    rec = {'schema': SCHEMA, 'case': a.case_id or a.case.name, 'case_dir': str(a.case), 'netlist': str(nl),
           'status_checked': bool(a.status)}
    if a.out:
        rec['libs'] = build(a.out, case_lefs, binds, inst, ports, repo, a.prev_libs)
    tot = Counter()
    for m, b in binds.items():
        tot[b['class']] += b['instances']
    rec['summary'] = {'masters': len(binds), 'instances': sum(tot.values()), 'by_class_instances': dict(tot),
                      'by_class_masters': dict(Counter(b['class'] for b in binds.values())),
                      'slot_mismatch': sorted(m for m, b in binds.items() if b['reason'].startswith('view exists, slot'))}
    rec['masters'] = binds
    a.bind.parent.mkdir(parents=True, exist_ok=True)
    a.bind.write_text(json.dumps(rec, indent=1) + '\n')
    if a.log:
        import time
        with open(a.log, 'a') as fh:
            for m, b in binds.items():
                if b['candidates']:
                    fh.write(f"{time.strftime('%F %T %Z')} [qwen-tp8 real_bind {rec['case']}] {m} x{b['instances']} "
                             f"{b['class']} slot_fit={b['slot_fit']} case={b['case_size']} "
                             f"view={b.get('view') or b['candidates'][0]['view']} job={b['closed_job']} export={b['export']}\n")
    print(json.dumps(rec['summary']))
    for m, b in binds.items():
        if b['candidates']:
            print(f"{b['instances']:6d} {m:28s} {b['class']:11s} {b['reason'][:150]}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
