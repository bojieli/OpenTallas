#!/usr/bin/env python3
"""Die-STA class check: reset release into foreign clocks (QW-L1K 10-20; COORD 21:29 (c): land reset crossings between
regions in each region's own clock).

A die passes when NO timing path launched by a reset-tree flop (reset repeater / sequencer / synchroniser / reset
lane relay) fails setup (TT) or hold (FF) into a flop clocked by a DIFFERENT clock region ("foreign-clock release").
Such a path is the reset release crossing a region boundary reg->reg with no landing in the receiver's own clock; the
structural fix is in the GEN (regional reset leaf: release re-timed / landed in the destination region), never an SDC
false path.

Static classes (GEN time, die.v only; run on every GEN before the chain):
  FOREIGN       reset-tree hop driver region not among the load's regions, load not a landing / synchroniser -> must be 0
  NO_CLOCK      a reset hop end with no clock net (unknown region)                                        -> must be 0
  LANDED / SYNC / INTRA   into a landing ring / a synchroniser async input / same region (fine)
STA classes (per corner, with --setup / --hold):
  RESET_XREG    failing path, reset-tree startpoint, start region not among the endpoint instance's regions  -> must be 0
  RESET_INTRA   failing path, reset-tree startpoint, same region (plain timing of the reset tree; reported, own fix)
  RESET_UNK     failing reset-tree path whose region cannot be resolved (counts as FAIL: no unknowns)
  OTHER         failing non-reset paths (not judged here)
Regions come from the die netlist: the die-level clock net(s) on an instance's clock pins (one net per regional tree,
QCLK landed-regions standard); reset-tree instances are recognised by master.  A landing / ring with two clocks (ck_s,
ck) belongs to both of its regions.

  reset_release_check.py --die-v die.v \
      --setup sta_tt/grt_tt_summary.rpt --hold sta_ff/grt_ff_summary.rpt [--out report.json] [--diagnostic REASON]
exit 1 on FAIL (0 with --diagnostic; verdict stays FAIL, labelled).
"""
import argparse
import collections
import json
import re
import sys

SCHEMA = 'opentallas.die_reset_release_check.v1'
RESET_MASTER = re.compile(r'^(qfd_rst_rep|qfd_rstseq|qfd_rstsync|qfd_rlyr0?_|qfd_rlyrl_|ot_rst_relay|ot_reset_sync|qkd_rst_rep)')
INST_RE = re.compile(r'^\s*([A-Za-z_][\w$]*)\s+(?:#\(.*?\)\s*)?([A-Za-z_][\w$\[\]\.]*)\s*\(')


CONN_RE = re.compile(r'\.([A-Za-z_][\w$]*)\s*\(\s*([^()]*?)\s*\)')
CLK_PIN = re.compile(r'^(clk|ck|ck_s|ckf|clk_\w+|ck_\w+|\w*_ck|\w*_clk)$')
KEYWORDS = ('module', 'input', 'output', 'wire', 'inout', 'assign', 'endmodule', 'reg', 'parameter', 'localparam')


def netlist(die_v):
    """die.v (one generated top): inst -> master, inst -> set(clock nets on its clock pins) = its clock REGIONS
    (QCLK regional standard: one tree per qfd_clkrx output = one die-level clock net per region)"""
    mast, reg, conns = {}, collections.defaultdict(set), collections.defaultdict(list)
    buf = ''
    for line in open(die_v):
        t = line.strip()
        if not buf:
            g = INST_RE.match(line)
            if not g or g.group(1) in KEYWORDS:
                continue
        buf += ' ' + t
        if not t.endswith(';'):
            continue
        g = INST_RE.match(buf)
        if g:
            inst = g.group(2)
            mast[inst] = g.group(1)
            for pin, net in CONN_RE.findall(buf):
                net = net.strip()
                if not net or "'" in net:
                    continue
                if CLK_PIN.match(pin):
                    reg[inst].add(net.split('[')[0])
                else:
                    conns[net].append((inst, pin))
        buf = ''
    return mast, reg, conns


RST_OUT = re.compile(r'^(q\d*|b|rso_\w+|rst_o\w*)$')        # reset-tree master outputs
ASYNC_IN = ('arst_n',)                                        # synchroniser async input (designed CDC)
LANDING_M = re.compile(r'^(qfd_rlyrl_|qfd_landh0?_|qkd_landsh)')


def static_judge(mast, reg, conns):
    """GEN-time structure (no STA): every reset-tree hop driver -> load; FOREIGN when the driver's clock region is not
    among the load's regions and the load is neither a landing ring nor a synchroniser async input -> must be 0"""
    cnt, fam, ex = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    for net, ends in conns.items():
        drv = [(i, p) for i, p in ends if RESET_MASTER.match(mast.get(i, '')) and RST_OUT.match(p)]
        if len(drv) != 1:
            continue
        di, dp = drv[0]
        rd = reg.get(di, set())
        for li, lp in ends:
            if (li, lp) == (di, dp):
                continue
            rl, lm = reg.get(li, set()), mast.get(li, '?')
            if lp in ASYNC_IN:
                c = 'SYNC'
            elif not rd or not rl:
                c = 'NO_CLOCK'
            elif rd & rl:
                c = 'INTRA'
            elif LANDING_M.match(lm):
                c = 'LANDED'
            else:
                c = 'FOREIGN'
            cnt[c] += 1
            if c in ('FOREIGN', 'NO_CLOCK'):
                fam[(c, re.sub(r'(__t?\d+|_\d+)+$', '', di), lm)] += 1
                if len(ex[c]) < 25:
                    ex[c].append(dict(src=di, src_master=mast.get(di), src_region=sorted(rd), net=net, dst=li + '/' + lp,
                                      dst_master=lm, dst_region=sorted(rl)))
    return dict(counts=dict(cnt), families=[dict(cls=c, tree=t, dst_master=m, n=n) for (c, t, m), n in fam.most_common(30)],
                examples=dict(ex))


def summary_rows(path):
    """report_checks -format summary: 'start_pin (master) end_pin (master) slack' -> (start_inst, end_inst, slack)"""
    rows = []
    for line in open(path):
        p = line.split()
        if len(p) < 3 or '/' not in p[0]:
            continue
        try:
            slack = float(p[-1])
        except ValueError:
            continue
        ends = [x for x in p[1:-1] if '/' in x and not x.startswith('(')]
        if not ends:
            continue
        rows.append((p[0].split('/')[0], ends[0].split('/')[0], ends[0], slack))
    return rows


def judge(rows, mast, reg, corner):
    cnt = collections.Counter()
    worst = collections.defaultdict(list)
    fam = collections.Counter()
    for s, e, epin, slack in rows:
        if slack >= 0:
            continue
        if not RESET_MASTER.match(mast.get(s, '')):
            cnt['OTHER'] += 1
            continue
        rs, re_ = reg.get(s, set()), reg.get(e, set())
        if not rs or not re_:
            c = 'RESET_UNK'
        elif rs & re_:
            c = 'RESET_INTRA'
        else:
            c = 'RESET_XREG'
        cnt[c] += 1
        fam[(c, re.sub(r'(__t?\d+|_\d+)+$', '', s), mast.get(e, '?'))] += 1
        if len(worst[c]) < 400:
            worst[c].append(dict(start=s, start_master=mast.get(s), start_region=sorted(rs)[:2], end=epin,
                                 end_master=mast.get(e), end_region=sorted(re_)[:2], slack_ps=slack))
    for c in worst:
        worst[c] = sorted(worst[c], key=lambda r: r['slack_ps'])[:25]
    families = [dict(cls=c, tree=t, end_master=m, n=n) for (c, t, m), n in fam.most_common(40)]
    ws = {c: min((r['slack_ps'] for r in worst[c]), default=None) for c in worst}
    return dict(corner=corner, counts=dict(cnt), worst_slack_ps=ws, families=families, worst=dict(worst))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--setup', help='TT setup summary report'); ap.add_argument('--hold', help='FF hold summary report')
    ap.add_argument('--out'); ap.add_argument('--diagnostic')
    a = ap.parse_args()
    mast, reg, conns = netlist(a.die_v)
    st = static_judge(mast, reg, conns)
    res = []
    for corner, f in (('TT_setup', a.setup), ('FF_hold', a.hold)):
        if f:
            res.append(judge(summary_rows(f), mast, reg, corner))
    bad = sum(r['counts'].get('RESET_XREG', 0) + r['counts'].get('RESET_UNK', 0) for r in res)
    bad += st['counts'].get('FOREIGN', 0) + st['counts'].get('NO_CLOCK', 0)
    rep = dict(schema=SCHEMA, verdict='PASS' if bad == 0 else 'FAIL', diagnostic=a.diagnostic, static=st,
               sta='judged' if res else 'NOT RUN (static structure only)',
               reset_instances=sum(1 for v in mast.values() if RESET_MASTER.match(v)), corners=res,
               inputs=dict(die_v=a.die_v, setup=a.setup, hold=a.hold),
               rule='COORD 10-20 21:29 (c) + owner CLOCK RULE 08:55: reset release lands in the receiving region clock')
    sc = st['counts']
    line = 'RESET_RELEASE_CHECK %s%s static foreign %d no_clock %d landed %d sync %d intra %d | ' % (
        rep['verdict'], ' (DIAGNOSTIC %s)' % a.diagnostic if a.diagnostic else '', sc.get('FOREIGN', 0),
        sc.get('NO_CLOCK', 0), sc.get('LANDED', 0), sc.get('SYNC', 0), sc.get('INTRA', 0)) + \
        ' | '.join('%s xreg %d intra %d unk %d worst %s' % (r['corner'], r['counts'].get('RESET_XREG', 0),
                   r['counts'].get('RESET_INTRA', 0), r['counts'].get('RESET_UNK', 0), r['worst_slack_ps']) for r in res)
    if a.out:
        json.dump(rep, open(a.out, 'w'), indent=1)
    print(line)
    return 0 if rep['verdict'] == 'PASS' or a.diagnostic else 1


if __name__ == '__main__':
    sys.exit(main())
