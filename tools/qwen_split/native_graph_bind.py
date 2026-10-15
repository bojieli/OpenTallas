"""Bind the compute-die spine graph to the actual source join (tt / seq / su / vm / native59 / io / embed).

The die graph of the controller, sequencer, SU, VM and collective still carried historical abstract words (SU q / eq /
ea / ecr / q_cr / ckx, VM ar_cr / rc / rk, sequencer credit cd_cr).  The source join
results/arch/qwen_split_compute_1014/native_join/actual_join.json (69 real source-output -> source-input edges, the
950-root hierarchy that elaborates on main) is the truth: this module replaces every die bus between those seven
nodes by the join's edges, adds the two masters the die lacked (qfd_native59_compute_service, the static embedding
core provider) as NEW unclosed parents, swaps the sequencer to qfd_seq_su_static, gives every node its real clock /
reset roots, and assigns top-down pins from the RTL port lists (no overlap, per face toward the peer).

Inputs without a producer on the compute die (HOST / calendar slots, KV-die link payloads, embedding beats) stay
unconnected and are enumerated; nothing is tied.  The io node is the static production collective
(native_static_io_bind) with the same command / data / return ports as the join's internal parent.
"""
import hashlib
import json
from pathlib import Path

from qwen_split.source_pin_plan import rtl_ports

ROOT = Path(__file__).resolve().parents[2]
JOIN = 'results/arch/qwen_split_compute_1014/native_join/actual_join.json'
INST = dict(tt='tt_ctlm', seq='seq_su', su='sp_su64_sfu', vm='sp_vector_memory', io='io_collective',
            native='native59', embed='embed_prov')
MASTER = dict(seq=('qfd_seq_su_static', 'rtl/qwen_split/qfd_seq_su_static.sv'),
              su=('qfd_sp_su64_sfu', 'rtl/qwen_split/qfd_sp_su64_sfu.sv'),
              native=('qfd_native59_compute_service', 'rtl/qwen_split/qfd_native59_compute_service.sv'),
              embed=('qkd_embedding_static_core_provider',
                     'rtl/qwen_sys/static_embedding_20261014/qkd_embedding_static_core_provider.sv'))
# NEW parents: native59 site request (Codex C15 candidate frame 777.6 x 518.4: 11,717 FF, 6 roots); the embedding
# provider = one ot_sram_1r1w_64x512_m1_r2c2 (171.3 x 77.8) + the beat / epoch faces
NEW_WH = dict(native=(777.6, 518.4), embed=(259.2, 216.0))
HALO = 4.32
OWNED = ('tt', 'seq', 'su', 'vm', 'io')       # die masters these edges replace (the io node's die master is static)


def _free_site(model, wh, target, die):
    """Nearest legal site (grid 2.16 um, halo 4.32) to target that overlaps no instance and stays inside the die."""
    rects = [(i.x - HALO, i.y - HALO, i.x + i.w + HALO, i.y + i.h + HALO) for i in model['insts']]
    w, h = wh
    best = None
    tx, ty = target
    for r in range(0, 4000, 2):
        step = 4.32 * 5
        cand = []
        for dx in range(-r, r + 1):
            for dy in (-r, r) if abs(dx) != r else range(-r, r + 1):
                cand.append((tx - w / 2 + dx * step, ty - h / 2 + dy * step))
        for x, y in cand:
            x, y = round(round(x / 2.16) * 2.16, 4), round(round(y / 2.16) * 2.16, 4)
            if x < 30 or y < 30 or x + w > die['w'] - 30 or y + h > die['h'] - 30:
                continue
            if any(x < c and a < x + w and y < d and b < y + h for a, b, c, d in rects):
                continue
            dist = abs(x + w / 2 - tx) + abs(y + h / 2 - ty)
            if best is None or dist < best[0]:
                best = (dist, x, y)
        if best is not None and best[0] < (r + 1) * step:
            return best[1], best[2]
    raise ValueError(f'no free {wh} site near {target}')


def _segments(width, selects):
    cuts = {0, width}
    for lo, hi in selects:
        cuts |= {lo, hi + 1}
    cuts = sorted(cuts)
    return [(a, b - 1) for a, b in zip(cuts, cuts[1:])]


def apply(model):
    j = json.loads((ROOT / JOIN).read_text())
    nodes = j['nodes']
    by = {i.name: i for i in model['insts']}
    if 'native_static_io_bind' not in model:
        raise ValueError('native graph bind requires the static IO bind (io node = static production collective)')
    for k, inst in INST.items():
        if k in ('native', 'embed'):
            continue
        if inst not in by:
            raise ValueError(f'native graph: die instance {inst} missing')
    for k, (mst, src) in MASTER.items():
        if k in ('native', 'embed'):
            continue
        by[INST[k]].master = mst
    # NEW parents at their nearest free sites: native59 between the SU and the VM / tt it serves, the embedding
    # provider beside the sequencer it answers
    Inst = type(by['seq_su'])
    su, vm, seq = by['sp_su64_sfu'], by['sp_vector_memory'], by['seq_su']
    targets = dict(native=(vm.x + vm.w + NEW_WH['native'][0] / 2 + HALO, vm.y + vm.h / 2),
                   embed=(seq.x + seq.w / 2, seq.y - NEW_WH['embed'][1] / 2 - HALO))
    for k in ('native', 'embed'):
        x, y = _free_site(model, NEW_WH[k], targets[k], model['die'])
        model['insts'].append(Inst(INST[k], MASTER[k][0], x, y, NEW_WH[k][0], NEW_WH[k][1], 'R0',
                                   kind=getattr(seq, 'kind', None), region=getattr(seq, 'region', None),
                                   domain=getattr(seq, 'domain', None)))
    by = {i.name: i for i in model['insts']}
    ports = {k: {p: (v['bits'], v['direction']) for p, v in nodes[k]['ports'].items()} for k in nodes}
    io_master = by['io_collective'].master
    ports['io'] = {p: (n, d) for p, (n, d) in rtl_ports(ROOT / 'rtl/physical/ot_qfd_collective_static_io_production.sv',
                                                            io_master).items()}
    for k, (mst, src) in MASTER.items():
        rp = rtl_ports(ROOT / src, mst)
        bad = {p for p in ports[k] if rp.get(p) != ports[k][p]}
        if bad:
            raise ValueError(f'native graph: join node {k} differs from {src}: {sorted(bad)[:8]}')
    node_of = {v: k for k, v in INST.items()}
    # ---- remove every historical functional bus among the seven nodes and every bus on a port the RTL lacks
    removed, kept = [], []
    for b, c, n, es in model['buses']:
        if c in ('clock_trunk', 'reset'):
            kept.append((b, c, n, es))
            continue
        inside = [node_of.get(i) for i, _ in es]
        legacy = any(k in ports and p.lstrip('*') not in ports[k] and k != 'io' for (i, p), k in zip(es, inside))
        if (all(k is not None for k in inside) and any(k in OWNED for k in inside)) or legacy:
            if 'io' in inside and b.startswith(('coll_', 'ucie_', 'serdes')):
                if b in ('coll_cd', 'coll_cc'):
                    removed.append(b)
                    continue
                kept.append((b, c, n, es))
                continue
            removed.append(b)
            continue
        kept.append((b, c, n, es))
    # the io node's command / data / return ports move from the static IO bind's split to the join's slices
    model.get('port_split', {}).pop(io_master, None)
    join_alias = model.setdefault('port_join', {})
    new = []
    edges = list(j['directed_edges'])
    # sink-side assemblies (seq.cc <- io out_*) name the sink bits explicitly
    sink_sel = {}
    for a in j['assemblies']:
        for part in a['parts']:
            sink_sel[(tuple(part['source']), tuple(a['sink']))] = tuple(sorted(part['sink_select']))
    # source ports: elementary segments over every select of that port
    by_src = {}
    for e in edges:
        by_src.setdefault(tuple(e['source']), []).append(e)
    alias_ct = {}

    def alias(k, port, lo, hi):
        n = ports[k][port][0]
        if (lo, hi) == (0, n - 1):
            return port
        name = f'{port}__{lo}_{hi}'
        join_alias.setdefault(by[INST[k]].master, {})[name] = (port, list(range(lo, hi + 1)))
        alias_ct[(k, port)] = alias_ct.get((k, port), 0) + 1
        return name
    for (sk, sp), es in by_src.items():
        n = ports[sk][sp][0]
        sels = [tuple(sorted(e['source_select'])) if e['source_select'] else (0, n - 1) for e in es]
        for lo, hi in _segments(n, sels):
            src_name = alias(sk, sp, lo, hi)
            eps = [(INST[sk], src_name)]
            for e, (slo, shi) in zip(es, sels):
                if not (slo <= lo and hi <= shi):
                    continue
                tk, tp = e['sink']
                tn = ports[tk][tp][0]
                sel = sink_sel.get(((sk, sp), (tk, tp)))
                if sel is not None:                       # assembly part: sink bits named by the join
                    tlo = sel[0] + (lo - slo)
                elif tn == n or e['source_select']:
                    tlo = (lo - slo) if tn != n else lo
                else:
                    raise ValueError(f'native graph: width {sp}{n} -> {tp}{tn} without a select')
                thi = tlo + (hi - lo)
                eps.append((INST[tk], alias(tk, tp, tlo, thi)))
            cls = 'spine_local'
            new.append((f'ng_{sk}_{sp}_{lo}', cls, hi - lo + 1, eps))
    # ---- clocks and resets: every node root on the trunk / reset bus that already serves the node (new nodes:
    # the sequencer's); the io node keeps the static IO bind's trunks
    clk_of = {k: [x['port'] for x in j['external_ports'] if x['node'] == k and x['role'] == 'clock'] for k in nodes}
    rst_of = {k: [x['port'] for x in j['external_ports'] if x['node'] == k and x['role'] == 'reset'] for k in nodes}
    trunk_of, reset_of = {}, {}
    for b, c, n, es in kept:
        for i, p in es:
            k = node_of.get(i)
            if k is None:
                continue
            if c == 'clock_trunk':
                trunk_of.setdefault(k, b)
            elif c == 'reset':
                reset_of.setdefault(k, b)
    for k in ('native', 'embed'):
        trunk_of[k] = trunk_of['seq']
        reset_of[k] = reset_of.get('seq') or reset_of['su']
    out = []
    for b, c, n, es in kept:
        if c == 'clock_trunk':
            es = [(i, p) for i, p in es if node_of.get(i) in (None, 'io', 'tt', 'vm')]
            es += [(INST[k], p) for k in ('seq', 'su', 'native', 'embed') if trunk_of.get(k) == b for p in clk_of[k]]
        elif c == 'reset':
            es = [(i, p) for i, p in es if node_of.get(i) in (None, 'io', 'tt', 'vm')]
            es += [(INST[k], p) for k in ('seq', 'su', 'native', 'embed') if reset_of.get(k) == b for p in rst_of[k]]
        out.append((b, c, n, es))
    model['buses'] = out + new
    for k in ('seq', 'su', 'native', 'embed'):
        if k not in trunk_of or k not in reset_of:
            raise ValueError(f'native graph: node {k} has no clock trunk / reset bus')
    # ---- enumerate what stays open
    conn = {}
    for b, c, n, es in model['buses']:
        for i, p in es:
            k = node_of.get(i)
            if k is None:
                continue
            real = join_alias.get(by[i].master, {}).get(p, (p, None))[0]
            conn.setdefault(k, set()).add(real)
    tied = {(i, p) for i, p, n, v in model.get('ties', [])}
    open_in = {k: sorted(p for p, (n, d) in ports[k].items() if d == 'input' and p not in conn.get(k, set())
                         and (INST[k], p) not in tied) for k in nodes}
    rec = dict(join=JOIN, join_sha256=hashlib.sha256((ROOT / JOIN).read_bytes()).hexdigest(),
               instances=INST, masters={k: by[INST[k]].master for k in INST},
               new_parents={k: dict(inst=INST[k], frame=[by[INST[k]].x, by[INST[k]].y, *NEW_WH[k]],
                                    status='NEW unclosed parent; site request, no physical view') for k in NEW_WH},
               removed_buses=removed, added_buses=len(new), edges=len(edges),
               open_inputs={k: v for k, v in open_in.items() if v},
               clock_roots={k: len(clk_of[k]) for k in nodes},
               qualified=False)
    model['native_graph_bind'] = rec
    return rec


def install_masters(M, model, Master, pin_rects):
    """Assigned pins for seq / su / native / embed: every port on the face toward its die peer (centroid of the
    other endpoints), packed without overlap at 0.096 um (E/W on M4, N/S on M5) around the peer's projection."""
    rec = model.get('native_graph_bind')
    if not rec:
        return
    by = {i.name: i for i in model['insts']}
    peers = {}
    for b, c, n, es in model['buses']:
        if c in ('clock_trunk', 'reset'):
            continue
        for i, p in es:
            others = [by[x] for x, _ in es if x != i]
            if others:
                peers.setdefault((i, p), []).extend(others)
    from qwen_split.direct_up4 import partition_master
    for k in ('seq', 'su', 'native', 'embed'):
        assign_pins(M, model, Master, by[INST[k]], MASTER[k][0], MASTER[k][1], peers, partition_master)
        M.pop('qfd_seq_su', None)
    _vm_alias(M, model, by, pin_rects, partition_master)
    rec['assigned_pins'] = {k: MASTER[k][0] for k in ('seq', 'su', 'native', 'embed')}


def peer_map(model):
    by = {i.name: i for i in model['insts']}
    peers = {}
    for b, c, n, es in model['buses']:
        if c in ('clock_trunk', 'reset'):
            continue
        for i, p in es:
            others = [by[x] for x, _ in es if x != i]
            if others:
                peers.setdefault((i, p), []).extend(others)
    return peers


def assign_pins(M, model, Master, inst, mst, src, peers, partition_master):
    """Top-down pins of one NEW unclosed parent from its RTL port list, each port on the face toward its peers."""
    if True:
        orientation = getattr(inst, 'orient', 'R0')
        if orientation not in ('R0', 'MX', 'MY', 'R180'):
            raise ValueError(f'{mst}: unsupported pin-assignment orientation {orientation}')
        conflicts = [i.name for i in model.get('insts', [])
                     if i.name != inst.name and i.master == mst and
                     (getattr(i, 'orient', 'R0') != orientation or
                      (i.w, i.h) != (inst.w, inst.h))]
        if conflicts:
            raise ValueError(f'{mst}: incompatible shared-master orientation/outline; '
                             f'clone physical masters for {inst.name} and {conflicts}')
        rp = rtl_ports(ROOT / src, mst)
        q = Master(mst, inst.w, inst.h, 7, f'actual source ABI ({src}); NEW assigned unclosed parent')
        aliases = model.get('port_join', {}).get(mst, {})
        # die-level names: aliases replace their real port; other real ports stay whole
        die_ports = {a: (len(bits), real) for a, (real, bits) in aliases.items()}
        covered = {real for _, (_, real) in die_ports.items()}
        for p, (n, d) in rp.items():
            if p not in covered:
                die_ports[p] = (n, p)
        want = {}
        for p in die_ports:
            ps = peers.get((inst.name, p))
            if not ps or p.startswith('ck') or p in ('rst_n', 'rsi'):
                want[p] = ('N', inst.w / 2)
                continue
            ox = sum(o.x + o.w / 2 for o in ps) / len(ps)
            oy = sum(o.y + o.h / 2 for o in ps) / len(ps)
            cx, cy = inst.x + inst.w / 2, inst.y + inst.h / 2
            if abs(oy - cy) - inst.h / 2 >= abs(ox - cx) - inst.w / 2:
                want[p] = ('N' if oy > cy else 'S', min(max(ox - inst.x, 0), inst.w))
            else:
                want[p] = ('E' if ox > cx else 'W', min(max(oy - inst.y, 0), inst.h))
        pos = {}
        for f in 'NSEW':
            L = inst.w if f in 'NS' else inst.h
            items = sorted((c_, p) for p, (ff, c_) in want.items() if ff == f)
            pitch = .096
            need = sum(die_ports[p][0] * pitch + 1.0 for _, p in items)
            if need > L - 8.0:
                pitch = .048                              # every track of the face layer
                need = sum(die_ports[p][0] * pitch + 1.0 for _, p in items)
            if need > L - 8.0:
                raise ValueError(f'{mst}: face {f} needs {need:.1f} um of {L:.1f}')
            # place groups in peer order, centred on their wish, pushed right then clamped left
            cur, plan = 4.0, []
            for c_, p in items:
                span = die_ports[p][0] * pitch
                start = max(cur, c_ - span / 2)
                plan.append([p, start, span])
                cur = start + span + 1.0
            over = cur - 1.0 - (L - 4.0)
            if over > 0:
                hi = L - 4.0
                for e in reversed(plan):
                    e[1] = min(e[1], hi - e[2])
                    hi = e[1] - 1.0
            for p, start, span in plan:
                n = die_ports[p][0]
                z0 = round(.012 + round((start - .012) / pitch) * pitch, 4)
                pos[p] = (f, 'M5' if f in 'NS' else 'M4', [round(z0 + pitch * b, 4) for b in range(n)])
        # Wishes and group packing above are in die coordinates.  Invert the
        # instance transform for EVERY bit before emitting master-local pins.
        # Transforming only the face/centre would reverse a mirrored bus.
        if orientation != 'R0':
            local = {}
            for p, (face, layer, zs) in pos.items():
                f = face
                if orientation in ('MX', 'R180'):
                    f = {'N': 'S', 'S': 'N'}.get(f, f)
                if orientation in ('MY', 'R180'):
                    f = {'E': 'W', 'W': 'E'}.get(f, f)
                reverse = ((face in 'NS' and orientation in ('MY', 'R180')) or
                           (face in 'EW' and orientation in ('MX', 'R180')))
                length = inst.w if face in 'NS' else inst.h
                local[p] = (f, layer, [round(length-z, 4) for z in zs] if reverse else zs)
            pos = local
            model.setdefault('assigned_pin_orientation_corrections', {})[mst] = dict(
                instance=inst.name, orientation=orientation,
                kind='slot_change', scope='new unclosed native parent only',
                reason='inverse die-to-master pin transform, preserving numeric bit identity',
                physical_qualification=False)
        rects = []
        for p, (n, real) in die_ports.items():
            f, L_, zs = pos[p]
            idx = aliases[p][1] if p in aliases else range(n)
            for z, b in zip(zs, idx):
                r = {'W': (0, z - .012, .192, z + .012), 'E': (q.w - .192, z - .012, q.w, z + .012),
                     'S': (z - .012, 0, z + .012, .192), 'N': (z - .012, q.h - .192, z + .012, q.h)}[f]
                rects.append((real if rp[real][0] == 1 else f'{real}[{b}]', L_, r))
        for f in 'NSEW':
            zs = [z for p, (ff, _, zz) in pos.items() if ff == f for z in zz]
            if len(zs) != len(set(zs)):
                raise ValueError(f'{mst}: overlapping assigned pins on face {f}')
        for p, (n, d) in rp.items():
            q.ports[p] = ('pins', n, None, None, [], 1)
            q.order.append(p)
        whole = {real: [r for r in rects if r[0] == real or r[0].startswith(real + '[')] for real in rp}
        for real, rs in whole.items():
            if real in covered:
                continue
            f, L_, zs = pos[real]
            q.ports[real] = ('pins', rp[real][0], f, L_, zs, 1)
        if aliases:
            partition_master(q, aliases, rects)
        M[mst] = q


def _vm_alias(M, model, by, pin_rects, partition_master):
    # the VM keeps its own pin plan; the join's slices of its ports become fragments of those real pins
    vm_m = by['sp_vector_memory'].master
    al = model.get('port_join', {}).get(vm_m, {})
    al = {a: rb for a, rb in al.items() if vm_m in M and rb[0] in M[vm_m].ports}   # aliases already die ports stay
    if al and vm_m in M:
        q = M[vm_m]
        rects = list(pin_rects(q, 1, {p: sp[1] for p, sp in q.ports.items()}))
        partition_master(q, al, rects)
