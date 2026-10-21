import json
from pathlib import Path
import sys

import odb

root = Path(sys.argv[-2]).resolve()
out = Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root/'tools/die_clock'))
from receiver_guard import preflight, assert_disconnected, pin_name
from qwen_compute_dieclk_prep import receiver_target
from build import sink_record
from clock_reach_check import check


def coupon(kind):
    db = odb.dbDatabase.create()
    tech = odb.dbTech.create(db, 'guard_tech')
    layer = odb.dbTechLayer.create(tech, 'M1', 'ROUTING')
    lib = odb.dbLib.create(db, 'guard_lib', tech, ',')
    chip = odb.dbChip.create(db, tech)
    block = odb.dbBlock.create(chip, 'guard_coupon')

    def master(name, ports):
        m = odb.dbMaster.create(lib, name)
        m.setWidth(10000);m.setHeight(10000);m.setType('BLOCK')
        for port, direction in ports:
            t = odb.dbMTerm.create(m, port, direction, 'CLOCK' if port.startswith('pll') else 'SIGNAL')
            odb.dbBox.create(odb.dbMPin.create(t), layer, 0, 0, 2 if name == 'BUF' and port == 'A' else 1, 1)
        m.setFrozen()
        return m

    sm = master('qfd_ckbump', [('pll_ck[0]','OUTPUT')])
    rm = master('qfd_clkrx', [('pll_fwd[0]','INPUT'),
                            ('payload' if kind == 'data' else 'rst_n' if kind == 'reset' else 'pll_r0[0]','OUTPUT')])
    bm = master('BUF', [('A','INPUT'),('Y','OUTPUT')])
    source = odb.dbInst.create(block, sm, 'bump')
    rx = odb.dbInst.create(block, rm, 'rx')
    buf = odb.dbInst.create(block, bm, 'entry' if kind != 'foreign' else 'data_sink')
    source.setLocation(100000,200000)
    buf.setLocation(505000,200000)
    feed = odb.dbNet.create(block,'feed');level = odb.dbNet.create(block,'level')
    si = source.findITerm('pll_ck[0]');si.connect(feed)
    rx.findITerm('pll_fwd[0]').connect(feed)
    ro = next(it for it in rx.getITerms() if it.getIoType() == 'OUTPUT');ro.connect(level)
    bi = buf.findITerm('A');bi.connect(level)
    if kind == 'bterm':
        bt = odb.dbBTerm.create(level,'STATUS_boundary');bt.setIoType('OUTPUT')
    if kind == 'multisource':
        other = odb.dbInst.create(block,sm,'other_source');other.findITerm('pll_ck[0]').connect(feed)
    if kind == 'source_bterm':
        bt = odb.dbBTerm.create(feed,'other_input');bt.setIoType('INPUT')
    proof = {'qfd_clkrx':receiver_target('/work/inputs/die_glue.sv')}
    return db, block, si, rx, ro, bi, proof


results = []
for kind in ['nominal','bterm','data','reset','multisource','foreign','source_bterm']:
    db,block,source,rx,ro,bi,proof = coupon(kind)
    odb.write_db(db,str(out/(kind+'_before.odb')))
    try:
        inputs = preflight(source, {'entry'}, {'rx/pll_r0[0]'}, proof)
        if kind != 'nominal': raise AssertionError('unsafe native coupon admitted: '+kind)
        for it in inputs: it.disconnect()
        bi.disconnect();assert_disconnected(rx)
        # Native BTerm mutation AFTER preflight must also be refused by the final check.
        bt = odb.dbBTerm.create(ro.getNet(),'late_boundary');bt.setIoType('OUTPUT')
        try: assert_disconnected(rx)
        except ValueError: late_boundary_refused = True
        else: raise AssertionError('native final output BTerm passed')
        bbox = source.getBBox()
        pinbox = source.findITerm('pll_ck[0]').getBBox()
        xy = [(pinbox.xMin()+pinbox.xMax())/2/1000,(pinbox.yMin()+pinbox.yMax())/2/1000]
        assert xy == [100.0005,200.0005],xy
        sb = bi.getBBox()
        sk = sink_record('tree',('a','BUF',(sb.xMin()+sb.xMax())/2/1000,
                                (sb.yMin()+sb.yMax())/2/1000,'BUF/A'),[0,0,0])
        marginal = dict(source_xy={'root':xy},sinks={'a':sk},parent={'a':'root'})
        mr = check(marginal)
        assert mr['verdict'] == 'FAIL' and mr['max_raw_um'] > 405.0004,mr
        marginal['cells'] = [['root','BUF',xy[0]+0.001,xy[1]]]
        assert check(marginal)['verdict'] == 'FAIL'
        results.append(dict(id='NATIVE_'+kind,verdict='PASS',source_xy=xy,
                            late_boundary_refused=late_boundary_refused,raw_sink_reach_um=mr['max_raw_um'],
                            marginal_reach_refused=True,duplicate_coordinate_refused=True,physical_qualification_eligible=False))
    except ValueError as error:
        if kind == 'nominal': raise
        sb = bi.getBBox()
        sk = sink_record('tree',('a','BUF',(sb.xMin()+sb.xMax())/2/1000,
                                (sb.yMin()+sb.yMax())/2/1000,'BUF/A'),[0,0,0])
        marginal = dict(source_xy={'root':xy},sinks={'a':sk},parent={'a':'root'})
        mr = check(marginal)
        assert mr['verdict'] == 'FAIL' and mr['max_raw_um'] > 405.0004,mr
        marginal['cells'] = [['root','BUF',xy[0]+0.001,xy[1]]]
        assert check(marginal)['verdict'] == 'FAIL'
        results.append(dict(id='NATIVE_'+kind,verdict='EXPECTED_REFUSAL',message=str(error)))
    odb.write_db(db,str(out/(kind+'_after.odb')))
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('NATIVE_ODB_COUPONS PASS',json.dumps(results))
