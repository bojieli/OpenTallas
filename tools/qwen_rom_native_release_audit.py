#!/usr/bin/env python3
"""Independent full new-FF census and stage/ACK load audit of native r2.
No re-elaboration, map, hardware timing exception or new decode run.
"""
import collections
import gzip
import json
import hashlib
from pathlib import Path
import qwen_rom_native_local_release as J
R=J.R;M=J.M;N=J.N
OUT=J.OUT


def allocation():
    b,_,_,_=J.load()
    b.g=json.loads(gzip.decompress((R.ROOT/OUT/'allocation-r2.json.gz').read_bytes()))
    for row in b.g['source_clock_sinks']:b.net['cells'].setdefault(row['instance'],dict(type=row['cell'],connections={}))
    return b


def internal_stages(b):
    result={};g=b.g;coords=g['nominal_node_coordinates_um'];joins=R.obj(R.OUT/'inputs/launch_join_cells_r1.json')
    ackout=collections.defaultdict(list)
    for e in g['ACK_edges']:ackout[e['driver']].append(e)
    for corner in ('ss','ff'):
        _,libs,caps=R.library(corner)
        ck,_,_=M.propagate(g,b.net,corner,{g['root_driver']:{t:[0,0,5,80] for t in ('rise','fall')}})
        seeds={}
        for q in g['local_release_groups']:
            ff=q['FFs'][0];inv=q['inversions'][0];entry=q['hold_entry'];clk=ck[ff+':CLK']['rise']
            w0=max(2,sum(abs(a-c) for a,c in zip(coords[ff],coords[inv])))
            w1=max(2,sum(abs(a-c) for a,c in zip(coords[inv],coords[entry])))
            qcap=caps[(J.INV,'A')]['cap_fF']+J.C*w0;load=caps[(R.BUF,'A')]['cap_fF']+J.C*w1
            waves={}
            for transition,opposite in (('rise','fall'),('fall','rise')):
                delay=R.envelope(libs[R.ASR],'cell_'+opposite,qcap,*clk[2:],related='CLK')
                sl=R.envelope(libs[R.ASR],opposite+'_transition',qcap,*clk[2:],related='CLK')
                d=R.envelope(libs[J.INV],'cell_'+transition,load,*sl);s=R.envelope(libs[J.INV],transition+'_transition',load,*sl)
                rc=.0265684*(w0*(J.C*w0/2+caps[(J.INV,'A')]['cap_fF'])+w1*(J.C*w1/2+caps[(R.BUF,'A')]['cap_fF']))/1000
                waves[transition]=[clk[0]+delay[0]+d[0]+rc,clk[1]+delay[1]+d[1]+rc,*s]
            seeds[entry]=waves
        data,_,_=M.propagate(g,b.net,corner,seeds);rows=[]
        for q in g['local_release_groups']:
            clock=ck[q['FFs'][1]+':CLK']['rise'];wave=data[q['FFs'][1]+':D'];margin={}
            for transition,d in wave.items():
                setup=N.L.constraint(libs[R.ASR],'setup',transition,d[2:],clock[2:])
                hold=N.L.constraint(libs[R.ASR],'hold',transition,d[2:],clock[2:])
                margin[transition]=dict(setup_margin_ps=clock[0]+J.H.PERIOD-d[1]-setup-60,
                    hold_margin_ps=d[0]-clock[1]-hold-25)
            rows.append(dict(group=q['group'],margins=margin))
        loads=[]
        for driver,edges in ackout.items():
            typ=g['ACK_nodes'][driver]['type'];cap=0
            for e in edges:
                target=g['ACK_nodes'].get(e['sink'],dict(type=R.ASR))['type']
                cap+=J.C*e['length_um']+(joins[corner]['pin_caps_fF'][e['pin']] if target==J.AND else caps[(target,e['pin'])]['cap_fF'])
            cell=joins[corner]['cell_definition'] if typ==J.AND else libs[typ]
            table=R.tables(cell,'cell_rise')[0];limits=[table[1][0],table[1][-1]]
            loads.append(dict(driver=driver,type=typ,wire_and_sink_cap_fF=cap,characterized_cap_range_fF=limits,
                in_characterization=limits[0]<=cap<=limits[1]))
        result[corner]=dict(local_FF_stage_checks=rows,
            setup_failures=sum(any(m['setup_margin_ps']<0 for m in row['margins'].values()) for row in rows),
            hold_failures=sum(any(m['hold_margin_ps']<0 for m in row['margins'].values()) for row in rows),
            minimum_setup_margin_ps=min(m['setup_margin_ps'] for r in rows for m in r['margins'].values()),
            minimum_hold_margin_ps=min(m['hold_margin_ps'] for r in rows for m in r['margins'].values()),
            ACK_output_load_checks=loads,ACK_out_of_characterization=sum(not r['in_characterization'] for r in loads))
    return result


def price():
    b=allocation();m=J.record('model-r2.json');m['schema']='QWEN_NATIVE_RELEASE_FULL_NEW_FF_AUDIT_R3'
    m['timing']=J.checks(b);m['stage_and_ACK_audit']=internal_stages(b)
    m['allocation_sha256']=R.sha(OUT/'allocation-r2.json.gz');m['preserved_prior_model_sha256']=hashlib.sha256(J.model_bytes('model-r2.json')).hexdigest()
    m['all_new_raw_reset_FF_checks_include_ACK_receiver']=True
    m['complete_reserved_cell_area_scope']='Mapped subtotal and explicitly allocated primitives only; missing ACK receiver data/hold route and source-owned parent launch integration remain unpriced. Not a completed physical provider.'
    m['accepted_demand_admission']=False
    m['unqualified'].append('ACK_receiver_FF0_FF1_D_route_and_hold_cost')
    return m


if __name__=='__main__':
    path=R.ROOT/OUT/'model-r3.json'
    if path.exists() or path.with_suffix('.json.gz').exists():raise ValueError('preserve verdict')
    m=price();M.write(path,m)
    print({c:dict(raw_FF_reset_failures=t['raw_reset_failures'],controlled_reset_failures=t['controlled_reset_failures'],
        stage_setup_failures=m['stage_and_ACK_audit'][c]['setup_failures'],stage_hold_failures=m['stage_and_ACK_audit'][c]['hold_failures'],
        ACK_load_failures=m['stage_and_ACK_audit'][c]['ACK_out_of_characterization']) for c,t in m['timing'].items()},flush=True)
