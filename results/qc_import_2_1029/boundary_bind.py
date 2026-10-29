#!/usr/bin/env python3
"""QC-IMPORT-2 step 1: native boundary nets + explicit provider boundary bindings.

The fresh clock source (clock_grafted.odb) carries the 313 START nets only as die-top
INPUT placeholder BTerms and has no reset nets. This copies, from the SAME fresh build's
target_signal.odb, exactly the native partition ITerms of (a) the 313 START nets
(dst part cland_tstart_in) and (b) the local root reset net rstw_<part>_<pin> named by the
plan reset_source, and removes the 313 placeholder BTerms (the provider becomes their only
driver). Clock cells, clock nets, placements and the other BTerms are unchanged (checked).
Then it writes ot_provider_boundary_bindings/1 for every mapped provider topport:
  t_st_*__clk -> ck_<clock_net>  (single driver ck_<actual_clock_driver>/Y; node cell clock_from pin on it)
  pst_*       -> pst_*           (native endpoint dst_part/cland_tstart_in)
  rst_raw_n   -> plan reset_source net (native endpoint = its single registered rst_o driver)
"""
import argparse, hashlib, json, collections
from pathlib import Path
import odb

def fh(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):
    d = odb.dbDatabase.create(); odb.read_db(d, str(p)); return d, d.getChip().getBlock()
def iterms(n): return sorted((it.getInst().getName(), it.getMTerm().getName()) for it in n.getITerms())

def main():
    ap = argparse.ArgumentParser()
    for k in ('source', 'signal', 'stages', 'plan', 'mapped', 'out_odb', 'out_bindings', 'report'):
        ap.add_argument('--' + k.replace('_', '-'), required=True)
    ap.add_argument('--top', default='ot_die_start_stages')
    a = ap.parse_args()
    stages = json.load(open(a.stages)); plan = json.load(open(a.plan))
    rs = plan['clock']['landing_network']['start_tree']['reset_source']
    ports = json.load(open(a.mapped))['modules'][a.top]['ports']
    d, b = load(a.source); _, s = load(a.signal)
    if any(n.getWire() or list(n.getSWires()) for n in b.getNets()): raise SystemExit('source already routed')
    def snap():
        cells = sorted((i.getName(), i.getMaster().getName(), tuple(i.getLocation()), str(i.getOrient())) for i in b.getInsts())
        ck = sorted((n.getName(), tuple(iterms(n)), tuple(sorted(t.getName() for t in n.getBTerms()))) for n in b.getNets() if n.getName().startswith('ck_') or n.getName() == 'root')
        return hashlib.sha256(json.dumps([cells, ck]).encode()).hexdigest()
    before = snap(); keep_bt = sorted(t.getName() for t in b.getBTerms() if not t.getName().startswith('pst_'))
    rep = collections.Counter(); bind = {}
    # (a) START outputs
    for e in stages['die_outputs']:
        n = b.findNet(e['net']); sn = s.findNet(e['net'])
        if not n or not sn: raise SystemExit('missing START net ' + e['net'])
        bts = list(n.getBTerms())
        if list(n.getITerms()) or len(bts) != 1 or str(bts[0].getIoType()) != 'INPUT' or bts[0].getName() != e['net']:
            raise SystemExit('START net is not a bare placeholder ' + e['net'])
        want = iterms(sn)
        if want != [(e['dst_part'], 'cland_tstart_in')]: raise SystemExit('signal START net differs %s %s' % (e['net'], want))
        it = b.findInst(e['dst_part']).findITerm('cland_tstart_in')
        if it.getNet(): raise SystemExit('START pin already connected ' + e['net'])
        it.connect(n); (getattr(odb, "dbBTerm_destroy", None) or odb.dbBTerm.destroy)(bts[0]); rep['start_nets_grafted'] += 1
        if e['net'] not in ports: raise SystemExit('START net not a mapped port ' + e['net'])
        bind[e['net']] = dict(net=e['net'], role='start_output', native_endpoints=[dict(inst=e['dst_part'], pin='cland_tstart_in')])
    # (b) local root reset
    rnet = rs['net']; sn = s.findNet(rnet)
    if b.findNet(rnet) or not sn: raise SystemExit('reset net state unexpected ' + rnet)
    drv = [(it.getInst().getName(), it.getMTerm().getName()) for it in sn.getITerms() if str(it.getMTerm().getIoType()) == 'OUTPUT']
    if drv != [(rs['part'], rs['pin'])] or list(sn.getBTerms()): raise SystemExit('reset source is not a single native registered output %s' % drv)
    n = odb.dbNet_create(b, rnet)
    for inst, pin in iterms(sn):
        it = b.findInst(inst).findITerm(pin)
        if it.getNet(): raise SystemExit('reset pin already connected %s/%s' % (inst, pin))
        it.connect(n); rep['reset_iterms_grafted'] += 1
    bind[rs['port']] = dict(net=rnet, role='reset', native_endpoints=[dict(inst=rs['part'], pin=rs['pin'])])
    # (c) stage clocks
    for st in stages['stages']:
        n = b.findNet('ck_' + st['clock_net']); node = b.findInst('ck_' + st['node_cell'])
        drv = [(it.getInst().getName(), it.getMTerm().getName()) for it in n.getITerms() if str(it.getMTerm().getIoType()) == 'OUTPUT'] if n else []
        tap = node.findITerm(st['clock_from']) if node else None
        if drv != [('ck_' + st['actual_clock_driver'], 'Y')] or not tap or not tap.getNet() or tap.getNet().getName() != n.getName() or list(n.getBTerms()):
            raise SystemExit('stage clock driver/net mismatch %s %s' % (st['id'], drv))
        if st['clock_port'] not in ports: raise SystemExit('clock port not mapped ' + st['clock_port'])
        bind[st['clock_port']] = dict(net=n.getName(), role='clock', native_endpoints=[dict(inst=drv[0][0], pin='Y')])
        rep['clock_ports'] += 1; rep['clock_tap_' + st['clock_from']] += 1
    if set(bind) != set(ports): raise SystemExit('binding/port set mismatch %d %d' % (len(bind), len(ports)))
    after = snap()
    if after != before: raise SystemExit('clock cells / clock nets changed')
    if sorted(t.getName() for t in b.getBTerms()) != keep_bt: raise SystemExit('non-START BTerms changed')
    odb.write_db(d, a.out_odb)
    out = dict(schema='ot_provider_boundary_bindings/1', source_odb_sha256=fh(a.out_odb), ports=dict(sorted(bind.items())))
    Path(a.out_bindings).write_text(json.dumps(out, indent=1) + '\n')
    r = dict(rep, clock_and_cells_sha=before, remaining_bterms=keep_bt, source_in_sha256=fh(a.source), signal_sha256=fh(a.signal),
             stages_sha256=fh(a.stages), plan_sha256=fh(a.plan), out_odb_sha256=out['source_odb_sha256'], bindings_sha256=fh(a.out_bindings),
             roles=collections.Counter(v['role'] for v in bind.values()))
    Path(a.report).write_text(json.dumps(r, indent=1) + '\n'); print(json.dumps(r))

if __name__ == '__main__': main()
