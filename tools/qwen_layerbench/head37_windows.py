#!/usr/bin/env python3
"""Validate source-selected LOCAL4 installation/HEAD admission at receiver edges.

The first supported contract is the measured native zero-external 3/1 packet.
Physical MEM44 requires its own calibrated macro-store/read boundary contract;
changing a profile label never transfers the native earliest-command45 proof.
"""
import hashlib,json
from pathlib import Path

NATIVE_INSTALL_CONTRACT_SHA256='70cbe097a3a8f45878daebadc942a0808fde80f0f68f5c3e26520c2c6aa2d4ef'
NATIVE_PROFILE={'MIF':1,'MEMORY_ALIGNMENT':3,'MEMORY_READ_EXTRA':1}
NATIVE_FLAT='52ba50094b38e8438837cfca3c846ece2c58ac98e9983022c0f773c55b28a4a4'

def edge(row,key):
    v=row.get(key)
    if type(v)is not int or v<0:raise ValueError('actual nonnegative receiver edge required: '+key)
    return v

def validate(window,contract,allocation,*,require_all=True):
    if window.get('schema')!='opentallas.qc-head37-loader-windows.v1':raise ValueError('source-selected loader-window schema required')
    if window.get('unresolved'):raise ValueError('unresolved actual loader-window inputs')
    if contract.get('status')!='PASS_COMPONENT_ONLY' or contract.get('earliest_measured_safe_command_after_treq')!=45:
        raise ValueError('measured native install contract required')
    selected=window.get('selected_actual_source',{})
    if selected.get('memory_profile')!=NATIVE_PROFILE or selected.get('flat_sha256')!=NATIVE_FLAT or selected.get('external_memory_transport')!=0:
        raise ValueError('native3/1 zero-external window proof cannot qualify a physical MEM44 or different source profile')
    for k in ('request_edge_authority','command_edge_authority','lease_authority','table_mask_receipt_sha256'):
        if not isinstance(window.get(k),str)or not window[k].strip():raise ValueError('actual '+k+' required')
    rows=window.get('windows',[]);ids={(v.get('slice'),v.get('user'))for v in rows}
    if len(rows)!=len(ids):raise ValueError('duplicate slice/user window')
    if require_all and ids!={(s,u)for s in range(12)for u in range(4)}:raise ValueError('all48 source-selected slice/user windows required')
    r=contract['early45_relative_to_treq'];intr=contract['delivered_cmd_intrinsic'];out=[]
    for v in rows:
        if type(v.get('slice'))is not int or not 0<=v['slice']<12 or type(v.get('user'))is not int or not 0<=v['user']<4:raise ValueError('actual slice/user identity required')
        bank=next((b for b in allocation['allocation']['users']if b['user']==v['user']),None)
        if bank is None or v.get('pidx')!=bank['pidx']:raise ValueError('window does not select the genuine user programme lease')
        n=v.get('FP32_words')
        if type(n)is not int or n not in (256,384):raise ValueError('native slice footprint required')
        for key,want in [('x_range',[bank['vm_x_first'],bank['vm_x_first']+n]),('rstd_range',[bank['vm_rstd'],bank['vm_rstd']+1]),('gain_range',[bank['crom_first'],bank['crom_first']+n])]:
            if v.get(key)!=want:raise ValueError('window differs from genuine source lease: '+key)
        t=edge(v,'table_request_edge');c=edge(v,'command_input_edge')
        expected={'first_tw_edge':t+r['first_tw'],'last_tw_edge':t+r['last_tw'],'programme_store_edge':t+r['prog_store'],'first_gain_store_edge':t+r['first_gain_store'],'last_gain_store_edge':t+r['last_gain_store'],'loader_done_edge':t+r['loader_done'],'programme_read_edge':c+intr['programme_macro_read'],'first_gain_read_edge':c+intr['first_gain_macro_read'],'first_vm_write_edge':c+intr['first_vm_write'],'last_vm_write_edge':c+intr['last_vm_write'],'first_BF16_receiver_edge':c+intr['first_bf16_receiver'],'last_BF16_receiver_edge':c+intr['last_bf16_receiver']}
        for k,want in expected.items():
            if edge(v,k)!=want:raise ValueError(f'slice{v["slice"]} user{v["user"]} {k} differs from calibrated native boundary')
        if c-t<45 or v['first_gain_read_edge']<=v['first_gain_store_edge'] or v['programme_read_edge']<=v['programme_store_edge']:raise ValueError('native storage read is not strictly after actual installation')
        if edge(v,'writer_reserved_through_edge')<v['loader_done_edge']:raise ValueError('writer reservation ends before native loader completion')
        if edge(v,'x_ready_edge')>=c+intr['first_memory_request'] or edge(v,'rstd_ready_edge')>=c+intr['first_memory_request']:raise ValueError('finite X/RSTD lease is not visible before native request')
        if edge(v,'operand_lease_through_edge')<v['last_vm_write_edge']:raise ValueError('operand lease expires before measured last VM write')
        out.append(v)
    for sid in {v['slice']for v in rows}:
        stream=sorted((v for v in rows if v['slice']==sid),key=lambda v:v['table_request_edge'])
        for a,b in zip(stream,stream[1:]):
            if b['table_request_edge']-a['table_request_edge']<contract['loader_contract']['earliest_next_request_interval']:raise ValueError('next request violates measured busy admission')
            if b['first_tw_edge']<=a['writer_reserved_through_edge']:raise ValueError('exclusive table writer windows overlap')
    return {'status':'COMPLETE_SOURCE_SELECTED_LOCAL4_WINDOWS'if require_all else'NATIVE_COMPONENT_WINDOWS_VALID','windows':out,'global_enable':False,'physical_adoption':False}

def load(path,*,require_all=True):
    p=Path(path);w=json.loads(p.read_text());cp=Path(w['native_install_contract'])
    if not cp.is_absolute():cp=p.parent/cp
    raw=cp.read_bytes()
    if w.get('native_install_contract_sha256')!=NATIVE_INSTALL_CONTRACT_SHA256:raise ValueError('unqualified install contract; new profile requires its own actual source gate')
    if hashlib.sha256(raw).hexdigest()!=w.get('native_install_contract_sha256'):raise ValueError('native install contract identity differs')
    lp=Path(w['source_lease'])
    if not lp.is_absolute():lp=p.parent/lp
    lr=lp.read_bytes()
    if hashlib.sha256(lr).hexdigest()!=w.get('source_lease_sha256'):raise ValueError('genuine source lease identity differs')
    return validate(w,json.loads(raw),json.loads(lr),require_all=require_all)

def main():
    import argparse
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--windows',type=Path,required=True)
    ap.add_argument('--component-only',action='store_true',help='allow the actual partial native component; never activation')
    ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();v=load(a.windows,require_all=not a.component_only)
    a.out.write_text(json.dumps(v,indent=2)+'\n');print(v['status'])
if __name__=='__main__':main()
