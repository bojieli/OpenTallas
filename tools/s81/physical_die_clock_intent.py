#!/usr/bin/env python3
"""Resolve the existing source-bound die model's clock buses against actual ODB.

Uses clock/col_clock/fclk/clock_trunk intent, never pin-name guesses, and retains
actual native macro output drivers and every placed input pin. This inventories
physical distribution obligations; generated-clock ratios and real per-child R
still require their native source contracts. Run with OpenROAD -python.
"""
import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path


CLASSES={'clock','col_clock','fclk','clock_trunk'}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def intents(model):
    for bid,kind,bits,eps in model['buses']:
        if kind not in CLASSES:continue
        if bits!=1:raise ValueError(f'non-scalar clock bus needs an explicit per-bit map: {bid}')
        if not eps or len(eps)<2:raise ValueError(f'incomplete source clock bus: {bid}')
        yield bid,kind,eps


def main():
    import odb
    ap=argparse.ArgumentParser(description=__doc__)
    for key in ('odb','model','out'):ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--model-receipt',type=Path,help='source-bound output_sha256 receipt when model has no source_commit')
    a=ap.parse_args()
    model=json.load(gzip.open(a.model) if a.model.suffix=='.gz' else a.model.open())
    receipt=json.loads(a.model_receipt.read_text()) if a.model_receipt else None
    if receipt and receipt.get('output_sha256')!=sha(a.model):
        raise ValueError('source receipt does not hash the supplied clock model')
    source_commit=receipt.get('source_commit') if receipt else model.get('source_commit')
    if not source_commit:raise ValueError('clock model needs a source commit or source-bound model receipt')
    db=odb.dbDatabase.create();odb.read_db(db,str(a.odb));block=db.getChip().getBlock();unit=block.getDbUnitsPerMicron()
    roots=[];seen=set();byclass=Counter();entries=Counter();errors=[]
    for bid,kind,eps in intents(model):
        candidates=[n for name in (f'n_{bid}[0]',f'n_{bid}') if (n:=block.findNet(name))]
        if len(candidates)!=1:
            errors.append(dict(bus=bid,kind=kind,reason='actual net missing or ambiguous',count=len(candidates)));continue
        net=candidates[0]
        if net.getName() in seen:raise ValueError(f'duplicate native clock bus {bid}')
        seen.add(net.getName())
        drivers=[p for p in net.getITerms() if p.getIoType()=='OUTPUT']
        if len(drivers)!=1:
            source_pins=[dict(pin=p.getInst().getName()+'/'+p.getMTerm().getName(),
                master=p.getInst().getMaster().getName(),direction=p.getIoType())
                for p in net.getITerms() if p.getInst().getName()==eps[0][0]]
            errors.append(dict(bus=bid,kind=kind,net=net.getName(),reason='actual output driver count',
                output_drivers=len(drivers),expected_source=eps[0],actual_source_pins=source_pins));continue
        source=drivers[0]
        if source.getInst().getName()!=eps[0][0]:
            errors.append(dict(bus=bid,kind=kind,reason='actual/source driver differs',expected_source=eps[0],
                actual_source=source.getInst().getName()+'/'+source.getMTerm().getName()));continue
        loads=[p for p in net.getITerms() if p.getIoType()=='INPUT']
        if {p.getInst().getName() for p in loads}!={e[0] for e in eps[1:]}:
            errors.append(dict(bus=bid,kind=kind,reason='actual/source input instance coverage differs',
                missing=sorted({e[0] for e in eps[1:]}-{p.getInst().getName() for p in loads}),
                extra=sorted({p.getInst().getName() for p in loads}-{e[0] for e in eps[1:]})));continue
        box=source.getBBox();pins=[]
        for p in loads:
            b=p.getBBox();pins.append(dict(pin=p.getInst().getName()+'/'+p.getMTerm().getName(),
                master=p.getInst().getMaster().getName(),x_um=(b.xMin()+b.xMax())/2/unit,
                y_um=(b.yMin()+b.yMax())/2/unit))
        roots.append(dict(bus=bid,kind=kind,net=net.getName(),
            driver=source.getInst().getName()+'/'+source.getMTerm().getName(),
            driver_master=source.getInst().getMaster().getName(),
            driver_xy_um=[(box.xMin()+box.xMax())/2/unit,(box.yMin()+box.yMax())/2/unit],entries=pins))
        byclass[kind]+=1;entries[kind]+=len(pins)
    rec=dict(schema='opentallas.s81.actual_clock_intent.v1',
        scope='SOURCE_CLOCK_BUS_AND_ACTUAL_PIN_TOPOLOGY_ONLY_NO_NATIVE_CLOCK_QUALIFICATION',
        verdict='FAIL_NATIVE_CLOCK_INTENT_BINDING' if errors else 'PASS_CLOCK_INTENT_TOPOLOGY_ONLY',errors=errors,
        odb_sha256=sha(a.odb),model_sha256=sha(a.model),model_source_commit=source_commit,source_receipt_sha256=sha(a.model_receipt) if a.model_receipt else None,
        roots_by_class=dict(byclass),actual_entries_by_class=dict(entries),roots=roots,
        open=['native source/forwarded/generated-clock ratios','source-exact real loads and per-child corner R',
              'physical buffers/wires/PG and propagated TT/FF with unchanged uncertainty'])
    a.out.write_text(json.dumps(rec,separators=(',',':'))+'\n')
    print(json.dumps({k:v for k,v in rec.items() if k not in ['roots','open','errors']}))
    if errors:raise SystemExit(1)


if __name__=='__main__':main()
