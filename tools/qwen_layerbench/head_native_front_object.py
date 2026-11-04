#!/usr/bin/env python3
"""Extract current bound command transport equations for native HEAD calls.

No executable issue times are selected. Landed, aligned source paths are read
from the explicit frozen bus_groups cohort, never old lane-depth defaults.
"""
import argparse,hashlib,json
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

PRIMARY={
 'rtl/qwen_dv/s5/s8/qfd_dv_s8_fdn_arf1.sv':'bad64d67691f2bca53804b884d5da41b4900e4801db53da3c6e352b1796395a9',
 'rtl/qwen_dv/s5/s6/qfd_dv_s6_leaves.sv':'686650fa5e7e5f3523a344f3c90d1f3ada14d411c1ab064901375269e6beb53a',
 'rtl/qwen_dv/s5/qfd_dv_s5_ctl_repair4_leaf.sv':'43e4fdb1799703b377cc2bf1af9531b6d1af9405b60d97175f1fb28138181f6e',
 'rtl/qwen_dv/s5/qfd_dv_s5_leaves.sv':'97d84d865584bbf8eb747f1f082da48cf897bfe2f6fba2c78033d16bed135b22'}

def build(groups,param,rtl_root):
    for n,h in PRIMARY.items():
        if sha(rtl_root/n)!=h:raise ValueError('primary register contract source changed: '+n)
    j=json.loads(groups.read_text());p=json.loads(param.read_text());order=[f'dvs_W{x}'for x in range(5,-1,-1)]+[f'dvs_E{x}'for x in range(6)]
    inp={};local={};su={};receipts=[]
    for g in j['landing']:
        sid=g['sink'].split('.')[0]
        if sid not in order:continue
        for m in g['members']:
            key=None
            if m['sink_port']=='cmd_i' and '.u_fdn' in g['sink']:key='forward'
            elif '.u_fdn.cmd_q' in m['source'] and '.u_rp' in g['sink']:key='local'
            elif '.u_ctl.su_cmd' in m['source'] and 'u_rpg' in g['sink']:key='SU'
            if key:
                if not g['aligned_landed']:raise ValueError('actual command fragments must be aligned')
                d=(inp if key=='forward' else local if key=='local' else su)
                row=(m['source'].split('.')[0],m['landed_stages'])if key=='forward' else m['landed_stages']
                if sid in d and d[sid]!=row:raise ValueError('command payload fragments have different source/age')
                d[sid]=row;receipts.append(dict(path=key,sink=g['sink'],source=m['source'],source_bits=m['source_bits'],sink_bits=m['sink_bits'],landed_stages=m['landed_stages'],lane=m['lane']))
    if any(set(x)!=set(order)for x in (inp,local,su)):raise ValueError('all12 complete actual command paths required')
    ages={};rows=[]
    for n,sid in enumerate(order):
        src,depth=inp[sid]
        if n==0:
            if src!='tt_ctlm':raise ValueError('selected command chain must start at actual TT')
            fdn=depth
        else:
            if src!=order[n-1]:raise ValueError('actual native command forward chain differs')
            fdn=ages[src]+1+1+depth # actual FDN register, then actual FUP cmd_o register
        ages[sid]=fdn
        cmd_age=fdn+1+local[sid]+1+su[sid] # FDN, registered HARD1 CTL, direct SU port
        rows.append(dict(slice=n,node=sid,TT_to_FDN_input=fdn,local_FW_to_CTL=local[sid],CTL_to_SU=su[sid],TT_to_native_SU_command=cmd_age,equation=f'HEAD_NATIVE_SU_S{n}_CMD = HEAD_CALR_APPLY_S{n}_ISSUE + {cmd_age}'))
    return dict(schema='opentallas.qwen.native-head-command-front-source.v1',status='SOURCE_TRANSPORT_EQUATIONS_NOT_EXECUTABLE_DATES',rows=rows,source_bus_groups_sha256=sha(groups),source_param_regen_sha256=sha(param),cohort='explicit frozen bind_complete4 82190/factory-f79 source; functional/module/PHY qualification remains separate',primary_source_sha256=PRIMARY,primary_register_contract=dict(FDN=1,FUP=1,RP_passthrough=0,HARD1_CTL=1),head_prepare=p['record']['qwen_head_prepare_profile'],landing_receipts=receipts,added_pipeline_edges=0,remaining=['current bound SU internal lane/VM path numerical qualification and H emission age','native SU output write→CTL→STREAM transport','real stream merge/headtap/Xfill arm and operand epoch leases','all executable peruser H/GME/station issue dates'],warning='do not add the direct unbound-H component70/110 offsets to claim current bound headtap timing; additional arithmetic/write/stream crossings remain',executable=False)

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for k in ('groups','param','rtl-root','out'):a.add_argument('--'+k,type=Path,required=True)
    p=a.parse_args();r=build(p.groups,p.param,p.rtl_root);p.out.write_text(json.dumps(r,indent=2)+'\n');print([x['TT_to_native_SU_command']for x in r['rows']])
