"""Source-exact parallel result writeback graph for join961w.

The issuer taps existing TT numeric bits and fans 42 command bits to three
parallel serializers. TRAIN_EDGES is explicitly unassigned until actual route
ages exist. Candidate sites and pins carry no physical qualification credit.
"""
import hashlib
import json
from pathlib import Path

from qwen_split.source_pin_plan import rtl_ports

ROOT = Path(__file__).resolve().parents[2]
SOURCE = 'rtl/qwen_split/qfd_sp_res_train_par.sv'
ISSUE_SOURCE = 'rtl/qwen_split/qfd_res_train_issue.sv'
ISSUE_MASTER = 'qfd_res_train_issue'
ISSUE = 'res_train_issue'
ISSUE_WH = (129.6, 129.6)
VM_MASTER = 'qfd_sp_vector_memory_par'
VM_SOURCE = 'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory_par.sv'
TT_SOURCE = 'rtl/qwen_sys/static_schedule_20261014/qfd_tt_ctlm_static_s.sv'
TAPS = {'me_go': ('ib', 0, 0), 'me_tiles': ('ib', 19, 36),
        'me_ts': ('ib', 80, 103), 'me_split': ('ib', 251, 254),
        'me_oen': ('ib', 353, 353), 'tag_v': ('c1', 26, 26),
        'tag_last': ('c1', 139, 139)}
LEGACY = 'qfd_sp_res_ser'
BANDS = 3
CLOCKS = ['ck'] + [f'ck_bank{k}' for k in range(24)]
RENAME = {'i': 'rq', 'o': 'rb'}
COMMAND = ('train_start', 'train_count', 'capture_stride', 'payload_write', 'slot_count')


def master(b):
    return f'qfd_sp_res_train_par_{b}'


def mapped_inventory(core_sha256, slot):
    """Preserve the static-bank census as historical evidence, never as a parallel fit claim."""
    base = ROOT / 'results/arch/qwen_res_train_physical_1015'
    return dict(status='stale_architecture', qualified=False,
                why='static qfd_res_train_static inventory predates parallel qfd_res_train_par / join961w',
                historical_records=[str(p.relative_to(ROOT)) for p in sorted(base.glob('inventory_band*.json'))],
                current_core_sha256=core_sha256, requested_slot_um=slot)


def _tap_tt(model, by, issue_ports):
    """Partition existing nets at tap boundaries; fan out each source bit exactly once.

    Every peer slice moves with the matching numeric source bit. A tap can span
    several old segments, in which case the issue input is partitioned too.
    """
    from qwen_split.native_graph_bind import _segments
    tt = by['tt_ctlm']
    tp = rtl_ports(ROOT / TT_SOURCE, tt.master)
    aliases = model.setdefault('port_join', {})
    ta = aliases.setdefault(tt.master, {})
    ia = aliases.setdefault(ISSUE_MASTER, {})
    for sink, (real, lo, hi) in TAPS.items():
        if tp.get(real, (0, None))[1] != 'output' or hi >= tp[real][0]:
            raise ValueError(f'res train issue source {real}[{hi}:{lo}] missing')
        if issue_ports.get(sink) != (hi-lo+1, 'input'):
            raise ValueError(f'res train issue input {sink} ABI mismatch')
    affected = {v[0] for v in TAPS.values()}
    import copy
    snapshots = copy.deepcopy(aliases)
    old_alias = dict(ta)
    retired_aliases = set()
    # All aliases of a real port form its complete physical pin partition.
    for a, (real, bits) in list(ta.items()):
        if real in affected:
            del ta[a]
    def resolve(inst, port, width):
        real, bits = snapshots.get(by[inst].master, {}).get(port, (port, list(range(width))))
        if inst == tt.name and port in old_alias:
            real, bits = old_alias[port]
        if len(bits) != width or len(bits) != len(set(bits)):
            raise ValueError(f'res train issue malformed endpoint {inst}.{port}')
        return real, list(bits)
    def alias(inst, real, bits):
        rp = tp if inst == tt.name else (issue_ports if inst == ISSUE else None)
        if rp is not None and len(bits) == rp[real][0] and bits == list(range(len(bits))):
            return real
        name = f'{real}__{bits[0]}_{bits[-1]}'
        amap = aliases.setdefault(by[inst].master, {})
        value = (real, bits)
        if name in amap and amap[name] != value:
            raise ValueError(f'res train issue alias collision {inst}.{name}')
        amap[name] = value
        return name
    coverage = {real: set() for real in affected}
    out = []
    for bus, cls, width, es in model['buses']:
        sources = [(p, resolve(i, p, width)) for i, p in es if i == tt.name]
        sources = [(p, rb) for p, rb in sources if rb[0] in affected]
        if not sources:
            out.append((bus, cls, width, es)); continue
        if len(sources) != 1:
            raise ValueError(f'res train issue duplicate TT source on {bus}')
        source_port, (real, bits) = sources[0]
        if bits != list(range(bits[0], bits[-1]+1)) or coverage[real].intersection(bits):
            raise ValueError(f'res train issue overlapping/noncontiguous TT source {bus}')
        coverage[real].update(bits)
        cuts = {0, width}
        for sink, (src, lo, hi) in TAPS.items():
            if src == real:
                cuts.update(k-bits[0] for k in (lo, hi+1) if bits[0] < k <= bits[-1])
        cuts = sorted(cuts)
        for a, z in zip(cuts, cuts[1:]):
            sbits = bits[a:z]
            eps = []
            for inst, port in es:
                er, eb = resolve(inst, port, width)
                if (a, z) != (0, width) and port in snapshots.get(by[inst].master, {}):
                    retired_aliases.add((by[inst].master, port))
                eps.append((inst, alias(inst, er, eb[a:z])))
            for sink, (src, lo, hi) in TAPS.items():
                if src == real and lo <= sbits[0] and sbits[-1] <= hi:
                    eps.append((ISSUE, alias(ISSUE, sink, [k-lo for k in sbits])))
            out.append((f'{bus}__rsi_{a}', cls, z-a, eps))
    # The TT's ib is an external output in actual_join.json. Expose its
    # unconnected segments as real source nets, including unused physical pins.
    for real in affected:
        missing = set(range(tp[real][0])) - coverage[real]
        selects = [(lo, hi) for src, lo, hi in TAPS.values() if src == real]
        # Existing coverage boundaries must also cut the partition.
        selects += [(k, k) for k in coverage[real]]
        for lo, hi in _segments(tp[real][0], selects):
            bits = list(range(lo, hi+1))
            if not set(bits) <= missing: continue
            eps = [(tt.name, alias(tt.name, real, bits))]
            for sink, (src, a, z) in TAPS.items():
                if src == real and a <= lo and hi <= z:
                    eps.append((ISSUE, alias(ISSUE, sink, [k-a for k in bits])))
            # Singleton source segments retain physical aliases; omit unused nets.
            if len(eps) > 1:
                out.append((f'rsi_tt_{real}_{lo}', 'spine_local', hi-lo+1, eps))
    used = {(by[i].master, p) for _, _, _, es in out for i,p in es}
    for mst, port in retired_aliases - used:
        aliases[mst].pop(port, None)
    model['buses'] = out
    receipt = model.get('native_control_contract')
    if receipt:
        connected = {aliases.get(tt.master, {}).get(p, (p, []))[0]
                     for _, _, _, es in out for i,p in es if i==tt.name}
        receipt['unread_outputs'] = sorted(p for p,(w,d) in tp.items()
                                          if d=='output' and p not in connected)


def _issue(model):
    from qwen_split.native_graph_bind import _free_site
    by = {i.name: i for i in model['insts']}
    if ISSUE in by:
        raise ValueError('res train issue already present')
    tt, su = by['tt_ctlm'], by['sp_su64_sfu']
    wh = ISSUE_WH
    target = ((tt.x + tt.w/2 + su.x + su.w/2)/2,
              (tt.y + tt.h/2 + su.y + su.h/2)/2)
    x, y = _free_site(model, wh, target, model['die'])
    Inst = type(tt)
    inst = Inst(ISSUE, ISSUE_MASTER, x, y, *wh, 'R0',
                kind=getattr(tt, 'kind', None), region=getattr(tt, 'region', None),
                domain=getattr(tt, 'domain', None))
    model['insts'].append(inst)
    by[ISSUE] = inst
    ports = rtl_ports(ROOT / ISSUE_SOURCE, ISSUE_MASTER)
    _tap_tt(model, by, ports)
    for p in COMMAND:
        width, direction = ports[p]
        if direction != 'output':
            raise ValueError(f'res train issue {p} must be an output')
        model['buses'].append((f'rsi_{p}', 'spine_local', width,
                               [(ISSUE, p)] + [(f'sp_res_ser_{b}', p) for b in range(BANDS)]))
    for cls, port in [('clock_trunk', 'ck'), ('reset', 'rst_n')]:
        candidates = [j for j, (bus, c, n, es) in enumerate(model['buses'])
                      if c == cls and any(i == tt.name and
                          (p == 'ck_me_sched' if cls == 'clock_trunk' else p == 'rsi') for i, p in es)]
        if len(candidates) != 1:
            raise ValueError(f'res train issue needs one explicit TT {cls} trunk')
        j = candidates[0]
        bus, c, n, es = model['buses'][j]
        model['buses'][j] = (bus, c, n, es + [(ISSUE, port)])
    return dict(instance=ISSUE, master=ISSUE_MASTER, source=ISSUE_SOURCE,
                source_sha256=hashlib.sha256((ROOT / ISSUE_SOURCE).read_bytes()).hexdigest(),
                frame_um=[x, y, *wh], status='NEW unclosed parent; candidate site and assigned source pins only',
                command_bits=sum(ports[p][0] for p in COMMAND),
                source_selects={p: dict(instance=tt.name, port=r, bits=list(range(a,z+1)))
                                for p,(r,a,z) in TAPS.items()},
                fault=dict(status='OPEN', port='fault', why='join961w exposes rsi_fault; no actual on-die consumer'),
                TRAIN_EDGES=None, route_age_status='explicitly unassigned; source-only graph cannot elaborate issuer',
                route_age_requirement='derive tag -> port -> port-tile -> serializer capture edges from actual assigned route; >=2',
                qualified=False)


def apply(model):
    by = {i.name: i for i in model['insts']}
    sers = {f'sp_res_ser_{b}': b for b in range(BANDS)}
    for n in sers:
        if n not in by or by[n].master != LEGACY:
            raise ValueError(f'res train bind needs the legacy {n} ({LEGACY})')
    ports = {b: rtl_ports(ROOT / SOURCE, master(b)) for b in range(BANDS)}
    for n, b in sers.items():
        by[n].master = master(b)
    out, retired = [], []
    for bus, c, nb, es in model['buses']:
        names = [i for i, _ in es]
        if not any(i in sers for i in names):
            out.append((bus, c, nb, es))
            continue
        if c == 'clock_trunk':
            e2 = []
            for i, p in es:
                if i in sers and p in ('ck', 'clk'):
                    e2 += [(i, q) for q in CLOCKS if (i, q) not in e2]
                elif i in sers and p.startswith('ck'):
                    if (i, p) not in e2:
                        e2.append((i, p))
                else:
                    e2.append((i, p))
            out.append((bus, c, nb, e2))
            continue
        if c == 'reset' or bus.startswith('rst_'):
            out.append((bus, c, nb, es))
            continue
        if any(i in sers and p == 'me_en' for i, p in es):
            retired.append(bus)
            continue
        es = [(i, RENAME.get(p, p)) if i in sers else (i, p) for i, p in es]
        for i, p in es:
            if i in sers:
                n_src = ports[sers[i]].get(p)
                if n_src is None:
                    raise ValueError(f'res train bind: {i}.{p} is not a source port')
                if n_src[0] != nb:
                    raise ValueError(f'res train bind: {bus} is {nb} b but {i}.{p} is {n_src[0]} b')
        out.append((bus, c, nb, es))
    model['buses'] = out
    issue = _issue(model)
    vm = by['sp_vector_memory']
    old_vm = vm.master
    if old_vm != 'qfd_sp_vector_memory':
        raise ValueError(f'res train bind needs actual legacy VM source master, got {old_vm}')
    vm_ports = rtl_ports(ROOT / VM_SOURCE, VM_MASTER)
    old_ports = rtl_ports(ROOT / 'rtl/qwen_sys/vm_nox_20261014/qfd_sp_vector_memory.sv', old_vm)
    if vm_ports != old_ports:
        raise ValueError('parallel VM wrapper differs from actual VM numeric ABI')
    aliases = model.setdefault('port_join', {})
    if VM_MASTER in aliases:
        raise ValueError('parallel VM alias namespace already present')
    aliases[VM_MASTER] = aliases.pop(old_vm, {})
    vm.master = VM_MASTER
    conn = {}
    for bus, c, nb, es in model['buses']:
        for i, p in es:
            if i in sers:
                conn.setdefault(i, set()).add(p)
    for n, b in sers.items():
        unknown = sorted(conn.get(n, set()) - set(ports[b]))
        if unknown:
            raise ValueError(f'res train bind: {n} non-source endpoints {unknown}')
        need = {'rq', 'rb', 'fault', 'rst_n', *CLOCKS, *COMMAND}
        if need - conn.get(n, set()):
            raise ValueError(f'res train bind: {n} missing {sorted(need - conn.get(n, set()))}')
    rec = dict(masters=[master(b) for b in range(BANDS)], source=SOURCE,
               source_sha256=hashlib.sha256((ROOT / SOURCE).read_bytes()).hexdigest(),
               core='rtl/qwen_split/qfd_res_train_par.sv',
               core_sha256=hashlib.sha256((ROOT / 'rtl/qwen_split/qfd_res_train_par.sv').read_bytes()).hexdigest(),
               decision='Q-VMWB parallel-band writeback join961w', issue=issue,
               vm_contract=dict(master=VM_MASTER, source=VM_SOURCE, PAR_RB=1,
                                source_sha256=hashlib.sha256((ROOT / VM_SOURCE).read_bytes()).hexdigest(),
                                status='actual specialized source fixes PAR_RB=1; NEW unclosed physical master'),
               retired=dict(master=LEGACY, buses=retired),
               open_inputs={n: sorted(p for p, (w, d) in ports[b].items() if d == 'input' and p not in conn[n])
                            for n, b in sers.items()},
               open_owner='issuer fault consumer and physical TRAIN_EDGES assignment remain OPEN',
               slot_um=[round(by['sp_res_ser_0'].w, 3), round(by['sp_res_ser_0'].h, 3)],
               slot_note='legacy serializer frame retained as candidate only; static inventory is stale; parallel area/route/native qualification OPEN',
               qualified=False)
    rec['mapped_inventory'] = mapped_inventory(rec['core_sha256'], rec['slot_um'])
    model['res_train_bind'] = rec
    return rec


def install_masters(M, model, Master, partition_master):
    if 'res_train_bind' not in model:
        return
    from qwen_split.native_graph_bind import assign_pins, peer_map
    by = {i.name: i for i in model['insts']}
    peers = peer_map(model)
    for b in range(BANDS):
        assign_pins(M, model, Master, by[f'sp_res_ser_{b}'], master(b), SOURCE, peers, partition_master)
    assign_pins(M, model, Master, by[ISSUE], ISSUE_MASTER, ISSUE_SOURCE, peers, partition_master)
    M.pop(LEGACY, None)
    for b in range(BANDS):
        M.pop(f'qfd_sp_res_train_{b}', None)
    validate_case_masters(M, model)


def validate_case_masters(M, model):
    if not model.get('res_train_bind'):
        return
    if LEGACY in M:
        raise ValueError('res train bind: legacy qfd_sp_res_ser master still generated')
    for mn, src in [(master(b), SOURCE) for b in range(BANDS)] + [(ISSUE_MASTER, ISSUE_SOURCE)]:
        if mn not in M:
            raise ValueError(f'res train bind: {mn} missing from the generated masters')
        rp = rtl_ports(ROOT / src, mn)
        aliases = model.get('port_join', {}).get(mn, {})
        covered = {r for r, bits in aliases.values()}
        expected = {p: w for p, (w,d) in rp.items() if p not in covered}
        expected.update({a:len(bits) for a,(r,bits) in aliases.items()})
        if {p:s[1] for p,s in M[mn].ports.items()} != expected:
            raise ValueError(f'res train bind: {mn} ports disagree with the actual RTL')
        for real in covered:
            bits = [b for r,bs in aliases.values() if r==real for b in bs]
            if sorted(bits) != list(range(rp[real][0])):
                raise ValueError(f'res train bind: {mn}.{real} alias partition incomplete/overlapping')
