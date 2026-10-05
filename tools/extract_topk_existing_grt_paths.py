#!/usr/bin/env python3
"""Parse read-only existing GRT timing replay. Does not run any physical flow."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

def extract(text,metrics):
    if 'worst slack max' not in text or re.search(r'\[ERROR ',text):raise ValueError('incomplete/error report')
    chunks=text.split('Startpoint: ')[1:]
    if len(chunks)!=10:raise ValueError('path coverage')
    paths=[]
    for chunk in chunks:
        start=chunk.splitlines()[0].strip()
        def field(name):
            m=re.search('^'+re.escape(name)+r': (.+)$',chunk,re.M)
            if not m:raise ValueError('missing field '+name)
            return m[1].strip()
        end=field('Endpoint');corner=field('Corner')
        if corner!='WC' or field('Path Type')!='max':raise ValueError('wrong path corner/type')
        if not start.startswith('cnt[') or not end.startswith('suf['):raise ValueError('unbound source endpoint')
        slack=re.search(r'(-?\d+\.\d+)\s+slack \(VIOLATED\)',chunk)
        if not slack:raise ValueError('missing slack')
        entries=[]
        for line in chunk.splitlines():
            m=re.match(r'^\s*([\d.\s-]+)\s+([\^v]) (\S+) \(([^)]+)\)$',line)
            if not m:continue
            nums=[float(x) for x in m[1].split()]
            if len(nums) not in (3,5):continue
            entries.append({'pin':m[3],'cell':m[4],'edge':m[2],'delay_ps':nums[-2],'arrival_ps':nums[-1],
                'arc_kind':'cell_output' if len(nums)==5 else 'wire_to_input','slew_ps':nums[-3],
                'fanout':int(nums[0]) if len(nums)==5 else None,'capacitance_fF':nums[1] if len(nums)==5 else None})
        launch=next((i for i,e in enumerate(entries) if e['pin']==start+'/CLK'),None)
        capture=next((i for i,e in enumerate(entries) if e['pin']==end+'/D'),None)
        if launch is None or capture is None or launch>=capture:raise ValueError('missing launch/capture pins')
        data=entries[launch+1:capture+1]
        clkq=data[0]
        if not clkq['pin'].startswith(start+'/Q'):raise ValueError('missing clock-to-Q')
        cells=[e for e in data if e['arc_kind']=='cell_output'];wires=[e for e in data if e['arc_kind']=='wire_to_input']
        delay=data[-1]['arrival_ps']-entries[launch]['arrival_ps']
        if abs(delay-sum(e['delay_ps'] for e in data))>0.1:raise ValueError('arc delay accounting')
        paths.append({'startpoint':start,'endpoint':end,'corner':corner,'slack_ps':float(slack[1]),
            'data_arrival_ps':data[-1]['arrival_ps'],'launch_clock_arrival_ps':entries[launch]['arrival_ps'],
            'clock_to_Q_ps':clkq['delay_ps'],'data_path_delay_including_clock_to_Q_ps':delay,
            'data_cell_output_arcs':len(cells),'combinational_cell_output_arcs':len(cells)-1,
            'data_cell_delay_ps':sum(e['delay_ps'] for e in cells),'data_wire_delay_ps':sum(e['delay_ps'] for e in wires),
            'cell_histogram':dict(Counter(e['cell'] for e in cells)),'data_arc_trace':data})
    if len({p['endpoint'] for p in paths})!=10:raise ValueError('duplicate endpoint')
    reported=float(re.search(r'worst slack max (-?\d+\.\d+)',text)[1])
    baseline=metrics['globalroute__timing__setup__ws']
    if abs(paths[0]['slack_ps']-reported)>0.02 or abs(reported-baseline)>0.05:raise ValueError('GRT WS reproduction mismatch')
    return {'status':'FAILED_TIMING_AS_BUILT_EXISTING_GRT_REPRODUCED','original_ws_ps':baseline,'replay_ws_ps':reported,
        'paths':paths,'source_operation':'S_PICK pk==0: a=0; for b=NBIN-1..0: suf[b]<=a; a=a+cnt[b]',
        'source_location':'topk_source.sv:195-201','source_bin_count':256,
        'interpretation':'All ten max paths launch cnt254 and capture suffix counts, consistent with the source single-cycle suffix accumulation. Exact cell/wire arcs recorded; no guessed critical-path replacement.',
        'physical_closure':False,'DRT_terminal_claim':False,'new_place_route':False,
        'method':'exact remote tool and SS/FF libs, existing GRT ODB/SDC and same RC; estimate_parasitics -global_routing then report_checks locally; no timing constraints changed',
        'warning':'report_checks emitted unknown field nets; ignored presentation field, all pin/cell delays and reproduced slack retained. No tool error.'}

if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('log',type=Path);a.add_argument('metrics',type=Path);a.add_argument('output',type=Path);args=a.parse_args()
    r=extract(args.log.read_text(),json.loads(args.metrics.read_text()));args.output.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:r[k] for k in ['status','original_ws_ps','replay_ws_ps']}))
