#!/usr/bin/env python3
"""Select the actual owner VPOS/KVmp/near source join; emits only, never builds."""
import argparse
import hashlib
import json
from pathlib import Path
import qwen_rom_combined_nearbaseline_sources as predecessor
import qwen_rom_verify_core_emit_w12 as vpos
import qwen_rom_rt_core_emit_w12 as core
import qwen_rom_combined_stream4_sources as stream4

ROOT=Path(__file__).resolve().parents[1]
TOP='ot_qwen_rom_combined_dspark_die'


def selected(output, *, use_stream4=False, seq_la=False, native_mp_commit=False, stream4_source_root=None):
    output=Path(output)
    if (seq_la or native_mp_commit) and not use_stream4:
        raise ValueError('adopted joins require the actual STREAM4 selection')
    joins=[]
    for enabled,name in ((seq_la,'rtl/qwen_sys/combined/ot_qwen_tp_seq_combined_vp_la.sv'),
                         (native_mp_commit,'rtl/hdc/kv/ot_qwen_rt_kv_stream4_mp_commit_service.sv'),
                         (native_mp_commit,'rtl/hdc/kv/ot_qwen_kv_mp_commit.sv')):
        if enabled:
            source=ROOT/name
            if not source.is_file():raise FileNotFoundError('required adopted source not landed: '+str(source))
            joins.append(source)
    saved_stream_root=stream4.ROOT
    if stream4_source_root is not None:
        if not use_stream4:raise ValueError('STREAM4 reuse root requires --stream4')
        stream4.ROOT=Path(stream4_source_root).resolve(strict=True)
    try:
        rec=(stream4.selected(output,hbm_layers=36) if use_stream4 else predecessor.selected(output,hbm_layers=36))
        if use_stream4:rec['stream4_source_root']=str(stream4.ROOT)
    finally:stream4.ROOT=saved_stream_root
    generated=output/'gen/ot_qwen_rom_core.sv'
    generated.write_text(vpos.emit(core.CORE.read_text()))
    omit={'ot_qwen_rom_combined_nearbaseline_die.sv','ot_qwen_tp_seq_combined.sv',
          'ot_qwen_nearhbm_realmem_service.sv','ot_qwen_rom_combined_stream4_die.sv',
          'ot_qwen_rt_kv_stream4_service.sv'}
    die=[Path(p) for p in rec['die'] if Path(p).name not in omit]
    combined=ROOT/'rtl/qwen_sys/combined'
    die += [combined/name for name in [TOP+'.sv','ot_qwen_tp_seq_combined_vp.sv',
             'ot_qwen_combined_nearhbm_mp_service.sv','ot_qwen_combined_dspark_accept.sv']]
    die += [ROOT/'rtl/hdc/kv/ot_qwen_rt_kv_mp_service.sv',ROOT/'rtl/hdc/ot_hdc_accept.sv']
    if use_stream4:die.append(ROOT/'rtl/hdc/kv/ot_qwen_rt_kv_stream4_mp_service.sv')
    original_top=combined/(TOP+'.sv')
    if seq_la or native_mp_commit:
        text=original_top.read_text()
        parameter='    parameter integer DSPARK=0,'
        if text.count(parameter)!=1:raise ValueError('combined top parameter anchor changed')
        text=text.replace(parameter,'    parameter integer SEQ_LA=0, MP_COMMIT_NATIVE=0,\n'+parameter)
        def variant(old_module,new_module,condition,extra='',outer=False):
            nonlocal text
            anchor='    '+old_module+' #('
            if text.count(anchor)!=1:raise ValueError('combined instance anchor changed: '+old_module)
            start=text.index(anchor);end=text.index(');',start)+2
            original=text[start:end]
            adopted=original.replace(old_module,new_module,1)
            if extra:adopted=adopted.replace('#(','#('+extra,1)
            branch=('    if('+condition+') begin:g_'+condition.lower()+'\n'+adopted+
                    '\n    end else begin:g_'+condition.lower()+'_off\n'+original+'\n    end')
            if outer:branch='    generate\n'+branch+'\n    endgenerate'
            text=text[:start]+branch+text[end:]
        if seq_la:variant('ot_qwen_tp_seq_combined_vp','ot_qwen_tp_seq_combined_vp_la',
                          'SEQ_LA',extra='.LA(SEQ_LA),',outer=True)
        if native_mp_commit:variant('ot_qwen_rt_kv_stream4_mp_service',
                                    'ot_qwen_rt_kv_stream4_mp_commit_service','MP_COMMIT_NATIVE')
        top=output/'gen'/(TOP+'.sv');top.write_text(text)
        die=[top if path==original_top else path for path in die]
        rec['generated_top']=str(top)
    die+=joins
    die=list(dict.fromkeys(die))
    for p in die:
        if not p.is_file():raise FileNotFoundError(p)
    rec['die']=list(map(str,die));rec['top']=TOP
    rec['parameters'].update(DSPARK=1,ACCEPT_COMMIT=1,VPMAX=4,VWA=16,
                             NPROG=1024,NDESC=64,VM_ELEMS=1048576)
    rec['parameters']['HBM_STREAM4']=int(use_stream4)
    if seq_la or native_mp_commit:
        rec['parameters'].update(SEQ_LA=int(seq_la),MP_COMMIT_NATIVE=int(native_mp_commit))
    rec['adopted_joins']=dict(sequencer_la=seq_la,native_mp_commit=native_mp_commit)
    if seq_la or native_mp_commit:
        import uarch_model
        rec['integration_model_delta']={}
        if seq_la:rec['integration_model_delta']['sequencer_la']=uarch_model.qwen_combined_sequencer_la()
        if native_mp_commit:rec['integration_model_delta']['native_mp_commit']=uarch_model.qwen_combined_native_mp_commit(fill_lat=rec['parameters']['FILL_LAT'])
    rec['optional_candidates']['DSpark']=True
    rec['scope']='Opt-in owner VPOS/KVmp/near integration component; no full-token or timing qualification'
    rec['source_sha256']={str(p):hashlib.sha256(p.read_bytes()).hexdigest()
                         for p in dict.fromkeys(die+list(map(Path,rec['tile']))+list(map(Path,rec['collective']))+list(map(Path,rec.get('hbm',[]))))}
    if seq_la or native_mp_commit:
        rec['source_sha256'][str(original_top)]=hashlib.sha256(original_top.read_bytes()).hexdigest()
    (output/'sources.json').write_text(json.dumps(rec,indent=2)+'\n')
    (output/'die_sources.f').write_text('\n'.join(map(str,die))+'\n')
    return rec


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--stream4',action='store_true',help='Select owner tagged STREAM4 and actual multi-position service')
    p.add_argument('--stream4-source-root',type=Path,help='Explicit pinned source root of the retained native HBM archive; its existing hash checks remain mandatory')
    p.add_argument('--seq-la',action='store_true')
    p.add_argument('--native-mp-commit',action='store_true')
    a=p.parse_args();r=selected(a.output,use_stream4=a.stream4,seq_la=a.seq_la,native_mp_commit=a.native_mp_commit,stream4_source_root=a.stream4_source_root);print(json.dumps({'top':r['top'],'parameters':r['parameters']}))
