import json
from pathlib import Path
import sys

import odb

root = Path(sys.argv[-2]).resolve()
out = Path(sys.argv[-1]).resolve()
out.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(root/'tools/die_clock'))
from receiver_guard import preflight, assert_disconnected, pin_name


def coupon(kind):
    db = odb.dbDatabase.create()
    tech = odb.dbTech.create(db, 'guard_tech')
    layer = odb.dbTechLayer.create(tech, 'M1')
    layer.setType('ROUTING')
    lib = odb.dbLib.create(db, 'guard_lib', tech, ',')
    chip = odb.dbChip.create(db)
    block = odb.dbBlock.create(chip, 'guard_coupon')

    def master(name, ports):
        m = odb.dbMaster.create(lib, name)
        m.setWidth(10000);m.setHeight(10000);m.setType('BLOCK')
        for port, direction in ports:
            t = odb.dbMTerm.create(m, port, direction, 'CLOCK' if port.startswith('pll') else 'SIGNAL')
            odb.dbBox.create(odb.dbMPin.create(t), layer, 0, 0, 1, 1)
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
    proof = {'qfd_clkrx':dict(view='MODEL_PASS_THROUGH_R0',physical_qualification_eligible=False,
                             rtl_sha256='a'*64)}
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
        results.append(dict(id='NATIVE_'+kind,verdict='PASS',source_xy=xy,
                            late_boundary_refused=late_boundary_refused,physical_qualification_eligible=False))
    except ValueError as error:
        if kind == 'nominal': raise
        results.append(dict(id='NATIVE_'+kind,verdict='EXPECTED_REFUSAL',message=str(error)))
    odb.write_db(db,str(out/(kind+'_after.odb')))
(out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
print('NATIVE_ODB_COUPONS PASS',json.dumps(results))
