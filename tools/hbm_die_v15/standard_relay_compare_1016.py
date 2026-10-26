#!/usr/bin/env python3
"""Actual source-pinned standard relay native arcs and624-bit station costs."""
import argparse
import hashlib
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as PA


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ref',default='a0924c57c')
    ap.add_argument('--out',default='results/arch/hbm_die_v15/relay_compare_1016.json')
    a=ap.parse_args();rows=[]
    for width in [48,136,304,624,1136]:
        for flow in ['WE','EW','SN','NS']:
            master=f'hbfd_rly_{width}_{flow}';base=f'physical/ref_tile/hbfd_rly_{width}_{flow.lower()}/views/{master}/'
            get=lambda name:subprocess.check_output(['git','-C',str(ROOT),'show',a.ref+':'+base+name],stderr=subprocess.DEVNULL)
            try:raw={f:get(f) for f in [master+'.lef',master+'_tt.lib',master+'_ff.lib','insertion.json','abstract.json']}
            except subprocess.CalledProcessError:
                rows.append(dict(master=master,error='missing actual view'));continue
            ins=json.loads(raw['insertion.json']);abstract=json.loads(raw['abstract.json'])
            tables={}
            for corner in ['tt','ff']:
                with tempfile.NamedTemporaryFile(suffix='.lib') as f:
                    f.write(raw[master+'_'+corner+'.lib']);f.flush();lib=PA.parse_lib(f.name)
                    refs=PA.clock_refs(lib,ins,corner);tables[corner]=PA.pin_metrics(lib,refs)
            sizes=re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',raw[master+'.lef'].decode());w,h=map(float,sizes.groups())
            n=math.ceil(624/width);used=[624//n+(k<624%n) for k in range(n)]
            native=[]
            for count in used:
                out=max(tables['tt'][f'o[{k}]']['out'] for k in range(count))
                inp=max(tables['tt'][f'i[{k}]']['inp'] for k in range(count))
                hold=min(tables['ff'][f'o[{k}]']['lmin']-tables['ff'][f'i[{k}]']['hold']-115 for k in range(count))
                native.append(dict(bits=count,launch_max_ps=out,capture_max_ps=inp,
                                   ff_hold_after25plus90_ps=hold,pin_native_pass=out<=220 and inp<=190))
            allout=max(v['out'] for k,v in tables['tt'].items() if k.startswith('o['))
            allin=max(v['inp'] for k,v in tables['tt'].items() if k.startswith('i['))
            boundary=ins['tt']['boundary'];spread=boundary['max']-boundary['min']
            maxo=max(x['launch_max_ps'] for x in native);maxs=max(x['capture_max_ps'] for x in native)
            skew=150 if boundary['mean']>300 else 90
            reach=(833.3-60-skew-maxo-maxs)/.76
            export=abstract.get('verdict',{}).get('check',{})
            row=dict(master=master,width=width,flow=flow,source_ref=a.ref,view=base,
                     hashes={f:hashlib.sha256(b).hexdigest() for f,b in raw.items()},
                     export_verdict_checks=export,outline_um=[w,h],one_station_leaves=n,
                     one_station_area_mm2=n*w*h/1e6,
                     area_scope='native leaf footprints only; excludes composition reset/clock/wire glue',
                     composition_reset_extra_ff=15 if width==48 else None,
                     composition_reset_scope='13 region + 2 sync FF for source-proven 13x48 station' if width==48 else 'not established for this composition',
                     one_station_clock_sinks=n*ins['tt'].get('all',{}).get('n',boundary['n']),
                     unused_lanes=n*width-624,payload_lane_map=used,
                     full_master_launch_ps=allout,full_master_capture_ps=allin,
                     full_master_native_pass=allout<=220 and allin<=190 and spread<=80,
                     payload_native_pass=all(x['pin_native_pass'] for x in native) and spread<=80,
                     payload_native=native,tt_insertion_mean_ps=boundary['mean'],tt_boundary_spread_ps=spread,
                     conservative_stream_reach_um=round(reach,3),
                     reach_scope='same candidate kind; strongest used-bit O plus strongest used-bit S; measured reference; no source/sink endpoint views or routed wire')
            rows.append(row)
    out=dict(schema='opentallas.hbm.relay_compare.v1',payload_bits=624,views=rows,
             qualification='COMPARISON_ONLY_NO_SOURCE_OR_DIE_ADOPTION',
             obligations=['source must instantiate selected real master leaves with explicit lane padding',
                          'count actual footprints/pins/clocks/cuts and per-bit native reach',
                          '13x48 reset composition adds 15 FF per station; qualify actual reset placement/release and price glue',
                          'no source cycles changed without measured compiler/performance proof'])
    (ROOT/a.out).write_text(json.dumps(out,indent=1)+'\n')
    for r in rows:
        if 'error' in r:print(r['master'],r['error']);continue
        print(r['master'],'O/S',round(r['full_master_launch_ps'],2),round(r['full_master_capture_ps'],2),
              'full/pass',r['full_master_native_pass'],r['payload_native_pass'],'reach',r['conservative_stream_reach_um'],
              'area',r['one_station_area_mm2'])


if __name__=='__main__':main()
