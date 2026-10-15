#!/usr/bin/env python3
"""qwen KV die iteration (die_iter_1012, kv-die lead): bind CLOSED element views (exact-shape LEF + TT/FF ETM libs)
onto the die case's contract masters, in place of the generated contract-shaped frame and its ASSUMED
single-flop constants.

Pin mapping = kv_die.real_pin_bindings convention: die port bit i of die port dp is bit i of the concatenation of
BINDINGS[master]['ports'][dp] (RTL port order, LSB first); a 'sliced' die port continues its base port's
concatenation after the base port's bits.  Every die-port bit of the frame must map onto a real pin, or the master is
NOT bound (reported, stays a placeholder).  RTL pins without a die port keep their own name (no die net).

Outline rule: the real view must fit the contract slot (frame size + 0.05 um); a larger view is a FLOORPLAN-class
mismatch reported for a contract change, not bound.

Per bound master: elements.lef MACRO replaced (frame -> real, renamed); LIBS/qfd_etm_<master>_<c>.lib written from
the view's own ETM (pins renamed, related_pin retargeted); the frame cell removed from LIBS/qfd_elements_<c>.lib.

    python3 tools/qwen_kv_die/bind_views.py --case CASE --libs LIBS --view qkd_kvwq_ctl_bin=DIR [...] --out views.json
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
sys.path.insert(0, str(ROOT / 'tools' / 'qwen_kv_die'))
import kv_die as KV  # noqa: E402
from binding_order import sliced_order

CORNERS = ('tt', 'ff')
OPTIONAL_CORNERS = ('ss',)     # qwen-split kvsys: SS is a reported sensitivity only (owner option B), bound when the view has it


def macro_block(text, name=None):
    m = re.search(r'^MACRO (\S+)\s*$' if name is None else rf'^MACRO ({re.escape(name)})\s*$', text, re.M)
    if not m:
        raise KeyError(name)
    nm = m.group(1)
    e = re.search(rf'^END {re.escape(nm)}\s*$', text[m.end():], re.M)
    return nm, m.start(), m.end() + e.end()


def lef_pins(block):
    """pin name -> (start, end) span of its PIN ... END block inside the macro block."""
    out = {}
    for m in re.finditer(r'^  PIN (\S+)\s*$', block, re.M):
        e = re.search(rf'^  END {re.escape(m.group(1))}\s*$', block[m.end():], re.M)
        out[m.group(1)] = (m.start(), m.end() + e.end())
    return out


def size(block):
    s = re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)', block)
    return float(s.group(1)), float(s.group(2))


def widths(names):
    w = {}
    for n in names:
        mm = re.fullmatch(r'(.+)\[(\d+)\]', n)
        if mm:
            w[mm.group(1)] = max(w.get(mm.group(1), 0), int(mm.group(2)) + 1)
        else:
            w.setdefault(n, 0)        # 0 = scalar
    return w


def bit_names(port, w):
    return [port] if w == 0 else [f'{port}[{i}]' for i in range(w)]


def pin_map(master, frame_w, real_w):
    """real pin bit -> die pin bit; raises ValueError on any frame bit with no real pin."""
    b = KV.BINDINGS[master]
    sliced = b.get('sliced', {})
    groups = {}
    for dp in frame_w:
        base = dp if dp in b['ports'] else sliced.get(dp)
        if base is None:
            raise ValueError(f'{master}: die port {dp} not bound')
        groups.setdefault(base, []).append(dp)
    out = {}
    for base, dps in groups.items():
        seq = []
        for rp in b['ports'][base]:
            if rp not in real_w:
                raise ValueError(f'{master}: real view has no RTL port {rp}')
            seq += bit_names(rp, real_w[rp])
        dps = sliced_order(base, dps)
        need = sum(max(frame_w[d], 1) for d in dps)
        if need != len(seq):
            raise ValueError(f'{master}: die ports {dps} carry {need} bits, RTL {b["ports"][base]} {len(seq)}')
        k = 0
        for d in dps:
            for i in range(max(frame_w[d], 1)):
                out[seq[k]] = f'{d}[{i}]'
                k += 1
    return out


def lib_blocks(text):
    """name -> body of every pin("...") group (scalars and bus members) of the (single) cell."""
    out = {}
    for m in re.finditer(r'\bpin\s*\(\s*"?([^")]+)"?\s*\)\s*\{', text):
        i, depth = m.end(), 1
        while depth:
            c = text[i]
            depth += (c == '{') - (c == '}')
            i += 1
        out[m.group(1)] = text[m.end():i - 1]
    return out


def strip_cell(text, cell):
    m = re.search(rf'^\s*cell\s*\(\s*"?{re.escape(cell)}"?\s*\)\s*\{{', text, re.M)
    if not m:
        return text, False
    i, depth = m.end(), 1
    while depth:
        c = text[i]
        depth += (c == '{') - (c == '}')
        i += 1
    return text[:m.start()] + text[i:], True


def write_lib(master, corner, src, pmap, frame_w, dst):
    t = src.read_text()
    hdr = t[:re.search(r'^\s*cell\s*\(', t, re.M).start()]
    hdr = re.sub(r'library\s*\(\s*"?[^")]+"?\s*\)', f'library (qfd_etm_{master}_{corner})', hdr, count=1)
    bodies = lib_blocks(t[len(hdr):])
    rel = {k: v for k, v in pmap.items()}

    def retarget(body):
        return re.sub(r'related_pin\s*:\s*"([^"]+)"', lambda m: f'related_pin : "{rel.get(m.group(1), m.group(1))}"', body)
    inv = {}
    for rp, dp in pmap.items():
        inv[dp] = rp
    L = [hdr.rstrip()]
    for w in sorted({max(v, 1) for v in frame_w.values()}):
        L.append(f'  type ("kvb{w}") {{\n    base_type : array;\n    data_type : bit;\n    bit_width : {w};\n'
                 f'    bit_from : {w - 1};\n    bit_to : 0;\n    downto : true;\n  }}')
    L += [f'  cell ("{master}") {{', '    is_macro_cell : true;', '    dont_touch : true;', '    dont_use : true;']
    missing = []
    for dp, w in sorted(frame_w.items()):
        w = max(w, 1)
        bits = [inv.get(f'{dp}[{i}]') for i in range(w)]
        if any(b is None or b not in bodies for b in bits):
            missing += [f'{dp}[{i}]' for i, b in enumerate(bits) if b is None or b not in bodies]
            continue
        d = re.search(r'direction\s*:\s*(\w+)', bodies[bits[0]]).group(1)
        L.append(f'    bus("{dp}") {{\n      bus_type : kvb{w};\n      direction : {d};')
        for i, b in enumerate(bits):
            L.append(f'    pin("{dp}[{i}]") {{{retarget(bodies[b])}}}')
        L.append('    }')
    L += ['  }', '}']
    if missing:
        raise ValueError(f'{master} {corner}: lib has no timing pin for {missing[:5]} (+{len(missing) - 5})')
    dst.write_text('\n'.join(L) + '\n')
    return hashlib.sha256(src.read_bytes()).hexdigest()


def bind(case, libs, master, vdir):
    vdir = Path(vdir)
    lef = next(vdir.glob('*.lef'))
    elef = case / 'elements.lef'
    et = elef.read_text()
    _, s0, s1 = macro_block(et, master)
    frame = et[s0:s1]
    fw, fh = size(frame)
    frame_w = widths(lef_pins(frame))
    rt = lef.read_text()
    rname, r0, r1 = macro_block(rt)
    real = rt[r0:r1]
    rw, rh = size(real)
    rec = dict(view=str(vdir.relative_to(ROOT)) if vdir.is_absolute() and ROOT in vdir.parents else str(vdir),
               module=rname, real_um=[rw, rh], slot_um=[fw, fh], lef_sha256=hashlib.sha256(lef.read_bytes()).hexdigest())
    if rw > fw + 0.05 or rh > fh + 0.05:
        rec.update(bound=False, cls='floorplan', reason=f'real {rw} x {rh} exceeds slot {fw} x {fh}')
        return rec
    rpins = lef_pins(real)
    real_w = widths(p for p in rpins if p not in ('VDD', 'VSS'))
    try:
        pmap = pin_map(master, frame_w, real_w)
    except ValueError as e:
        rec.update(bound=False, cls='interface', reason=str(e))
        return rec
    # LEF: rename the macro and every mapped pin
    out, last = [], 0
    for p, (a, b) in sorted(rpins.items(), key=lambda kv: kv[1][0]):
        out.append(real[last:a])
        blk = real[a:b]
        if p in pmap:
            blk = blk.replace(f'  PIN {p}\n', f'  PIN {pmap[p]}\n', 1)
            blk = re.sub(rf'^  END {re.escape(p)}\s*$', f'  END {pmap[p]}', blk, flags=re.M)
        out.append(blk)
        last = b
    out.append(real[last:])
    new = ''.join(out)
    new = re.sub(rf'^MACRO {re.escape(rname)}\s*$', f'MACRO {master}', new, count=1, flags=re.M)
    new = re.sub(rf'^END {re.escape(rname)}\s*$', f'END {master}', new, count=1, flags=re.M)
    new = re.sub(rf'FOREIGN {re.escape(rname)}\b', f'FOREIGN {master}', new)
    libsha = {}
    try:
        for c in CORNERS + OPTIONAL_CORNERS:
            src = next(vdir.glob(f'*_{c}.lib'), None)
            if src is None:
                if c in OPTIONAL_CORNERS:
                    continue
                raise ValueError(f'{master}: view has no {c} lib')
            libsha[c] = write_lib(master, c, src, pmap, frame_w, libs / f'qfd_etm_{master}_{c}.lib')
    except (ValueError, StopIteration) as e:
        for c in CORNERS + OPTIONAL_CORNERS:
            (libs / f'qfd_etm_{master}_{c}.lib').unlink(missing_ok=True)
        rec.update(bound=False, cls='timing_view', reason=str(e))
        return rec
    elef.write_text(et[:s0] + new + et[s1:])
    for c in CORNERS + OPTIONAL_CORNERS:
        f = libs / f'qfd_elements_{c}.lib'
        if not f.exists():
            continue
        t, ok = strip_cell(f.read_text(), master)
        f.write_text(t)
    rec.update(bound=True, mapped_bits=len(pmap), unmapped_real_pins=len(real_w) and sum(1 for p in rpins if p not in pmap and p not in ('VDD', 'VSS')),
               lib_sha256=libsha)
    return rec


def share(case, bound):
    """instance / area share: real (PHY macros + bound views), relay, placeholder."""
    et = (case / 'elements.lef').read_text() + ''.join(p.read_text() for p in case.glob('phy*.lef'))
    sz = {m.group(1): size(et[m.start():et.index(f'END {m.group(1)}', m.start())])
          for m in re.finditer(r'^MACRO (\S+)\s*$', et, re.M)}
    v = (case / 'die.v').read_text()
    agg = {'real': [0, 0.0], 'relay': [0, 0.0], 'placeholder': [0, 0.0]}
    per = {}
    for m in re.finditer(r'^\s+(\w+)\s+(\w+)\s*\(', v, re.M):
        mst = m.group(1)
        if mst not in sz:
            continue
        k = 'relay' if mst.startswith('qkd_rly') else 'real' if (mst in bound or mst.startswith('ot_')) else 'placeholder'
        a = sz[mst][0] * sz[mst][1] / 1e6
        agg[k][0] += 1
        agg[k][1] += a
        per.setdefault(mst, [k, 0, 0.0])
        per[mst][1] += 1
        per[mst][2] += a
    ni = sum(x[0] for x in agg.values())
    na = sum(x[1] for x in agg.values())
    return dict({k: dict(inst=n, inst_pct=round(100 * n / ni, 1), mm2=round(a, 3), area_pct=round(100 * a / na, 1))
                 for k, (n, a) in agg.items()}, per_master={k: dict(kind=a, inst=b, mm2=round(c, 3)) for k, (a, b, c) in sorted(per.items())})


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--case', type=Path, required=True)
    ap.add_argument('--libs', type=Path, required=True)
    ap.add_argument('--view', action='append', default=[], help='master=view_dir')
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--split', action='store_true', help='qwen-split KV/system die bindings (kv_die SPLIT_BINDINGS)')
    a = ap.parse_args(argv)
    if a.split:
        KV._set_geometry(True)
    recs = {}
    for v in a.view:
        mst, d = v.split('=', 1)
        recs[mst] = bind(a.case, a.libs, mst, (ROOT / d) if not Path(d).is_absolute() else Path(d))
    bound = {m for m, r in recs.items() if r.get('bound')}
    rec = dict(schema='opentallas.qwen_kv_die_views.v1', views=recs, bound=sorted(bound), share=share(a.case, bound))
    a.out.write_text(json.dumps(rec, indent=1) + '\n')
    print(json.dumps(dict(bound=sorted(bound), unbound={m: r['reason'] for m, r in recs.items() if not r.get('bound')},
                          share={k: v for k, v in rec['share'].items() if k != 'per_master'}), indent=1))


if __name__ == '__main__':
    main()
