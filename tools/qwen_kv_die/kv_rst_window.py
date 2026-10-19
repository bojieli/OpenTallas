#!/usr/bin/env python3
"""KV-LANDSLOT 10-18 (lanes/KV-CLOCK.md OWED item 4): RESET RELEASE WINDOW of every plain reset / boot ROOT HOP that
crosses core clock trees on the KV die (OT_KV_RST_PER_TREE leaves one root hop a net and tree: kvs14b 749 -> 122).

The five core trees are independent (tools/die_clock/specs/kv_regions_1018.json, no balance group), so a reset hop from a
station / block on tree X into a load on tree Y is a cross-region path.  It is NOT laned (reset defines the epochs); it
is timed as a deterministic MULTICYCLE release: the release launched at edge 0 must be captured at edge E_r and not at
E_r - 1, i.e. set_multicycle_path -setup E_r / -hold (E_r - 1) on the hop, setup at TT, hold at FF, both >= 0 after the
measured inter-region clock arrival difference of the two ends (dieclk dump of this floorplan, launch vs capture pin).
E_r = OT_KV_RST_ER (default 2): the release reaches the region one cycle later than a plain hop (the region roots hold
reset >= RELAY_FLUSH = 128 cycles after the clock runs, so a fixed +1 is free; recorded per hop).

    kv_rst_window.py hops --die-v CASE/die.v --lef CASE/elements.lef --out RUN/rst_window_hops.json
    kv_rst_window.py tcl  --hops RUN/rst_window_hops.json --corner tt|ff --out STA_DIR/rst_window.tcl
        (sourced at the end of the die STA session: MCP per hop, then one find_timing_paths per hop -> /work/rst_window_<c>.tsv)
    kv_rst_window.py report --hops ... --tt STA_tt/rst_window_tt.tsv --ff STA_ff/rst_window_ff.tsv
                            [--dump-tt DIECLK/dump_tt.tsv --dump-ff DIECLK/dump_ff.tsv] --out RUN/rst_window.json
"""
import argparse
import json
import os
import re
from collections import defaultdict

RST = re.compile(r'^n_(rst_|hboot|rrs_)')
INST = re.compile(r'^\s+(\S+) (\S+) \((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(([^()]*)\)')
BIT = re.compile(r'(n_[A-Za-z0-9_$]+)(?:\[(\d+)(?::(\d+))?\])?')
RELAY = re.compile(r'^(qkd_rly|qkd_rlys_|qkd_rst_region|qkd_rlysh|qkd_landsh)')
ER = int(os.environ.get('OT_KV_RST_ER', '2'))


def _bits(expr, wires):
    out = []
    for part in [p.strip() for p in expr.strip().strip('{}').split(',')]:
        m = BIT.fullmatch(part)
        if not m:
            continue
        n, hi, lo = m.groups()
        if hi is None:
            out += [f'{n}[{i}]' for i in range(wires.get(n, 1))]
        else:
            h, l_ = int(hi), int(lo if lo is not None else hi)
            out += [f'{n}[{i}]' for i in range(min(h, l_), max(h, l_) + 1)]
    return out


def hops(a):
    lines = open(a.die_v).read().split('\n')
    wires = {}
    for ln in lines:
        m = re.match(r'\s*wire\s+\[(\d+):0\]\s+(\S+);', ln)
        if m:
            wires[m.group(2)] = int(m.group(1)) + 1
    dirs, cur, pin = defaultdict(dict), None, None
    for ln in open(a.lef).read().split('\n'):
        s = ln.strip()
        if s.startswith('MACRO '):
            cur, pin = s.split()[1], None
        elif cur and s.startswith('PIN '):
            pin = s.split()[1]
        elif cur and pin and s.startswith('DIRECTION'):
            dirs[cur][pin] = s.split()[1].rstrip(';').upper()
    tree, drv, lds = {}, {}, defaultdict(list)
    for ln in lines:
        m = INST.match(ln)
        if not m or m.group(1) in ('module', 'wire', 'input', 'output', 'inout'):
            continue
        mst, nm, body = m.groups()
        cs = dict(CONN.findall(body))
        tree[nm] = frozenset(t for v in cs.values() for t in re.findall(r'n_clk_core_(\w+?)(?=\[|\b)', v))
        rly = bool(RELAY.match(mst))
        for p, v in cs.items():
            if p in ('ck', 'ckf', 'ck_s') and rly:
                continue
            d = (('OUTPUT' if p in ('b', 'ck_o', 'eb') else 'INPUT') if rly else dirs.get(mst, {}).get(p, 'INOUT'))
            for b in _bits(v, wires):
                if not RST.match(b):
                    continue
                if d in ('OUTPUT', 'INOUT'):
                    drv.setdefault(b, (nm, p, mst))
                if d in ('INPUT', 'INOUT'):
                    lds[b].append((nm, p, mst))
    out, nets = [], defaultdict(list)
    for b, (dn, dp, dm) in sorted(drv.items()):
        tx = tree.get(dn, frozenset())
        if not tx:
            continue
        for ln_, lp, lm in lds.get(b, ()):
            ty = tree.get(ln_, frozenset())
            if ln_ == dn or not ty or tx & ty:
                continue
            out.append(dict(net=b, drv=dn, drv_port=dp, drv_master=dm, load=ln_, load_port=lp, load_master=lm,
                            src_tree='+'.join(sorted(tx)), dst_tree='+'.join(sorted(ty)), E_r=ER))
            nets[b].append(ln_)
    rec = dict(schema='opentallas.qwen_kv_rst_window_hops.v1', die_v=a.die_v, E_r=ER, hops=out, hop_count=len(out),
               nets=len(nets), per_pair=dict(sorted(((f"{h['src_tree']}->{h['dst_tree']}"), 0) for h in out)))
    for h in out:
        rec['per_pair'][f"{h['src_tree']}->{h['dst_tree']}"] += 1
    json.dump(rec, open(a.out, 'w'), indent=1)
    print(f"KV RST WINDOW HOPS: {len(out)} cross-tree reset root hops on {len(nets)} nets {rec['per_pair']}")


def _esc(s):
    return re.sub(r'([\[\]\\*?])', r'\\\1', s)


def tcl(a):
    H = json.load(open(a.hops))
    c = a.corner
    mm = 'max' if c in ('tt', 'ss') else 'min'
    nets = sorted({h['net'] for h in H['hops']})
    er = {h['net']: h['E_r'] for h in H['hops']}
    L = [f'# KV-LANDSLOT reset release window ({c}): MCP setup E_r / hold E_r-1 per cross-tree reset root hop, then the',
         f'# worst {mm} path through each hop net -> /work/rst_window_{c}.tsv',
         f'set ot_rw [open /work/rst_window_{c}.tsv w]', 'set ot_rw_n 0; set ot_rw_miss 0']
    for n in nets:
        alt = re.sub(r'\[0\]$', '', n) if wires_one(n) else n
        L.append(f'set n [get_nets -quiet {{{_esc(n)}}}]; if {{![llength $n]}} {{ set n [get_nets -quiet {{{_esc(alt)}}}] }}')
        L.append(f'if {{![llength $n]}} {{ puts $ot_rw [join [list MISS {{{n}}}] \\t]; incr ot_rw_miss }} else {{ '
                 f'set_multicycle_path -setup {er[n]} -through $n; set_multicycle_path -hold {er[n] - 1} -through $n; '
                 f'lappend ot_rw_nets [list {{{n}}} $n] }}')
    L.append('if {![info exists ot_rw_nets]} { set ot_rw_nets {} }')
    L.append('foreach kn $ot_rw_nets {')
    L.append('  lassign $kn k nn')
    L.append(f'  set ps [find_timing_paths -path_delay {mm} -through $nn -group_path_count 64 -endpoint_path_count 1]')
    L.append('  if {![llength $ps]} { puts $ot_rw [join [list NOPATH $k] \\t]; continue }')
    L.append('  foreach p $ps { puts $ot_rw [join [list P $k [get_full_name [get_property $p startpoint]] '
             '[get_full_name [get_property $p endpoint]] [get_property $p slack]] \\t]; incr ot_rw_n }')
    L.append('}')
    L.append(f'close $ot_rw; puts "OT_RST_WINDOW corner={c} nets={len(nets)} paths=$ot_rw_n missing=$ot_rw_miss"')
    open(a.out, 'w').write('\n'.join(L) + '\n')


def wires_one(n):
    return n.endswith('[0]')


def _dump(path):
    arr = {}
    if not path or not os.path.exists(path):
        return arr
    for ln in open(path):
        f = ln.rstrip('\n').split('\t')
        if f[0] == 'T' and len(f) >= 8:
            try:
                arr[f[1]] = (float(f[6]), float(f[7]) if f[7] not in ('-', '') else float(f[6]))
            except ValueError:
                pass
    return arr


def _inst_arr(arr, inst):
    v = [x for k, x in arr.items() if k.split('/')[0] == inst]
    return (min(t[0] for t in v), max(t[0] for t in v)) if v else None


def _num(s):
    """slack in the STA time unit (ps: the ASAP7 libs and the die clocks, period 833.333)"""
    try:
        return float(s)
    except ValueError:
        return None


def report(a):
    H = json.load(open(a.hops))
    by_net = defaultdict(list)
    for h in H['hops']:
        by_net[h['net']].append(h)
    res = {}
    for c, path in (('tt', a.tt), ('ff', a.ff)):
        rows, miss, nopath = defaultdict(list), set(), set()
        if path and os.path.exists(path):
            for ln in open(path):
                f = ln.rstrip('\n').split('\t')
                if f[0] == 'MISS':
                    miss.add(f[1])
                elif f[0] == 'NOPATH':
                    nopath.add(f[1])
                elif f[0] == 'P' and len(f) >= 5:
                    rows[f[1]].append((f[2], f[3], _num(f[4])))
        res[c] = (rows, miss, nopath, bool(path and os.path.exists(path)))
    arr = {'tt': _dump(a.dump_tt), 'ff': _dump(a.dump_ff)}
    out, worst = [], dict(tt=None, ff=None)
    fails = defaultdict(int)
    for h in H['hops']:
        r = dict(h)
        for c, kind in (('tt', 'setup'), ('ff', 'hold')):
            rows, miss, nopath, have = res[c]
            if not have:
                r[kind] = 'NOT_RUN'
                fails[f'{c}_not_run'] += 1
                continue
            if h['net'] in miss:
                r[kind] = 'NET_MISSING'
                fails[f'{c}_net_missing'] += 1
                continue
            ps = [p for p in rows.get(h['net'], ()) if p[1].split('/')[0] == h['load']]
            if not ps:
                r[kind] = 'NO_PATH'
                fails[f'{c}_no_path'] += 1
                continue
            s = min(p[2] for p in ps if p[2] is not None) if any(p[2] is not None for p in ps) else None
            if s is None:
                r[kind] = 'UNCONSTRAINED'
                fails[f'{c}_unconstrained'] += 1
                continue
            la, ca = _inst_arr(arr[c], h['drv']), _inst_arr(arr[c], h['load'])
            skew = None
            if la and ca:
                # setup: capture later = more slack (worst = earliest capture vs latest launch); hold: the opposite
                skew = (ca[0] - la[1]) if kind == 'setup' else -(ca[1] - la[0])
            adj = s + (skew or 0.0)
            r[kind] = dict(sta_slack_ps=round(s, 1), measured_skew_ps=None if skew is None else round(skew, 1),
                           slack_ps=round(adj, 1), arrivals='dieclk' if skew is not None else 'ideal (no dieclk arrival)')
            if worst[c] is None or adj < worst[c][0]:
                worst[c] = (round(adj, 1), h['net'], h['load'])
            if adj < 0:
                fails[f'{c}_{kind}_negative'] += 1
            if skew is None:
                fails[f'{c}_no_measured_arrival'] += 1
        out.append(r)
    hard = {k: v for k, v in fails.items() if not k.endswith('no_measured_arrival')}
    verdict = 'PASS' if H['hops'] and not hard else 'FAIL'
    rec = dict(schema='opentallas.qwen_kv_rst_window.v1', E_r=H['E_r'], hops=len(H['hops']), verdict=verdict,
               problems=dict(fails), worst_setup_tt=worst['tt'], worst_hold_ff=worst['ff'], rows=out,
               method='set_multicycle_path -setup E_r / -hold E_r-1 per hop net; TT setup + FF hold on the die GRT '
                      'parasitics; slack corrected by the dieclk measured launch / capture pin arrivals of this floorplan')
    json.dump(rec, open(a.out, 'w'), indent=1)
    print(f"KV RST WINDOW {verdict}: {len(H['hops'])} hops E_r={H['E_r']} worst TT setup {worst['tt']} "
          f"worst FF hold {worst['ff']} problems {dict(fails)}")
    return 0 if verdict == 'PASS' else 1


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('hops')
    p.add_argument('--die-v', required=True)
    p.add_argument('--lef', required=True)
    p.add_argument('--out', required=True)
    p = sp.add_parser('tcl')
    p.add_argument('--hops', required=True)
    p.add_argument('--corner', required=True, choices=('tt', 'ff', 'ss'))
    p.add_argument('--out', required=True)
    p = sp.add_parser('report')
    p.add_argument('--hops', required=True)
    p.add_argument('--tt')
    p.add_argument('--ff')
    p.add_argument('--dump-tt')
    p.add_argument('--dump-ff')
    p.add_argument('--out', required=True)
    a = ap.parse_args()
    return dict(hops=hops, tcl=tcl, report=report)[a.cmd](a) or 0


if __name__ == '__main__':
    raise SystemExit(main())
