#!/usr/bin/env python3
"""Selected low-half scoped-SU RF compaction; no ordinary HGI COPY alias.

Raw templates do not carry dates. Scheduled emission requires a matched measured
phase book; the HBM caller owns the single runtime and all production leases.
"""
import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

PG='rtl/hbm_accel/die_glue/scoped_d4g/pgslice.sv'
QC='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_qcore_r13.sv'
ST='rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_stree.sv'
RD='rtl/hbm_accel/generic/adapters/static_su/reduction/ot_hbm_su_reduce_static_r13.sv'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def load_api(root):
    root=Path(root)
    sys.path.insert(0,str(root/'tools/hbm_static'))
    spec=importlib.util.spec_from_file_location('actual_su_compiler',root/'tools/hbm_static/su_arith_compile.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def templates(source_root,api_root,staging_row=510,scratch_row=509,rf=255,offsets=(0,1),destination_words=(0,1)):
    source_root=Path(source_root);api_root=Path(api_root)
    if not 0<=staging_row<512 or not 0<=scratch_row<512 or staging_row==scratch_row:raise ValueError('distinct actual nine-bit pinned rows required')
    if not 0<=rf<256:raise ValueError('RF address is exactly eight bits')
    if len(offsets)!=len(destination_words) or not offsets or len(set(destination_words))!=len(destination_words):raise ValueError('unique scalar destination mapping required')
    if any(not 0<=x<16 for x in offsets):raise ValueError('only low-half G0 sixteen-word staging supported')
    if any(not 0<=x<8 for x in destination_words):raise ValueError('one dense eight-word destination sector per book')
    for f in (PG,QC,ST,RD):
        if not (source_root/f).is_file():raise ValueError('missing selected source '+f)
    pg=(source_root/PG).read_text()
    for marker in ('function automatic integer lid','rd_src[n*8+2*p+:2]==2\'d0','rf_src_bad','dr_row[h]=w[32:24]'):
        if marker not in pg:raise ValueError('unsupported selected scoped store ABI: '+marker)
    api=load_api(api_root)
    physical=lambda row:api.physical_word(0,row)
    # Every active bank reads its own lane address. The full16 delivery payload
    # must be initialized; all16 output banks are disposable scratch. No lane
    # rotation, wrapped liveness counters or fabricated STREAM descriptor.
    terms=0
    for role in range(5):
        for k in range(7):
            if role!=0:terms|=(1<<k)<<(24*(10*role+k))
    def ctl(source_rf,dest,setup):
        t=terms
        if not source_rf:
            for k in range(7):t|=(1<<k)<<(24*k)
        vb=sum((rf if source_rf and s==0 else physical(scratch_row if s==4 else staging_row))<<(24*s) for s in range(5))
        return dict(ld=int(setup),emit=int(not setup),no=1,ni=16,ls=4,lvw=4,srcs=int(source_rf),dst=dest,co_dst=dest,ld_c=t,vb=vb)
    def packed(fields):return f'{api.pack(fields):0436x}'
    def red(op,a=0,d=0,tag=0,lane=0):return (1<<73)|(op<<70)|(a<<60)|(d<<40)|(tag<<8)|lane
    commands=[]
    for index,(offset,dword) in enumerate(zip(offsets,destination_words)):
        fields={'source_setup':ctl(False,0,True),'source_emit':ctl(False,0,False),
                'target_setup':ctl(True,1,True),'target_emit':ctl(True,1,False)}
        commands.append(dict(index=index,source_offset=offset,source_lane=offset,destination_word=dword,
            control={k:packed(v) for k,v in fields.items()},control_fields=fields,
            reducer_load=f'{red(0,d=0,lane=offset):019x}',
            reducer_export=f'{red(4,a=0,tag=0x100|rf):019x}',
            rf_class0=f'{0x100|rf:03x}',
            drain=dict(port=0,src=0,group=0,row=scratch_row,mask=1<<dword,sector=None),
            dates=None))
    return dict(schema='opentallas.hbm.scoped_su_rf_templates.v1',status='UNBOOKED_RAW_TEMPLATES',
        qid=0,group=0,half=0,read_return=10,write_return=7,collport=1,rf_local=1,
        staging_row=staging_row,delivery_obase=staging_row<<7,scratch_row=scratch_row,rf_scratch=rf,
        scratch_scope='Fresh-reset component reservation only; no production lease',reducer_scratch=0,
        minimum_dependencies=[
            'All16 staging lane writes committed before source native reads; no injection/fill collision.',
            'Source offset setup reaches actual lane offset bank before its source emit.',
            'Source ro_v must be high at matching red_sel LOAD sampling edge.',
            'Reducer scratch0 actual LOAD commit precedes matching EXPORT read.',
            'EXPORT tag0x1ff carries RF255 unchanged through the actual selected stree.',
            'Actual RF255 commit precedes class0 read sampling; no intervening overwrite.',
            'RF class0 address255 must match actual SRC1 request after RF_LOCAL register.',
            'Target source setup and RF response are valid at actual target native request/capture.',
            'All16 scratch509 writes commit before selected group0 drain sampling.',
            'One-word masks preserve all other destination VM words; actual VM commit observed.',
            'Keep each source/scratch/RF/reducer reservation through its last observed read; serialize scratch reuse after drain.'
        ],
        required_initialized_source_words=list(range(16)),overwritten_scratch_lanes=list(range(16)),
        source_sha256={f:sha(source_root/f) for f in (PG,QC,ST,RD)},
        compiler_sha256={f:sha(api_root/f) for f in ('tools/hbm_static/su_arith_compile.py','tools/hbm_static/su_arith_generate.py')},
        ordinary_HGI_COPY_supported=False,production_qualified=False,physical_epoch_mapping=None,
        commands=commands)

PHASES=('source_setup','source_emit','reducer_load','reducer_export','rf_class0','target_setup','target_emit','drain')
def emit(plan,book,book_root):
    if book.get('schema')!='opentallas.hbm.scoped_su_rf_phasebook.v1':raise ValueError('actual caller phase book required')
    if book.get('source_sha256')!=plan['source_sha256'] or book.get('compiler_sha256')!=plan['compiler_sha256']:raise ValueError('phase authority source/API mismatch')
    if book.get('scope')!='fresh_reset_component' or book.get('physical_epoch_mapping') is not None:raise ValueError('helper supports component-relative dates only')
    evidence=book.get('measured_events')
    if not isinstance(evidence,dict) or not evidence.get('path') or not evidence.get('sha256'):raise ValueError('actual RF/stree/store/VM event authority absent')
    path=Path(book_root)/evidence['path']
    if sha(path)!=evidence['sha256']:raise ValueError('measured event authority hash mismatch')
    observed=json.loads(path.read_text())
    if observed.get('status')!='PASS' or observed.get('source_sha256')!=plan['source_sha256']:raise ValueError('actual selected measured receipt required')
    leases=book.get('component_reservations',{})
    if leases!={'staging_row':plan['staging_row'],'scratch_row':plan['scratch_row'],'rf_scratch':plan['rf_scratch'],'reducer_scratch':plan['reducer_scratch'],'all16_source_words_initialized':True,'all16_scratch_lanes_disposable':True}:raise ValueError('complete component scratch reservation required')
    rows=book.get('commands',[])
    if len(rows)!=len(plan['commands']):raise ValueError('complete measured scalar phase books required')
    emitted=[]
    for cmd,dates in zip(plan['commands'],rows):
        if dates.get('index')!=cmd['index'] or any(type(dates.get(k)) is not int or dates[k]<0 for k in PHASES):raise ValueError('all command sampled edges required')
        if dates['source_setup']>=dates['source_emit'] or dates['reducer_load']>=dates['reducer_export'] or dates['target_setup']>=dates['target_emit'] or dates['target_emit']>=dates['drain']:raise ValueError('contradictory source/target command order')
        actual=observed.get('commands',[])
        if dates not in actual:raise ValueError('command dates absent from exact measured authority')
        # No hardcoded unmeasured stree delay: all causal windows must be
        # established by that same actual source-bound receipt.
        for key in ('source_ro_valid_at_load','reducer_export_after_load_ready','rf_committed_before_class0','rf_class0_matches_target_read','scratch_committed_before_drain','vm_masked_commit_observed'):
            if dates.get(key) is not True:raise ValueError('unmeasured phase hazard '+key)
        if not 0<=dates.get('destination_sector',-1)<65536:raise ValueError('actual sixteen-bit destination sector required')
        drain=cmd['drain'];word=(1<<38)|(drain['group']<<33)|(drain['row']<<24)|(dates['destination_sector']<<8)|drain['mask']
        emitted.append(dict(cmd,dates=dates,drain_word39=f'{word:010x}'))
    return dict(plan,status='BOOKED_COMPONENT_COMMANDS',commands=emitted,phasebook=book,production_qualified=False)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source-root',type=Path,required=True);p.add_argument('--api-root',type=Path,required=True);p.add_argument('--phasebook',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise ValueError('preserve prior emitted programme')
    plan=templates(a.source_root,a.api_root)
    result=emit(plan,json.loads(a.phasebook.read_text()),a.phasebook.parent)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
