#!/usr/bin/env python3
"""QC-IMPORT-3 / QC-001: clock polarity of every provider START stage and every START capture partition, as bound.

For each net on the die clock tree, walk the single OUTPUT driver chain back to the die-top root BTerm and count the
inverting cells (master name contains INV). A stage's tap net must be TRUE phase (even count): the landing contract
(count_align_bind regions -> start_stages edge_fall) times every stage on the root's rising edge, with the EDGE_FALL
stages sampling START on that same true clock's falling edge (DFFLQN in the mapped netlist). Also checks the
mapped netlist realises EDGE_FALL (2 negedge flops per fall stage, origin sf + reset relay) and that every
START destination partition (cland_tstart_in capture) and every partition clock pin on the tree is TRUE phase.
"""
import argparse, collections, hashlib, json, re
from pathlib import Path
import odb

ap = argparse.ArgumentParser()
for k in ('odb', 'stages', 'bindings', 'bind', 'mapped_v', 'out'):
    ap.add_argument('--' + k.replace('_', '-'), required=True)
ap.add_argument('--root', default='root')
a = ap.parse_args()
fh = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
d = odb.dbDatabase.create(); odb.read_db(d, a.odb); b = d.getChip().getBlock()
stages = json.load(open(a.stages)); bindings = json.load(open(a.bindings))['ports']
bind = json.load(open(a.bind)); regions = bind['regions']

def driver(n):
    o = [it for it in n.getITerms() if it.isOutputSignal()]
    return o
memo = {}
def parity(net):
    """(#inverting cells, #cells) from the root BTerm to net; raises on multi-driver / dangling."""
    chain, n = [], net
    while True:
        nm = n.getName()
        if nm in memo:
            inv, cells = memo[nm]; break
        if any(t.getName() == a.root for t in n.getBTerms()):
            inv, cells = 0, 0; break
        dr = driver(n)
        if len(dr) != 1:
            raise SystemExit(f'net {nm}: {len(dr)} drivers')
        inst = dr[0].getInst(); m = inst.getMaster().getName()
        ins = [it for it in inst.getITerms() if it.isInputSignal() and it.getNet()]
        if len(ins) != 1:
            raise SystemExit(f'clock cell {inst.getName()} ({m}) has {len(ins)} connected inputs')
        chain.append((nm, 'INV' in m.upper()))
        n = ins[0].getNet()
    for nm, isinv in reversed(chain):
        inv += isinv; cells += 1; memo[nm] = (inv, cells)
    return memo[net.getName()]

rep = collections.Counter(); bad = []
rows = []
for st in stages['stages']:
    port = st['clock_port']; bn = bindings[port]['net']
    n = b.findNet(bn)
    inv, cells = parity(n)
    node = b.findInst('ck_' + st['node_cell'])
    node_inv, _ = parity(node.findITerm('Y').getNet())
    # the tap the emitter chose: A when the node output is inverted, Y otherwise
    want_from = 'A' if node_inv % 2 else 'Y'
    rg = regions.get(st['region'], {})
    ok = (inv % 2 == 0) and want_from == st['clock_from'] and bool(rg.get('edge_fall')) == bool(st['edge_fall'])
    rep[f"tap_{st['clock_from']}_{'true' if inv % 2 == 0 else 'INVERTED'}"] += 1
    rep['edge_fall' if st['edge_fall'] else 'edge_rise'] += 1
    if 'INV' in node.getMaster().getName().upper(): rep['node_cell_inverter'] += 1
    if not ok:
        bad.append(dict(stage=st['id'], region=st['region'], net=bn, inv=inv, clock_from=st['clock_from'], want_from=want_from,
                        edge_fall=st['edge_fall'], bind_edge_fall=rg.get('edge_fall')))
    rows.append((st['id'], bn, inv, cells, st['clock_from'], st['edge_fall']))
rep['stages'] = len(stages['stages']); rep['stage_tree_depth_max'] = max(r[3] for r in rows)
rep['bind_regions_edge_fall'] = sum(1 for r in regions.values() if r.get('edge_fall'))

# START launch/capture: parent stage launches posedge on its true clock; the child captures on edge_fall per bind
by_region = {s['region']: s for s in stages['stages']}
link_bad = []
for s in stages['stages']:
    if s['parent'] is None: continue
    p = by_region.get(s['parent'])
    if p is None or s['region'] not in p['children']:
        link_bad.append((s['id'], 'parent/child mismatch'))
rep['start_links'] = sum(1 for s in stages['stages'] if s['parent'] is not None); rep['start_link_errors'] = len(link_bad)

# mapped netlist: EDGE_FALL realised as negedge flops (origin sf + reset relay first flop) per fall stage
v = Path(a.mapped_v).read_text()
neg = len(re.findall(r'\bDFFLQN\w*\s', v)); pos = len(re.findall(r'\bDFFHQN\w*\s', v))
rep['mapped_negedge_ff'] = neg; rep['mapped_posedge_ff'] = pos
rep['mapped_negedge_expected'] = 2 * sum(1 for s in stages['stages'] if s['edge_fall'])

# START capture partitions (die_outputs dst_part) + every partition clock pin on the clock tree: phase
cap = collections.Counter(); cap_bad = []
macro_clk = {}
for n in b.getNets():
    if not (n.getName().startswith('ck_') or n.getName() == a.root): continue
    for it in n.getITerms():
        inst = it.getInst()
        if inst.getMaster().isBlock() and it.isInputSignal():
            macro_clk.setdefault(inst.getName(), []).append((it.getMTerm().getName(), n))
for part, pins in macro_clk.items():
    for pin, n in pins:
        inv, _ = parity(n)
        cap['partition_clock_pins_true' if inv % 2 == 0 else 'partition_clock_pins_INVERTED'] += 1
        if inv % 2: cap_bad.append((part, pin, n.getName(), inv))
dst = [e['dst_part'] for e in stages['die_outputs']]
cap['start_capture_parts'] = len(dst)
cap['start_capture_parts_true'] = sum(1 for p in dst if p in macro_clk and all(parity(n)[0] % 2 == 0 for _, n in macro_clk[p]))
cap['start_capture_parts_no_clock_pin'] = sum(1 for p in dst if p not in macro_clk)
rep.update(cap)
out = dict(schema='qc_import_3_polarity/1', verdict='PASS' if not bad and not cap_bad and not link_bad and neg == rep['mapped_negedge_expected'] and cap['start_capture_parts_true'] == len(dst) else 'FAIL',
           counts=dict(sorted(rep.items())), stage_errors=bad[:50], n_stage_errors=len(bad), partition_errors=cap_bad[:50],
           n_partition_errors=len(cap_bad), link_errors=link_bad[:50],
           inputs=dict(odb=fh(a.odb), stages=fh(a.stages), bindings=fh(a.bindings), bind=fh(a.bind), mapped_v=fh(a.mapped_v)))
Path(a.out).write_text(json.dumps(out, indent=1) + '\n'); print(json.dumps({k: out[k] for k in ('verdict', 'counts', 'n_stage_errors', 'n_partition_errors')}, indent=1))
