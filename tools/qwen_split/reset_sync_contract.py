#!/usr/bin/env python3
"""Q-RSTGEN7 10-19 (RELEASE_TREE Q.STA.GEN.7): reset release into a foreign clock, structurally.

The registered die reset tree (tools/qwen_rom_fulldie_b3r2.py _reset_tree) carries the reset LEVEL as data, synchronous
to the tree's clock.  Two sink classes are not single-cycle synchronous captures of that level, and the die STA timed
them as if they were (dv2f15codex TT):

  (b) a TILE whose rst_n port drives only its own 2-flop reset synchroniser (async assert, sync release) at the pin:
      qfd_d2d_static (ot_rst_pipe u_reset_regions) and qfd_sys_face (rr_s / rr_q relay).  The port release is captured
      on the tile's internal clock (d2d_rom: early tap, 420.7 ps TT insertion; -100.7 ps against a stream repeater),
      re-synchronised inside, and no consumer counts cycles from the port (ot_rst_pipe: "Consumers must not count
      cycles from the port"; sys_face: "boot replay and every production event are anchored to boot_done / the epoch
      strobe, never to the reset edge").  => async reset-synchroniser input: the hop is not a timed release.
  (c) a sink on a FOREIGN clock domain (not mesochronous with the tree: ucie 1000 ps 6:5, serial 4:3; the SerDes FDI
      roots are mesochronous with the core, clock_contract.py) whose reset input is NOT synchronised inside: the
      licensed link-PHY abstracts (ot_qfd_ucie_x64_phy: model `always @(posedge clk or negedge rst_n)`, rst_n timed as
      a setup pin, no synchroniser).  The stream repeater -> io_ucie rst_n path was a stream -> ucie (6:5)
      inter-clock path (-220.9 ps).  => the LAST tree hop into such a sink is re-clocked onto the sink's own clock: the
      qfd_rst_rep (d -> s[0] -> r0/r1, no logic between: a 2-flop synchroniser of the level) synchronises the release in
      the receiving domain, its q -> PHY rst_n hop is an ordinary single-domain timed path, and only its d pin (the
      synchroniser input) is the async crossing.  Fixed latency 2 PHY edges (+-1 edge synchroniser resolution; the PHY
      boundary is elastic: link training / tx_up, flow control kept at off-die boundaries).

Declared synchroniser inputs become `set_false_path -to` exceptions in the die STA (case/reset_sync.sdc, read by
tools/qwen_tp8/die_sta_libs.py), each with its structural reason; a pin is declared only when
  * its master + port is in SYNC_PINS and rtl_check() proves, from the source RTL, that the port reaches nothing but
    the asynchronous clear of a synchroniser whose first stage takes a constant 1, or
  * it is the d pin of a qfd_rst_rep that the generator re-clocked onto its sink's foreign clock,
and the net feeding it is driven by a registered reset repeater output (a glitch-free flop level).
"""
import re
from pathlib import Path

# master -> port -> where the synchroniser is (module chain from the master's RTL top to the async-clear block)
SYNC_PINS = {
    'qfd_d2d_static': {'rst_n': dict(rtl=('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'rtl/lib/ot_rst_pipe.sv'),
                                     top='qfd_d2d_static',
                                     why='port -> qfd_d2d_static_core -> ot_rst_pipe u_reset_regions 2-flop synchroniser '
                                         '(async assert, sync release); cold release outside the compiled timeline'),
                       'por_n': dict(rtl=('rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_dies.sv', 'rtl/lib/ot_rst_pipe.sv'),
                                     top='qfd_d2d_static',
                                     why='port -> qfd_d2d_static_core -> ot_rst_pipe u_por_region 2-flop synchroniser')},
    'qfd_sys_face': {'rst_n': dict(rtl=('rtl/qwen_split/qfd_sys_face.sv',), top='qfd_sys_face',
                                   why='port -> rr_s 2-flop synchroniser + rr_q relay flops (async assert, sync release); '
                                       'production events anchored to boot_done / epoch strobe')},
}
# reset tree repeaters: d -> s[0] -> r0 / r1 (PAD 0), no logic between the two flops (rtl/qwen_sys/reset_tree_20261013)
REP_SYNC = {'qfd_rst_rep': 'rtl/qwen_sys/reset_tree_20261013/ot_qwen_rst_rep.sv'}


def ck_domain(net):
    """clock domain of a clock bus / net name (the die STA's grouping, tools/qwen_tp8/die_sta_libs.py domain())."""
    n = net[2:] if net.startswith('n_') else net
    if n == 'clk_coll_blk':
        return 'coll_blk'
    m = re.match(r'clk_hbm_(\w+?)(?:__.*)?$', n)
    if m:
        return 'hclk_' + m.group(1)
    for k in ('serial', 'ucie', 'serdes'):
        if n.startswith('clk_' + k):
            return k
    return 'stream'


def mesochronous(model=None):
    """clock domains that share the stream PLL edge (same period, phase 0) -- tools/qwen_split/clock_contract.py: the
    SerDes FDI roots are mesochronous with the core when the PHY-clock collective is bound (periods 833.3, related);
    ucie (1000 ps, 6:5) and serial (1111 ps, 4:3) are rationally related only: a flop-to-flop release has no
    single-cycle-safe edge pair there."""
    d = {'stream'}
    if model is None or ((model.get('native_static_io_bind') or {}).get('phy_clocks')):
        d.add('serdes')
    return frozenset(d)


def foreign(a, b, meso):
    """True when a reset level launched on clock domain a cannot be a single-cycle timed capture on domain b."""
    return a != b and not (a in meso and b in meso)


def _modules(text):
    out = {}
    for m in re.finditer(r'^\s*module\s+(\w+)\b(.*?)^\s*endmodule\b', text, re.S | re.M):
        out[m.group(1)] = m.group(2)
    return out


def _strip_comments(text):
    return re.sub(r'//[^\n]*', '', re.sub(r'/\*.*?\*/', '', text, flags=re.S))


def _port_is_sync(mods, mod, port, seen=()):
    """True when, inside module `mod`, `port` is used only (a) as the async clear of always blocks
    `@(posedge <clk> or negedge port)` whose non-reset branch loads a constant 1 into the first stage, or (b) connected
    to a child instance port that satisfies the same rule.  Returns (ok, reason)."""
    if (mod, port) in seen:
        return False, f'recursion at {mod}.{port}'
    body = mods.get(mod)
    if body is None:
        return False, f'module {mod} not in the RTL given'
    p = re.escape(port)
    ok_async = False
    uses = clears = 0
    # (a) async-clear always blocks
    for m in re.finditer(r'always\s*@\s*\(\s*posedge\s+\w+\s+or\s+negedge\s+' + p + r'\s*\)(.*?)(?=\balways\b|\bassign\b|'
                         r'\bgenerate\b|\bwire\b|\breg\b|\blocalparam\b|\Z)', body, re.S):
        blk = m.group(1)
        if not re.search(r"if\s*\(\s*!\s*" + p + r"\s*\)", blk):
            return False, f'{mod}: negedge {port} block without an if (!{port}) clear'
        if not re.search(r"<=\s*(?:1'b1|\{[^}]*1'b1\s*\})", blk.split('else', 1)[-1]):
            return False, f'{mod}: negedge {port} block loads no constant 1 into a first stage'
        clears += len(re.findall(r'if\s*\(\s*!\s*' + p + r'\s*\)', blk))
        ok_async = True
    # every textual use of the port
    for m in re.finditer(r'(?<!\.)\b' + p + r'\b', body):     # .port( names are not uses
        uses += 1
    # declarations, async sensitivity and the clear test are the allowed plain uses
    allowed = len(re.findall(r'\b(?:input|output|inout)\s+(?:wire\s+)?(?:\[[^\]]*\]\s*)?(?:\w+\s*,\s*)*' + p + r'\b', body))
    allowed += len(re.findall(r'negedge\s+' + p + r'\b', body))
    allowed += clears                      # the clear tests INSIDE the async blocks only
    # (b) child connections .X(port)
    for m in re.finditer(r'\b(\w+)\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s+(\w+)\s*\(((?:[^;])*?)\)\s*;', body, re.S):
        child, conns = m.group(1), m.group(3)
        for cm in re.finditer(r'\.(\w+)\s*\(\s*' + p + r'\s*\)', conns):
            ok, why = _port_is_sync(mods, child, cm.group(1), seen + ((mod, port),))
            if not ok:
                return False, f'{mod}.{port} -> {child}.{cm.group(1)}: {why}'
            allowed += 1
            ok_async = True
    if uses != allowed:
        return False, f'{mod}: {port} used {uses} times, only {allowed} are synchroniser clears / declarations / sync children'
    if not ok_async:
        return False, f'{mod}: {port} reaches no synchroniser'
    return True, 'ok'


def rtl_check(repo, sync_pins=None, texts=None):
    """Prove every SYNC_PINS entry from its source RTL.  texts: {rtl path: text} overrides (tests / mutants).
    Returns {master.port: (ok, reason)}."""
    res = {}
    for mst, ports in (sync_pins or SYNC_PINS).items():
        for port, r in ports.items():
            src = ''
            for f in r['rtl']:
                if texts and f in texts:
                    src += texts[f] + '\n'
                else:
                    pth = Path(repo) / f
                    if not pth.exists():
                        res[f'{mst}.{port}'] = (False, f'RTL missing: {f}')
                        break
                    src += pth.read_text() + '\n'
            else:
                res[f'{mst}.{port}'] = _port_is_sync(_modules(_strip_comments(src)), r['top'], port)
    return res


def rep_check(repo, texts=None):
    """qfd_rst_rep (ot_qwen_rst_rep PAD 0): d feeds only s[0]; r0 / r1 take s[PAD] (no logic between the flops)."""
    f = REP_SYNC['qfd_rst_rep']
    t = texts[f] if texts and f in texts else (Path(repo) / f).read_text()
    t = _strip_comments(t)
    if not re.search(r's\[0\]\s*<=\s*d\s*;', t):
        return False, 'ot_qwen_rst_rep: d is not the input flop s[0]'
    if len(re.findall(r'(?<!\.)\bd\b', t)) != 2 + len(re.findall(r'\?\s*d\b', t)):   # port decl + s[0] <= d (+ MUT-only)
        return False, 'ot_qwen_rst_rep: d used beyond the input flop'
    if not re.search(r'r0\s*<=\s*s\[PAD\]\s*;', t):
        return False, 'ot_qwen_rst_rep: r0 is not s[PAD]'
    return True, 'ok'


def _sink_clock(ckof, inst, port):
    """the clock bus of a sink pin (the reset tree's vote rule: a CDC leaf with two clocks -> h_* pins ride hclk)."""
    c = ckof.get(inst, [])
    if len(c) > 1:
        hb = port.lstrip('*').startswith('h')
        c = [q for q in c if q[1].lstrip('*').startswith('h') == hb] or c
    return c[0][0] if c else None


def plan(cells, wires, ck_of_bus, ckof, master_of, sync_ok=None, meso=None):
    """Reset-tree synchroniser plan.  cells: (name, master, x, y, bus, mv) tree repeaters; wires: (net, bus, eps) with
    eps[0] the driver; ck_of_bus: tree bus -> clock bus; ckof: inst -> [(clock bus, clock pin)]; master_of: inst ->
    master.  Returns dict(reclock={rep: clock bus}, endpoints=[dict(pin, why, ...)], errors=[...]).
      * a sink on a clock DOMAIN other than its tree's (one clock pin on the sink: CDC leaves keep their own sync)
        and not itself a declared synchroniser pin -> its driving repeater is re-clocked onto the sink's clock (it must
        drive only sinks of that one clock, else an error) and the repeater's d pin is a synchroniser endpoint;
      * a sink whose master.port is a declared SYNC_PINS entry (rtl_check ok) driven by a tree repeater -> endpoint."""
    reps = {c[0]: c[4] for c in cells}
    sync_ok = sync_ok or {}
    meso = mesochronous() if meso is None else meso
    drv_sinks = {}
    for net, bus, eps in wires:
        if not eps or eps[0][0] not in reps or eps[0][1] not in ('q0', 'q1'):
            continue
        drv_sinks.setdefault(eps[0][0], []).extend((net, i, p) for i, p in eps[1:])
    reclock, endpoints, errors = {}, [], []
    for rep, sinks in sorted(drv_sinks.items()):
        tree_ck = ck_of_bus.get(reps[rep])
        fcks, other = set(), []
        for net, i, p in sinks:
            if i in reps:
                other.append((i, p, tree_ck))
                continue
            mst = master_of.get(i)
            key = f'{mst}.{p.lstrip("*")}'
            if key in sync_ok:
                if sync_ok[key][0]:
                    endpoints.append(dict(pin=f'{i}/{p.lstrip("*")}', inst=i, master=mst, net=net, driver=rep,
                                          cls='tile_reset_synchroniser', why=SYNC_PINS[mst][p.lstrip('*')]['why']))
                    continue
                errors.append(dict(rep=rep, sink=f'{i}/{p}', error=f'declared synchroniser pin fails its RTL check: '
                                                                    f'{sync_ok[key][1]}'))
                continue
            ck = _sink_clock(ckof, i, p)
            single = len({c for c, _ in ckof.get(i, [])}) == 1
            if ck and tree_ck and single and foreign(ck_domain(tree_ck), ck_domain(ck), meso):
                fcks.add(ck)
            else:
                other.append((i, p, ck))
        if not fcks:
            continue
        if len(fcks) > 1 or other:
            errors.append(dict(rep=rep, foreign=sorted(fcks), other=[f'{i}/{p}' for i, p, _ in other],
                               error='a foreign-clock reset sink shares its last repeater with sinks of another clock: '
                                     'no single synchronising clock (split the leaf)'))
            continue
        ck = fcks.pop()
        reclock[rep] = ck
        endpoints.append(dict(pin=f'{rep}/d', inst=rep, master='qfd_rst_rep', net=None, driver=None,
                              cls='foreign_clock_reset_synchroniser', clock=ck,
                              why=f'last reset hop re-clocked onto {ck} ({ck_domain(ck)}): qfd_rst_rep d -> s[0] -> r0 is a '
                                  f'2-flop synchroniser of the level in the receiving domain; fixed 2 edges, +-1 resolution; '
                                  f'q -> sink rst_n timed single-domain'))
    return dict(reclock=reclock, endpoints=endpoints, errors=errors)


INST = re.compile(r'^\s*(\w+)\s+(\w+)\s*\((.*)\);\s*$')
CONN = re.compile(r'\.(\w+)\(\s*([\w$]+)(?:\[\d+(?::\d+)?\])?\s*\)')
CLOCK_PINS = ('clk', 'ck')


def model_from_netlist(text):
    """(cells, wires, ck_of_bus, ckof, master_of) in plan()'s form from a flat die netlist (one instance per line):
    reset-tree repeaters = qfd_rst_rep*, each on its own 'bus' (its clock is the tree clock), one wire per output net."""
    insts = {}
    for ln in text.split('\n'):
        m = INST.match(ln)
        if m and m.group(1) not in ('module', 'wire', 'input', 'output', 'inout'):
            insts[m.group(2)] = (m.group(1), CONN.findall(m.group(3)))
    strip = lambda n: n[2:] if n.startswith('n_') else n
    ckof = {nm: [(strip(v), p) for p, v in cs if p in CLOCK_PINS and strip(v).startswith('clk')] for nm, (_, cs) in insts.items()}
    master_of = {nm: mst for nm, (mst, _) in insts.items()}
    cells, ck_of_bus, loads = [], {}, {}
    for nm, (mst, cs) in insts.items():
        for p, v in cs:
            if p not in CLOCK_PINS:
                loads.setdefault(v, []).append((nm, p))
    wires = []
    for nm, (mst, cs) in sorted(insts.items()):
        if not mst.startswith('qfd_rst_rep'):
            continue
        cells.append((nm, mst, 0.0, 0.0, nm, 0.0))
        ck_of_bus[nm] = next((c for c, _ in ckof.get(nm, [])), None)
        for p, v in cs:
            if p in ('q0', 'q1'):
                wires.append((v, nm, [(nm, p)] + [e for e in loads.get(v, []) if e != (nm, p)]))
    return cells, wires, ck_of_bus, ckof, master_of


def audit(wires, rep_clock, ckof, master_of, endpoints, meso=None):
    """untreated reset release hops: a tree-repeater output reaching (1) a sink on another clock domain than the
    repeater's clock, or (2) a declared tile synchroniser pin (deep internal clock: the die STA times it as a release)
    -- neither declared as a synchroniser endpoint.  0 = every release is single-domain timed or synchronised."""
    declared = {e['pin'] for e in endpoints}
    meso = mesochronous() if meso is None else meso
    bad = []
    for net, bus, eps in wires:
        rep, _ = eps[0]
        if rep not in rep_clock:
            continue
        for i, p in eps[1:]:
            pin = f'{i}/{p.lstrip("*")}'
            if i in rep_clock:
                if foreign(ck_domain(rep_clock[rep]), ck_domain(rep_clock[i]), meso) and f'{i}/d' not in declared:
                    bad.append(dict(hop=f'{rep} -> {pin}', cls='cross-domain repeater hop'))
                continue
            ck = _sink_clock(ckof, i, p)
            if master_of.get(i) in SYNC_PINS and p.lstrip('*') in SYNC_PINS[master_of[i]] and pin not in declared:
                bad.append(dict(hop=f'{rep} -> {pin}', cls='tile synchroniser input timed as a release'))
            elif ck and foreign(ck_domain(rep_clock[rep]), ck_domain(ck), meso) and len(ckof.get(i, [])) == 1:
                bad.append(dict(hop=f'{rep} -> {pin}', cls=f'{ck_domain(rep_clock[rep])} -> {ck_domain(ck)} reset release'))
    return bad


def sdc(endpoints):
    """die STA exceptions for the declared synchroniser inputs (appended to the die clocks by die_sta_libs.py)."""
    L = ['# Q-RSTGEN7 reset synchroniser inputs (tools/qwen_split/reset_sync_contract.py): the release is captured by a',
         '# 2-flop synchroniser in the receiving domain (async assert, sync release; +-1 edge), never a timed release',
         'set ::ot_rsync_n 0; set ::ot_rsync_miss 0',
         'proc ot_rsync {p} { set q [get_pins -quiet $p]; if {[llength $q]} { set_false_path -to $q; incr ::ot_rsync_n } '
         'else { incr ::ot_rsync_miss } }']
    for e in endpoints:
        L.append(f"ot_rsync {{{e['pin']}}}   ;# {e['cls']}")
    L.append('puts "OT_RESET_SYNC set $::ot_rsync_n missing $::ot_rsync_miss of %d"' % len(endpoints))
    return '\n'.join(L) + '\n'


def main():
    """audit a GEN netlist: reset_sync_contract.py --die-v CASE/die.v [--sync CASE/reset_sync.json] [--repo .]
    prints RESET_SYNC_AUDIT PASS|FAIL untreated=<n>; exit 1 on FAIL (run on every GEN case after Q-RSTGEN7)."""
    import argparse
    import json
    ap = argparse.ArgumentParser(description=main.__doc__.splitlines()[0])
    ap.add_argument('--die-v', required=True)
    ap.add_argument('--sync', help='case/reset_sync.json written by the GEN (declared endpoints)')
    a = ap.parse_args()
    cells, wires, ckb, ckof, mof = model_from_netlist(Path(a.die_v).read_text())
    eps = json.loads(Path(a.sync).read_text())['endpoints'] if a.sync and Path(a.sync).exists() else []
    bad = audit(wires, dict(ckb), ckof, mof, eps)
    print(f"RESET_SYNC_AUDIT {'PASS' if not bad else 'FAIL'} repeaters={len(cells)} endpoints={len(eps)} "
          f"untreated={len(bad)} {[b['hop'] for b in bad[:8]]}")
    return 1 if bad else 0


if __name__ == '__main__':
    raise SystemExit(main())
