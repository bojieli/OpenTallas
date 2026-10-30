#!/usr/bin/env python3
"""DIE-QC-50/gen47b: provider boundary bindings on the fresh gen47 native source (QC-IMPORT-2 boundary_bind.py recipe).

The fresh source (native_clock_source on the island-holed plan_qc49 target) already carries the native signal nets
from route.v: each START net pst_* = one die-top INPUT placeholder BTerm (pinless) + its <dst_part>/cland_tstart_in
ITerm, and the reset_source net rstw_sl_E0_fw_rst_o_0 with its native driver. This only removes the 313 placeholder
BTerms (the provider becomes the sole driver) and writes ot_provider_boundary_bindings/1:
  t_st_*__clk -> ck_<stage.clock_net> (role clock; single OUTPUT driver ck_*/Y; node cell clock_from pin on that net;
                 the emitted ctree.v assign t_st_*__clk = <clock_net> must agree)
  pst_*       -> pst_* (role start_output, native endpoint dst_part/cland_tstart_in)
  rst_raw_n   -> plan reset_source net (role reset, single native rst_o driver)
Clock cells, ck_* nets and placements are hash-checked unchanged."""
import argparse, hashlib, json, collections, re
from pathlib import Path
import odb

def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def iterms(n): return sorted((it.getInst().getName(), it.getMTerm().getName()) for it in n.getITerms())

def main():
    ap = argparse.ArgumentParser()
    for k in ('source', 'stages', 'ctree', 'plan', 'mapped', 'out_odb', 'out_bindings', 'report'):
        ap.add_argument('--' + k.replace('_', '-'), required=True)
    ap.add_argument('--top', default='ot_die_start_stages')
    a = ap.parse_args()
    stages = json.load(open(a.stages)); plan = json.load(open(a.plan))
    rs = plan['clock']['landing_network']['start_tree']['reset_source']
    ports = json.load(open(a.mapped))['modules'][a.top]['ports']
    assign = dict(re.findall(r'(?m)^\s*assign\s+(\w+)\s*=\s*(\w+)\s*;', Path(a.ctree).read_text()))
    d = odb.dbDatabase.create(); odb.read_db(d, a.source); b = d.getChip().getBlock()
    if any(n.getWire() or list(n.getSWires()) for n in b.getNets()): raise SystemExit('source already routed')
    def snap():
        cells = sorted((i.getName(), i.getMaster().getName(), tuple(i.getLocation()), str(i.getOrient())) for i in b.getInsts())
        ck = sorted((n.getName(), tuple(iterms(n)), tuple(sorted(t.getName() for t in n.getBTerms()))) for n in b.getNets()
                    if n.getName().startswith('ck_') or n.getName() == 'root')
        return hashlib.sha256(json.dumps([cells, ck]).encode()).hexdigest()
    before = snap(); keep_bt = sorted(t.getName() for t in b.getBTerms() if not t.getName().startswith('pst_'))
    rep = collections.Counter(); bind = {}
    for e in stages['die_outputs']:
        n = b.findNet(e['net'])
        if not n: raise SystemExit('missing START net ' + e['net'])
        bts = list(n.getBTerms())
        if iterms(n) != [(e['dst_part'], 'cland_tstart_in')] or len(bts) != 1 or str(bts[0].getIoType()) != 'INPUT' \
                or bts[0].getName() != e['net'] or list(bts[0].getBPins()):
            raise SystemExit('START net is not native ITerm + bare placeholder %s %s' % (e['net'], iterms(n)))
        odb.dbBTerm.destroy(bts[0]); rep['start_placeholders_removed'] += 1
        if e['net'] not in ports or ports[e['net']]['direction'] != 'output': raise SystemExit('START net not a mapped output ' + e['net'])
        bind[e['net']] = dict(net=e['net'], role='start_output', native_endpoints=[dict(inst=e['dst_part'], pin='cland_tstart_in')])
    n = b.findNet(rs['net'])
    drv = [(it.getInst().getName(), it.getMTerm().getName()) for it in n.getITerms() if str(it.getMTerm().getIoType()) == 'OUTPUT'] if n else None
    if drv != [(rs['part'], rs['pin'])] or list(n.getBTerms()): raise SystemExit('reset source is not a single native registered output %s' % drv)
    rep['reset_net_iterms'] = len(iterms(n))
    bind[rs['port']] = dict(net=rs['net'], role='reset', native_endpoints=[dict(inst=rs['part'], pin=rs['pin'])])
    for st in stages['stages']:
        n = b.findNet('ck_' + st['clock_net']); node = b.findInst('ck_' + st['node_cell'])
        drv = [(it.getInst().getName(), it.getMTerm().getName()) for it in n.getITerms() if str(it.getMTerm().getIoType()) == 'OUTPUT'] if n else []
        tap = node.findITerm(st['clock_from']) if node else None
        if len(drv) != 1 or drv[0][1] != 'Y' or not drv[0][0].startswith('ck_') or not tap or not tap.getNet() \
                or tap.getNet().getName() != n.getName() or list(n.getBTerms()):
            raise SystemExit('stage clock driver/net mismatch %s %s' % (st['id'], drv))
        if assign.get(st['clock_port']) != st['clock_net']: raise SystemExit('emitted ctree alias differs ' + st['clock_port'])
        if st['clock_port'] not in ports: raise SystemExit('clock port not mapped ' + st['clock_port'])
        bind[st['clock_port']] = dict(net=n.getName(), role='clock', native_endpoints=[dict(inst=drv[0][0], pin='Y')])
        rep['clock_ports'] += 1; rep['clock_tap_' + st['clock_from']] += 1
    if set(bind) != set(ports): raise SystemExit('binding/port set mismatch %d %d %s' % (len(bind), len(ports), sorted(set(ports) ^ set(bind))[:5]))
    if snap() != before: raise SystemExit('clock cells / clock nets changed')
    if sorted(t.getName() for t in b.getBTerms()) != keep_bt: raise SystemExit('non-START BTerms changed')
    odb.write_db(d, a.out_odb)
    out = dict(schema='ot_provider_boundary_bindings/1', source_odb_sha256=fh(a.out_odb), ports=dict(sorted(bind.items())))
    Path(a.out_bindings).write_text(json.dumps(out, indent=1) + '\n')
    r = dict(rep, clock_and_cells_sha=before, remaining_bterms=keep_bt, source_in_sha256=fh(a.source), stages_sha256=fh(a.stages),
             ctree_sha256=fh(a.ctree), plan_sha256=fh(a.plan), out_odb_sha256=out['source_odb_sha256'], bindings_sha256=fh(a.out_bindings),
             roles=collections.Counter(v['role'] for v in bind.values()))
    Path(a.report).write_text(json.dumps(r, indent=1) + '\n'); print(json.dumps(r))

if __name__ == '__main__': main()
