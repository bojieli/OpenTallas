#!/usr/bin/env python3
"""Select the actual linked single-store STREAM4 minimum-layer host."""
import argparse
import hashlib
import json
from pathlib import Path
import qwen_rom_combined_nearbaseline_selection as base
import qwen_rom_combined_stream4_runtime_emit as runtime

TOP_SOURCE='rtl/qwen_sys/combined/ot_qwen_rom_combined_stream4_die.sv'
sha=base.sha
require=base.require


def create(source_root,compiled_source_root,model_sources,link_dir,clocks,output):
    root,compiled,model_sources,link_dir,output=map(Path,(source_root,compiled_source_root,model_sources,link_dir,output))
    require(not output.exists(),'immutable selection exists')
    model=json.loads(model_sources.read_text());link_path=link_dir/'link.json';link=json.loads(link_path.read_text())
    dspark=model['top']=='ot_qwen_rom_combined_dspark_die'
    top_source='rtl/qwen_sys/combined/ot_qwen_rom_combined_dspark_die.sv' if dspark else TOP_SOURCE
    require(model['top'] in (runtime.TOP,'ot_qwen_rom_combined_dspark_die') and model['hbm_top']=='ot_qwen_hbm_stream4_tagged'
            and model['parameters']['HBM_STREAM4']==1 and model['parameters']['NEAR_HBM']==1,
            'actual STREAM4/near source book required; frozen near-only model refused')
    require(link['returncode']==0 and link['archives_stable'] is True and link['runtime_abi']==runtime.ABI,
            'actual successful STREAM4 link required')
    require(link['top']==model['top'] and link.get('dspark_enabled',False)==dspark,
            'actual runtime/model DSpark selection differs')
    require(link['generated_runtime_sha256']==hashlib.sha256(runtime.emit(root,dspark=dspark,full_decoder=link.get("full_decoder",False)).encode()).hexdigest(),
            'actual initialized STREAM4 runtime differs')
    params=link['resolved_parameters']
    for key in ('SEQ_LA','MP_COMMIT_NATIVE'):
        require(params['die'].get(key,0)==model['parameters'].get(key,0),
                'compiled adopted source flag differs: '+key)
    adopted=all(params['die'].get(k)==1 for k in ('SEQ_LA','MP_COMMIT_NATIVE'))
    if link.get('adopted_required'):require(adopted,'required adopted source flags absent')
    if dspark:
        require(all(params['die'].get(k)==v for k,v in dict(DSPARK=1,ACCEPT_COMMIT=1,VPMAX=4,VWA=16,
                    VM_ELEMS=1048576,NPROG=1024,NDESC=64).items()), 'actual ACCEPT_COMMIT1 compiled model required')
    require(params['hbm']['NSTK']==4 and params['hbm']['NPC']==128 and params['hbm']['TAGW']==9
            and params['hbm']['TTAGW']==13
            and params['die']['HBM_STREAM4']==1 and params['die']['NEAR_HBM']==1,
            'actual single-store compiled STREAM4 models required')
    native=Path(link['native_tagged_source'])
    require(sha(native)==link['native_tagged_sha256'],'required native shared-row source changed')
    pins,external={},{}
    for name,h in model['source_sha256'].items():
        p=Path(name).resolve(strict=True);require(sha(p)==h,'compiled model source changed: '+name)
        if p.is_relative_to(compiled.resolve()):
            relative=str(p.relative_to(compiled.resolve()))
            require(sha(root/relative)==h,'selected runtime/model source differs: '+relative);pins[relative]=h
        else:
            external[str(p)]=h
            reuse=Path(model.get('stream4_source_root',str(compiled))).resolve()
            if p.is_relative_to(reuse):
                relative=str(p.relative_to(reuse));equivalent=root/relative
                if equivalent.is_file() and sha(equivalent)==h:pins[relative]=h
    if model['parameters'].get('SEQ_LA')==1:
        require('rtl/qwen_sys/combined/ot_qwen_tp_seq_combined_vp_la.sv' in pins,'actual LA successor source missing')
    if model['parameters'].get('MP_COMMIT_NATIVE')==1:
        require(all(path in pins for path in ('rtl/hdc/kv/ot_qwen_kv_mp_commit.sv',
                    'rtl/hdc/kv/ot_qwen_rt_kv_stream4_mp_commit_service.sv')),'actual canonical MP join source missing')
    required=[top_source,'rtl/qwen_sys/combined/ot_qwen_combined_stream4_rows.sv',base.SUBSYSTEM,
              'rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv']
    if dspark:required.append('rtl/hdc/kv/ot_qwen_rt_kv_stream4_mp_service.sv')
    for pinfile in (base.PIN_SOURCE,'rtl/qwen_sys/combined/stream4_tagged_source_pin.json'):
        pin_root=Path(model.get('stream4_source_root',str(root))) if pinfile.endswith('stream4_tagged_source_pin.json') else root
        source=json.loads((pin_root/pinfile).read_text())
        for path,h in source['sources'].items():
            if dspark and path=='rtl/hdc/kv/ot_qwen_rt_kv_stream4_service.sv':continue
            if not dspark and path=='rtl/hdc/kv/ot_qwen_rt_kv_stream4_mp_service.sv':continue
            selected_hashes=[value for selected_path,value in model['source_sha256'].items()
                             if Path(selected_path)==pin_root/path]
            require(selected_hashes==[h],'required native stream/near engine source absent/changed: '+path)
        if pin_root==root:pins[pinfile]=sha(root/pinfile)
        else:external[str(pin_root/pinfile)]=sha(pin_root/pinfile)
    require(all(p in pins for p in required),'actual stream row/subsystem/top pins required')
    for p in ('tools/qwen_rom_combined_stream4_runtime_emit.py','tools/qwen_rom_combined_stream4_access.py',
              'tools/qwen_rom_combined_nearbaseline_runtime_emit.py','tools/qwen_rom_combined_runtime_emit.py',
              'tools/qwen_rom_combined_runtime_emit_initialized.py',runtime.initialized.predecessor.BASE,
              'tools/runtime/qwen_combined/stream4_runtime_binding.hpp','tools/runtime/qwen_combined/stream4_memory_binding.hpp',
              'tools/runtime/qwen_combined/stream4_clock_driver.hpp','tools/runtime/qwen_combined/combined_driver.hpp',
              'tools/runtime/qwen_combined/attention_descriptors.py'):
        pins[p]=sha(root/p)
    if dspark:
        for p in ('tools/qwen_rom_combined_dspark_runtime_emit.py','tools/runtime/qwen_combined/dspark_slot_binding.hpp'):
            pins[p]=sha(root/p)
    for domain,port in (('core','clk'),('service','hclk')):
        c=clocks[domain]
        require(c['port']==port and type(c['period_fs']) is int and c['period_fs']>=2
                and type(c['first_rise_fs']) is int and c['first_rise_fs']>0,'actual source clock/phase required')
    require(clocks['core']['period_fs']==params['hbm']['CORE_FS'],'STREAM4 actual core period mismatch')
    exe=link_dir/'qwen_rom_combined';require(sha(exe)==link['executable_sha256'],'linked binary changed')
    book=dict(geometry=dict(tp=4,groups=6144,sw=64,nw=18),real_mem=True,near_hbm_enabled=True,
              stream4_enabled=True,dspark_enabled=dspark,adopted_joins_enabled=adopted,top_source=top_source,runtime_abi=runtime.ABI,
              full_decoder=link.get("full_decoder",False),maximum_stages=37 if link.get("full_decoder",False) else (2 if dspark else 1),maximum_position=8191,
              source_sha256=pins,external_generated_source_sha256=external,clocks=clocks,
              stream4_core_fs=params['hbm']['CORE_FS'],stream4_controller_fs=params['hbm']['CTL_FS'],
              executable=str(exe.resolve()),executable_sha256=link['executable_sha256'],
              link_record=str(link_path.resolve()),link_record_sha256=sha(link_path),
              native_tagged_source=str(native.resolve()),native_tagged_sha256=sha(native),
              initialization_abi=runtime.initialized.INITIALIZATION_ABI,
              model_source_record=str(model_sources.resolve()),model_source_sha256=sha(model_sources),
              scope='One actual initialized P8191 STREAM4/near layer; no full-token gain or physical verdict')
    with output.open('x') as stream:stream.write(json.dumps(book,indent=2)+'\n')
    return book


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('source-root','compiled-source-root','model-sources','link-dir','output'):p.add_argument('--'+key,type=Path,required=True)
    for domain in ('core','service'):
        for k in ('period-fs','first-rise-fs'):p.add_argument('--'+domain+'-'+k,type=int,required=True)
    a=p.parse_args();clocks={d:dict(port='clk' if d=='core' else 'hclk',period_fs=getattr(a,d+'_period_fs'),first_rise_fs=getattr(a,d+'_first_rise_fs')) for d in ('core','service')}
    create(a.source_root,a.compiled_source_root,a.model_sources,a.link_dir,clocks,a.output)
