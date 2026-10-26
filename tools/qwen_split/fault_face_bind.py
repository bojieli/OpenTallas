"""Connect the actual registered fault root to the new coherent system face.

This runs before relay planning. Any physical hop or landing is consequently
planned as real hardware; its age is not guessed by this source-stage binder.
"""
import os
from pathlib import Path
from qwen_split.source_pin_plan import rtl_ports

MASTER='qfd_sys_face_ovl_fault1'
SOURCE='rtl/qwen_split/qfd_sys_face_ovl_fault1.sv'
from qwen_split.sysface_lctx_source import select as select_lctx_source
MASTER,SOURCE=select_lctx_source((MASTER,SOURCE),Path(__file__).resolve().parents[2])

def install(v, model, fault):
    for flag in ('OT_QWEN_HEAD_PREP','OT_QWEN_ROPE','OT_QWEN_STATUS_OBS','OT_SPLIT_FAULT_SOURCE_BITS','OT_SPLIT_FAULT_EMIT'):
        if os.environ.get(flag)!='1':
            raise ValueError('fault1 requires actual coherent source and fault tree: '+flag)
    by={i.name:i for i in model['insts']}
    if by['d2d_rom'].master != 'qfd_d2d_static_ovl_sf7_obs1':
        raise ValueError('fault1 coherent vehicle requires actual STATUS208 obs1 D2D source, never an old view alias')
    if by['sys_face'].master!=MASTER:
        raise ValueError('die fault root requires the actual new fault1 master, never an old view alias')
    source=Path(__file__).resolve().parents[2]/SOURCE
    if rtl_ports(source,MASTER).get('obs_fault')!=(1,'input'):
        raise ValueError('fault1 actual source input is missing or differs')
    if model.get('hp13_clock_bind'):
        # Source ownership is known before regional roots exist. Revalidate the
        # exact source proof here; common acceptance must discharge the real
        # endpoints and every deferred fault follower after regional rebuild.
        from qwen_split.fault_emit import _tt_cf_clock_guard
        _tt_cf_clock_guard(model, {'tt_ctlm': ['cf']})
        info = model['hp13_clock_bind']
        if (model['hp13_cf_clock']['owner'] != ['tt_ctlm', 'ck_hr']
                or info['targets'].get('ck_hr') != ['dvs_W5', 'ck']
                or model.get('hp13_deferred_follow', {}).get(('tt_ctlm', 'ck_hr')) != ('dvs_W5', 'ck')):
            raise ValueError('fault1 HP13 cf lacks exact deferred HR endpoint ownership')
    else:
        tt_clocks = {bid for bid,kind,width,endpoints in model['buses']
                     if kind == 'clock_trunk'
                     and any(inst == 'tt_ctlm' for inst,pin in endpoints)}
        if len(tt_clocks) != 1:
            raise ValueError('fault1 TT.cf requires exact hr-clock owner and real crossing; ambiguous multi-clock TT is not admitted')
    root=fault['roots']['sys_face']['inst']
    if root not in by or not by[root].master.startswith('qfd_fault_or_n'):
        raise ValueError('fault1 source is not the actual registered fault root')
    if model.get('ck_follow',{}).get((root,'ck'))!='sys_face':
        raise ValueError('fault1 root must follow the actual sys_face clock region')
    clocks={}
    for bid,kind,width,endpoints in model['buses']:
        if kind=='clock_trunk':
            for e in endpoints:
                if e in ((root,'ck'),('sys_face','ck')):
                    if width!=1 or e in clocks:raise ValueError('fault1 source clock identity ambiguous')
                    clocks[e]=bid
        if ('sys_face','obs_fault') in endpoints:
            raise ValueError('fault1 input already has a source')
    if set(clocks)!={(root,'ck'),('sys_face','ck')} or len(set(clocks.values()))!=1:
        raise ValueError('fault1 root/source face clocks differ; an explicit real landing is required')
    debt=set(model['sys_face_bind'].get('deferred_inputs',[]))
    if debt!={'obs_fault'}:
        raise ValueError('fault1 unexpected actual source-stage debt: '+str(sorted(debt)))
    model['buses'].append(('sf_fault_observe','spine_local',1,[(root,'o'),('sys_face','obs_fault')]))
    model['sys_face_bind']['deferred_inputs']=[]
    fault['root_sink']='sys_face.obs_fault'
    fault['root_sink_contract']=dict(source=[root,'o'],consumer=['sys_face','obs_fault'],
        source_clock=clocks[root,'ck'],consumer_clock=clocks['sys_face','ck'],
        final_clock_owner='sys_face via existing ck_follow',local_capture_edges=1,
        transport_edges='derive from actual GEN; every cross-region hop must be a real landing',
        clear='local regional reset only; HOST/context/epoch changes never clear',
        normal_programme_edges_added=0,physical_qualification_eligible=False)
