#!/usr/bin/env python3
"""Conditional serialized-reference cost of the captured joined native calendar."""
import argparse, hashlib, json, sys
from collections import Counter
from pathlib import Path

def model(root, calendar):
    sys.path.insert(0,str(root/'tools'))
    from qwen_rom_finite_vm_schedule import compile_frame, READ_ORDER, WRITE_ORDER
    x=json.loads(calendar.read_text()); rows=[]; counts=Counter(e['frame'] for e in x['edges'])
    for index,f in enumerate(x['frames']):
        reads=[dict(source=s,seat=i,address=a) for s in READ_ORDER for i,a in f['reads'].get(s,[])]
        writes=[dict(source=r['family'],seat=r['seat'],address=r['address']) for r in f['writes']]
        assert writes==sorted(writes,key=lambda r:(WRITE_ORDER.index(r['source']),r['seat']))
        r=compile_frame(reads,writes)
        rows.append(dict(frame=index,repeated_edges=counts[index],read_seats=len(reads),write_seats=len(writes),families=sorted({w['source'] for w in writes}),**{k:r[k] for k in ('current_adapter_window_misses','physical_write_batches','conservative_current_adapter_edges')}))
    selected=next(e for e in x['edges'] if e['cycle']==160); collision=rows[selected['frame']]
    assert collision['read_seats']==2048 and collision['write_seats']==1 and collision['families']==['REDUCER']
    total=sum(r['repeated_edges']*r['conservative_current_adapter_edges'] for r in rows)
    return dict(schema='opentallas.qwen-vm-parent-service.v1',source_sha256={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [root/'tools/qwen_rom_finite_vm_schedule.py']},calendar_sha256=hashlib.sha256(calendar.read_bytes()).hexdigest(),scope=x['scope'],source_clock='logical native edges held while unchanged serialized reference services immutable PRE frame',active_native_edges=len(x['edges']),serialized_reference_service_edges=total,conditional_additional_native_edges=total-len(x['edges']),delayed_reducer_overlap=dict(parent_edge=160,**collision),frames=rows,assumptions=['Existing controller9-read/28-postverified-write calendar and full2256/865 source walkers only','Reads precede ordered writes, including delayed reducer at160; no independent-provider overlap credit','Empty logical frames cost one native edge only if actual admission implementation proves bypass','All native core, sequencer, response, progress and collective participants obey joint admission','This address-only composition does not close four-state backend data-X/postverify-ACK failure'],full_target_enrollment=False,measured_parent_latency=False,full_token_latency=None,physical_admission=False,adopted=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--calendar',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();r=model(a.root,a.calendar);a.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ('frames','source_sha256','assumptions')}))
