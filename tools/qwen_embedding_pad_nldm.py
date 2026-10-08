#!/usr/bin/env python3
"""Source-pinned BUFx2 NLDM chain estimates, not physical closure evidence."""
import argparse,bisect,gzip,hashlib,json,re
from pathlib import Path

def block(text,kind,name=None):
    pat=r'\b'+re.escape(kind)+r'\s*\(\s*'+(re.escape(name) if name else '[^)]*')+r'\s*\)\s*\{'
    m=re.search(pat,text)
    if not m: raise ValueError((kind,name))
    start=m.end(); depth=1; i=start
    while depth:
        depth+=(text[i]=='{')-(text[i]=='}');i+=1
    return text[start:i-1]

def number(text,key):
    return float(re.search(r'\b'+re.escape(key)+r'\s*:\s*([-+\deE.]+)',text)[1])

def caps(text,cell,pin):
    p=block(block(text,'cell',cell),'pin',pin)
    return {pol:number(p,pol+'_capacitance') for pol in ('rise','fall')}

def table(text,kind):
    b=block(text,kind)
    axis=lambda n:[float(x) for x in re.search(r'index_'+str(n)+r'\s*\("([^"]+)"\)',b)[1].split(',')]
    rows=[[float(x) for x in row.split(',')] for row in re.findall(r'"([^"]+)"',b[b.index('values'):])]
    x,y=axis(1),axis(2)
    assert len(rows)==len(x) and all(len(r)==len(y) for r in rows)
    return x,y,rows

def interpolate(tbl,slew,load,mode='linear'):
    x,y,z=tbl
    outside=[]
    for name,a,v in [('slew_ps',x,slew),('load_ff',y,load)]:
        if v<a[0] or v>a[-1]: outside.append({'axis':name,'value':v,'range':[a[0],a[-1]]})
    if mode=='clamp': slew=max(x[0],min(x[-1],slew));load=max(y[0],min(y[-1],load))
    i=max(0,min(len(x)-2,bisect.bisect_right(x,slew)-1));j=max(0,min(len(y)-2,bisect.bisect_right(y,load)-1))
    a=(slew-x[i])/(x[i+1]-x[i]);b=(load-y[j])/(y[j+1]-y[j])
    val=(1-a)*((1-b)*z[i][j]+b*z[i][j+1])+a*((1-b)*z[i+1][j]+b*z[i+1][j+1])
    return val,outside

def chain(tables,count,pol,internal_cap,final_cap,input_slew=150.,mode='linear',wire_cap=0.):
    slew=input_slew; total=0.; stages=[]
    for k in range(count):
        load=(internal_cap if k<count-1 else final_cap)+wire_cap
        delay,extra=interpolate(tables['cell_'+pol],slew,load,mode)
        out_slew,extra2=interpolate(tables[pol+'_transition'],slew,load,mode)
        stages.append({'stage':k+1,'input_slew_ps':slew,'load_ff':load,'delay_ps':delay,'output_slew_ps':out_slew,'outside_table':extra})
        assert extra==extra2 and delay>0 and out_slew>0
        total+=delay;slew=out_slew
    return {'delay_ps':total,'output_slew_ps':slew,'stages':stages,'has_extrapolation':any(s['outside_table'] for s in stages)}

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,default=Path(__file__).resolve().parents[1]/'results/uarch/topk_station_SSFF_cell_model_20261002/inputs');p.add_argument('--out',type=Path,default=Path(__file__).with_name('characterization.json'));a=p.parse_args()
    result={'purpose':'Analytical pad sizing only; fresh routed SS/FF and DRC are required.','units':{'time':'ps','capacitance':'fF','slew':'10%-90%, slew_derate_from_library=1'},'input_slew_ps':150,'limitations':['Cell-only delays exclude routed wire resistance, wire capacitance, clock insertion, setup/hold/recovery/removal constraints and resizer changes.','Nominal pin rise/fall capacitances from Liberty are used, not a waveform-dependent effective-capacitance solver.','BUFx2 input load is below its characterized output-load minimum; linear edge extrapolation is required for internal stages. Every extrapolated stage is flagged.','Clamped table-edge sensitivity is included, but neither result is a rigorous silicon bound.','Added wire-capacitance scenarios 0, 0.5 and 1 fF are sensitivities, not measured wire bounds.','SS worst and FF best refer only to extrema over the two polarities for each stated load scenario.'], 'libraries':{},'corners':{}}
    for corner in ['SS','FF']:
        paths=[a.inputs/f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz',a.inputs/f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib']
        inv=gzip.open(paths[0],'rt').read();seq=paths[1].read_text()
        for path,txt in zip(paths,[inv,seq]):
            assert 'time_unit : "1ps"' in txt and 'capacitive_load_unit (1,ff)' in txt
            assert 'slew_derate_from_library : 1;' in txt
            assert all(f'slew_{bound}_threshold_pct_{pol} : {value};' in txt for bound,value in [('lower',10),('upper',90)] for pol in ['rise','fall'])
            result['libraries'][str(path)]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'time_unit':'1ps','capacitance_unit':'1ff'}
        names={'buffer_a':(inv,'BUFx2_ASAP7_75t_R','A'),'inverter_a':(inv,'INVx1_ASAP7_75t_R','A'),'dff_d':(seq,'DFFHQNx1_ASAP7_75t_R','D'),'async_dff_d':(seq,'DFFASRHQNx1_ASAP7_75t_R','D'),'async_resetn':(seq,'DFFASRHQNx1_ASAP7_75t_R','RESETN'),'async_setn':(seq,'DFFASRHQNx1_ASAP7_75t_R','SETN')}
        cp={key:caps(*args) for key,args in names.items()}
        template=block(inv,'lu_table_template','delay_template_7x7_x1')
        assert 'variable_1 : input_net_transition;' in template and 'variable_2 : total_output_net_capacitance;' in template
        buf=block(inv,'cell','BUFx2_ASAP7_75t_R'); tables={key:table(buf,key) for key in ['cell_rise','cell_fall','rise_transition','fall_transition']}
        loads={'next_buffer':{'buffer_a':1},'dff_d_plus_inverter':{'dff_d':1,'inverter_a':1},'two_dff_d':{'dff_d':2},'four_dff_d':{'dff_d':4},'two_async_dff_d':{'async_dff_d':2},'four_resetn':{'async_resetn':4},'two_resetn_two_setn':{'async_resetn':2,'async_setn':2}}
        cr={'pin_capacitance_ff':cp,'load_recipes':loads,'runs':[]};result['corners'][corner]=cr
        for mode in ['linear','clamp']:
            for wire in [0.,.5,1.]:
                for label,recipe in loads.items():
                    for n in range(1,13):
                        pols={pol:chain(tables,n,pol,cp['buffer_a'][pol],sum(cp[key][pol]*mult for key,mult in recipe.items()),mode=mode,wire_cap=wire) for pol in ['rise','fall']}
                        cr['runs'].append({'mode':mode,'extra_wire_cap_ff_per_stage':wire,'final_load':label,'count':n,'minimum_polarity_delay_ps':min(q['delay_ps'] for q in pols.values()),'maximum_polarity_delay_ps':max(q['delay_ps'] for q in pols.values()),'polarities':pols})
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    # Exact table-node and bilinear arithmetic checks; excludes physical claims.
    t=([0.,2.],[0.,4.],[[0.,4.],[2.,6.]])
    assert interpolate(t,1.,2.)[0]==3. and interpolate(t,2.,4.)[0]==6.
    assert interpolate(t,-1.,2.)[0]==1. and interpolate(t,-1.,2.,'clamp')[0]==2.
    print(a.out)
    for corner in ['SS','FF']:
        print(corner,'6 stages, linear extrapolation, zero wirecap:')
        for run in result['corners'][corner]['runs']:
            if run['count']==6 and run['mode']=='linear' and run['extra_wire_cap_ff_per_stage']==0:
                print(run['final_load'],round(run['minimum_polarity_delay_ps'],3),round(run['maximum_polarity_delay_ps'],3))
if __name__=='__main__':main()
