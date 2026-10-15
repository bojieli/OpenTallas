#!/usr/bin/env python3
"""qwen-tp8 die lead r9 (2026-10-13): bind every CLOSED view onto the die case by NAME.

A die master is bound when a view directory holds <master>.lef (+ <master>_tt.lib / _ff.lib) and
  * the view's SIZE is the case macro's SIZE (+- 0.03 um), and
  * every port the die netlist connects on that master is a pin of the view, at least as wide.
Then the case's MACRO block is REPLACED by the view's own MACRO text (so die_real_census.py sees the exact LEF) and the
view's Liberty files are listed for the die STA. The two explicit cbuf/crom slot wrappers use identity-only
case-local aliases with recorded source provenance; their pins and all timing groups remain unchanged. Other masters
whose views differ are refused with the reason (outline, missing pin, narrower bus) and stays a generated frame.

Reported per bound master: view pins the die leaves unconnected (inputs without a die net are an OPEN item, never tied
here) and the largest move of a pin group's centroid between the generated frame and the view (the relay plan was
made on the frame's pins: hops grow by up to that much).

    bind_real.py --case CASE --repo ROOT [--view MASTER=DIR ...] [--skip MASTER ...] --out bind.json
                 [--lef-out FILE]   (default: CASE/elements.lef rewritten in place, original kept as elements.lef.gen)
View search order per master: --view, physical/ref_tile/<master>/views/<master>, physical/ref_tile/*/views/<master>,
physical/qwen_die_masters/views/<master>, physical/qwen_missing_phy/tp8_1013/<master>, physical/qwen_missing_phy/<master>.
"""
import argparse
import collections
import hashlib
import json
import re
import shutil
from pathlib import Path

SKIP_RE = re.compile(r'^(q[fk]d_rly|qfd_rst_rep)')
PG = ('VDD', 'VSS', 'VDDM', 'VSSM')
# Slot-name wrappers are identity renames only: pins, geometry and timing stay in the
# CLOSED source view. tp8b_v5 emits the source RTL ports and preserves the clock pin clk.
VIEW_ALIASES = {
    'qfd_su_cbuf_g': ('ot_qfd_su_cbuf_g', 'physical/ref_tile/qfd_su_cbuf_g_m5/views/ot_qfd_su_cbuf_g'),
    'qfd_crom_g': ('ot_qfd_crom_gr', 'physical/ref_tile/qfd_crom_g_m5/views/ot_qfd_crom_gr'),
}


def alias_view(root, case, master):
    if master not in VIEW_ALIASES:
        return None
    source, directory = VIEW_ALIASES[master]
    src = root / directory
    required = [src / f'{source}.lef'] + [src / f'{source}_{c}.lib' for c in ('tt', 'ff', 'ss')] + [src / 'insertion.json']
    if not all(p.exists() for p in required):
        return None
    out = (case / 'bound_views' / master).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for p in required:
        txt = p.read_text()
        if p.suffix == '.lef':
            txt = re.sub(rf'(?m)^(MACRO|END) {re.escape(source)}[ \t]*$', rf'\1 {master}', txt)
        elif p.suffix == '.lib':
            # Liberty cell identity changes; all timing/pin/clock groups stay byte-for-byte.
            txt, n = re.subn(rf'(cell\s*\(\s*)"?{re.escape(source)}"?(\s*\))', rf'\1{master}\2', txt)
            if n != 1:
                raise ValueError(f'{p}: expected exactly one source cell, got {n}')
        (out / p.name.replace(source, master)).write_text(txt)
    provenance = dict(source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in required},
                      source_master=source, slot_master=master, source_view=directory,
                      pin_mapping='identity, all pins including clk', liberty_corners=['tt', 'ff', 'ss'],
                      insertion='unchanged from closed source')
    (out / 'alias_provenance.json').write_text(json.dumps(provenance, indent=1) + '\n')
    return out


def macros(text):
    """name -> (start, end, block text)"""
    out = {}
    for m in re.finditer(r'^MACRO (\S+)[ \t]*$', text, re.M):
        nm = m.group(1)
        e = re.search(rf'^END {re.escape(nm)}[ \t]*$', text[m.end():], re.M)
        if e:
            out[nm] = (m.start(), m.end() + e.end(), text[m.start():m.end() + e.end()])
    return out


def size(block):
    m = re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)', block)
    return (float(m.group(1)), float(m.group(2))) if m else None


def pins(block):
    """base name -> dict(bits, cx, cy, layers, direction)"""
    out = {}
    for m in re.finditer(r'^\s*PIN (\S+)\s*$(.*?)^\s*END \1\s*$', block, re.M | re.S):
        base = re.sub(r'\[\d+\]$', '', m.group(1))
        d = out.setdefault(base, dict(bits=0, sx=0.0, sy=0.0, n=0, layers=set(), direction=None))
        d['bits'] += 1
        dm = re.search(r'DIRECTION\s+(\w+)', m.group(2))
        if dm:
            d['direction'] = dm.group(1).lower()
        for lay, r in re.findall(r'LAYER (\S+) ;\s*\n\s*RECT ([-\d. ]+) ;', m.group(2)):
            x0, y0, x1, y1 = map(float, r.split()[:4])
            d['sx'] += (x0 + x1) / 2
            d['sy'] += (y0 + y1) / 2
            d['n'] += 1
            d['layers'].add(lay)
    for d in out.values():
        k = max(d.pop('n'), 1)
        d['cx'], d['cy'] = d.pop('sx') / k, d.pop('sy') / k
        d['layers'] = sorted(d['layers'])
    return out


def die_ports(die_v):
    """master -> {port: widest connection}, master -> instance count"""
    txt = Path(die_v).read_text()
    width = {m.group(2): int(m.group(1)) + 1 for m in re.finditer(r'wire \[(\d+):0\] (\S+);', txt)}
    ports, count = collections.defaultdict(dict), collections.Counter()
    for m in re.finditer(r'^\s+(\w+) (\S+) \((.*?)\);', txt, re.M):
        mst, body = m.group(1), m.group(3)
        if mst in ('wire', 'module'):
            continue
        count[mst] += 1
        for p in re.finditer(r'\.(\S+?)\(([^()]*)\)', body):
            port, ex = p.group(1).lstrip('\\').strip(), p.group(2).strip()
            if ex.startswith('{'):
                n = 0
                for e in ex.strip('{}').split(','):
                    q = re.fullmatch(r'\s*\S+?\[(\d+)(?::(\d+))?\]\s*', e)
                    n += (int(q.group(1)) - int(q.group(2) or q.group(1)) + 1) if q else 1
            else:
                q = re.fullmatch(r"(\S+?)\[(\d+)(?::(\d+))?\]", ex)
                c = re.fullmatch(r"(\d+)'[bdh]\w+", ex)
                n = (int(q.group(2)) - int(q.group(3) or q.group(2)) + 1) if q else int(c.group(1)) if c else width.get(ex, 1)
            ports[mst][port] = max(ports[mst].get(port, 0), n)
    return ports, count


def find_view(root, master, explicit):
    if master in explicit:
        return Path(explicit[master])
    cands = [root / 'physical/ref_tile' / master / 'views' / master]
    cands += sorted((root / 'physical/ref_tile').glob(f'*/views/{master}'))
    cands += [root / 'physical/qwen_die_masters/views' / master, root / 'physical/qwen_missing_phy/tp8_1013' / master,
              root / 'physical/qwen_missing_phy' / master]
    for c in cands:
        if (c / f'{master}.lef').exists():
            return c
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--case', required=True)
    ap.add_argument('--repo', required=True)
    ap.add_argument('--view', action='append', default=[])
    ap.add_argument('--skip', action='append', default=[])
    ap.add_argument('--out', required=True)
    ap.add_argument('--lef-out')
    ap.add_argument('--dry', action='store_true', help='report only: the case LEF is not rewritten')
    a = ap.parse_args()
    case, root = Path(a.case), Path(a.repo).resolve()
    explicit = dict(q.split('=', 1) for q in a.view)
    src = case / 'elements.lef.gen'          # not *.lef: the case readers glob the LEFs
    if not src.exists():
        shutil.copy(case / 'elements.lef', src)
    text = src.read_text()
    M = macros(text)
    ports, count = die_ports(case / 'die.v')
    rep, repl = {}, {}
    for mst in sorted(count):
        if SKIP_RE.match(mst) or mst not in M:
            continue
        r = rep.setdefault(mst, dict(instances=count[mst], bound=False))
        if mst in a.skip:
            r['reason'] = 'skipped on the command line'
            continue
        vd = find_view(root, mst, explicit)
        if vd is None:
            vd = alias_view(root, case, mst)
            if vd is not None:
                r['alias_provenance'] = json.loads((vd / 'alias_provenance.json').read_text())
        if vd is None:
            r['reason'] = 'no view by this name'
            continue
        r['view'] = str(vd.relative_to(root)) if vd.is_absolute() and root in vd.parents else str(vd)
        vt = (vd / f'{mst}.lef').read_text()
        vm = macros(vt).get(mst)
        if vm is None:
            r['reason'] = f'{mst}.lef holds no MACRO {mst}'
            continue
        sg, sv = size(M[mst][2]), size(vm[2])
        r['size_case'], r['size_view'] = sg, sv
        if abs(sg[0] - sv[0]) > 0.03 or abs(sg[1] - sv[1]) > 0.03:
            r['reason'] = f'outline: case {sg[0]} x {sg[1]}, view {sv[0]} x {sv[1]}'
            continue
        pg, pv = pins(M[mst][2]), pins(vm[2])
        miss = sorted(p for p in ports[mst] if p not in pv)
        narrow = sorted(f'{p} {ports[mst][p]} > {pv[p]["bits"]}' for p in ports[mst] if p in pv and ports[mst][p] > pv[p]['bits'])
        if miss or narrow:
            r['reason'] = 'pins: ' + '; '.join(([f'{len(miss)} die ports not in the view ({", ".join(miss[:8])})'] if miss else []) +
                                              ([f'narrower in the view ({", ".join(narrow[:6])})'] if narrow else []))
            continue
        open_in = sorted(p for p, d in pv.items() if p not in ports[mst] and p not in PG and d['direction'] in ('input', 'inout'))
        open_out = sorted(p for p, d in pv.items() if p not in ports[mst] and p not in PG and d['direction'] == 'output')
        wider = sorted(f'{p} {pv[p]["bits"]} > {ports[mst][p]}' for p in ports[mst] if pv[p]['bits'] > ports[mst][p])
        mv = sorted(((round(abs(pg[p]['cx'] - pv[p]['cx']) + abs(pg[p]['cy'] - pv[p]['cy']), 2), p) for p in ports[mst] if p in pg),
                    reverse=True)
        lay = sorted(f'{p} {"/".join(pg[p]["layers"])} -> {"/".join(pv[p]["layers"])}' for p in ports[mst]
                     if p in pg and pg[p]['layers'] != pv[p]['layers'])
        libs = {c: str((vd / f'{mst}_{c}.lib').relative_to(root)) if root in vd.parents else str(vd / f'{mst}_{c}.lib') for c in ('tt', 'ff', 'ss') if (vd / f'{mst}_{c}.lib').exists()}
        r.update(bound=True, pins=len(ports[mst]), inputs_without_die_net=open_in, outputs_without_die_net=open_out,
                 die_bus_narrower_than_view=wider, pin_centroid_move_um=mv[:4], pin_layer_changes=lay[:8], libs=libs,
                 insertion=(vd / 'insertion.json').exists(), pg_layers=sorted({l for p in PG if p in pv for l in pv[p]['layers']}))
        if not libs.get('tt'):
            r['note'] = 'LEF bound; no TT Liberty beside it'
        repl[mst] = vm[2]
    if not a.dry:
        out = text
        for mst in sorted(repl, key=lambda q: -M[q][0]):          # back to front: offsets stay valid
            s, e, _ = M[mst]
            out = out[:s] + repl[mst] + out[e:]
        Path(a.lef_out or case / 'elements.lef').write_text(out)
    tot = sum(r['instances'] for r in rep.values())
    b = sum(r['instances'] for r in rep.values() if r['bound'])
    summary = dict(schema='opentallas.qwen-tp8.bind-real.v1', case=str(case), masters=len(rep), masters_bound=sum(1 for r in rep.values() if r['bound']),
                   instances=tot, instances_bound=b, relays_and_reset_repeaters=sum(n for q, n in count.items() if SKIP_RE.match(q)),
                   refused={q: r['reason'] for q, r in rep.items() if not r['bound'] and r.get('view')},
                   no_view=sorted(q for q, r in rep.items() if not r['bound'] and not r.get('view')),
                   open_inputs={q: r['inputs_without_die_net'] for q, r in rep.items() if r.get('inputs_without_die_net')},
                   lib_list=sorted(l for r in rep.values() if r['bound'] for l in r.get('libs', {}).values()))
    Path(a.out).write_text(json.dumps(dict(summary, masters_detail=rep), indent=1) + '\n')
    print(json.dumps({k: summary[k] for k in ('masters', 'masters_bound', 'instances', 'instances_bound', 'refused', 'open_inputs')}))


if __name__ == '__main__':
    main()
