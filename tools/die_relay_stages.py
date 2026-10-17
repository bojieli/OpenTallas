#!/usr/bin/env python3
"""opentallas.die_relay_stages.v1 -- the ONE per-bus relay-stage table shared by die plans and the compilers.

Owner rule (static fixed-cycle schedule, no on-die credits/backpressure): every die bus's relay stage count is a
compile-time constant.  So every die plan / die run EXPORTS its per-bus stages in this schema, every compiler / timing
model LOADS them from the selected plan's file (never a private literal), and tools/die_relay_check.py FAILS when a die
run's table differs from the table a compiled schedule was built against.

FILE (JSON, optionally .gz; JSON Schema: schemas/die/die_relay_stages_v1.schema.json)
  schema            "opentallas.die_relay_stages.v1"
  role              "die_plan"          table exported from a die plan / die run (generator side)
                    "compiled_schedule" table a compiler/timing model scheduled with (consumer side; see compiled())
  design            die design key of results/arch/die_reach_1016.json: hbm | s81 | qwen_compute | qwen_kv
  plan              {id, commit, generator, sources[]}   die plan / run identity (commit = source commit or null)
  clock_period_ps   relay clock period (all stages counted in this clock)
  reach_um          one-cycle relay reach the plan was made with (tools/die_reach.py; reach_source = its table)
  coverage          "complete"      every die data bus is listed (0-stage buses included) -> a missing bus is an error
                    "relayed_only"  only buses with >= 1 stage are listed (lookups of unlisted buses still FAIL)
  stage_definition  what one stage counts (default STAGE_DEFINITION)
  buses[]           one record per (source pin group -> destination pin group) edge; a multicast is one record per
                    destination with a shared eq_age_group:
     id             stable name the compiler uses: "<src.inst>.<src.port> -> <dst.inst>.<dst.port>" (bus_id())
     src, dst       {inst, port, master?}   (port may be a '+'-joined port group of one route)
     width          bits
     stages         relay flops on the path (int >= 0)      <- the compile-time constant
     domain         clock domain of the stages
     eq_age_group   null, or a group name: every member sees the group's max age (pads at near sinks)
     direction      optional flow letter(s) (WE/EW/SN/NS) or "multi"
     stations       optional [{depth, x, y, master?}] relay station homes (geometry; not part of the digest)
     span_um        optional pin-to-pin Manhattan span;  note: optional text
     bid            optional generator bus id(s) of the origin hop ('+'-joined), for generator-keyed consumers
  bus_count         len(buses)
  digest            "sha256:<hex>" of the canonical bus table [[id, width, stages, domain]...] sorted by id
  compiled          (role compiled_schedule only) {consumer, loaded_from, loaded_digest, overrides[], used_by{}}
  problems          optional list of exporter warnings (non-uniform bits, unplanned over-reach hops ...)

API
  bus_id(src_inst, src_port, dst_inst, dst_port)
  make_doc(design, plan, clock_period_ps, reach_um, buses, role='die_plan', coverage='complete', **extra) -> doc
  validate(doc) -> [errors];  write(path, doc);  load(path) -> doc (validates + re-checks the digest, fails closed)
  Table(doc)    .stages(bus_id) / .bus(bus_id) (KeyError-type MissingBus = fail closed), .match(**filters),
                .group_age(group)
  plan_path(design, path=None)  the selected plan file: explicit path, else env OT_DIE_RELAY_STAGES_<DESIGN>, else
                fail closed (no default literal stages anywhere)
  parse_overrides(list)/apply: diagnostic-only "BUS_ID=N" overrides; logged to stderr and recorded in compiled.overrides
                (die_relay_check then FAILS that bus -- overrides never qualify a schedule)
  compiled(doc, consumer, used_by=None, overrides=None, loaded_from=None, scheduled=None)
                -> role compiled_schedule doc (full table; scheduled = the constants the compiler baked in)
  trace_model(insts, buses, is_relay, thru)  generic generator-model tracer -> bus records (S81 / Qwen exporters)
"""
import copy
import gzip
import hashlib
import json
import os
import sys
from pathlib import Path

SCHEMA = 'opentallas.die_relay_stages.v1'
ROLES = ('die_plan', 'compiled_schedule')
COVERAGE = ('complete', 'relayed_only')
DESIGNS = ('hbm', 's81', 'qwen_compute', 'qwen_kv')
STAGE_DEFINITION = ('registered relay flops on the die path between the source pin and the destination pin, '
                    'excluding the source/destination tile pin registers; one stage = one clock of fixed latency')


class RelayStagesError(ValueError):
    pass


class MissingBus(RelayStagesError, KeyError):
    pass


def bus_id(src_inst, src_port, dst_inst, dst_port):
    return f'{src_inst}.{src_port} -> {dst_inst}.{dst_port}'


def _canon(buses):
    return sorted([b['id'], int(b['width']), int(b['stages']), b.get('domain')] for b in buses)


def digest(buses):
    return 'sha256:' + hashlib.sha256(json.dumps(_canon(buses), separators=(',', ':')).encode()).hexdigest()


def make_doc(design, plan, clock_period_ps, reach_um, buses, role='die_plan', coverage='complete', **extra):
    buses = sorted((dict(b) for b in buses), key=lambda b: b['id'])
    for b in buses:
        b.setdefault('id', bus_id(b['src']['inst'], b['src']['port'], b['dst']['inst'], b['dst']['port']))
        b.setdefault('eq_age_group', None)
    doc = dict(schema=SCHEMA, role=role, design=design,
               plan=dict(dict(id=None, commit=None, generator=None, sources=[]), **(plan or {})),
               clock_period_ps=float(clock_period_ps), reach_um=float(reach_um) if reach_um is not None else None,
               coverage=coverage, stage_definition=STAGE_DEFINITION)
    doc.update(extra)
    doc.update(buses=buses, bus_count=len(buses), digest=digest(buses))
    errs = validate(doc)
    if errs:
        raise RelayStagesError('invalid die_relay_stages doc: ' + '; '.join(errs[:10]))
    return doc


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def validate(doc):
    e = []
    if not isinstance(doc, dict):
        return ['document is not an object']
    if doc.get('schema') != SCHEMA:
        e.append(f"schema {doc.get('schema')!r} != {SCHEMA}")
    if doc.get('role') not in ROLES:
        e.append(f"role {doc.get('role')!r} not in {ROLES}")
    if doc.get('design') not in DESIGNS:
        e.append(f"design {doc.get('design')!r} not in {DESIGNS}")
    if doc.get('coverage') not in COVERAGE:
        e.append(f"coverage {doc.get('coverage')!r} not in {COVERAGE}")
    if not isinstance(doc.get('plan'), dict) or not doc['plan'].get('id'):
        e.append('plan.id missing')
    cp = doc.get('clock_period_ps')
    if not isinstance(cp, (int, float)) or isinstance(cp, bool) or cp <= 0:
        e.append('clock_period_ps must be > 0')
    ru = doc.get('reach_um')
    if ru is not None and (not isinstance(ru, (int, float)) or ru <= 0):
        e.append('reach_um must be > 0 or null')
    buses = doc.get('buses')
    if not isinstance(buses, list):
        return e + ['buses missing']
    seen = set()
    for i, b in enumerate(buses):
        w = f"bus[{i}] {b.get('id')!r}" if isinstance(b, dict) else f'bus[{i}]'
        if not isinstance(b, dict):
            e.append(f'{w}: not an object'); continue
        for k in ('src', 'dst'):
            if not isinstance(b.get(k), dict) or not b[k].get('inst') or not b[k].get('port'):
                e.append(f'{w}: {k}.inst/{k}.port missing')
        if not isinstance(b.get('id'), str) or not b['id']:
            e.append(f'{w}: id missing')
        elif b['id'] in seen:
            e.append(f'{w}: duplicate id')
        else:
            seen.add(b['id'])
        if not _is_int(b.get('width')) or b['width'] <= 0:
            e.append(f'{w}: width must be an int > 0')
        if not _is_int(b.get('stages')) or b['stages'] < 0:
            e.append(f'{w}: stages must be an int >= 0')
        if 'domain' not in b:
            e.append(f'{w}: domain missing (null allowed)')
        g = b.get('eq_age_group')
        if g is not None and not isinstance(g, str):
            e.append(f'{w}: eq_age_group must be a string or null')
    if doc.get('bus_count') != len(buses):
        e.append(f"bus_count {doc.get('bus_count')} != {len(buses)}")
    if not e and doc.get('digest') != digest(buses):
        e.append(f"digest {doc.get('digest')} != recomputed {digest(buses)} (bus table edited after export?)")
    if doc.get('role') == 'compiled_schedule':
        c = doc.get('compiled')
        if not isinstance(c, dict) or not c.get('consumer') or not c.get('loaded_digest'):
            e.append('compiled.consumer / compiled.loaded_digest missing')
    return e


def _read(path):
    p = Path(path)
    raw = gzip.open(p).read() if p.suffix == '.gz' else p.read_bytes()
    return json.loads(raw)


def load(path):
    p = Path(path)
    if not p.exists():
        raise RelayStagesError(f'die relay stage file missing: {p} (fail closed: no default stages)')
    doc = _read(p)
    errs = validate(doc)
    if errs:
        raise RelayStagesError(f'{p}: ' + '; '.join(errs[:10]))
    return doc


def write(path, doc):
    errs = validate(doc)
    if errs:
        raise RelayStagesError('refusing to write an invalid doc: ' + '; '.join(errs[:10]))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    txt = json.dumps(doc, indent=None, separators=(',', ':'), sort_keys=False) + '\n'
    if p.suffix == '.gz':
        with gzip.open(p, 'wt') as f:
            f.write(txt)
    else:
        p.write_text(txt)
    return p


def plan_path(design, path=None):
    """the selected plan's stage file; explicit path > env OT_DIE_RELAY_STAGES_<DESIGN>; else fail closed"""
    env = f'OT_DIE_RELAY_STAGES_{design.upper()}'
    v = path or os.environ.get(env)
    if not v:
        raise RelayStagesError(f'no die relay stage file selected for {design}: pass the plan\'s '
                               f'die_relay_stages file or set {env} (fail closed: no default stages)')
    return Path(v)


class Table:
    def __init__(self, doc, source=None):
        self.doc, self.source = doc, source
        self.by_id = {b['id']: b for b in doc['buses']}
        self.digest = doc['digest']

    @classmethod
    def from_file(cls, path):
        return cls(load(path), str(path))

    def bus(self, bid):
        b = self.by_id.get(bid)
        if b is None:
            raise MissingBus(f'bus {bid!r} not in die relay stage table {self.source or self.doc["plan"]["id"]} '
                             f'(design {self.doc["design"]}, coverage {self.doc["coverage"]}): fail closed')
        return b

    def stages(self, bid):
        return self.bus(bid)['stages']

    def match(self, **f):
        """buses whose fields match: src_inst/src_port/src_master/dst_inst/dst_port/dst_master (exact, or a callable),
        port filters also accept one member of a '+'-joined port group"""
        out = []
        for b in self.doc['buses']:
            ok = True
            for k, want in f.items():
                side, fld = k.split('_', 1)
                have = b[side].get(fld)
                if callable(want):
                    ok = bool(want(have))
                elif fld == 'port':
                    ok = have == want or want in (have or '').split('+')
                else:
                    ok = have == want
                if not ok:
                    break
            if ok:
                out.append(b)
        return out

    def group_age(self, group):
        m = [b['stages'] for b in self.doc['buses'] if b.get('eq_age_group') == group]
        if not m:
            raise MissingBus(f'eq_age_group {group!r} not in table')
        return max(m)


def parse_overrides(items):
    out = {}
    for s in items or []:
        if '=' not in s:
            raise RelayStagesError(f'override {s!r}: expected BUS_ID=N')
        k, v = s.rsplit('=', 1)
        out[k.strip()] = int(v)
    return out


def compiled(doc, consumer, used_by=None, overrides=None, loaded_from=None, scheduled=None):
    """the compiled-schedule side: the full table the consumer scheduled with (+ who used which bus).
    scheduled = {bus id: stages} the compiler actually baked in (e.g. RTL latency parameters): substituted, so any
    difference from the plan shows up as a die_relay_check stage diff; overrides = diagnostic replacements, applied,
    logged AND recorded (die_relay_check fails them)"""
    overrides = dict(overrides or {})
    scheduled = dict(scheduled or {})
    buses = copy.deepcopy(doc['buses'])
    ids = {b['id'] for b in buses}
    bad = [k for k in list(overrides) + list(scheduled) if k not in ids]
    if bad:
        raise MissingBus(f'scheduled/override value for bus(es) not in the plan {bad[:5]} (fail closed)')
    rec = []
    for b in buses:
        if b['id'] in scheduled:
            b['stages'] = int(scheduled[b['id']])
        if b['id'] in overrides:
            rec.append(dict(bus=b['id'], plan_stages=b['stages'], used_stages=overrides[b['id']]))
            print(f'die_relay_stages: DIAGNOSTIC OVERRIDE {b["id"]}: plan {b["stages"]} -> {overrides[b["id"]]} '
                  '(this schedule cannot pass die_relay_check)', file=sys.stderr)
            b['stages'] = overrides[b['id']]
    extra = {k: v for k, v in doc.items() if k not in ('schema', 'role', 'design', 'plan', 'clock_period_ps', 'reach_um',
                                                       'coverage', 'stage_definition', 'buses', 'bus_count', 'digest',
                                                       'compiled', 'problems')}
    out = make_doc(doc['design'], doc['plan'], doc['clock_period_ps'], doc['reach_um'], buses,
                   role='compiled_schedule', coverage=doc['coverage'],
                   compiled=dict(consumer=consumer, loaded_from=str(loaded_from) if loaded_from else None,
                                 loaded_digest=doc['digest'], overrides=rec,
                                 used_by={k: sorted(set(v)) for k, v in (used_by or {}).items()}), **extra)
    return out


def trace_model(insts, buses, is_relay, thru, port_base=None, skip_cls=('clock', 'clock_trunk', 'reset', 'constant'),
                relay_control=None):
    """Generic die-model tracer shared by the generator exporters (S81, Qwen compute, Qwen KV).

    insts     {name: {master, kind, domain}}
    buses     iterable of (bid, cls, bits, eps) with eps = [(inst, port), ...], driver first (the generators' m['buses'])
    is_relay  name -> bool (a registered relay / station instance: one stage)
    thru      (inst, port_base) -> output port_base of that relay input, or None (the pin is a terminal load)
    relay_control (inst, port_base) -> True for a relay's own control input (enable / select): a terminal, not a finding
    -> (bus records for make_doc, problems): one record per (origin inst.port -> terminal inst.port) pin pair, stages =
       relay instances walked; width = bits of the distinct last-hop buses; bid = the origin generator bus id(s)."""
    pb = port_base or (lambda p: p)
    outs = {}
    for bid, cls, bits, eps in buses:
        if cls in skip_cls or len(eps) < 2:
            continue
        d = (eps[0][0], pb(eps[0][1]))
        outs.setdefault(d, []).append((bid, bits, [(e[0], e[1]) for e in eps[1:]]))
    pairs, problems = {}, []
    for (di, dp), lst in outs.items():
        if is_relay(di):
            continue
        for obid, obits, oloads in lst:
            stack = [(obid, obits, oloads, 0, frozenset())]
            while stack:
                bid, bits, loads, n, seen = stack.pop()
                for li, lp in loads:
                    lb = pb(lp)
                    o = thru(li, lb) if is_relay(li) else None
                    if o is not None:
                        key = (li, o)
                        if key in seen:
                            problems.append(f'relay loop at {li}.{o} from {di}.{dp}'); continue
                        nxt = outs.get(key)
                        if not nxt:
                            problems.append(f'relay {li}.{o} drives nothing (chain from {di}.{dp} ends)'); continue
                        for b2, bits2, l2 in nxt:
                            stack.append((b2, bits2, l2, n + 1, seen | {key}))
                        continue
                    if is_relay(li) and not (relay_control and relay_control(li, lb)):
                        problems.append(f'relay input {li}.{lb} has no pass-through (terminal, from {di}.{dp})')
                    r = pairs.setdefault((di, dp, li, lb), dict(st=set(), last={}, bids=set()))
                    r['st'].add(n); r['last'][bid] = bits; r['bids'].add(obid)
    recs = []
    for (di, dp, li, lb), r in sorted(pairs.items()):
        bid = bus_id(di, dp, li, lb)
        if len(r['st']) > 1:
            problems.append(f'{bid}: paths with different stages {sorted(r["st"])} (max taken)')
        i0, i1 = insts.get(di, {}), insts.get(li, {})
        recs.append(dict(id=bid, src=dict(inst=di, port=dp, master=i0.get('master')),
                         dst=dict(inst=li, port=lb, master=i1.get('master')),
                         width=max(1, sum(r['last'].values())), stages=max(r['st']), domain=i0.get('domain'),
                         eq_age_group=None, bid='+'.join(sorted(r['bids']))))
    return recs, problems


if __name__ == '__main__':
    for p in sys.argv[1:]:
        d = load(p)
        print(f"{p}: {d['design']} {d['role']} plan {d['plan']['id']} buses {d['bus_count']} "
              f"max stages {max((b['stages'] for b in d['buses']), default=0)} {d['digest']}")
