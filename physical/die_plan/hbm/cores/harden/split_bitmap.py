#!/usr/bin/env python3
"""HBM-CORES-KITS-5 (2026-10-28): bit-level cut map for REMAINDER split cores (rest_extract.sh + rest_wrap.py tops).

The remainder tops regroup the cut bits under as-built hierarchical names (rest_wrap.py), so a plan cut pin bus is not
always one whole RTL port: e.g. split3 ctl plan ro_x_{n,s,e,w}[128] = RTL u_core_ro_x_{e,w}[256] halves, 16 per-lane
plan ro_x[32] buses = RTL u_core_e_rox[512].  build_split_tops.auto_map only maps whole buses by name / unique width,
so gen_core_kit_hbm.build_wrapper stopped with MAP_AMBIGUOUS.  This tool derives the map from NET IDENTITY instead of
names or widths:

  * the master RTL is elaborated (yosys proc; memory_map; flatten; opt_clean -> write_json), so every hierarchical
    wire / blackbox cell port of the master that is one net shares the same sigbit;
  * every plan cut pin bus (ports_cut.json) resolves to a master wire or cell port by its cleaned hierarchical name
    (the name rule the cut used: '.', '[', ']' -> '_', optional 'x_' prefix);
  * every RTL top port bit resolves, through the rest_wrap.py wrapper (u_x connections + __full assigns), to the
    as-built hierarchical bit it carries;
  * plan bit -> RTL bit = same sigbit.  Inputs may fan out to several RTL bits of one net; outputs take one.

Output (opt-in, read by gen_core_kit_hbm.py only when present): {type_id: {plan_bus: [[rtl_port, rtl_lsb, plan_lsb,
nbits], ...]}} plus a check record.  Whole-bus renames in canonical_ports_split.json are re-proved (same sigbits) and
reported; they are not rewritten.

    split_bitmap.py --master-json master.json --master-top ot_hgi_sfu_core_split3 --rest-sv CORE.sv --rest-top TOP
                    --cut ports_cut.json --piece PLAN_MODULE --canon canonical_ports_split.json --ftype sfu_ctl
                    --out OUT.json
"""
import argparse
import json
import re
import sys


def clean(nm):
    s = nm.lstrip('\\')
    s = re.sub(r'[^A-Za-z0-9_]+', '_', s).strip('_')
    return re.sub(r'_+', '_', s)


def master_index(mj, top):
    """name -> list of sigbits (LSB first, index = bit - offset) for netnames and blackbox cell ports."""
    m = mj['modules'][top]
    names = {}
    for n, v in m['netnames'].items():
        bits = v['bits']
        names[n] = dict(bits=bits, offset=v.get('offset', 0), upto=v.get('upto', 0))
    for cn, c in m.get('cells', {}).items():
        if c['type'].startswith('$'):
            continue
        for p, bits in c.get('connections', {}).items():
            k = cn + '.' + p
            if k not in names:
                names[k] = dict(bits=bits, offset=0, upto=0, cell=True,
                                dir=c.get('port_directions', {}).get(p))
    return names


def bit_of(rec, idx):
    i = idx - rec['offset']
    if rec['upto']:
        i = len(rec['bits']) - 1 - i
    if not 0 <= i < len(rec['bits']):
        return None
    return rec['bits'][i]


def rest_ports(txt, top):
    """RTL top ports [(name, dir, width)] and rtl bit -> (hier name, hier index)."""
    m = re.search(r'(?ms)^module\s+' + re.escape(top) + r'\s*\((.*?)^\);(.*?)^endmodule', txt)
    if not m:
        raise SystemExit(f'no module {top}')
    ports = []
    for d, h, l, n in re.findall(r'(input|output)\s+wire\s+(?:\[(\d+):(\d+)\]\s*)?(\w+)', m.group(1)):
        ports.append((n, d, int(h) - int(l) + 1 if h else 1))
    pw = {n: w for n, _, w in ports}
    body = m.group(2)
    full = {}
    for f, i, c, k in re.findall(r'assign\s+(\w+__full)\[(\d+)\]\s*=\s*(\w+)(?:\[(\d+)\])?\s*;', body):
        full[(f, int(i))] = (c, int(k) if k else 0)
    inst = re.search(r'(?ms)^\s*' + re.escape(top) + r'_x\s+u_x\s*\((.*?)\);', body)
    if not inst:
        raise SystemExit(f'no {top}_x u_x instance')
    rtl2h = {}
    for pn, tgt in re.findall(r'\.(\\\S+|\w+)\s*\(([^()]*)\)', inst.group(1)):
        tgt = tgt.strip()
        if not tgt or re.match(r"^\d+'", tgt):
            continue
        hm = re.match(r'^\\(.+)\[(\d+)\]$', pn)
        base, hi = (hm.group(1), int(hm.group(2))) if hm else (pn.lstrip('\\'), None)
        tm = re.match(r'^(\w+)(?:\[(\d+)\])?$', tgt)
        if not tm:
            raise SystemExit(f'unparsed connection .{pn}({tgt})')
        tn, tk = tm.group(1), tm.group(2)
        if tn.endswith('__full'):
            for (f, i), (c, k) in full.items():
                if f == tn:
                    rtl2h[(c, k)] = (base, i)
        elif tk is not None:
            rtl2h[(tn, int(tk))] = (base, hi if hi is not None else 0)
        else:
            for j in range(pw[tn]):
                rtl2h[(tn, j)] = (base, j) if hi is None else (base, hi)
    return ports, rtl2h


def runs(pairs):
    """[(plan_bit, port, port_bit)] -> [[port, port_lsb, plan_lsb, n]] (maximal ascending runs)."""
    out = []
    for pb, p, k in sorted(pairs, key=lambda x: (x[0], x[1], x[2])):
        if out and out[-1][0] == p and out[-1][1] + out[-1][3] == k and out[-1][2] + out[-1][3] == pb:
            out[-1][3] += 1
        else:
            out.append([p, k, pb, 1])
    return out


def build(mj, mtop, rest_txt, rtop, cut, canon_tid=None):
    names = master_index(mj, mtop)
    byclean = {}
    for n in names:
        byclean.setdefault(clean(n), []).append(n)
    ports, rtl2h = rest_ports(rest_txt, rtop)
    pdir = {n: d for n, d, _ in ports}
    sig2rtl = {}
    unresolved_rtl = []
    for (p, k), (h, i) in sorted(rtl2h.items()):
        rec = names.get(h)
        if rec is None:
            c = byclean.get(clean(h), [])
            rec = names[c[0]] if len(c) == 1 else None
        b = bit_of(rec, i) if rec else None
        if b is None:
            unresolved_rtl.append(f'{p}[{k}]<-{h}[{i}]')
            continue
        sig2rtl.setdefault(b, []).append((p, k))
    smap, problems, consts, notes, left = {}, [], {}, {}, []
    canon_pins = (canon_tid or {}).get('cut_pins', {})
    for c, d, w, lsb in cut:
        keys = [k for k in (c, c[2:] if c.startswith('x_') else None) if k]
        cands = [n for k in keys for n in byclean.get(k, [])]
        if not cands:  # cell-port / deeper-path names: unique cleaned-suffix match
            cands = [n for n in names if any(clean(n).endswith('_' + k) for k in keys)]
        exact = [n for n in cands if len(names[n]['bits']) == w]
        sigs = {tuple(names[n]['bits']) for n in exact}
        narrow = False
        if len(sigs) != 1:
            wide = [n for n in cands if len(names[n]['bits']) > w]
            if not exact and wide and len({tuple(names[n]['bits']) for n in wide}) == 1:
                narrow = True  # the cut kept only the bits the piece uses: take them in ascending net order
            else:
                left.append((c, d, w, f'{len(exact)} same-width master candidates, {len(sigs)} distinct nets'))
                continue
        bits = names[(exact or wide)[0]]['bits']
        if all(isinstance(b, str) for b in bits):
            p0, w0 = next(iter(canon_pins[c].items())) if len(canon_pins.get(c, {})) == 1 else (None, 0)
            if pdir.get(p0) == d and w0 == w:
                smap[c] = [[p0, 0, 0, w]]  # constant net carried by the cut; the rest top drives / ignores it
                notes[c] = 'CONST_NET: whole-bus canonical entry kept'
            else:
                left.append((c, d, w, 'constant net in the master'))
            continue
        if narrow:
            used = [b for b in bits if not isinstance(b, str) and any(pdir[p] == d for p, _ in sig2rtl.get(b, []))]
            if len(used) != w:
                left.append((c, d, w, f'narrowed net: {len(used)} reached bits != {w}'))
                continue
            bits = used
            notes[c] = f'NARROW: {w} of {len(names[wide[0]]["bits"])} master bits reached by the piece, ascending order'
        pairs = []
        for j, b in enumerate(bits):
            if isinstance(b, str):
                consts.setdefault(c, []).append(f'{j}={b}')
                continue
            tgt = [(p, k) for p, k in sig2rtl.get(b, []) if pdir[p] == d]
            if not tgt:
                problems.append(f'{c}[{j}] ({d}): no RTL {d} bit on that net')
                continue
            if d == 'output':
                tgt = tgt[:1]
            pairs += [(j, p, k) for p, k in tgt]
        smap[c] = runs(pairs)
    # name-less cut buses (e.g. 'glue') and constant nets: by elimination only -- the bits of ONE RTL port that no
    # other plan bus reaches, same direction, exactly the plan width (ascending), and no other leftover of that shape
    reached = {(p, k + t) for rl in smap.values() for p, k, _, n in rl for t in range(n)}
    for c, d, w, why in left:
        free = {}
        for p, d0, w0 in ports:
            fb = [k for k in range(w0) if (p, k) not in reached]
            if d0 == d and fb:
                free[p] = fb
        m = [p for p, fb in free.items() if len(fb) == w]
        rivals = sum(1 for c2, d2, w2, _ in left if d2 == d and w2 == w)
        if len(m) == 1 and rivals == 1:
            smap[c] = runs([(j, m[0], k) for j, k in enumerate(free[m[0]])])
            reached |= {(m[0], k) for k in free[m[0]]}
            notes[c] = (f'BY_ELIMINATION: the only free {d} bits of width {w} ({m[0]} bits '
                        f'{free[m[0]][0]}..{free[m[0]][-1]}; {why})')
        else:
            problems.append(f'{c}[{w}] {d}: {why}; {len(m)} free same-width bit groups, {rivals} rival buses')
    # coverage: every RTL input bit driven by exactly one plan bit, every RTL output bit read at most once per plan bit
    cov = {}
    for c, rl in smap.items():
        for p, k, pb, n in rl:
            for t in range(n):
                cov.setdefault((p, k + t), []).append((c, pb + t))
    in_unc = [f'{p}[{k}]' for p, d, w in ports if d == 'input' for k in range(w) if (p, k) not in cov]
    in_multi = [f'{p}[{k}]' for (p, k), v in cov.items() if pdir[p] == 'input' and len(v) > 1]
    out_open = [f'{p}[{k}]' for p, d, w in ports if d == 'output' for k in range(w) if (p, k) not in cov]
    whole = {}
    if canon_tid:
        for c, m in canon_tid.get('cut_pins', {}).items():
            (p, w), = m.items()
            exp = [[p, 0, 0, w]]
            whole[c] = 'SAME_NET' if smap.get(c) == exp else f'DIFFERS: bit map {smap.get(c)}'
    # Candidate regrouping is useful diagnostics, but lost cut-bit identity cannot be
    # established by width/order inference. Never install these candidates as PASS maps.
    unproven = {bus: note for bus, note in notes.items()
                if note.startswith(('NARROW:', 'BY_ELIMINATION:'))}
    ok = not problems and not in_multi and not unresolved_rtl and not in_unc
    verdict = 'FAIL' if not ok else ('UNPROVEN' if unproven else 'PASS')
    return dict(slices=smap, check=dict(
        verdict=verdict, unproven_mappings=unproven, plan_buses=len(cut), mapped_buses=len(smap),
        plan_bits=sum(w for _, _, w, _ in cut), problems=problems, unresolved_rtl=unresolved_rtl[:50],
        n_unresolved_rtl=len(unresolved_rtl), rtl_inputs_uncovered=in_unc[:200], n_rtl_inputs_uncovered=len(in_unc),
        rtl_inputs_multi=in_multi[:50], rtl_outputs_open=len(out_open), constant_plan_bits=consts,
        whole_bus_entries=whole, notes=notes))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master-json', required=True)
    ap.add_argument('--master-top', required=True)
    ap.add_argument('--rest-sv', required=True)
    ap.add_argument('--rest-top', required=True)
    ap.add_argument('--cut', required=True)
    ap.add_argument('--piece', required=True)
    ap.add_argument('--canon', default=None)
    ap.add_argument('--ftype', default=None)
    ap.add_argument('--out', required=True)
    ap.add_argument('--sidecar', default=None,
                    help='merge the result into canonical_bitmap_split.json (types.<ftype>.type_ids.<tid>)')
    a = ap.parse_args()
    mj = json.load(open(a.master_json))
    cut = json.load(open(a.cut))[a.piece][a.piece]
    tids = {}
    if a.canon:
        tids = json.load(open(a.canon))['types'][a.ftype]['type_ids']
    canon_tid = next(iter(tids.values())) if tids else None
    r = build(mj, a.master_top, open(a.rest_sv).read(), a.rest_top, cut, canon_tid)
    r.update(piece=a.piece, type_ids=sorted(tids), rest_top=a.rest_top, master_top=a.master_top)
    json.dump(r, open(a.out, 'w'), indent=1, sort_keys=True)
    c = r['check']
    if a.sidecar and c['verdict'] == 'PASS':
        import hashlib
        import os
        sc = json.load(open(a.sidecar)) if os.path.exists(a.sidecar) else dict(
            schema='opentallas.hbm.split_bitmap.v1',
            doc='opt-in bit-level cut map (split_bitmap.py); gen_core_kit_hbm.py uses slices instead of '
                'canonical_ports_split.json cut_pins for the listed type_ids only', types={})
        sha = lambda f: hashlib.sha256(open(f, 'rb').read()).hexdigest()
        for tid in tids:
            sc['types'].setdefault(a.ftype, {}).setdefault('type_ids', {})[tid] = dict(
                slices=r['slices'], check=c, rest_top=a.rest_top, master_top=a.master_top,
                src=dict(rest_sv=os.path.basename(a.rest_sv), rest_sv_sha256=sha(a.rest_sv),
                         ports_cut_sha256=sha(a.cut), master_json_sha256=sha(a.master_json)))
        json.dump(sc, open(a.sidecar, 'w'), indent=1, sort_keys=True)
        open(a.sidecar, 'a').write('\n')
    print(a.piece, c['verdict'], 'buses', c['mapped_buses'], '/', c['plan_buses'], 'problems', len(c['problems']),
          'rtl unresolved', c['n_unresolved_rtl'], 'rtl inputs uncovered', c['n_rtl_inputs_uncovered'],
          'outputs open', c['rtl_outputs_open'])
    return 0 if c['verdict'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main())
