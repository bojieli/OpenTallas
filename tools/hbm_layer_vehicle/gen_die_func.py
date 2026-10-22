#!/usr/bin/env python3
"""HBMc/TOKEN2 (10-22): functional view of a GEN die.v for the token bench (tok_func_hbm.sh --die-netlist).

A GEN die.v (tools/hbm_die_v15/die_case_v16.py, the netlist the die GRT/STA/CLK runs) is bit-blasted (n123 / nc_* nets,
p_<pin>_<k>_ die pins), uses parameter-uniquified view masters (<master>__pvN) and carries the die clock distribution as
single-line ASAP7 buffers (dkh_/dkr_/dks_, .A -> .Y).  cut_slice.py / the slice bench need the contract_die_v.py form
(instances + wires, every output on a <inst>__<port> net).  This tool rebuilds that form FROM THE GEN CONNECTIVITY:

  * every instance output bit is identified from the contract port directions/widths (fail closed on width mismatch);
  * a buffer is a pure delay (insertion/skew are STA/CLK results): its output resolves to its root driver;
  * every input bit is re-expressed as the bit of the instance output / die pin / constant that drives it on the GEN
    netlist; a bit driven by nothing on the GEN netlist (nc_* or undriven net) becomes a listed nc__ gap wire, never tied;
  * the instance header (source master + parameters) comes from the contract, so children are the die's source RTL
    (MODE=gen_rtl: GEN-composed connectivity, source children).

It also compares the GEN driver of every contract input bit with the contract's own driver (edges / clock_resets /
straps / die pins): CONN_EQUIV PASS means the GEN netlist implements exactly the contract's connectivity (clock bits
compare by domain root).  Every difference is listed (a GEN-netlist functional bug, or an expected physical-only
insertion that must then be explained).

  gen_die_func.py --die GEN_die.v --contract CONTRACT.json[.gz] --out die_func.v [--report report.json]
"""
import argparse, collections, gzip, json, re, sys
from pathlib import Path

CELL = re.compile(r"^\s*(\w+_ASAP7_75t_\w+)\s+(\w+)\s*\(\s*\.A\((\w+)\)\s*,\s*\.Y\((\w+)\)\s*\);\s*$")
HDR = re.compile(r"^\s*([A-Za-z_]\w*)\s*(#\(.*\))?\s*([A-Za-z_]\w*)\s*\(\s*$")
CONN = re.compile(r"^\s*\.(\w+)\((.*)\),?\s*$")
CONST = re.compile(r"^(\d+)'([bdh])([0-9a-fA-F_xXzZ]+)$")


def ld(p):
    return json.load(gzip.open(p, 'rt') if str(p).endswith('.gz') else open(p))


def bits_of(expr, width, where):
    """MSB-first expression -> list index b (LSB=0) of tokens: net name, ('C', 0|1) or None (empty)."""
    e = expr.strip()
    if e == '':
        return [None] * width
    items = [x.strip() for x in e[1:-1].split(',')] if e.startswith('{') else [e]
    out = []
    for it in items:
        m = CONST.match(it)
        if m:
            n, base, val = int(m.group(1)), m.group(2), m.group(3).replace('_', '')
            if re.search(r'[xXzZ]', val):
                out += [None] * n; continue
            v = int(val, {'b': 2, 'd': 10, 'h': 16}[base])
            out += [('C', (v >> k) & 1) for k in range(n - 1, -1, -1)]
        elif re.fullmatch(r'\w+', it):
            out.append(it)
        else:
            sys.exit(f'gen_die_func: unsupported connection element {it!r} at {where}')
    if len(out) != width:
        sys.exit(f'gen_die_func: {where} has {len(out)} bits, contract width {width}')
    return out[::-1]


def parse_gen(path):
    text = Path(path).read_text()
    m = re.search(r"\bmodule\s+(\w+)\s*\((.*?)\);", text, re.S)
    pins = {}
    for d, n in re.findall(r"(input|output)\s+wire\s*(?:\[\d+:\d+\])?\s*(\w+)", m.group(2)):
        pins[n] = d
    lines = text[m.end():text.rindex('endmodule')].split('\n')
    for ln in lines:
        d = re.match(r"\s*(input|output)\s+wire\s*(?:\[\d+:\d+\])?\s*(\w+)\s*;", ln)
        if d:
            pins[d.group(2)] = d.group(1)
    insts, alias, i = {}, {}, 0
    while i < len(lines):
        ln = lines[i]
        c = CELL.match(ln)
        h = HDR.match(ln)
        if c:
            if c.group(4) in alias:
                sys.exit(f'gen_die_func: net {c.group(4)} driven by two buffers')
            alias[c.group(4)] = c.group(3)
        elif h:
            conns = {}
            i += 1
            while not re.match(r"\s*\);\s*$", lines[i]):
                cm = CONN.match(lines[i])
                if not cm:
                    sys.exit(f'gen_die_func: unparsed connection line {lines[i][:120]!r}')
                conns[cm.group(1)] = cm.group(2)
                i += 1
            insts[h.group(3)] = dict(master=h.group(1), conns=conns)
        elif '_ASAP7_75t_' in ln:
            sys.exit(f'gen_die_func: unsupported std-cell line {ln.strip()[:120]!r} (only .A/.Y buffers)')
        elif ln.strip() and not re.match(r"\s*(wire\b|//|`)", ln):
            sys.exit(f'gen_die_func: unexpected line {ln.strip()[:120]!r}')
        i += 1
    return pins, insts, alias


def contract_drivers(c):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v16'))
    import contract_die_v as CDV
    return CDV


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die', required=True); ap.add_argument('--contract', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--report')
    ap.add_argument('--patch-open', action='store_true', help='simulate past GEN-open bits with the contract driver (listed; CONN_EQUIV stays FAIL)')
    ap.add_argument('--open-zero', action='store_true', help='tie every GEN-open input bit to 0 (listed): unpatched GEN behaviour in a 2-state bench')
    ap.add_argument('--cdv', help='contract_die_v.py of the die source revision (default: this checkout)')
    a = ap.parse_args()
    c = ld(a.contract); I = c['instances']
    if a.cdv:
        sys.path.insert(0, str(Path(a.cdv).resolve().parent))
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'hbm_die_v16'))
    import contract_die_v as CDV
    pins, G, alias = parse_gen(a.die)
    miss = sorted(set(I) - set(G)); extra = sorted(set(G) - set(I))
    if miss or extra:
        sys.exit(f'gen_die_func: instance sets differ: contract-only {len(miss)} {miss[:5]} GEN-only {len(extra)} {extra[:5]}')
    # die pins: contract die_pins name -> GEN p_<name> (1 bit) / p_<name>_<k>_ (bit k)
    cpin = {x['name']: x for x in c.get('die_pins', [])}
    pinbit = {}
    for n, d in pins.items():
        mm = re.fullmatch(r'p_(\w+?)(?:_(\d+)_)?', n)
        base, k = (mm.group(1), int(mm.group(2) or 0)) if mm else (None, 0)
        if base not in cpin:
            sys.exit(f'gen_die_func: GEN die pin {n} has no contract die_pin')
        pinbit[n] = (base, k)
    # GEN net drivers
    drv_net = {}
    for i, x in G.items():
        for p, e in x['conns'].items():
            pd = I[i]['ports'].get(p)
            if pd is None:
                sys.exit(f'gen_die_func: {i}.{p} not a contract port')
            if pd['direction'] != 'output':
                continue
            for b, t in enumerate(bits_of(e, pd['bits'], f'{i}.{p}')):
                if isinstance(t, str):
                    if t in drv_net:
                        sys.exit(f'gen_die_func: net {t} driven by {drv_net[t]} and {i}.{p}[{b}]')
                    drv_net[t] = (i, p, b)
    for n, d in pins.items():
        if d == 'input':
            drv_net[n] = ('PIN', pinbit[n][0], pinbit[n][1])

    def root(n):
        seen = 0
        while n in alias:
            n = alias[n]; seen += 1
            if seen > 10000:
                sys.exit(f'gen_die_func: buffer loop at {n}')
        return n
    # contract driver map (reference) and clock-root normalisation
    ref, bad = CDV.drivers(c)
    ck_src = {}   # contract CKNET net name 'inst__port' -> GEN driver tuple of that output bit 0
    gen = {}
    gaps = []
    for i, x in G.items():
        for p, pd in I[i]['ports'].items():
            if pd['direction'] != 'input':
                continue
            e = x['conns'].get(p, '')
            for b, t in enumerate(bits_of(e, pd['bits'], f'{i}.{p}')):
                if t is None:
                    gaps.append((i, p, b, '<unconnected>')); continue
                if isinstance(t, tuple):
                    gen[(i, p, b)] = ('CONST', t[1], 0); continue
                r = root(t)
                s = drv_net.get(r)
                if s is None:
                    gaps.append((i, p, b, t)); continue
                gen[(i, p, b)] = s if s[0] == 'PIN' else (s[0], s[1], s[2])
    # straps: the GEN netlist leaves strap pins open (nc_*); the physical flow ties them from the contract straps
    # (die_port_bind --strap-file).  Apply exactly the contract strap value on such a gap bit; any other gap stays open.
    straps_applied, open_gaps = 0, []
    for (i, p, b, t) in gaps:
        r = ref.get((i, p, b))
        if r is not None and r[0] == 'CONST':
            gen[(i, p, b)] = ('CONST', r[1], 0); straps_applied += 1
        elif r is not None or t != '<unconnected>':
            open_gaps.append((i, p, b, t))
    gaps = open_gaps
    # --patch-open: a GEN-open bit that the contract drives gets the contract driver so the rest of the die can still
    # be simulated.  CONN_EQUIV stays FAIL and every patched bit is listed: the GEN netlist itself is NOT fixed by this.
    patched = []
    if a.patch_open:
        for (i, p, b, t) in gaps:
            r = ref.get((i, p, b))
            if r is not None:
                gen[(i, p, b)] = tuple(r)
                patched.append([i, p, b, t, list(r)])
    elif a.open_zero:
        # negative-control form: a GEN-open input reads 0 (what a floating pin does in a 2-state simulation); listed
        for (i, p, b, t) in gaps:
            gen[(i, p, b)] = ('CONST', 0, 0)
            patched.append([i, p, b, t, ['OPEN_ZERO']])
    # equivalence vs contract
    def norm(s):
        if s is None:
            return None
        if s[0] == 'CKNET':
            si, sp = s[1].split('__', 1)
            return (si, sp, 0)
        return tuple(s)
    keys = set(gen) | set(ref)
    diff = collections.Counter(); samples = collections.defaultdict(list); by_port = collections.Counter()
    for k in keys:
        g, r = gen.get(k), norm(ref.get(k))
        if g == r:
            continue
        cls = 'gen_only' if r is None else ('contract_only' if g is None else 'different_driver')
        diff[cls] += 1
        q = lambda n: re.sub(r'(SW|SE|NW|NE)(\d|_\d+)*', 'Q', str(n))
        by_port[f"{cls} {q(k[0])}.{k[1]} <- gen {q(g[0]) + '.' + str(g[1]) if g else '-'} / contract {q(r[0]) + '.' + str(r[1]) if r else '-'}"] += 1
        if len(samples[cls]) < 12:
            samples[cls].append(dict(sink=list(k), gen=g, contract=r))
    # emit in contract_die_v form from the GEN driver map
    drv_emit = {}
    for k, s in gen.items():
        if s[0] in ('PIN', 'CONST'):
            drv_emit[k] = s
        else:
            drv_emit[k] = (s[0], s[1], s[2])
    orig = CDV.drivers
    CDV.drivers = lambda _c: (drv_emit, [])
    try:
        text, _ = CDV.emit(c)
    finally:
        CDV.drivers = orig
    text = text.replace('generated by tools/hbm_die_v16/contract_die_v.py from the final d4f source contract',
                        f'generated by tools/hbm_layer_vehicle/gen_die_func.py from GEN {Path(a.die).name} connectivity '
                        f'+ contract headers ({len(alias)} clock buffers collapsed)', 1)
    Path(a.out).write_text(text)
    rep = dict(schema='opentallas.gen_die_func.v1', gen_die=str(a.die), contract=str(a.contract),
               instances=len(G), buffers_collapsed=len(alias), die_pins=len(pins), input_bits_gen=len(gen),
               input_bits_contract=len(ref), straps_applied=straps_applied, gen_open_input_bits=len(gaps), gen_gap_samples=[list(g) for g in gaps[:20]], patched_open_bits=patched,
               conn_equiv='PASS' if not diff and not gaps else 'FAIL', diff=dict(diff), diff_by_port=dict(by_port.most_common(200)), diff_samples=samples,
               contract_driver_conflicts=bad[:20])
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1, default=str) + '\n')
    print(f"GEN_DIE_FUNC instances={len(G)} buffers={len(alias)} input_bits={len(gen)} straps={straps_applied} open={len(gaps)} "
          f"CONN_EQUIV {rep['conn_equiv']} {dict(diff)} -> {a.out}")
    sys.exit(0)


if __name__ == '__main__':
    main()
