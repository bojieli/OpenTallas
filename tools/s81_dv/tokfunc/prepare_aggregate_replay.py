#!/usr/bin/env python3
"""Actual VQ source fragments + native XS/CAP words -> explicit local ri_e replay.

This writes source-connected replay inputs, never a positive verdict. Every
context's measured source cycles and chosen retiming are retained. Host ages,
global KS/END, and predicted aggregate return/FIN ages are never imported.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--producer',type=Path,required=True)
    p.add_argument('--source-assets',type=Path,required=True)
    p.add_argument('--inventory',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--gather-origin',type=int,required=True)
    p.add_argument('--command-origin',type=int,required=True)
    a=p.parse_args()
    producer=json.loads((a.producer/'receipt.json').read_text())
    assert producer['status']=='ACTUAL_COMPOSITIONAL_NORM_PRODUCER_COMPONENT_ONLY'
    assert not producer['scoreboard_only']['mismatches']
    inventory=json.loads(a.inventory.read_text())
    assets=json.loads((a.source_assets/'assets.json').read_text())
    assert assets['inventory_sha256']==sha(a.inventory)
    assert assets['die_sha256']==inventory['die_sha256']
    for rel,d in assets['files'].items():assert sha(a.source_assets/rel)==d
    a.out.mkdir(parents=True,exist_ok=False)
    packets=[]
    outputs=sorted(producer['actual_leaf_outputs'],key=lambda c:5*c['sid']+c['leaf'])
    assert len(outputs)==80
    for expected,context in enumerate(outputs):
        beat=5*context['sid']+context['leaf'];assert beat==expected
        trace=a.producer/f'sid{context["sid"]}_leaf{context["leaf"]}.log'
        assert sha(trace)==context['log_sha256']
        fragments=context['xf'];assert len(fragments)==4
        assert [f['first'] for f in fragments]==[1,0,0,0]
        assert [f['cycle']-fragments[0]['cycle'] for f in fragments]==[0,1,2,3]
        word=sum(int(f['data276'],16)<<(276*i) for i,f in enumerate(fragments))
        assert word&1 and (word>>1)&7==1 and (word>>4)&31==1
        assert (word>>9)&15==context['sid'] and (word>>13)&255==beat
        local=a.gather_origin+2*beat
        packets.append(dict(edge=local,kind='ACTUAL_VQ_XQ',data1104=f'{word:0276x}',
            sid=context['sid'],leaf=context['leaf'],global_beat=beat,
            source_fragment_cycles=[f['cycle'] for f in fragments],
            source_first_fragment_to_local_line_edge_offset=local-fragments[0]['cycle'],
            conversion='four consecutive real VQ fragments concatenated low-first; no payload changes',
            source_log_sha256=context['log_sha256']))
    assert a.command_origin>a.gather_origin+160
    for half in ['A','B']:
        native_path=next((a.source_assets/half/'prog').rglob('programme.json'))
        native=json.loads(native_path.read_text())
        assert native['selected_slice_source']['streamer']=='ot_s81sl_xs4'
        assert native['selected_slice_source']['streamer_added_capture_edges']==1
        events=list(packets)
        for c in native['command_descriptors']:
            payload=int(c['payload186'],16)
            assert payload&65535==2 and (payload>>16)&31==c['target']
            word=1|(1<<4)|(payload<<21)
            events.append(dict(edge=a.command_origin+c['relative_pin_edge'],kind='NATIVE_CTL',
                target=c['target'],data1104=f'{word:0276x}',
                relative_calendar_edge=c['relative_pin_edge'],body160=c['body160']))
        events.sort(key=lambda e:e['edge'])
        assert len({e['edge'] for e in events})==len(events)
        out=a.out/half;out.mkdir()
        rom=out/'rom';rom.mkdir()
        for image in (a.source_assets/half/'rom').glob('*.viamap.hex'):
            shutil.copy2(image,rom/image.name)
        for image in native_path.parent.glob('*.viamap.hex'):
            target=rom/image.name
            if target.exists():assert sha(target)==sha(image),('shared XS image mismatch',image.name)
            else:shutil.copy2(image,target)
        (out/'ri_e_packets.txt').write_text(''.join(f'{e["edge"]} {e["data1104"]}\n' for e in events))
        record=dict(schema='opentallas.s81.aggregate_local_replay.v1',status='SOURCE_REPLAY_STAGED_NOT_EXECUTED',
            boundary='actual u_s_0N.ri_e raw slice input; adapter must bind this exact pin or measure retained incoming transport',
            selected_slice=inventory['selected_slice'],die_sha256=inventory['die_sha256'],
            producer_receipt_sha256=sha(a.producer/'receipt.json'),native_programme_sha256=sha(native_path),
            source_assets_sha256=sha(a.source_assets/'assets.json'),inventory_sha256=sha(a.inventory),
            production_ROM_images={f.name:sha(f) for f in rom.iterdir()},
            gather_origin=a.gather_origin,command_origin=a.command_origin,events=events,
            expected_XRT_pin_age=dict(edges=5,qualification='SOURCE MODEL TO BE MEASURED ON SELECTED RSTOPT_XO/XRT'),
            clocks='preserve every named source clock and forwarded clock path; no independent frame broadcast',
            capture=native['capture'],physical_phase_qualified=False,global_epoch_bound=False,
            excluded_historical_fields=['route.edges','programme_origin','source_frame_minimum',
                'source_last_return_pin_minimum','retire_not_before','inherited_op_end'],
            required_actual_observations=['ri_e→XR is_v/cfg_v', 'XS4 output and every actual frame x/xk/LK/xo',
                'all six frame returns and true return landing clocks', 'CAP cfg/FIN/collision/write transition traces'])
        (out/'replay.json').write_text(json.dumps(record,indent=1)+'\n')


if __name__=='__main__':main()
