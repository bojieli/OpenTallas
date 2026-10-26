#!/usr/bin/env python3
"""frame_seam_pipe.py -- S81-P6 (10-23): band seams at plan width.

Input: a frame_hier_part.py banded RTL (band modules <top>_b<k> + the wiring top).  Every landed crossing between two
bands is an ot_pl_land_vector_reset_w (source band) / ot_pl_land_vector_reset_r (destination band) pair whose D*W ring
bank (+ epochs + slot valids) crosses the band seam.  Under the die plan each band is a partition with its own clock
taps (TOPDOWN-PLAN R4), so the pair becomes ot_pl_seam_w / ot_pl_seam_r (rtl/common/landed_parent/ot_pl_seam.sv):
W bits across the seam, same latency (K + 1 edges), same rsi leaves, cycle-exact (tb_ot_pl_seam lockstep).

  frame_seam_pipe.py --rtl IN.sv --out OUT.sv [--report seams.json]      (any band/top names; idempotent check)

--report writes the band-to-band crossing widths (every band port net, by driver band -> reader band) before and after,
which is the census source for the die-plan frame-internal lanes (gen_plan_v4.py FRAME_INTERNAL).
"""
import argparse, collections, json, re, sys
from pathlib import Path

W_RE = re.compile(r'(\s*)ot_pl_land_vector_reset_w #\(\.W\((?P<w>.+?)\), \.D\((?P<d>\d+)\), \.CHUNK_BITS\((?P<cb>\d+)\)\) '
                  r'(?P<inst>u_lpl_(?P<n>\d+)_w) \(\.ck\((?P<ck>[^)]*)\), \.rsi\((?P<rsi>.+?)\), \.i\((?P<i>.+?)\), '
                  r'\.bank\(lpl_(?P=n)_bank\), \.epo\(lpl_(?P=n)_epo\), \.vld\(lpl_(?P=n)_vld\)\);\s*$')
R_RE = re.compile(r'(\s*)ot_pl_land_vector_reset_r #\(\.W\((?P<w>.+?)\), \.D\((?P<d>\d+)\), \.K\((?P<k>.+?)\), '
                  r'\.CHUNK_BITS\((?P<cb>\d+)\)\) (?P<inst>u_lpl_(?P<n>\d+)_r) \(\.ck\((?P<ck>[^)]*)\), \.rsi\((?P<rsi>.+?)\), '
                  r'\.bank\(lpl_(?P=n)_bank\), \.epo\(lpl_(?P=n)_epo\), \.vld\(lpl_(?P=n)_vld\), \.o\((?P<o>.+?)\)\);\s*$')
PORT_RE = re.compile(r'^(\s*)(input|output) wire (\[(\d+):0\] )?(\w+)(,?)\s*$')
WIRE_RE = re.compile(r'^(\s*)wire (\[(\d+):0\] )?(lpl_(\d+)_(bank|epo|vld));\s*$')
CONN_RE = re.compile(r'^(\s*)\.(lpl_(\d+)_(bank|epo|vld))\((lpl_\d+_(?:bank|epo|vld))\)(,?)\s*$')
MOD_RE = re.compile(r'^module (\w+)')


def band_ports(lines):
    """{module: {port: (dir, width)}} for every module; band instances of the top: {inst: module}"""
    ports, cur = collections.defaultdict(dict), None
    for ln in lines:
        m = MOD_RE.match(ln)
        if m:
            cur = m.group(1)
            continue
        if ln.startswith('endmodule'):
            cur = None
            continue
        p = PORT_RE.match(ln)
        if cur and p:
            ports[cur][p.group(5)] = (p.group(2), int(p.group(4)) + 1 if p.group(4) else 1)
    return ports


def crossings(text, top):
    """band-to-band bits by driver band -> reader band, from the wiring top's band-instance connections (.port(net))"""
    lines = text.split('\n')
    ports = band_ports(lines)
    body = text[text.index('module %s ' % top) if ('module %s ' % top) in text else text.index('module %s\n' % top):]
    body = body[:body.index('endmodule')]
    drv, rd = {}, collections.defaultdict(list)
    for mod, inst, conns in re.findall(r'^\s*(%s_b\d+) #\(.*?\) (u_b\d+) \((.*?)\);' % re.escape(top), body, flags=re.M | re.S):
        for port, net in re.findall(r'\.(\w+)\(([^()]*)\)', conns):
            d, w = ports[mod][port]
            if d == 'output':
                drv[net.strip()] = (inst, w)
            else:
                rd[net.strip()].append(inst)
    pair = collections.Counter()
    for net, (src, w) in drv.items():
        for dst in rd.get(net, []):
            if dst != src:
                pair['%s->%s' % (src[2:], dst[2:])] += w
    return dict(sorted(pair.items()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rtl', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--top', default=None, help='wiring top module (default: the last module)')
    ap.add_argument('--report')
    a = ap.parse_args()
    src = Path(a.rtl).read_text()
    lines = src.split('\n')
    top = a.top or [MOD_RE.match(l).group(1) for l in lines if MOD_RE.match(l)][-1]
    widths = {}
    out, nw, nr = [], 0, 0
    for ln in lines:
        m = W_RE.match(ln)
        if m:
            n = int(m.group('n'))
            out.append('%sot_pl_seam_w #(.W(%s), .CHUNK_BITS(%s)) %s (.ck(%s), .rsi(%s), .i(%s), .q(lpl_%d_d));'
                       % (m.group(1), m.group('w'), m.group('cb'), m.group('inst'), m.group('ck'), m.group('rsi'),
                          m.group('i'), n))
            nw += 1
            continue
        m = R_RE.match(ln)
        if m:
            n = int(m.group('n'))
            out.append('%sot_pl_seam_r #(.W(%s), .K(%s), .CHUNK_BITS(%s)) %s (.ck(%s), .rsi(%s), .d(lpl_%d_d), .o(%s));'
                       % (m.group(1), m.group('w'), m.group('k'), m.group('cb'), m.group('inst'), m.group('ck'),
                          m.group('rsi'), n, m.group('o')))
            nr += 1
            continue
        if re.search(r'\bot_pl_land_(vector_reset_|chunk_|local_)?[wr]\b', ln):
            raise SystemExit('unrecognised landing instance (no partial rewrite): ' + ln.strip()[:160])
        p = PORT_RE.match(ln)
        if p and re.fullmatch(r'lpl_\d+_(bank|epo|vld)', p.group(5)):
            n, kind = re.fullmatch(r'lpl_(\d+)_(bank|epo|vld)', p.group(5)).groups()
            if kind == 'bank':
                bw = int(p.group(4)) + 1
                d = widths.setdefault(int(n), bw // 4)
                assert bw % 4 == 0 and d == bw // 4, ln
                out.append('%s%s wire [%d:0] lpl_%s_d%s' % (p.group(1), p.group(2), bw // 4 - 1, n, p.group(6)))
            elif not p.group(6):
                raise SystemExit('last port is a landing tag; reorder not supported: ' + ln.strip())
            continue
        w = WIRE_RE.match(ln)
        if w:
            if w.group(6) == 'bank':
                bw = int(w.group(3)) + 1
                out.append('%swire [%d:0] lpl_%s_d;' % (w.group(1), bw // 4 - 1, w.group(5)))
            continue
        c = CONN_RE.match(ln)
        if c:
            if c.group(4) == 'bank':
                out.append('%s.lpl_%s_d(lpl_%s_d)%s' % (c.group(1), c.group(3), c.group(3), c.group(6)))
            elif not c.group(6):
                raise SystemExit('last connection is a landing tag: ' + ln.strip())
            continue
        out.append(ln)
    if nw != nr or nw == 0:
        raise SystemExit('landing halves: %d w / %d r' % (nw, nr))
    res = '\n'.join(out)
    if re.search(r'lpl_\d+_(bank|epo|vld)', res):
        raise SystemExit('left-over landing tag nets: ' + ', '.join(sorted(set(re.findall(r'lpl_\d+_(?:bank|epo|vld)', res)))[:8]))
    hdr = ('// GENERATED by tools/s81_dv/frame_seam_pipe.py from %s: %d band-seam landings (ot_pl_land_vector_reset_w/r, '
           'D*W ring across the seam) -> ot_pl_seam_w/r (W bits, same K+1 latency, same rsi leaves).\n' % (a.rtl, nw))
    Path(a.out).write_text(hdr + res)
    rep = dict(source=a.rtl, out=a.out, top=top, landings=nw, before=crossings(src, top), after=crossings(res, top),
               landing_w=dict(sorted(widths.items())))
    if a.report:
        Path(a.report).write_text(json.dumps(rep, indent=1) + '\n')
    print(json.dumps({k: rep[k] for k in ('landings', 'before', 'after')}))


if __name__ == '__main__':
    main()
