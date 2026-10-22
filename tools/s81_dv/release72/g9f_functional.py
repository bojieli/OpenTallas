#!/usr/bin/env python3
"""Add source-pinned SUKV and actual SO exchange to a fresh G9e plan/table.
Run prepare before ordinary route; finish after station directions and short-land.
This is an explicitly unqualified source assembly, not a parent-view alias.
"""
import argparse,copy,json,math,subprocess
from pathlib import Path
SO='e8561c9db';KV='75c077ec9'
WRAPPER='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_sukv_raw512.sv'
def read(p):return json.loads(Path(p).read_text())
def write(p,d):Path(p).write_text(json.dumps(d,indent=1)+'\n')
def split_pv(copy_source=False):
    # Exact ABI {pv_x[47:0],pv_d[512:0],pv_v}; three parallel 276b lanes.
    fields=[('pv_v',0,1),('pv_d',1,513),('pv_x',514,48)]
    result=[]
    for lane in range(3):
        lo,hi=lane*276,min((lane+1)*276,562);parts=[]
        for port,start,width in fields:
            a,b=max(lo,start),min(hi,start+width)
            if b>a:parts.append([('='+port if copy_source else port),a-start,a-lo,b-a])
        result.append({'split':parts})
    return result
def prepare(plan,table,manifest,wrapper_ref):
    blocks={b['name']:(i,b) for i,b in enumerate(plan['blocks'])}
    svc=table['masters']['dsdv_svc_rs'];svc.setdefault('params',{})['PV_IDENTITY']=1
    entry=copy.deepcopy(svc);entry.pop('inst_module',None)
    entry.update(module='dsdv_svc_rs_pvso_entry',ref=SO,view=None,
      view_note='Unqualified PVSO assembly; 136 new 32x64 SRAMs per entry, no inherited parent view')
    entry['params'].update(PVSO_ENABLE=1,SMT=1)
    entry['top_ports']=list(entry.get('top_ports',[]))+[dict(port=p,dir='output',bits=w) for p,w in [('so_ready',1),('so_done',1),('so_fault_code',12)]]
    entry['ports']['pvcopy.o']={'lanes':split_pv(True)}
    entry['ports']['pvlocal.i']={'land':True,'lanes':[{'split':[['local_pv_landed',i*276,0,min(276,562-i*276)]]} for i in range(3)]}
    entry['ports']['pvpeer.i']={'land':True,'lanes':[{'split':[['peer_pv',i*276,0,min(276,562-i*276)]]} for i in range(3)]}
    table['masters']['dsdv_svc_pvso_entry']=entry
    table['rtl_widths']['dsdv_svc_rs_pvso_entry']=dict(table['rtl_widths']['dsdv_svc_rs_entry'],local_pv_landed=562,peer_pv=562,so_ready=1,so_done=1,so_fault_code=12)
    for name in ('rsv_05','rsv_11'):
        blocks[name][1]['master']='dsdv_svc_pvso_entry'
    table['status_fault_masters'].append('dsdv_svc_pvso_entry')
    for key in ('so','sukv_raw'):
        rec=manifest[key];ref=rec['ref'];paths=rec['rtl_paths']
        table['rtl_refs'].setdefault(ref,[]).extend(paths)
        table['prefer']=[p for p in table['prefer'] if not any(p.endswith('/'+q) for q in paths)]
        table['prefer'].extend(ref+'/'+p for p in paths)
    table.setdefault('defines',[])
    for define in manifest['so']['required_defines']:
        if define not in table['defines']:table['defines'].append(define)
    raw=table['masters']['dsdv_slice_kv512'];raw.update(module='ot_s81sl_slice_sukv_raw512',ref=wrapper_ref,view=None,
        view_note='KV_ENABLE/CNIK/CP=1 raw75c077ec9; no whole-SUKV physical qualification; pool delta mapped area pending')
    table['rtl_widths']['ot_s81sl_slice_sukv_raw512']=dict(table['rtl_widths']['ot_s81sl_slice_kv512'])
    table['rtl_refs'].setdefault(wrapper_ref,[]).append(WRAPPER)
    table['prefer'].append(wrapper_ref+'/'+WRAPPER)
    # Two source broadcasts: each producer drives local and peer copies. Each
    # logical port has three lanes; use distinct port groups for local vs peer.
    entry['ports']['pvpeerout.o']={'lanes':split_pv(True)}
    for source,peer,label in [('rsv_05','rsv_11','W'),('rsv_11','rsv_05','E')]:
        si,s=blocks[source]
        for dest,kind,outport in [(source,'local','pvcopy'),(peer,'peer','pvpeerout')]:
            di,d=blocks[dest]
            for lane in range(3):
                # Place ports along the upper face in an existing free corridor.
                sx=s['x']+s['w']*.5+lane*43.2;dx=d['x']+d['w']*.5+lane*43.2+(86.4 if kind=='local' else 0)
                plan['links'].append(dict(i=f'pvso_{label}_{kind}_l{lane}',c='attn',b=276,d=1,
                    e=[[si,outport,sx,s['y']+s['h'],'box'],[di,'pvlocal' if kind=='local' else 'pvpeer',dx,d['y']+d['h'],'box']],
                    endpoint_faces=['N','N'],n='Actual P.V broadcast; three parallel lanes, 562 live bits plus 266 declared spares'))
    table['functional_successor']={'so_source':SO,'sukv_raw_source':KV,'sukv_wrapper_ref':wrapper_ref,
        'pv_layout':'{pv_x48,pv_d513,pv_v1}','added_ingress_sram_macros':272,'added_ingress_sram_bits':557056,
        'new_parent_views_qualified':False,'body_area':'stand-in pending mapped logic and ingress placement; not inherited closure',
        'hbc':'Not selected until real stage/rank, clock/reset origin and upstream arrival authority exist'}
def finish(plan,land):
    rows={r['link']:r for r in land['links']};links={l['i']:l for l in plan['links']}
    ledger={}
    for producer in ('E','W'):
        names=[f'pvso_{producer}_{kind}_l{i}' for kind in ('local','peer') for i in range(3)]
        # Conservative ordinary long-ring window, explicit source/receiver epoch
        # calendars still solved by dv_bind. Equalize all six by real station count.
        age=max(math.ceil(links[n].get('s',0)/2)+max(2,math.ceil(.47*links[n].get('s',0))+1)+1 for n in names)
        for name in names:
            l=links[name];n=l.get('s',0);e=max(2,math.ceil(.47*n)+1);k=age-math.ceil(n/2)-1
            if not e<=k<=63:raise ValueError((name,n,e,k))
            rows[name]=dict(link=name,cls='attn',dst=plan['blocks'][l['e'][1][0]]['name'],bits=276,stages=n,E=e,K=k,D=8,
                master='dsfd_dvland_276l',force_landing=not n,model=True,bundle=f'pvso_{producer}',
                K_source='Actual routed station count; all three local and three peer lanes at one producer age; pilot physical window owed')
        ledger[producer]={'age_cycles':age,'lanes':{n:{k:rows[n][k] for k in ('stages','E','K','D','master')} for n in names}}
    land['links']=list(rows.values());land['pvso_routes']=ledger
    return ledger
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','finish']);ap.add_argument('plan');ap.add_argument('other');ap.add_argument('out_plan');ap.add_argument('out_other');ap.add_argument('--wrapper-ref');a=ap.parse_args()
    p,t=read(a.plan),read(a.other)
    if a.mode=='prepare':
        m=json.loads(subprocess.check_output(['git','show','0a28869d5:results/rtl/s81_rtlgap_codex_2000/die_source_import.json']))
        prepare(p,t,m,a.wrapper_ref or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
    else:print(json.dumps(finish(p,t),indent=1))
    write(a.out_plan,p);write(a.out_other,t)
