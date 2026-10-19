#!/usr/bin/env python3
"""LAYERBENCH-QWEN 2026-10-18: GEN die netlist -> opentallas.die_relay_stages.v1 (role die_plan, coverage complete).

    netlist_relay_stages.py --die-v die.v --port-bind port_bind.json --design qwen_kv|qwen_compute
        --commit SHA [--src-prefix /srv/.../src/] [--local-rtl DIR ...] --plan-id ID --out relay_stages.json

Why: the die chains print 'RELAY_CHECK SKIPPED' because (a) no compiler pass wrote a compiled schedule and (b) the KV
case (kvs14c case_kv) never exported its die-run table (case_kv/relay_stages.json MISSING).  This exporter walks the
NETLIST itself (not the generator model): every non-relay output pin bit is followed through relay instances to the
non-relay input pins it reaches; stages = relay instances walked.  Port directions come from the bound RTL read out of
git at the die's source commit (port_bind.json masters[*].rtl / rtl_files), so no checkout is needed.
Relay masters (one stage each, data a -> b): qkd_rlys_* (KV standard relays), qfd_rly_* / qfd_rlyh*_ (half-cycle
forwarded stations) / qfd_land*_ (landing: counted as one relay instance, the generator's rule; its read age in core
cycles is the K strap, recorded per bus as 'landing_k').  Clock / reset / constant / tie classes are skipped as the
generator exporters do (tools/qwen_split/relay_stages_export.py RELAY_SKIP): a pin whose RTL port name is a clock
(ck*, clk*, *_ck, gclk), the elastic PHY instances of SKIP_INST (--skip-inst), relay control pins (ea/eb/en/k*/tie_*/ck_o/ckf), and
reset-repeater tree masters (qfd_rst_rep*, qkd_rst_region).
Domain: the clock net on the source instance's first clock port mapped by --domain-map (default: n_clk_coll* ->
serial_0p9, everything else on the die core -> stream_1p2, n_clk_hbm* -> hbm_cdc).
"""
import argparse, json, re, subprocess, sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import die_port_bind as P   # noqa: E402
import die_relay_stages as DRS   # noqa: E402
from qwen_split import lane_groups as LG  # noqa: E402

# QXF-SEAMK 10-18: + the KV forwarded-lane stations / landings (tools/qwen_kv_die/kv_fwd_lanes.py, qkd_rlysh0?_<S> /
# qkd_landsh0?_<S>: same instance per relay station, a -> b, one stage each as the generator counts them)
RELAY_RE = re.compile(r'^(qkd_rlys_\d+|qkd_rlysh0?_\d+|qkd_landsh0?_\d+|qfd_rly_|qfd_rlyh0?_|qfd_landh?0?_)')
FORWARDED_RE = re.compile(r'^(qkd_rlysh0?_\d+|qkd_landsh0?_\d+|qfd_rlyh0?_|qfd_landh?0?_)')
RESET_MASTER_RE = re.compile(r'^(qfd_rst_rep|qkd_rst_region)')
CLOCK_PORT_RE = re.compile(r'^(ck|clk|ck_\w+|clk_\w+|\w+_ck|\w+_clk|gclk|ck\d+|refclk|face_ck|fdi_ck|hck)$')
RELAY_CTRL = {'ea', 'eb', 'en', 'k0', 'k1', 'k2', 'tie_hi', 'tie_lo', 'ck_o', 'ckf', 'ck_s', 'fault', 'ck', 'rs'}
DOMAIN_MAP = [(re.compile(r'^n_clk_coll'), 'serial_0p9'), (re.compile(r'^n_clk_hbm'), 'hbm_cdc'),
              (re.compile(r'^n_clk_(host|ingest|phy)'), 'stream_1p2'), (re.compile(r'^n_clk'), 'stream_1p2')]
CLOCK_PERIOD_PS = 833.333
# elastic PHY edges left out, as the generator exporters' class skips: compute coll_fdi / phy_dfi (collective SerDes +
# collective UCIe; the D2D FDI to ucie_kv IS listed by the compute generator); KV d2d_fdi / phy_dfi / hbm_cdc (ABUT)
SKIP_INST = dict(qwen_compute=r'^(io_serdes(_\d+)?|io_ucie)$', qwen_kv=r'^$')
SKIP_MODEL_MASTERS = dict(qwen_compute=False, qwen_kv=True)   # KV: every PHY / analog model instance (d2d_fdi, phy_dfi ABUT)


def is_relay(master):
    return bool(RELAY_RE.match(master))


def rtl_text(path, commit, src_prefixes, local_dirs):
    p = str(path)
    for d in local_dirs:
        q = Path(d) / Path(p).name
        if q.exists():
            return q.read_text(errors='replace'), f'local:{q}'
    rel = p
    for pre in src_prefixes:
        if p.startswith(pre):
            rel = p[len(pre):].lstrip('/')
            break
    if rel.startswith('/'):
        raise SystemExit(f'netlist_relay_stages: absolute RTL path {p} outside --src-prefix and --local-rtl (fail closed)')
    t = subprocess.run(['git', '-C', str(ROOT), 'show', f'{commit}:{rel}'], capture_output=True, text=True)
    if t.returncode and Path(p).is_absolute() and Path(p).is_file():
        # QXF-SEAMK 10-18: a die chain's source tree without git history (rsync'd src/): the run's own file (recorded)
        return Path(p).read_text(errors='replace'), f'disk:{p}'
    if t.returncode:
        raise SystemExit(f'netlist_relay_stages: git show {commit}:{rel} failed: {t.stderr.strip()[:200]}')
    return t.stdout, f'git:{commit}:{rel}'


def load_ports(pb, commit, src_prefixes, local_dirs):
    defines = {d: '' for d in pb.get('defines') or []}
    files = {}
    for m, v in pb['masters'].items():
        files.setdefault(v['rtl'], set()).add(m)
    for f in pb.get('rtl_files') or []:
        files.setdefault(f, set())
    mods, srcs = {}, {}
    for f in sorted(files):
        txt, how = rtl_text(f, commit, src_prefixes, local_dirs)
        for mod in P.parse_modules(P.preprocess(P.strip_comments(txt), dict(defines)), f):
            mods.setdefault(mod.name, mod)
        srcs[f] = how
    missing = sorted(m for m in pb['masters'] if m not in mods)
    if missing:
        raise SystemExit(f'netlist_relay_stages: masters without RTL ports {missing[:8]} (fail closed)')
    return mods, srcs


def domain_of(net, dmap=DOMAIN_MAP):
    for rx, d in dmap:
        if rx.match(net or ''):
            return d
    return None


def age_fields(r, land_k, land_e=None):
    """Destination-pin ages use the same lane_cycles source as record_bundles.

    K is an epoch strap, not a latency. A forwarded path requires its own lane
    metadata and matching actual straps, even when it has only one frame.
    """
    lands = {l for l in r['lands'] if l}
    if not lands:
        return dict(age_edges=LG.lane_cycles(dict(n=max(r['st']))), age_basis='relay flops')
    ks = sorted({land_k.get(l[-1]) for l in lands}, key=str)
    if len(r['lands']) == 1 and len(lands) == 1 and len(next(iter(lands))) == 1:
        name = next(iter(lands))[-1]
        row = (land_e or {}).get(name)
        post = int((row or {}).get('post_stages', 0))
        if row is not None and post >= 0 and ks == [int(row.get('K', -1)) % 8] and r['st'] == {int(row.get('n', -1)) + post}:
            return dict(age_edges=LG.lane_cycles(row) + post, landing_k=ks[0],
                        age_basis='lane_groups.lane_cycles: forwarded E + registered landing output + explicit plain post stages')
        # A die endpoint may also have plain relay flops before the forwarded
        # lane. Require the walked forwarded instance set to match the GEN
        # chain exactly; unexplained frame counts alone never establish age.
        stations = row.get('stations') if row else None
        plain = r.get('plain_counts', set())
        if (stations and len(stations) == int(row.get('n', -1)) and post >= 0
                and ks == [int(row.get('K', -1)) % 8]
                and r.get('forwarded_paths') == {frozenset(stations)} and len(plain) == 1
                and min(plain) >= post and r['st'] == {len(stations) + min(plain)}):
            return dict(age_edges=LG.lane_cycles(row) + min(plain), landing_k=ks[0],
                        plain_relay_stages=min(plain),
                        age_basis='exact GEN forwarded chain + individually walked plain relay flops')
    return dict(age_edges=None, landing_k=ks[0] if len(ks) == 1 else ks,
                age_basis='landed path: missing lane metadata, mixed paths, or actual K differs from recorded K')


def export_lanes(path):
    """Landing -> checked GEN lane row, retaining E/calendar/K evidence."""
    if not path:
        return None
    fl = json.loads(Path(path).read_text())
    result = {}
    for r in fl.get('lanes', []):
        if r.get('E') is None or not r.get('landing'):
            continue
        if r.get('K') is None or r.get('cal') is None:
            raise ValueError(f"{r['bid']}: missing K/reset calendar")
        e, k, cal = int(r['E']), int(r['K']) % 8, int(r['cal'])
        if k != (e + cal) % 8:
            raise ValueError(f"{r['bid']}: K {k} != (E {e} + calendar {cal}) mod8")
        if r['landing'] in result:
            raise ValueError(f"{r['bid']}: duplicate landing {r['landing']}")
        result[r['landing']] = dict(r, E=e, K=k)
    return result


def export(die_v, pb, design, commit, src_prefixes, local_dirs, plan_id, reach=None, skip_inst=None, land_e=None):
    skip_inst = re.compile(skip_inst or SKIP_INST[design])
    skip_masters = {m for m, v in pb['masters'].items() if v.get('kind') == 'model'} if SKIP_MODEL_MASTERS[design] else set()
    mods, srcs = load_ports(pb, commit, src_prefixes, local_dirs)
    nets, _tin, _tout, insts = P.parse_die(die_v)
    drv = {}                         # bit -> (inst, port, master)
    loads = defaultdict(list)        # bit -> [(inst, port, master, pos)]
    relay_out = {}                   # (inst, in_port, pos) -> out bit
    inst_master, inst_clk, land_k = {}, {}, {}
    problems = []
    const_assign = 0
    for mst, name, _prm, cm in insts:
        if mst == '__assign__':
            m = re.match(r'assign\s+(.+?)\s*=\s*(.+)$', name, re.S)
            if m:
                rb = P.expr_bits(m.group(2), nets)
                if rb is not None and all(b[0] == 'CONST' for b in rb):
                    const_assign += 1
                    continue
                lb = P.expr_bits(m.group(1), nets)
                if lb is None or rb is None or len(lb) != len(rb):
                    problems.append(f'unparsed assign {name[:80]}'); continue
                for x, y in zip(lb, rb):     # alias: y drives x (zero stages), modelled as a pass-through pseudo relay
                    if y[0] not in ('CONST', 'Z', 'UNDECL'):
                        loads[y].append(('__alias__', 'a', '__alias__', len(loads[y])))
                        relay_out[('__alias__', 'a', len(loads[y]) - 1)] = ('ALIAS', x)
            continue
        mod = mods.get(mst)
        if mod is None:
            problems.append(f'{name}: master {mst} without RTL'); continue
        inst_master[name] = mst
        env = mod.env({k: v for k, v in _prm.items()}) if _prm else mod.env()
        bits = {}
        for pn, ex in cm.items():
            b = P.expr_bits(ex, nets)
            if b is None:
                problems.append(f'{name}.{pn}: unparsed connection'); continue
            bits[pn] = b
            if pn in mod.ports and CLOCK_PORT_RE.match(pn) and name not in inst_clk and b and b[0][0] not in ('CONST', 'Z', 'UNDECL'):
                inst_clk[name] = b[0][0]
        relay = is_relay(mst)
        if re.match(r'^(qfd_land|qkd_land)', mst):
            ks = [cm.get(k, '').strip() for k in ('k2', 'k1', 'k0')]
            hi, lo = cm.get('tie_hi'), cm.get('tie_lo')
            if hi and lo and hi != lo and all(k in (hi, lo) for k in ks):
                land_k[name] = sum((1 << (2 - i)) for i, k in enumerate(ks) if k == hi)
            else:
                problems.append(f'{name}: landing K strap not tied from tie_hi / tie_lo: {ks}')
        for pn, b in bits.items():
            d = (mod.ports.get(pn) or (None,))[0]
            if d is None:
                if not (skip_inst.match(name) or mst in skip_masters):
                    problems.append(f'{name}.{pn}: port not in RTL {mst}')
                continue
            n = len(b)
            for i, bit in enumerate(b):
                if bit[0] in ('CONST', 'Z', 'UNDECL'):
                    continue
                pos = n - 1 - i                       # LSB-relative position inside the port
                if d == 'output':
                    if bit in drv:
                        problems.append(f'multi-driven {bit} by {name}.{pn} and {drv[bit][0]}.{drv[bit][1]}')
                    drv[bit] = (name, pn, mst, pos)
                elif d == 'input':
                    loads[bit].append((name, pn, mst, pos))
        if relay and 'a' in bits and 'b' in bits:
            a, bo = bits['a'], bits['b']
            if len(a) != len(bo):
                problems.append(f'{name}: a/b width {len(a)} != {len(bo)}')
            na, nb = len(a), len(bo)
            outpos = {nb - 1 - i: bit for i, bit in enumerate(bo)}
            for i in range(na):
                relay_out[(name, 'a', na - 1 - i)] = outpos.get(na - 1 - i)
    # resolve aliases: ('ALIAS', x) means the load continues on bit x with no stage
    pairs, path_kinds = {}, {}

    def terminal(inst, port, mst):
        if mst == '__alias__':
            return False
        return True

    def skip_pin(inst, port, mst):
        return (CLOCK_PORT_RE.match(port) or port.startswith('arst') or RESET_MASTER_RE.match(mst) or skip_inst.match(inst) or mst in skip_masters
                or (is_relay(mst) and port != 'a' and port in RELAY_CTRL) or port in ('tie_hi', 'tie_lo'))

    for bit, (si, sp, sm, spos) in drv.items():
        if is_relay(sm) or skip_pin(si, sp, sm):
            continue
        stack = [(bit, 0, frozenset(), ())]
        while stack:
            b, n, seen, lands = stack.pop()
            for (li, lp, lm, lpos) in loads.get(b, ()):
                if lm == '__alias__':
                    nx = relay_out.get((li, 'a', lpos))
                    if nx:
                        stack.append((nx[1], n, seen, lands))
                    continue
                if is_relay(lm) and lp == 'a':
                    if li in seen:
                        problems.append(f'relay loop at {li} from {si}.{sp}'); continue
                    nx = relay_out.get((li, 'a', lpos))
                    if nx is None or nx[0] in ('CONST', 'Z', 'UNDECL'):
                        problems.append(f'relay {li}.b bit {lpos} open (chain from {si}.{sp})'); continue
                    stack.append((nx, n + 1, seen | {li}, lands + ((li,) if re.match(r'^(qfd_land|qkd_land)', lm) else ())))
                    continue
                if skip_pin(li, lp, lm):
                    continue
                if seen not in path_kinds:
                    forwarded = frozenset(q for q in seen if FORWARDED_RE.match(inst_master[q]))
                    path_kinds[seen] = (forwarded, len(seen) - len(forwarded))
                forwarded, plain = path_kinds[seen]
                r = pairs.setdefault((si, sp, li, lp), dict(st=set(), bits=set(), sm=sm, lm=lm, lands=set(),
                                                           forwarded_paths=set(), plain_counts=set()))
                r['st'].add(n); r['bits'].add(lpos); r['lands'].add(lands)
                r['forwarded_paths'].add(forwarded); r['plain_counts'].add(plain)
    recs = []
    feeders = defaultdict(list)
    for (si, sp, li, lp) in pairs:
        feeders[(li, lp)].append((si, sp))
    for (si, sp, li, lp), r in sorted(pairs.items()):
        dp = lp
        if len(feeders[(li, lp)]) > 1:            # a concatenated input fed by several sources: name the slice (generator rule)
            dp = f"{lp}__{max(r['bits'])}_{min(r['bits'])}"
        bid = DRS.bus_id(si, sp, li, dp)
        if len(r['st']) > 1:
            problems.append(f'{bid}: bits with different stages {sorted(r["st"])} (max taken)')
        ages = age_fields(r, land_k, land_e)
        if ages['age_edges'] is None:
            problems.append(f"{bid}: unresolved landed age ({ages['age_basis']})")
        recs.append(dict(id=bid, src=dict(inst=si, port=sp, master=r['sm']), dst=dict(inst=li, port=dp, master=r['lm']),
                         width=len(r['bits']), stages=max(r['st']), stage_spread=sorted(r['st']) if len(r['st']) > 1 else None,
                         domain=domain_of(inst_clk.get(si) or inst_clk.get(li)) or 'stream_1p2', eq_age_group=None,
                         **ages))
    doc = DRS.make_doc(design, dict(id=plan_id, commit=commit, generator='tools/qwen_layerbench/netlist_relay_stages.py',
                                    sources=[str(die_v)] + sorted(set(srcs.values()))[:400], kind='GEN netlist walk (die run)'),
                       CLOCK_PERIOD_PS, reach, recs, coverage='complete', problems=problems[:200],
                       problem_count=len(problems), relay_instances=sum(1 for m in inst_master.values() if is_relay(m)),
                       constant_assigns=const_assign,
                       skipped_classes=['clock', 'reset', 'constant', 'relay_control'])
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--die-v', required=True); ap.add_argument('--port-bind', required=True)
    ap.add_argument('--design', required=True, choices=['qwen_compute', 'qwen_kv'])
    ap.add_argument('--commit', required=True); ap.add_argument('--src-prefix', action='append', default=[])
    ap.add_argument('--local-rtl', action='append', default=[]); ap.add_argument('--plan-id', required=True)
    ap.add_argument('--reach', type=float); ap.add_argument('--out', required=True); ap.add_argument('--skip-inst')
    ap.add_argument('--lanes', help='fwd_lanes.json of the same GEN: E of landed lanes with n > 1 (else age unknown)')
    a = ap.parse_args(argv)
    pb = json.load(open(a.port_bind))
    doc = export(a.die_v, pb, a.design, a.commit, a.src_prefix, a.local_rtl, a.plan_id, a.reach, a.skip_inst,
                 land_e=export_lanes(a.lanes))
    DRS.write(a.out, doc)
    print(f"{a.out}: {doc['design']} buses {doc['bus_count']} relays {doc['relay_instances']} max stages "
          f"{max((b['stages'] for b in doc['buses']), default=0)} problems {doc['problem_count']} {doc['digest']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
