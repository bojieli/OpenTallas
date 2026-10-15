#!/usr/bin/env python3
"""Source-bound PV association and conservative fixed-cycle component calendar.

Inputs are the SM's canonical 128-row subtree nodes, not arbitrary quadrant
partials. This is a compiler/component contract; it is not native SM, memory,
die routing, physical timing or end-to-end throughput evidence.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import pathlib
import random
import struct

ROOT = pathlib.Path(__file__).resolve().parents[2]
P = pathlib.Path('rtl/hbm_accel/generic/collective/p2p')
SOURCES = [P / n for n in ('ot_hgi_coll_pring_static.sv',
                           'ot_hgi_coll_reduce_static.sv',
                           'ot_hgi_attn_pv_pkg.sv', 'ot_hgi_attn_pv_native.sv')]


def placement(block):
    """The SU's row-to-slice rule fixes the two low bits; do not reorder."""
    return {'quadrant': block % 4, 'sm': (block // 4) // 2,
            'block_slot': (block // 4) % 2}


def pairwise(xs):
    xs = list(xs)
    if not xs:
        raise ValueError('empty tree')
    xs += [None] * ((1 << (len(xs) - 1).bit_length()) - len(xs))
    while len(xs) > 1:
        xs = [(xs[i], xs[i + 1]) for i in range(0, len(xs), 2)]
    return xs[0]


def prune(x):
    if not isinstance(x, tuple):
        return x
    a, b = map(prune, x)
    if a is None:
        return b
    if b is None:
        return a
    return (a, b)


class Slots:
    def __init__(self):
        self.events = {}

    def put(self, resource, cycle, op, **fields):
        k = (resource, cycle)
        if k in self.events:
            raise ValueError(f'fixed resource collision: {k}')
        self.events[k] = dict(resource=resource, cycle=cycle, op=op, **fields)


def compile_calendar(tokens=8192, words=1024, block_ready=0):
    if tokens not in (128, 640, 8192):
        raise ValueError('supported exact full shapes: T128, T640, T8192')
    if words != (1024 if tokens == 8192 else 512):
        raise ValueError('full output shape is mandatory')
    blocks = tokens // 128
    # Block partials must already be golden subtrees of sixteen chunk8 nodes.
    # Qwen64 blocks are bits [SM2 SM1 SM0 slot quadrant1 quadrant0].
    groups = (blocks + 3) // 4
    ng = 1 << (groups - 1).bit_length()
    s = Slots()
    batches = []
    cursor = block_ready
    for word in range(0, words, 8):
        dst = ((word // 128) % 4 if tokens == 8192 else word // 128)
        starts = []
        if blocks == 1:
            s.put(f'q{dst}.landing.write', cursor, 'single', slot=0, word=word)
            cursor += 4
        for group in range(groups if blocks > 1 else 0):
            b = cursor
            starts.append(b)
            for q in range(4):
                block = 4 * group + q
                s.put(f'q{q}.ring.lp', b, 'load', tag=0,
                      block=block if block < blocks else None, word=word)
            # Native CW order is 0,1,3,2. Both first-level pairs are adjacent;
            # pair(01) -> pair(23) also has one physical hop, never an ideal bus.
            for source, dest in ((0, 1), (2, 3)):
                direction = 1 if source == 2 else 0
                s.put(f'q{source}.ring.read_tx', b + 1, 'read', tag=0)
                s.put(f'q{source}.ring.tx{direction}', b + 2, 'carry', dest=dest, tag=0)
                s.put(f'q{dest}.ring.rx{direction}', b + 4, 'carry', source=source, tag=0)
                s.put(f'q{dest}.ring.read_add', b + 5, 'read', tag=0, source=source)
                s.put(f'q{dest}.ring.add', b + 6, 'add', tag=0, rhs_acc=False)
                s.put(f'q{dest}.ring.wb', b + 14, 'writeback', tag=0)
            s.put('q1.ring.read_tx', b + 15, 'read', tag=0, acc=True)
            s.put('q1.ring.tx0', b + 16, 'carry', dest=3, tag=0, acc=True)
            s.put('q3.ring.rx0', b + 18, 'carry', source=1, tag=0)
            s.put('q3.ring.read_add', b + 19, 'read', tag=0, source=1)
            s.put('q3.ring.add', b + 20, 'add', tag=0, rhs_acc=True)
            s.put('q3.ring.wb', b + 28, 'writeback', tag=0)
            s.put('q3.ring.read_tx', b + 29, 'read', tag=0, acc=True)
            s.put('q3.ring.read_rr', b + 29, 'read', tag=0)
            s.put('q3.ring.tx0', b + 30, 'result', tag=0, dest=3, acc=True)
            s.put('q3.ring.publish', b + 30, 'publish', tag=0)
            for hop, q in enumerate((2, 0, 1), 1):
                c = b + 30 + 2 * hop
                s.put(f'q{q}.ring.rx0', c, 'result', source=3, tag=0)
                s.put(f'q{q}.ring.publish', c, 'publish', tag=0)
                if hop < 3:
                    s.put(f'q{q}.ring.tx0', c, 'forward', tag=0)
            arrive = b + {3: 30, 2: 32, 0: 34, 1: 36}[dst]
            # Ring output is an FF updated at arrive; landing SRAM/FF sees it
            # at arrive+1. No same-edge read of newly produced RTL data.
            s.put(f'q{dst}.landing.write', arrive + 1, 'store', slot=group,
                  word=word, tree=prune(pairwise(list(range(4*group, min(4*group+4, blocks))))))
            cursor = b + 40
        # The remaining levels are local at the final word's destination.
        # A sparse tail is explicitly zero padded; no data-dependent shortcut.
        for g in range(groups, ng):
            s.put(f'q{dst}.landing.write', cursor, 'zero', slot=g, word=word)
            cursor += 1
        reductions = []
        level = 2
        width = ng
        while width > 1:
            for k in range(0, width, 2):
                # Actual native reducer: load FF at C, right operand captured
                # at C+2, add issue C+3, WB C+11, pubread C+12,
                # pubissue/output FF C+13, landing store C+14.
                c = cursor
                s.put(f'q{dst}.landing.read', c - 1, 'read', slot=k)
                s.put(f'q{dst}.reduce.input', c, 'load', tag=0, slot=k)
                s.put(f'q{dst}.landing.read', c + 1, 'read', slot=k+1)
                s.put(f'q{dst}.reduce.input', c + 2, 'add_read', tag=0, slot=k+1)
                s.put(f'q{dst}.reduce.add', c + 3, 'add', tag=0)
                s.put(f'q{dst}.reduce.wb', c + 11, 'writeback', tag=0)
                s.put(f'q{dst}.reduce.pubread', c + 12, 'read', tag=0)
                s.put(f'q{dst}.reduce.publish', c + 13, 'publish', tag=0, release=True)
                s.put(f'q{dst}.landing.write', c + 14, 'store', slot=k//2, word=word)
                reductions.append(dict(level=level, left=k, right=k+1,
                                       result=k//2, load=c, store=c+14))
                cursor += 16
            level += 1
            width //= 2
        final = cursor
        s.put(f'q{dst}.landing.read', final - 1, 'read', slot=0)
        s.put(f'q{dst}.reduce.input', final, 'load', tag=0, slot=0)
        s.put(f'q{dst}.reduce.pubread', final + 2, 'read', tag=0)
        s.put(f'q{dst}.reduce.publish', final + 3, 'publish', tag=0, release=True)
        s.put(f'q{dst}.destination.commit', final + 4, 'commit', word=word)
        s.put(f'q{dst}.landing.clear', final + 4, 'clear')
        batches.append(dict(word=word, words=8, destination=dst,
                            quartet_starts=starts, local_reductions=reductions,
                            start=block_ready if not batches else batches[-1]['final_visible']+1,
                            final_output=final+3, final_visible=final+4,
                            tree=prune(pairwise(range(blocks)))))
        cursor += 5
    return dict(schema='hbm-attention-pv-calendar-v1', tokens=tokens, words=words,
                block_ready=block_ready, input_boundary='canonical128row_golden_subtree_FP32',
                production_flow_control='offdie block admission only; fixed cycles after block_ready',
                block_placement=[dict(block=k, **placement(k)) for k in range(blocks)],
                association_bits=['quadrant0', 'quadrant1', 'block_slot', 'sm0', 'sm1', 'sm2'],
                source_binding={str(p): hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
                ring_order=[0, 1, 3, 2], ring_hop_cycles=2, add_latency=8,
                landing_slots_per_destination=ng, batches=batches,
                events=sorted(s.events.values(), key=lambda x: (x['cycle'], x['resource'])),
                finish_cycle=cursor, scope='compiler/component contract; native composition and physical closure separate')


# MSB-to-LSB field layout is source-pinned to ot_hgi_attn_pv_pkg.sv.
RING_FIELDS = [('lp_we',1),('lp_tag',3),('lp_data',256),('read_add',1),('read_tx',1),('read_rr',1),
               ('read_add_tag',3),('read_tx_tag',3),('read_rr_tag',3),('read_add_src',2),
               ('read_rhs_acc',1),('read_tx_acc',1),('add_v',1),('add_tag',3),('add_src',2),
               ('rhs_acc',1),('inject',2),('fwd',2),('tx_tag',3),('dst',2),('result',1),('acc',1),
               ('rx',2),('kind',4),('src',4),('tag',6),('rr',1),('rr_tag',3)]
LOCAL_FIELDS = [('clear',1),('scratch_read',4),('scratch_read_v',1),('load_v',1),('add_read',1),
                ('add_issue',1),('pub_read',1),('pub_issue',1),('capture',1),('capture_slot',4)]


def pack(fields, values):
    v = 0
    for name, width in fields:
        x = values.get(name, 0)
        if not 0 <= x < 1 << width:
            raise ValueError(f'{name}: field overflow')
        v = (v << width) | x
    return v


def lower(out):
    """Emit literal programmes consumed by the actual native component bench.

    All fields come from the independent resource calendar. Numerical boundary
    block nodes remain declared test inputs; no intermediate result is emitted.
    """
    out.mkdir(parents=True, exist_ok=True)
    manifests = []
    for tokens in (128, 640, 8192):
        cal = compile_calendar(tokens, 1024 if tokens == 8192 else 512)
        for dst in range(4):
            batch = next(x for x in cal['batches'] if x['destination'] == dst)
            base, last = batch['start'], batch['final_visible']
            ring = [[{} for _ in range(last-base+1)] for _ in range(4)]
            local = [{} for _ in range(last-base+1)]
            landing = [0] * (last-base+1)
            single = [0] * (last-base+1)
            selected = [e for e in cal['events'] if base <= e['cycle'] <= last]
            index = {(e['resource'],e['cycle']):e for e in selected}
            for e in selected:
                c=e['cycle']-base;resource=e['resource'];unit=resource.split('.')[-1]
                if '.ring.' in resource:
                    q=int(resource[1]);v=ring[q][c]
                    if unit=='lp':v.update(lp_we=1,lp_tag=e['tag'])
                    elif unit=='read_tx':v.update(read_tx=1,read_tx_tag=e['tag'],read_tx_acc=int(e.get('acc',False)))
                    elif unit=='read_rr':v.update(read_rr=1,read_rr_tag=e['tag'])
                    elif unit=='read_add':
                        add=index[(f'q{q}.ring.add',e['cycle']+1)]
                        v.update(read_add=1,read_add_tag=e['tag'],read_add_src=e['source'],read_rhs_acc=int(add['rhs_acc']))
                    elif unit=='add':
                        read=index[(f'q{q}.ring.read_add',e['cycle']-1)]
                        v.update(add_v=1,add_tag=e['tag'],add_src=read['source'],rhs_acc=int(e['rhs_acc']))
                    elif unit.startswith('tx'):
                        direction=int(unit[2:])
                        if e['op']=='forward':v['fwd']=1<<direction
                        else:v.update(inject=1<<direction,tx_tag=e['tag'],dst=e['dest'],result=int(e['op']=='result'),acc=int(e.get('acc',False)))
                    elif unit.startswith('rx'):
                        direction=int(unit[2:])
                        v.update(rx=1<<direction,kind=(2 if e['op']=='result' else 1)<<(2*direction),src=e['source']<<(2*direction),tag=e['tag']<<(3*direction))
                    elif unit=='publish' and q==3:v.update(rr=1,rr_tag=e['tag'])
                elif '.landing.' in resource:
                    if unit=='read':local[c].update(scratch_read_v=1,scratch_read=e['slot'])
                    elif unit=='clear':local[c]['clear']=1
                    elif unit=='write':
                        if e['op']=='single':single[c]=1
                        elif 'tree' in e:landing[c]=e['slot']
                        else:local[c].update(capture=1,capture_slot=e['slot'])
                elif '.reduce.' in resource:
                    if unit=='input':local[c]['load_v' if e['op']=='load' else 'add_read']=1
                    elif unit=='add':local[c]['add_issue']=1
                    elif unit=='pubread':local[c]['pub_read']=1
                    elif unit=='publish':local[c]['pub_issue']=1
            directory=out/f'shape{tokens//128}'/f'dst{dst}';directory.mkdir(parents=True,exist_ok=True)
            files={}
            for name,words,width in [(f'ring{q}.hex',[pack(RING_FIELDS,v) for v in ring[q]],sum(w for _,w in RING_FIELDS)) for q in range(4)]+[
                    ('local.hex',[pack(LOCAL_FIELDS,v) for v in local],16),('landing.hex',landing,4),('single.hex',single,1)]:
                path=directory/name
                if len(words)>1100:raise ValueError('programme exceeds actual bench1100 edges')
                words += [0] * (1100-len(words))
                path.write_text(''.join(f'{x:0{(width+3)//4}x}\n' for x in words))
                files[name]=hashlib.sha256(path.read_bytes()).hexdigest()
            cycles=directory/'cycles.hex'
            cycles.write_text(f"{batch['final_output']-base:08x}\n{last-base:08x}\n")
            files['cycles.hex']=hashlib.sha256(cycles.read_bytes()).hexdigest()
            manifests.append(dict(tokens=tokens,blocks=tokens//128,destination=dst,last=last-base,
                                  final_output=batch['final_output']-base,files=files))
    manifest=dict(schema='hbm-attention-native-programmes-v1',programmes=manifests,
                  ring_bits=sum(w for _,w in RING_FIELDS),local_bits=16,
                  source_binding={str(p):hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def add(a, b):
    y = f32(a+b)
    return 0.0 if y == 0 else y


def numeric_tree(xs):
    xs = list(xs)
    xs += [0.0] * ((1 << (len(xs)-1).bit_length()) - len(xs))
    while len(xs) > 1:
        xs = [add(xs[k], xs[k+1]) for k in range(0, len(xs), 2)]
    return xs[0]


def check():
    rng = random.Random(1417)
    records = []
    for tokens in (128, 640, 8192):
        words = 1024 if tokens == 8192 else 512
        c = compile_calendar(tokens, words)
        assert c['batches'][0]['tree'] == prune(pairwise(range(tokens//128)))
        assert len(c['events']) == len({(x['resource'], x['cycle']) for x in c['events']})
        # Validate an actual physical hop independently from packed direction
        # bits. The native join caught the first draft's q2->q3 CW mistake.
        cw = {0:1, 1:3, 3:2, 2:0}
        ccw = {b:a for a,b in cw.items()}
        for e in c['events']:
            if e['op']=='carry' and '.ring.tx' in e['resource']:
                source=int(e['resource'][1]);direction=int(e['resource'][-1])
                assert (ccw if direction else cw)[source] == e['dest']
        checked = bad = 0
        for lane in range(64):
            # Finite signed cancellation exposes association changes. Chunk8
            # accumulation starts at canonical +0, exactly as att_pv.
            products = [f32(rng.choice((-1, 1))*2.0**rng.randrange(-20, 35)*rng.random()) for _ in range(tokens)]
            chunks = []
            for start in range(0, tokens, 8):
                a = 0.0
                for p in products[start:start+8]:
                    a = add(a, p)
                chunks.append(a)
            blocks = [numeric_tree(chunks[k:k+16]) for k in range(0, len(chunks), 16)]
            exact = numeric_tree(chunks)
            got = numeric_tree([numeric_tree(blocks[k:k+4]) for k in range(0, len(blocks), 4)])
            assert struct.pack('<f', exact) == struct.pack('<f', got)
            checked += 1
            # The tempting per-SM fold consumes quadrant-local blocks before
            # the quadrant bits; it is a numerical mutant, never accepted.
            if len(blocks) == 64:
                wrong = numeric_tree([numeric_tree(blocks[q::4]) for q in range(4)])
                bad += struct.pack('<f', wrong) != struct.pack('<f', exact)
        if tokens == 8192:
            assert bad > 0, 'association mutant escaped'
        records.append(dict(tokens=tokens, checked=checked, wrong_local_first_mismatches=bad,
                            events=len(c['events']), finish_cycle=c['finish_cycle'],
                            edges_per_batch=c['batches'][0]['final_visible']+1,
                            output_words=words,
                            scope='finite-buffer serial component calendar, not end-to-end token throughput'))
    # Compiler must reject schedule conflicts rather than waiting.
    slots = Slots(); slots.put('q0.add', 1, 'add')
    try:
        slots.put('q0.add', 1, 'second_add')
    except ValueError:
        pass
    else:
        raise AssertionError('resource collision mutant escaped')
    return dict(verdict='PASS', records=records, mutants=['local_before_quadrant', 'resource_collision'],
                native_full_shape=False, physical_qualification=False)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--tokens', type=int, choices=(128, 640, 8192), default=8192)
    ap.add_argument('--block-ready', type=int, default=0)
    ap.add_argument('--out', type=pathlib.Path)
    ap.add_argument('--check', action='store_true')
    ap.add_argument('--lower-out', type=pathlib.Path)
    args = ap.parse_args()
    result = lower(args.lower_out) if args.lower_out else check() if args.check else compile_calendar(args.tokens, 1024 if args.tokens == 8192 else 512, args.block_ready)
    payload = json.dumps(result, indent=2) + '\n'
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload)
    else:
        print(payload, end='')
