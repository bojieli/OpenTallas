#!/usr/bin/env python3
"""SU.VOP F2 compiler pass: per-quarter VM placement + operand reuse + static transport calendar.

Owner rules: static cycle schedule (no credits/ready/backpressure on chip), HBM static on-chip (0an).  Input: the
canonical SU fixtures of su_prod_vec.py (actual layer-0 records, actual VM word identities), the same records the
tensor plan su_tensor_plan.py (224c1359b) and the bound su_f2_placement_bound.py consume.

1. Lane identity is the static SU's (su_arith_lower.py): an issue covers 512 element positions; quarter q owns
   positions [128q, 128q+128).  Every VM word an SU record touches gets the set of quarters that read it and the
   quarter (elementwise O) or root (reduction R) that writes it.
2. Placement (compiler only, no hardware change): each word lives in the VM slice of every quarter that reads or
   elementwise-writes it.  Within slice q the words are packed in logical order (a new sector at every logical run
   break), so quarter q's share of every tensor is spread round-robin over its own 8 banks and each quarter's 128
   lanes still see an affine per-issue base (checked).  Words read by several quarters (row/inner broadcast operands,
   rope tables, the softmax row max) are replicated, one copy per reading quarter; reduction results are written to
   every demanding slice through the link's per-quarter operand broadcast (ot_hbm_su_f2_static_link operand_load /
   operand_replay).  A word elementwise-written by quarter a and read by quarter b != a would need a cross-quarter
   route: counted as a conflict (the F2 link refuses it: address_ok).
3. Operand reuse: (a) within a record each sector is fetched once per quarter (broadcast operands once per record);
   (b) across ADJACENT SU dispatches of the canonical trace (no other unit dispatch between them), words already in
   the quarter's local store (staged or produced by the predecessor) are not re-staged, and a predecessor output that
   the successor overwrites in place before any other reader is not drained (softmax.exp_sum E -> softmax.bf16_p).
   Adjacency comes from the canonical dispatch trace (--trace), never assumed.
4. Calendar (fixed edges, compiler owned, one read and one write sector per bank per edge, SU port groups on the LG
   SU station, GEO-H 10-15): stage reads are issued in issue order; issue g fires at max(issue g-1 + 1, last operand
   read + VM_RD + LS_WR); its outputs are in the local store at issue + ARITH and leave it LS_RD later; output
   sectors take the first free write edge of their bank; the record ends when its last write is done (+VM_WR).
   Back-to-back SU dispatches (adjacent in the canonical trace) share one calendar (ports and issue slot carried).
   Reduction rows add a declared tail (csum8 frontier, dependent interval 8 per level, reduction/model.json): a MODEL
   term, not an arithmetic measurement.  Every edge count here is re-executed and checked on the real link + 32 static
   banks + SRAM macros by tb_hbm_su_f2_spread_vehicle.sv (exact data and exact edges).
"""
import argparse
import gzip
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/hbm_static'))
from su_program_inventory import decode  # noqa: E402

# Fixed edges (all measured on RTL unless marked): VM_RD/VM_WR = SU (near) station of the LG tap, read return 10 /
# write done 7 (tb_hbm_vm_lg_static_split); LS_WR / LS_RD = pinned local-store commit n+1 / read n+2
# (data_store/pinned); ARITH = issue -> result in the local store, 23 (arithmetic baseline, model.json);
# RED_DEP = dependent reduction interval 8 (reduction component) -- the tree depth applied to it is a MODEL.
VM_RD, VM_WR, LS_WR, LS_RD, ARITH, RED_DEP = 10, 7, 1, 2, 23, 8
SLICE_WORDS = 1 << 16


def accesses(raw, rot=0):
    """Per issue, per quarter: read words (with role) and elementwise-written words; reduction words."""
    dispatch, unit, sut, desc = decode(raw)
    ni, no = dispatch['n'][0], desc['A'].m
    needed = {'A'}
    if sut['m1'] in (1, 4, 6) or sut['ad'] == 3 or sut['e2'] == 1:
        needed.add('B')
    if sut['m2'] == 1 or sut['qm'] or sut['ad'] in (1, 2) or sut['e1'] in (1, 2):
        needed.add('A' if sut['c_pair'] else 'C')
    if sut['qm'] or sut['ad'] == 5:
        needed.add('D')
    if sut['a_ind']:
        raise ValueError('runtime lane gather needs its real index/read calendar')
    slot = min(512, 1 << (max(ni, 8 if sut['red'] else 1) - 1).bit_length())
    per = 512 // slot
    positions = [(o, 0) for o in range(0, no, per)] if ni <= 512 else [(o, i) for o in range(no) for i in range(0, ni, 512)]
    roles = {}
    for name, md in desc.items():
        used = name in needed or (name == 'O' and sut['dst']) or (name == 'R' and sut['red'])
        if used:
            if md.space != 'VM':
                raise ValueError('nonVM tensor needs its actual native producer')
            roles[name] = md
    issues = []
    for outer, inner in positions:
        q_reads = [[] for _ in range(4)]
        q_writes = [[] for _ in range(4)]
        rows = set()
        for lane in range(512):
            if ni <= 512:
                o, i = outer + lane // slot, lane % slot
                if i >= ni or o >= no:
                    continue
            else:
                o, i = outer, inner + lane
                if i >= ni:
                    continue
            q = (lane // 128 + rot) % 4                 # compiler-chosen executing quarter (rotation)
            rows.add(o)
            for name, md in roles.items():
                if name == 'R':
                    continue
                ist = 0 if md.ibcast else (md.istride or 1)
                ii = (i >> 1) if name in 'BD' and sut['b_half'] else i
                w = md.base + o * md.stride + ii * ist
                if name == 'O':
                    q_writes[q].append(w)
                else:
                    q_reads[q].append((name, lane % 128, w))
                    if name == 'A' and sut['c_pair']:
                        q_reads[q].append((name + 'p', lane % 128, w ^ 1))
        issues.append(dict(reads=q_reads, writes=q_writes, rows=sorted(rows)))
    red = []
    if 'R' in roles:
        md = roles['R']
        n = 1 if sut['red_whole'] or sut['red_tree'] else no
        red = [md.base + k * (md.stride or 1) for k in range(n)]
    for w in [x for iss in issues for q in iss['reads'] for _, _, x in q] + [x for iss in issues for q in iss['writes'] for x in q] + red:
        if not 0 <= w < 1 << 18:
            raise ValueError('tensor exceeds real 2^18-word store')
    return dict(unit=unit, ni=ni, no=no, slot=slot, red=bool(sut['red']), sut=sut, issues=issues, red_words=red, rot=rot)


def canonical_trace(design, ds_program):
    """Ordered layer-0 dispatch list (unit, tag) of the canonical program, as su_prod_vec.py builds it."""
    sys.path[:0] = [str(ROOT / 'tools'), str(ROOT / 'tools/hgi_adapters')]
    import common as C  # noqa: E402
    from hgi_sim import timing as T  # noqa: E402
    if design == 'qwen':
        _, recs, _, _ = C.SV.qwen_program()
        pos = 8191
    else:
        from hgi_sim.records import decode_one
        dd = json.loads(Path(ds_program).read_text())
        recs = []
        for x in dd['layers'][0]['records']:
            r, _ = decode_one(bytes.fromhex(x['hex']), 0)
            r.tag = x['tag']
            recs.append(r)
        pos = (1 << 20) - 1
    out = []
    for k, layer, _ in T.expand(recs, pos):
        r = recs[k]
        if r.unit == 'CTL' or layer != 0:
            continue
        writes, unknown = set(), False
        for name, md in r.desc.items():
            if name not in 'OR' or md.space != 'VM':
                continue
            if getattr(md, 'indexed', 0) or getattr(md, 'dyn_sel', 0) or getattr(md, 'dyn_mul', 0):
                unknown = True                    # runtime address: invalidates every local copy
                continue
            ist = 0 if md.ibcast else (md.istride or 1)
            for o in range(max(1, md.m)):
                for i in range(max(1, md.n)):
                    writes.add(md.base + o * md.stride + i * ist)
        out.append((r.unit, r.tag, writes, unknown))
    return out


def compile_design(vectors, trace):
    manifest = json.loads((vectors / 'su_prod.json').read_text())
    raw = [int(x, 16) for x in (vectors / 'su_rec.mem').read_text().split()]
    cases = manifest['cases']
    # quarter rotation: each record runs on the quarters that already hold the words it reads (greedy, program
    # order); e.g. a 64-element rope tail of a 512-element norm output runs on quarter 3, where the norm wrote it.
    recs, owner = [], {}
    for b in raw:
        best = None
        for rot in range(4):
            cand = accesses(b, rot)
            score = sum(1 for iss in cand['issues'] for q in range(4) for _, _, w in iss['reads'][q] if owner.get(w) == q)
            if best is None or score > best[0]:
                best = (score, cand)
        recs.append(best[1])
        for iss in best[1]['issues']:
            for q in range(4):
                for w in iss['writes'][q]:
                    owner[w] = q
    # adjacency in the canonical trace: record k+1 directly follows record k (first layer-0 occurrence)
    index = {}
    for n, (unit, tag, _, _) in enumerate(trace):
        index.setdefault(tag, n)
    fixture_at = {index[c['tag']] for c in cases}
    adjacent = [k > 0 and cases[k]['tag'] in index and cases[k - 1]['tag'] in index and
                index[cases[k]['tag']] == index[cases[k - 1]['tag']] + 1 for k in range(len(cases))]
    # ---- demands
    readq = defaultdict(set)
    writeq = defaultdict(set)      # elementwise writer quarters
    redw = set()
    for r in recs:
        for iss in r['issues']:
            for q in range(4):
                for _, _, w in iss['reads'][q]:
                    readq[w].add(q)
                for w in iss['writes'][q]:
                    writeq[w].add(q)
        redw.update(r['red_words'])
    # A scalar-sized elementwise output (<= 8 words per record) read by other quarters is written to every reading
    # slice through the SU's global result broadcast register (the path reduction results take, +1 edge).  A larger
    # cross-quarter output would need a COLL route: counted as a conflict, never silently relocated.
    small_out = set()
    for r in recs:
        ws = {w for iss in r['issues'] for q in range(4) for w in iss['writes'][q]}
        if len(ws) <= 8:
            small_out |= ws
    bcast_out = {w for w in writeq if readq[w] - writeq[w] and w in small_out}
    conflicts = sorted(w for w in writeq if (len(writeq[w]) > 1 or readq[w] - writeq[w]) and w not in bcast_out)
    home = {}
    for w in set(readq) | set(writeq) | redw:
        h = readq[w] | writeq[w]
        home[w] = sorted(h) if h else [0]            # a reduction result nobody in the SU reads: root slice 0
    # ---- per-slice packing in logical order, new sector at each logical run break
    phys = defaultdict(dict)                          # w -> {q: physical word in slice q}
    used = [0] * 4
    for q in range(4):
        ws = sorted(w for w, h in home.items() if q in h)
        p, prev = 0, None
        for w in ws:
            if prev is None or w != prev + 1:
                p = (p + 7) // 8 * 8
            phys[w][q] = p
            p += 1
            prev = w
        used[q] = p
    if max(used) > SLICE_WORDS:
        raise SystemExit(f'slice capacity exceeded: {used}')
    inv = {}                                          # (q, sector) -> 8 logical words or -1
    for w, m in phys.items():
        for q, p in m.items():
            inv.setdefault((q, p >> 3), [-1] * 8)[p & 7] = w
    # ---- per-quarter control check: the static SU forms lane addresses as base + sum of per-lane-bit terms (ld_c,
    # 7 terms per role per quarter, su_arith_lower.py); every relocated role must still be of that form.  The c_pair
    # partner (a ^ 1) is formed by the lane hardware from A and is not a separate stream.
    affine_fail = 0
    affine_where = set()
    for k, r in enumerate(recs):
        for iss in r['issues']:
            for q in range(4):
                by = defaultdict(dict)
                for role, lane, w in iss['reads'][q]:
                    if role != 'Ap':
                        by[role][lane] = phys[w][q]
                for role, pts in by.items():
                    if 0 not in pts:
                        continue
                    base = pts[0]
                    term = {}
                    for kbit in range(7):
                        if (1 << kbit) in pts:
                            term[kbit] = pts[1 << kbit] - base
                    if any(lane >> kbit & 1 and kbit not in term for lane in pts for kbit in range(7)) or \
                       any(p != base + sum(term[kbit] for kbit in range(7) if lane >> kbit & 1) for lane, p in pts.items()):
                        affine_fail += 1
                        affine_where.add((cases[k]['tag'], role, q))
    # ---- calendar
    events = []                                       # (edge, kind, quarter, bank, sector, mask, record)
    local = [set() for _ in range(4)]                 # words valid in each quarter's local store (1 MiB = whole VM)
    rows = []
    elide_drain = set()
    for k in range(len(recs) - 1):
        if adjacent[k + 1]:                           # successor overwrites in place before any other reader
            over = [set() for _ in range(4)]
            for iss in recs[k + 1]['issues']:
                for q in range(4):
                    over[q].update(iss['writes'][q])
            for iss in recs[k]['issues']:
                for q in range(4):
                    for w in iss['writes'][q]:
                        if w in over[q]:
                            elide_drain.add((k, q, w))
    t_end = 0
    rfree = [0] * 32
    wfree = [0] * 32
    last_issue = -1
    invalidated = 0
    for k, r in enumerate(recs):
        tk = index[cases[k]['tag']]
        if k:
            # any other dispatch between the previous fixture record and this one that writes VM kills local copies
            for n in range(index[cases[k - 1]['tag']] + 1, tk):
                if n in fixture_at:
                    continue
                _, _, writes, unknown = trace[n]
                for q in range(4):
                    if unknown:
                        invalidated += len(local[q])
                        local[q] = set()
                    else:
                        invalidated += len(local[q] & writes)
                        local[q] -= writes
        if adjacent[k]:
            start = min(min(rfree), last_issue + 1)   # back-to-back SU dispatches: ports/issue carried over
        else:
            start = t_end                             # other units run between: no overlap claimed
            rfree = [start] * 32
            wfree = [start] * 32
            last_issue = start - 1
        first = None
        staged = [set() for _ in range(4)]
        last_done = start
        nread = nwrite = reuse_words = elided = 0
        red_rows_done = {}
        for g, iss in enumerate(r['issues']):
            ready = start
            for q in range(4):
                need = defaultdict(int)
                for _, _, w in iss['reads'][q]:
                    if w in staged[q]:
                        continue
                    if w in local[q]:
                        reuse_words += 1
                        staged[q].add(w)
                        continue
                    p = phys[w][q]
                    need[p >> 3] |= 1 << (p & 7)
                    staged[q].update(x for x in inv[(q, p >> 3)] if x >= 0)   # the whole sector is now local
                for s_, m in sorted(need.items()):
                    b = q * 8 + (s_ & 7)
                    e = rfree[b]
                    rfree[b] = e + 1
                    nread += 1
                    events.append((e, 'R', q, s_ & 7, s_, 0xff, k))
                    first = e if first is None else min(first, e)
                    ready = max(ready, e + VM_RD + LS_WR)
            fire = max(last_issue + 1, ready)
            first = fire if first is None else min(first, fire)
            last_issue = fire
            out = fire + ARITH + LS_RD
            wsec = [defaultdict(int) for _ in range(4)]
            for q in range(4):
                for w in iss['writes'][q]:
                    local[q].add(w)
                    if (k, q, w) in elide_drain:
                        elided += 1
                        continue
                    for qq in (home[w] if w in bcast_out else [q]):
                        p = phys[w][qq]
                        wsec[qq][p >> 3] |= 1 << (p & 7)
                        local[qq].add(w)
            for q in range(4):
                for s_, m in sorted(wsec[q].items()):
                    b = q * 8 + (s_ & 7)
                    e = max(wfree[b], out + (1 if any(x in bcast_out for x in inv[(q, s_)]) else 0))
                    wfree[b] = e + 1
                    nwrite += 1
                    events.append((e, 'W', q, s_ & 7, s_, m, k))
                    last_done = max(last_done, e + VM_WR)
            for o in iss['rows']:
                red_rows_done[o] = fire + ARITH
        if r['red_words']:
            # MODEL: csum8 frontier, ceil(log2(ceil(n/8))) dependent levels + 1 F2 quarter level after the last issue
            levels = max(1, math.ceil(math.log2(max(1, math.ceil(r['ni'] / 8))))) + 1
            done = max(red_rows_done.values()) + levels * RED_DEP + LS_RD
            for w in r['red_words']:
                for q in home[w]:                     # root result broadcast to every demanding slice
                    p = phys[w][q]
                    s_ = p >> 3
                    b = q * 8 + (s_ & 7)
                    e = max(wfree[b], done)
                    wfree[b] = e + 1
                    nwrite += 1
                    events.append((e, 'W', q, s_ & 7, s_, 1 << (p & 7), k))
                    last_done = max(last_done, e + VM_WR)
                    local[q].add(w)
        for q in range(4):
            local[q] |= staged[q]
        end = max(last_done, last_issue + ARITH)
        own = end - first
        inc = end - t_end if adjacent[k] else own
        t_end = max(t_end, end)
        rows.append(dict(tag=cases[k]['tag'], priced=cases[k]['priced'], issues=len(r['issues']),
                         stage_sectors=nread, drain_sectors=nwrite, reused_words=reuse_words, elided_drain_words=elided,
                         adjacent_to_predecessor=adjacent[k], first_edge=first, end_edge=end, own_edges=own,
                         edges=max(inc, 0), over_price=max(inc, 0) > cases[k]['priced'],
                         reduction_tail_model=bool(r['red_words'])))
    return dict(records=rows, events=events, phys=phys, home=home, inv=inv, used=used, conflicts=conflicts,
                affine_fail=affine_fail, affine_where=sorted(affine_where),
                replicated_words=sum(1 for h in home.values() if len(h) > 1), invalidated_local_words=invalidated,
                broadcast_written_words=len(bcast_out), rotations=[r['rot'] for r in recs],
                total=dict(priced=sum(x['priced'] for x in rows), edges=sum(x['edges'] for x in rows)))


def chains(rows):
    """Maximal runs of back-to-back SU dispatches: the unit runs them as one static calendar; compare the run's
    makespan with the sum of its records' immutable prices."""
    out, cur = [], None
    for x in rows:
        if cur is None or not x['adjacent_to_predecessor']:
            cur = dict(tags=[], priced=0.0, first=x['first_edge'], end=x['end_edge'])
            out.append(cur)
        cur['tags'].append(x['tag'])
        cur['priced'] += x['priced']
        cur['end'] = max(cur['end'], x['end_edge'])
    for c in out:
        c['edges'] = c['end'] - c['first']
        c['ratio'] = round(c['edges'] / c['priced'], 3)
    return out


def word_data(w):
    return (w * 2654435761 + 0x9E3779B9) & 0xffffffff


def emit_vehicle(res, stem):
    """Images for tb_hbm_su_static_spread_vehicle (stem_{n,pre,ev,final,win}.mem).

    pre: every physical sector the calendar touches, full 8-word image (preload, unmeasured). ev: the record calendar,
    one sector per line {edge32, record8, write4, quarter4, sector16, mask8, data256}; a read carries the sector image
    expected at that edge, a write carries record-tagged data, so a later read or the final readback proves the
    producing write landed in the right slice/bank/row. win: per record the expected VM transport window
    {first request edge, last return edge} (read +VM_RD, write done +VM_WR)."""
    inv = res['inv']
    image = {key: [word_data(x) if x >= 0 else 0 for x in ws] for key, ws in inv.items()}
    pre = sorted(inv)
    ev = sorted(res['events'], key=lambda x: (x[0], x[1] == 'W'))
    hexs = lambda ws: ''.join(f'{v:08x}' for v in reversed(ws))
    sec16 = lambda q, s: (q << 13) | s                # native sector {mirror0, SID=q, row10, bank3}
    Path(f'{stem}_pre.mem').write_text(''.join(f'{q:x}{sec16(q, s):04x}{hexs(image[(q, s)])}\n' for q, s in pre))
    lines = []
    win = {}
    for e, kind, q, b, s, m, k in ev:
        cur = image[(q, s)]
        if kind == 'W':
            for j, x in enumerate(inv[(q, s)]):
                if m >> j & 1:
                    cur[j] = word_data(x) ^ (0xA5000000 | k)
        lines.append(f'{e:08x}{k:02x}{1 if kind == "W" else 0:x}{q:x}{sec16(q, s):04x}{m:02x}{hexs(cur)}\n')
        lo, hi = win.get(k, (e, 0))
        win[k] = (min(lo, e), max(hi, e + (VM_WR if kind == 'W' else VM_RD)))
    Path(f'{stem}_ev.mem').write_text(''.join(lines))
    Path(f'{stem}_final.mem').write_text(''.join(f'{q:x}{sec16(q, s):04x}{hexs(image[(q, s)])}\n' for q, s in pre))
    nrec = len(res['records'])
    Path(f'{stem}_win.mem').write_text(''.join(f'{win.get(k, (0, 0))[0]:08x}{win.get(k, (0, 0))[1]:08x}\n'
                                               for k in range(nrec)))
    Path(f'{stem}_n.mem').write_text(f'{len(pre):08x}\n{len(ev):08x}\n{nrec:08x}\n')
    return len(pre), len(ev), win


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vectors', type=Path, required=True, help='su_prod_vec.py output directory')
    ap.add_argument('--design', choices=['qwen', 'deepseek'], required=True)
    ap.add_argument('--ds-program', default=str(ROOT / 'results/arch/hgi_programs_20261010/inputs/ds_rank0_program.json'))
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--vehicle', help='write the RTL vehicle images with this path stem')
    a = ap.parse_args()
    trace = canonical_trace(a.design, a.ds_program)
    res = compile_design(a.vectors, trace)
    report = dict(schema='opentallas.hbm.su_f2_spread.v1', tool='tools/hbm_static/su_f2_spread.py',
                  design=a.design, qualification=False,
                  kind='compiler placement + static transport calendar; transport re-executed on RTL by the vehicle',
                  constants=dict(VM_RD=VM_RD, VM_WR=VM_WR, LS_WR=LS_WR, LS_RD=LS_RD, ARITH=ARITH, RED_DEP=RED_DEP),
                  inputs={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(a.vectors.iterdir())
                          if p.name in ('su_rec.mem', 'su_prod.json')},
                  slice_words_used=res['used'], replicated_words=res['replicated_words'],
                  cross_quarter_conflict_words=len(res['conflicts']), affine_base_failures=res['affine_fail'],
                  affine_failures_at=res['affine_where'], broadcast_written_words=res['broadcast_written_words'],
                  rotations=res['rotations'], invalidated_local_words=res['invalidated_local_words'],
                  chains=chains(res['records']),
                  records=res['records'], total=res['total'])
    report['total']['ratio'] = round(res['total']['edges'] / res['total']['priced'], 3)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=1) + '\n')
    for x in res['records']:
        print(f"{x['tag']:28s} priced {x['priced']:6.0f} edges {x['edges']:5d} issues {x['issues']:4d} "
              f"rd {x['stage_sectors']:5d} wr {x['drain_sectors']:5d} reuse {x['reused_words']:6d} elide {x['elided_drain_words']:6d}"
              f"{'  OVER' if x['over_price'] else ''}")
    print(a.design, report['total'], 'slices', res['used'], 'replicated', res['replicated_words'],
          'conflicts', len(res['conflicts']), 'affine_fail', res['affine_fail'])
    if a.vehicle:
        npre, nev, win = emit_vehicle(res, a.vehicle)
        report['vehicle_transport_windows'] = {res['records'][k]['tag'] + f'#{k}': list(v) for k, v in sorted(win.items())}
        a.out.write_text(json.dumps(report, indent=1) + '\n')
        print('vehicle images', a.vehicle, 'preload sectors %d events %d' % (npre, nev))


if __name__ == '__main__':
    main()
