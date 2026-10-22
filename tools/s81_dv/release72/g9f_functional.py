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
    if 'OT_S81SL_KV_TRANSPORT' not in table['defines']:table['defines'].append('OT_S81SL_KV_TRANSPORT')
    xrt='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xrt.sv'
    table['rtl_refs'].setdefault(KV,[]).append(xrt)
    table['prefer']=[q for q in table['prefer'] if not q.endswith('/'+xrt)]+[KV+'/'+xrt]
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
def hbc_disabled(plan,table,source_ref,regional_manifest):
    """Bind real HBC and fixed transport while production enable stays off."""
    blocks={b['name']:(i,b) for i,b in enumerate(plan['blocks'])}
    _,body=blocks['s_0N']
    end=table['masters'][body['master']]
    old_module=end['module']
    top='ot_s81sl_slice_lepw_mab_hbc_r4d_mu_72'
    end.update(module=top,ref=source_ref,view=None,params={'HBC_ENABLE':0},
        view_note='Actual R4D HBC/status/transport source. HBC_ENABLE0; production identity and dates unassigned.')
    extra=['ck_K','ck_ML','ck_KA','ck_KB','ck_L0','ck_L1','ck_L3','ck_L4','ck_CAP_RT','ck_CAP_CW','ck_CAP_CE','ck_CAP_RN','ck_CAP_RS']
    end['clk_extra']=extra;end.pop('clock_ports',None)
    shape=dict(table['rtl_widths'][old_module])
    for k in list(shape):
        if k.startswith('ck_N'):shape.pop(k)
    shape.update(ck_KA=1,ck_KB=1,hb_status_t_host=77,hb_status_t_kd=54,hb_starter_armed=1,
        hb_f_host=515,hb_ks=53,hb_ks_slot=3,hb_arm_mask=6,hb_arm_commit=1,hb_fault=12,hb_hbc_fault=8,hb_return_fault=4,hb_ctx_valid=1)
    table['rtl_widths'][top]=shape
    end['top_ports']=[dict(port=p,dir='output',bits=w) for p,w in [('hb_arm_mask',6),('hb_arm_commit',1),('hb_fault',12),('hb_hbc_fault',8),('hb_return_fault',4),('hb_ctx_valid',1)]]
    rootmap=table['instance_clock_ports']['s_0N'];_,body=blocks['s_0N']
    for name,fraction in [('KA',.34),('KB',.67)]:
        cp='ck_'+name;net='ck_ep_s_0N_'+name;rootmap[cp]=net
        table['clock_domains'][net]=dict(table['clock_domains'][rootmap['ck_K']],receiver_clock_port=cp,receiver_region=name,
            receiver_pin_xy_um=[round(body['x']+648,4),round(body['y']+body['h']*fraction,4)],
            receiver_pin_source='Unqualified R4D pair-region seed; physical native pin authority remains owed')
    for lane in range(4):
        for kind,direction in [('tx','o'),('rx','i')]:end['ports'][f'{kind}{lane}.{direction}']['clock_port']='ck_KA' if lane<2 else 'ck_KB'
    # Distinct native output fields drive one three-lane forward bundle.
    end['ports']['hbf.o']={'clock_port':'ck_K','lanes':[{'split':[['hb_f_host',0,0,276]]},
        {'split':[['hb_f_host',276,0,239],['hb_ks',0,239,37]]},
        {'split':[['hb_ks',37,0,16],['hb_ks_slot',0,16,3]]}]}
    end['ports']['hbr.i']={'clock_port':'ck_K','land':True,'lanes':[{'split':[['hb_status_t_host',0,0,77],['hb_status_t_kd',0,77,54],['hb_starter_armed',0,131,1]]}]}
    seq=table['masters']['dsdv_seq_host_mux'];seq.update(module='dsdv_hostb_seqhost_mux',ref=source_ref,view=None)
    seq.setdefault('params',{}).update(HOSTB_ENABLE=0,STATIC_KS6=0)
    seq.setdefault('straps',[]).append('select_hbe');seq['strap_values']['select_hbe']="1'b0"
    seq['top_ports']=list(seq.get('top_ports',[]))+[dict(port='hostb_fault',dir='output',bits=3),dict(port='hb_job_active',dir='output',bits=1)]
    seq['ports']['hbf.i']={'land':True,'lanes':[{'split':[['hbe_f_host',0,0,276]]},
        {'split':[['hbe_f_host',276,0,239],['starter_f_ks',0,239,37]]},
        {'split':[['starter_f_ks',37,0,16],['hbe_ks_slot',0,16,3]]}]}
    seq['ports']['hbr.o']={'lanes':[{'split':[['=t_host',0,0,77],['=t_kd',0,77,54],['hb_starter_armed',0,131,1]]}]}
    seq['ports']['eks.o']={'lanes':[{'split':[['engram_f_ks',0,0,53]]}]}
    table['rtl_widths']['dsdv_hostb_seqhost_mux']=dict(table['rtl_widths']['dsdv_seq_host_mux'],select_hbe=1,hbe_f_host=515,starter_f_ks=53,
        hbe_ks_slot=3,engram_f_ks=53,hostb_fault=3,hb_job_active=1,hb_starter_armed=1)
    # The selected source mux drives the actual existing Engram KS input.
    for link in plan['links']:
        if link['i']=='eks_7N':
            i,b=blocks['seqhost'];link['e'][0]=[i,'eks',b['x']+b['w'],b['y']+b['h']*.5,'box'];link['endpoint_faces'][0]='E'
    si,src=blocks['s_0N'];di,dst=blocks['seqhost']
    for lane in range(3):
        plan['links'].append(dict(i=f'hbc_forward_l{lane}',c='ctrl',b=276,d=1,
            e=[[si,'hbf',src['x']+src['w'],src['y']+src['h']*.42+lane*43.2,'box'],[di,'hbf',dst['x'],dst['y']+dst['h']*.42+lane*43.2,'box']],
            endpoint_faces=['E','W'],n='HBC 571 live bits in three parallel 276-bit landed lanes; production enable off'))
    plan['links'].append(dict(i='hbc_reverse_l0',c='ctrl',b=276,d=1,
        e=[[di,'hbr',dst['x'],dst['y']+dst['h']*.7,'box'],[si,'hbr',src['x']+src['w'],src['y']+src['h']*.7,'box']],
        endpoint_faces=['W','E'],n='Real t_host77/t_kd54/starter1; 132 live bits plus144 declared spares'))
    paths=['rtl/dsrom_sys/s81_dv/hostb/'+n+'.sv' for n in ['dsdv_hostb_hold','dsdv_hostb_crc512','dsdv_hostb_rx','dsdv_hostb_tx','dsdv_hostb_stage','dsdv_hbc1_loader','dsdv_hbc1_affine_book','dsdv_hostb_return','dsdv_hostb_stage_hbc','dsdv_hostb_source','dsdv_hostb_seqhost_mux']]
    paths+=['rtl/dsrom_sys/s81_dv/slice/mu72/'+top+'.sv']
    table['rtl_refs'].setdefault(source_ref,[]).extend(paths)
    table['prefer'].extend(source_ref+'/'+path for path in paths)
    for rec in regional_manifest['files']:
        ref,path=regional_manifest['source_ref'],rec['path']
        if path.endswith('/ot_s81sl_slice_lepw_mab_r4d_mu_72.sv'):continue
        table['rtl_refs'].setdefault(ref,[]).append(path)
        table['prefer']=[v for v in table['prefer'] if not v.endswith('/'+path)]
        table['prefer'].append(ref+'/'+path)
    table['functional_successor']['hbc']={'source_ref':source_ref,'master':top,'HBC_ENABLE':0,'HOSTB_ENABLE':0,
        'production_clock_book_bound':False,'production_assignment':None,'clock_port':'ck_K','clock_root':rootmap['ck_K'],
        'transport_live_bits':{'forward':571,'reverse':132},'transport_wire_bits':{'forward':828,'reverse':276}}


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
    if 'hbc_forward_l0' in links:
        ledger['hbc']={}
        for direction,count in [('forward',3),('reverse',1)]:
            names=[f'hbc_{direction}_l{i}' for i in range(count)]
            age=max(math.ceil(links[n].get('s',0)/2)+max(2,math.ceil(.47*links[n].get('s',0))+1)+1 for n in names)
            for name in names:
                l=links[name];n=l.get('s',0);e=max(2,math.ceil(.47*n)+1);k=age-math.ceil(n/2)-1
                if not e<=k<=63:raise ValueError((name,n,e,k))
                rows[name]=dict(link=name,cls=l['c'],dst=plan['blocks'][l['e'][1][0]]['name'],bits=276,stages=n,E=e,K=k,D=8,
                    master='dsfd_dvland_276l',force_landing=not n,model=True,bundle=f'hbc_{direction}',
                    K_source='Actual routed station count; parallel bundle age equalized; physical pilot window owed')
            ledger['hbc'][direction]={'age_cycles':age,'lanes':{n:{k:rows[n][k] for k in ('stages','E','K','D','master')} for n in names}}
    land['links']=list(rows.values());land['pvso_routes']=ledger
    return ledger
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','finish']);ap.add_argument('plan');ap.add_argument('other');ap.add_argument('out_plan');ap.add_argument('out_other');ap.add_argument('--wrapper-ref');ap.add_argument('--hbc-ref');ap.add_argument('--regional-manifest');a=ap.parse_args()
    p,t=read(a.plan),read(a.other)
    if a.mode=='prepare':
        m=json.loads(subprocess.check_output(['git','show','0a28869d5:results/rtl/s81_rtlgap_codex_2000/die_source_import.json']))
        prepare(p,t,m,a.wrapper_ref or subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip())
        if a.hbc_ref:
            if not a.regional_manifest:raise ValueError('HBC R4D requires exact regional source manifest')
            hbc_disabled(p,t,a.hbc_ref,read(a.regional_manifest))
    else:print(json.dumps(finish(p,t),indent=1))
    write(a.out_plan,p);write(a.out_other,t)
