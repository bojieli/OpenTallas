"""Measured reduced-system registered-head debit; no async or clock gain."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 'results/rtl/qwen_rom_system_rtl_20261003/registered_head/'
OUT = 'results/uarch/qwen_headreg_measured_cost_20261003/model.json'


def price(record):
    if record['status']!='pass' or not record['source_stable'] or not record['images_stable']:
        raise ValueError('stable actual context PASS required')
    rows=[]
    for name in ('c1p1ah_u1','c1p1ah_u1_fphase1'):
        r=record['runs'][name]
        if not r['pass'] or r['returncode']!=0 or '+CLK=split' not in r['args'] or '+USERS=1' not in r['args']:
            raise ValueError('actual single-user split context required')
        before,after=r['reference_cycles'],r['cycles']
        if after-before!=126 or r['added_cycles']!=126:
            raise ValueError('source-measured debit is 126, not the prospective72')
        # cyc is incremented on sclk, not fclk: the harness uses four
        # 3.6GHz ticks per sclk edge. 126 counts therefore cost 140ns.
        rows.append(dict(case=name,reference_cycles=before,measured_cycles=after,
            added_sclk_cycles=126,sclk_hz=900000000, functional_added_ns=140.0,
            same_clock_context_rate_ratio=before/after,
            same_clock_context_rate_debit_percent=100*(1-before/after),
            full_token_rate=None, physical_clock_gain=None))
    return dict(schema='opentallas.qwen.headreg.measured-cost.v1',
        status='MEASURED_REDUCED_SYSTEM_CONTEXT_DEBIT_NOT_ADOPTED',rows=rows,
        projected72_not_used=True,clock_fix_adopted=False,async_adopted=False,
        asyncsub1_rejection_preserved=True,rate_bonus=0,
        physical_setup_hold_qualification=False,
        transfer_rule='apply 126 slow-domain cycles only to this matched reduced context; other token geometries require an actual dependency calendar',
        scope='reduced G4/NW16 system,18 checked steps including prompt/generation; no per-token division/extrapolation',
        future_same_scope_clock_price='(baseline_cycles+126)/qualified_sclk_Hz; a future SS/FF clock change requires source-matched measurement, never a free bonus')


def build(root=ROOT):
    names=[BASE+'result.json',BASE+'model.json',BASE+'source_relocation.json',
        'rtl/test/qwen_sys/async/headreg/tb_qwen_rom_sys.sv','rtl/test/qwen_sys/qsys_harness2.cpp']
    blobs={p:(root/p).read_bytes() for p in names}
    record=json.loads(blobs[names[0]])
    relocation=json.loads(blobs[names[2]])['byte_identical_source_relocation']
    aliases={new:old for old,new in relocation.items()}
    for p in names[3:]:
        if hashlib.sha256(blobs[p]).hexdigest()!=record['source_sha256'][aliases.get(p,p)]:
            raise ValueError('actual cycle-counter/harness source pin mismatch')
    bench=blobs[names[3]].decode(); harness=blobs[names[4]].decode()
    if 'wire clk = sclk;' not in bench or 'cyc <= cyc + 1;' not in bench or 'int sper = 4' not in harness or '2500.0 / 9.0' not in harness:
        raise ValueError('source clock/count contract changed')
    result=price(record)
    result['input_sha256']={p:hashlib.sha256(b).hexdigest() for p,b in blobs.items()}
    for p in ['tools/qwen_headreg_measured_cost.py','tools/uarch_model.py']:
        result['input_sha256'][p]=hashlib.sha256((root/p).read_bytes()).hexdigest()
    return result


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--verify',action='store_true')
    args=ap.parse_args();out=ROOT/OUT;payload=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    if args.verify:
        if out.read_text()!=payload:raise ValueError('record drift')
    else:out.parent.mkdir(parents=True,exist_ok=True);out.write_text(payload)
    print('PASS actual126 slowcycles/140ns debit; no async or physical clock gain')
