"""Price root hold repair from paired actual SS/FF and production Liberty tables.

No RTL, clocks or timing constraints are changed by this analytical model.
"""
import bisect
import gzip
import hashlib
import json
import re
from pathlib import Path
import uarch_topk_station_SSFF_cell_model as C
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'results/rtl/s81_ph_20261006/gather/root_selective_model_20261007'

def build():
    manifest = json.loads((C.BASE / 'source_manifest.json').read_text())
    inherited_pins = {}
    for corner in ['SS', 'FF']:
        for name in [f'asap7sc7p5t_SEQ_RVT_{corner}_nldm_220123.lib', f'asap7sc7p5t_INVBUF_RVT_{corner}_nldm_220122.lib.gz']:
            path = C.BASE / 'inputs' / name
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != manifest[name]['sha256']:
                raise ValueError('Pinned cell library changed: ' + name)
            inherited_pins[str(path.relative_to(ROOT))] = digest
    base=BASE; names=[f'HB{i}xp67_ASAP7_75t_R' for i in range(1,5)]
    lib={c:{n:C.cell_facts(gzip.decompress((C.BASE/'inputs'/f'asap7sc7p5t_INVBUF_RVT_{c.upper()}_nldm_220122.lib.gz').read_bytes()).decode(),n) for n in names} for c in ['ss','ff']}
    def interp(t,s,l):
     x,y=t['index1'],t['index2']
     if not x[0]<=s<=x[-1] or not y[0]<=l<=y[-1]:raise ValueError((s,l))
     i=max(0,min(len(x)-2,bisect.bisect_right(x,s)-1));j=max(0,min(len(y)-2,bisect.bisect_right(y,l)-1));a=(s-x[i])/(x[i+1]-x[i]);b=(l-y[j])/(y[j+1]-y[j]);v=t['values'];return (1-a)*((1-b)*v[i][j]+b*v[i][j+1])+a*((1-b)*v[i+1][j]+b*v[i+1][j+1])
    rows={};flops={}
    for c in ['ss','ff']:
     raw=(C.BASE/'inputs'/f'asap7sc7p5t_SEQ_RVT_{c.upper()}_nldm_220123.lib').read_text()
     for b in gzip.decompress((base/f'{c}.log.gz').read_bytes()).decode().split('ROOT_EDGE ')[1:]:
      name,edge=b.splitlines()[0].rsplit(' ',1)
      if 'No paths found.' in b:continue
      p=b.split('data arrival time')[0];end=next(l for l in reversed(p.splitlines()) if '/D (' in l);nums=end.split();master=re.search(r'\(([^)]+)\)',end)[1]
      if (c,master) not in flops:
       f=C.cell_facts(raw,master,True);f['D_cap']=C.number(C.group(C.group(raw,'cell',master),'pin','D'),'capacitance');flops[c,master]=f
      r=rows.setdefault(name,{'endpoint':name,'master':master});r[c+'_'+edge]=dict(slew=float(nums[0]),clock_slew=float(next(l.split()[0] for l in b.splitlines() if (' '+name[:-2]+'/CLK (') in l)),slack=float(re.search(r'([+-]?[\d.]+)\s+slack \(',b)[1]))
    for r in rows.values():
     opts=[]
     if len([k for k in r if k.startswith(('ss_','ff_'))])!=4:r['incomplete']=True;continue
     for n in names:
      pred={};loads={}
      try:
       for c in ['ss','ff']:
        f=flops[c,r['master']];load=f['D_cap']+(.18 if c=='ss' else 0);loads[c]=load
        for edge in ['rise','fall']:
         old=r[c+'_'+edge];tables=lib[c][n]['delay_transition_tables'];d=interp(tables['cell_'+edge],old['slew'],load);new=interp(tables[edge+'_transition'],old['slew'],load)
         tab=f['setup_rising' if c=='ss' else 'hold_rising'][edge+'_constraint'];delta=interp(tab,new,old['clock_slew'])-interp(tab,old['slew'],old['clock_slew']);pred[c+'_'+edge]=old['slack']+(-d if c=='ss' else d)-delta
      except ValueError:continue
      if min(pred['ss_'+e] for e in ['rise','fall'])>=15 and min(pred['ff_'+e] for e in ['rise','fall'])>=17:opts.append(dict(cell=n,predicted_slacks_ps=pred,load_fF=loads,area_um2=lib['ss'][n]['area_um2']))
     r['options']=opts
    
    m={'C':C,'interp':interp,'base':base,'rows':rows,'flops':flops,'lib':lib,'names':names}
    I=interp
    results={}
    for c in ['ss','ff']:
     raw=gzip.decompress((base/'libs'/f'asap7sc7p5t_AO_RVT_{c.upper()}_nldm_211120.lib.gz').read_bytes()).decode();gate=C.group(raw,'cell','AOI21x1_ASAP7_75t_R');gp=C.group(gate,'pin','A1');cap=C.number(gp,'capacitance');arcs=[b for _,b in C.groups(gate,'timing') if re.search(r'related_pin\s*:\s*"A1"',b)];seq=(C.BASE/'inputs'/f'asap7sc7p5t_SEQ_RVT_{c.upper()}_nldm_220123.lib').read_text()
     for b in (base/f'a1_{c}.log').read_text().split('ROOT_A1_EDGE ')[1:]:
      bit,pin,e=b.splitlines()[0].split();end=f'u_root.r2_w[{bit}]$_DFF_P_/D';r=m['rows'][end];p=b.split('data arrival time')[0];lines=p.splitlines()
      q=next(l for l in lines if '/QN (' in l);qv=q.split();src=qv[-2][:-3];srcmaster=qv[-1][1:-1];sf=C.cell_facts(seq,srcmaster,True);clk=float(next(l.split()[0] for l in lines if src+'/CLK (' in l))
      ai=next(l for l in lines if ' '+pin+' (' in l).split();y=next(l for l in lines if ' '+pin[:-2]+'Y (' in l).split();slack=float(re.search(r'([+-]?[\d.]+)\s+slack \(',b)[1]);oe='fall' if e=='rise' else 'rise';load=float(qv[1]);oldqslew=float(qv[2]);olddq=float(qv[3]);oldaslew=float(ai[0]);gyload=float(y[1]);gyslew=float(y[2]);gyd=float(y[3]);receiver=m['flops'][c,r['master']]
      row=results.setdefault(bit,dict(endpoint=end,patch_pin=pin,expected_master='AOI21x1_ASAP7_75t_R',corners={},options={}))
      row['corners'][c+'_'+e]=dict(slack_ps=slack,A1_cap_fF=cap,A1_slew_ps=oldaslew,source_output_load_fF=load)
      for n in m['names'][3:]:
       cell=m['lib'][c][n];edgecap=float(re.search(oe+r'_capacitance_range \(([^,]+), ([^)]+)\)',gp)[1 if c=='ff' else 2]);newload=load-edgecap+cell['input_cap_fF']['A'];sq=sf['delay_transition_tables'];dq=olddq*(I(sq['cell_'+oe],clk,newload)/I(sq['cell_'+oe],clk,load)-1);inslew=oldaslew*I(sq[oe+'_transition'],clk,newload)/I(sq[oe+'_transition'],clk,load);outload=edgecap+(.18 if c=='ss' else 0);bt=cell['delay_transition_tables'];bd=I(bt['cell_'+oe],inslew,outload);outslew=I(bt[oe+'_transition'],inslew,outload);posts=[]
       for arc in arcs:
        dt=C.table(arc,'cell_'+e);st=C.table(arc,e+'_transition');gd=gyd*(I(dt,outslew,gyload)/I(dt,oldaslew,gyload)-1);nds=r[c+'_'+e]['slew']*I(st,outslew,gyload)/I(st,oldaslew,gyload);ct=receiver['setup_rising' if c=='ss' else 'hold_rising'][e+'_constraint'];dc=I(ct,nds,r[c+'_'+e]['clock_slew'])-I(ct,r[c+'_'+e]['slew'],r[c+'_'+e]['clock_slew']);posts.append(dict(slack_ps=slack+(-1 if c=='ss' else 1)*(dq+bd+gd)-dc,source_delta_ps=dq,buffer_delay_ps=bd,gate_delta_ps=gd,constraint_delta_ps=dc))
       row['options'].setdefault(n,{})[c+'_'+e]=min(posts,key=lambda x:x['slack_ps'])
    
    assert len(rows) == 963 and all(len([k for k in r if k.startswith(('ss_', 'ff_'))]) == 4 for r in rows.values())
    assert set(results) == {'7', '13', '42'}
    source_sha256 = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(base.rglob('*')) if p.is_file() and p.name not in {'model.json','one_a1_plan.json','validation.json','tests.log'}}
    source_sha256.update(inherited_pins)
    return dict(schema='opentallas.s81.root_selective_model.v1', status='MEASURED_ENDPOINT_CONDITIONAL_CANDIDATE_NOT_CLOSED', source_sha256=source_sha256, baseline=dict(ss_ps=27.15, ff_ps=8.39, hold_low_pins=963), endpoint_screens=list(rows.values()), early_a1_candidates=results, architecture=dict(cycles_added=0, first_cell='HB4xp67_ASAP7_75t_R', first_area_um2=0.10206, changes_rounding=False, memory_bytes_added=0, communication_bits_added=0, replicas=1), limitations=['Full fresh extracted SS/FF and DRC required; this is no closure verdict.', 'Source clock-q ratios anchored to measured old delay; new source wire capacitance assumes old wire retained.', 'AOI conditional arcs use worst resulting slack across every matching A1 arc.', 'Existing late B timing path is unchanged logically; placement and routing can still perturb it.', 'Receiver D-pin screen is preliminary and not a selected bulk patch; actual FF capacitance ranges and upstream load changes need verification.', 'HB1-HB3 were not selected for first A1 patch: rounded source load enters or borders the characterized source-flop load floor.', 'HB4 new input loading uses nominal capacitance; actual slew, corner capacitance and route load remain fresh-STA gates.'])

if __name__ == '__main__':
    print(json.dumps(build(), indent=2))
