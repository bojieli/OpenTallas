#!/usr/bin/env python3
"""KDIE5-RTL2 10-22: per-port output flop copies for the bounded-driver KV group copies (qkd_kvs_grp{,_h}_r2c -> _r2d).

Why: in r2c one exit flop (cell DFF*, QN -> keep INV -> port) drives the SAME bit of two or more output words that leave
on far-apart pins: rsp[j] and krsp[k] (1056 bits; E face, the krsp block and the rsp block are ~500 um apart on the
1188 um face) and o_pc0..o_pc3 (56 bits; W face, four blocks).  The flow fixes the flop at ONE of its pins, so every
other pin gets an unregistered ~0.5-1 mm wire inside the IO budget: gate d957 placement check reg->out rsp[37] -714 ps
(= krsp[6]), grp_h krsp[944] -1638 ps.  Fix (0 edges, same function): every additional port word gets its own copy of
the flop (same cell module, same D / CLK / RESETN / SETN) and its own keep INV, so each pin has its own exit flop at
the pin (io_flop_at_pins).  The long wire moves to the D side (a full cycle, reg -> reg).  Constant (tie cell) outputs
are left as they are (no timing).  The D net of a copied flop gains one load per copy; the tool refuses if any D net
would exceed 32 terminal loads (native census bound).

    python3 tools/qwen_kv_die/kv_grp_portcopy.py grp|grp_h      (reads/writes rtl/qwen_sys/static_kv_die_20261017)
"""
import collections, hashlib, json, re, sys
from pathlib import Path

WT = Path(__file__).resolve().parents[2]
D = WT / 'rtl/qwen_sys/static_kv_die_20261017'
MAXL = 32


def main(k):
    src = D / f'qkd_kvs_{k}_r2c.sv'
    raw = src.read_text()
    t = re.sub(rf'\bqkd_kvs_{k}_r2c', f'qkd_kvs_{k}_r2d', raw)
    top_end = t.index('endmodule')                       # the top module is the first module in the file
    top = t[:top_end]
    asg = [(m.start(), m.group(1), m.group(2), m.group(3)) for m in
           re.finditer(r'^  assign (\w+)(?:\[(\d+)\])? = (\w+);$', top, re.M)]
    by = collections.defaultdict(list)
    for _, p, i, n in asg:
        by[n].append((p, i))
    invy = {m.group(4): (m.group(1), m.group(2), m.group(3)) for m in
            re.finditer(r'^  \(\* keep \*\) (INV\w+) (\w+) \(\.A\((\w+)\), \.Y\((\w+)\)\);$', top, re.M)}
    flops = {}
    for m in re.finditer(rf'^  (qkd_kvs_{k}_r2d_cell_\d+) (\w+) \((.*\.QN\((\w+)\).*)\);$', top, re.M):
        flops[m.group(4)] = (m.group(1), m.group(2), m.group(3))
    loads = collections.Counter()
    for m in re.finditer(r'^  (?:\(\* keep \*\) )?\w+ \w+ \((.*)\);$', top, re.M):
        for pn, net in re.findall(r'\.(\w+)\((\w+)\)', m.group(1)):
            if pn not in ('QN', 'Q', 'Y'):
                loads[net] += 1
    for m in re.finditer(r'\.\w+\(\{([^}]*)\}\)', top):
        for net in re.findall(r'\w+', m.group(1)):
            loads[net] += 1
    add, remap, rec, skipped = [], {}, collections.Counter(), []
    dload = collections.Counter()
    for net, bits in by.items():
        ports = list(dict.fromkeys(p for p, _ in bits))
        if len(ports) < 2:
            continue
        if net not in invy or invy[net][2] not in flops:
            skipped.append(dict(net=net, ports=ports, why='not a flop -> INV exit (constant tie or other)'))
            continue
        ityp, iname, qn = invy[net]
        ftyp, fname, conn = flops[qn]
        dnet = re.search(r'\.D\((\w+)\)', conn).group(1)
        for p in ports[1:]:
            qn2, y2 = f'{qn}_{p}', f'{net}_{p}'
            conn2 = re.sub(r'\.QN\(\w+\)', f'.QN({qn2})', conn)
            add.append(f'  wire {qn2};\n  wire {y2};\n  {ftyp} {fname}_{p} ({conn2});\n'
                       f'  (* keep *) {ityp} {iname}_{p} (.A({qn2}), .Y({y2}));\n')
            for pp, i in bits:
                if pp == p:
                    remap[(pp, i)] = y2
            rec[p] += 1
            dload[dnet] += 1
    # the copies of async-reset exit flops (RESETN / SETN) load the landed reset nets of r2c (each <= 32 there): every
    # such net the copies push over 32 gets extra driver copies (its landing flop + keep INV, same D / CLK = the same
    # release edge), the copies' reset pins move to them in groups of <= 32.  Constant (tie) nets are not dynamic.
    rloads = collections.Counter()
    for m in re.finditer(r'\.(?:RESETN|SETN)\((\w+)\)', top):
        rloads[m.group(1)] += 1
    radd = collections.Counter()
    for line in add:
        for m in re.finditer(r'\.(?:RESETN|SETN)\((\w+)\)', line):
            radd[m.group(1)] += 1
    rfix = {}
    for net, c in radd.items():
        if rloads[net] + c <= MAXL:
            continue
        if rloads[net] > MAXL and re.search(rf'^  (?:\(\* keep \*\) )?\w+ \w+ \(\.[LH]\({net}\)\);$', top, re.M):
            continue    # a tie cell (constant SETN / RESETN level), not a dynamic driver
        if rloads[net] > MAXL and re.search(rf'\.[LH]\({net}\)', top):
            continue
        if net not in invy or invy[net][2] not in flops:
            raise SystemExit(f'{k}: reset net {net} over {MAXL} after copies and not a flop -> INV landing driver')
        ityp, iname, qn = invy[net]
        ftyp, fname, conn = flops[qn]
        n_new = -(-c // MAXL)
        drivers = []
        for r in range(n_new):
            qn2, y2 = f'{qn}_rc{r}', f'{net}_rc{r}'
            conn2 = re.sub(r'\.QN\(\w+\)', f'.QN({qn2})', conn)
            add.append(f'  wire {qn2};\n  wire {y2};\n  {ftyp} {fname}_rc{r} ({conn2});\n'
                       f'  (* keep *) {ityp} {iname}_rc{r} (.A({qn2}), .Y({y2}));\n')
            dload[re.search(r'\.D\((\w+)\)', conn).group(1)] += 1
            drivers.append(y2)
        rfix[net] = drivers
    if rfix:
        cnt = collections.Counter()

        def rsub(m):
            net = m.group(2)
            if net not in rfix:
                return m.group(0)
            d = rfix[net][cnt[net] // MAXL]
            cnt[net] += 1
            return f'.{m.group(1)}({d})'
        add = [re.sub(r'\.(RESETN|SETN)\((\w+)\)', rsub, line) if f'_rc' not in line.split('(')[0] else line for line in add]
        rec['reset_driver_copies'] = sum(len(v) for v in rfix.values())
    over = {n: loads[n] + c for n, c in dload.items() if loads[n] + c > MAXL}
    if over:
        raise SystemExit(f'{k}: D nets over {MAXL} loads after copies: {list(over.items())[:5]}')

    def sub(m):
        key = (m.group(1), m.group(2))
        return f'  assign {m.group(1)}' + (f'[{m.group(2)}]' if m.group(2) else '') + f' = {remap[key]};' \
            if key in remap else m.group(0)
    top2 = re.sub(r'^  assign (\w+)(?:\[(\d+)\])? = (\w+);$', sub, top, flags=re.M)
    hdr = (f'// KDIE5-RTL2 10-22: GENERATED by tools/qwen_kv_die/kv_grp_portcopy.py from qkd_kvs_{k}_r2c.sv '
           f'(sha256 {hashlib.sha256(raw.encode()).hexdigest()}): {sum(rec.values())} per-port exit flop copies '
           f'{dict(rec)}; 0 edges.\n')
    out = hdr + top2 + ''.join(add) + t[top_end:]
    dst = D / f'qkd_kvs_{k}_r2d.sv'
    dst.write_text(out)
    cert = json.loads((D / f'qkd_kvs_{k}_r2c.json').read_text())
    cert.update(top=f'qkd_kvs_{k}_r2d', generated_sha256=hashlib.sha256(out.encode()).hexdigest(),
                portcopy=dict(tool='tools/qwen_kv_die/kv_grp_portcopy.py', input=str(src.relative_to(WT)),
                              input_sha256=hashlib.sha256(raw.encode()).hexdigest(), copies=dict(rec),
                              total=sum(rec.values()), d_net_max_loads=max((loads[n] + c for n, c in dload.items()), default=0),
                              skipped=skipped, edges=0))
    cert['generated_cells'] = cert.get('generated_cells', 0) + 2 * sum(rec.values())
    (D / f'qkd_kvs_{k}_r2d.json').write_text(json.dumps(cert, indent=1) + '\n')
    print(k, 'copies', dict(rec), 'D max loads', cert['portcopy']['d_net_max_loads'], 'skipped', len(skipped))


if __name__ == '__main__':
    main(sys.argv[1])
