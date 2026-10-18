#!/usr/bin/env python3
"""KVJ-SMALL (c) 2026-10-17: the OR of the 128 controller completion faults into the HOST root status input.

Producer RTL: rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv, node qkd_kv_cfault_node (registered OR of R
neighbour inputs, STAGES registers).  Sources: pc_<st>_<pc>.completion_fault (qkd_ctrl_static_commit.fault, a sticky
core-domain flop).  Sink: qkd_host_root_admission.ctrl_completion_fault, consumed only as |ctrl_completion_fault into
observed_physical_faults (sticky asynchronous single bit at the host service guard).

Tree (radix 4, 43 nodes, every hop a neighbour hop, no star hub):
  cf1_<st>_<g>   x32  beside group g's grp_ctl: the group's 4 abutted PCs (pc 4k..4k+3, k = slot of g in the strip)
  cf2_<st>_<h>   x8   four adjacent groups (strip slots 4h..4h+3)
  cf3_<side>     x2   W = WS + WN, E = ES + EN halves (4 inputs each, stack order)
  cf_root        x1   R 2, beside the HOST root
Latency fault -> host input = sum of the four levels' STAGES (STAGES 1 each = 4 core edges; the extra relay stages per
hop are compiler/floorplan-priced like every other relay, left null here until the static floorplan exists; reach 405 um).
The host port is 128 b wide (legacy per-PC vector) but only its OR is used, so the die join drives bit 0 and the
remaining 127 bits are recorded as REDUCED_BY_TREE; the narrowing to 1 b belongs to the host cluster rebuild (KVJ-A3).
Bench: tools/qwen_static_kv/run_cfault_tree.sh (128 leaves at exact latency; mutants caught).
"""
import kv_static as K
import kv_static_boot_join as B

TREE = ('rtl/qwen_sys/static_kv_20261014/qkd_kv_cfault_tree.sv', 'qkd_kv_cfault_node')
STACKS = B.STACKS
ORDER = (4, 5, 0, 1, 2, 3, 6, 7)          # kv_static.template strip order: pc = 4*ORDER.index(g) + q


def _add_node(graph, ins, name, r):
    spec = K.source(*TREE, K.ROOT)
    pp = K.ports(spec, dict(R=r, STAGES=1, MUT=0))
    if name in ins:
        raise ValueError(f'instance {name} already present')
    i = dict(name=name, role='producer', source=TREE[0], module=TREE[1], sha256=spec['sha256'],
             parameters=dict(R=r, STAGES=None, MUT=0), inputs={p: None for p, v in pp.items() if v['direction'] == 'input'})
    graph['instances'].append(i)
    ins[name] = i
    if not any(d['path'] == TREE[0] for d in graph['source_files']):
        import hashlib
        graph['source_files'].append(dict(path=TREE[0], sha256=hashlib.sha256((K.ROOT / TREE[0]).read_bytes()).hexdigest()))
        graph['source_files'].sort(key=lambda d: d['path'])
    return i


def cfault_join(graph, root=K.ROOT):
    ins = {i['name']: i for i in graph['instances']}

    def ep(n, p='fault'):
        return dict(instance=n, port=p, lo=0, width=1)

    def bind(i, items):
        if i['inputs'].get('fault_in', 0) is not None or len(items) != i['parameters']['R']:
            raise ValueError(f'{i["name"]}.fault_in already bound or width mismatch')
        i['inputs']['fault_in'] = items            # MSB first (kv_static concatenation order)
        bound.append(f'{i["name"]}.fault_in')
    bound = []
    for st in STACKS:
        for k in range(8):
            pcs = [f'pc_{st}_{4 * k + q}' for q in range(4)]
            for n in pcs:
                if n not in ins or ins[n]['role'] != 'pc_path':
                    raise ValueError(f'{n}: pc_path missing')
            bind(_add_node(graph, ins, f'cf1_{st}_{ORDER[k]}', 4), [ep(n, 'completion_fault') for n in reversed(pcs)])
        for h in range(2):
            bind(_add_node(graph, ins, f'cf2_{st}_{h}', 4), [ep(f'cf1_{st}_{ORDER[k]}') for k in reversed(range(4 * h, 4 * h + 4))])
    for side, sts in (('W', STACKS[:2]), ('E', STACKS[2:])):
        bind(_add_node(graph, ins, f'cf3_{side}', 4), [ep(f'cf2_{st}_{h}') for st in reversed(sts) for h in (1, 0)])
    bind(_add_node(graph, ins, 'cf_root', 2), [ep('cf3_E'), ep('cf3_W')])
    hp = K.ports(K.source(*B.HOST, root), B._host_params(B.HOST, root))
    if hp['ctrl_completion_fault']['direction'] != 'input':
        raise ValueError('HOST root ctrl_completion_fault is not an input')
    hw = hp['ctrl_completion_fault']['width']
    joins = [dict(consumer='host.ctrl_completion_fault', producer='cf_root.fault', lo=0, width=1,
                  host_master=f'{B.HOST[0]}:{B.HOST[1]}', **(dict(reduced_by_tree=dict(lo=1, width=hw - 1)) if hw > 1 else {}),
                  note='HOST consumes only |ctrl_completion_fault; bits [hw-1:1] are the tree-reduced per-PC bits '
                       '(narrow the port in the KVJ-A3 host cluster); same core clock family as the pc_path sources')]
    graph.setdefault('die_joins', []).extend(joins)
    graph.setdefault('joins_added', []).append(dict(producer=f'cf*:{TREE[1]}', bound_inputs=len(bound), die_joins=len(joins),
        owner_note='KVJ-SMALL (c) 10-17: registered radix-4 neighbour OR tree of the 128 completion faults; '
                   'latency = sum of 4 levels STAGES (min 4 core edges), STAGES compiler/floorplan-priced'))
    return bound, joins


def latency(graph):
    """Fault -> host edges (the slowest node of each of the 4 levels), or None while any STAGES is unpriced."""
    lv = {}
    for i in graph['instances']:
        if i['module'] == TREE[1]:
            lv.setdefault(i['name'].split('_')[0], []).append(i['parameters']['STAGES'])
    if any(v is None for vs in lv.values() for v in vs):
        return None
    return sum(max(vs) for vs in lv.values())
