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
    require(model['top']==runtime.TOP and model['hbm_top']=='ot_qwen_hbm_stream4_tagged'
            and model['parameters']['HBM_STREAM4']==1 and model['parameters']['NEAR_HBM']==1,
            'actual STREAM4/near source book required; frozen near-only model refused')
    require(link['returncode']==0 and link['archives_stable'] is True and link['runtime_abi']==runtime.ABI,
            'actual successful STREAM4 link required')
    require(link['generated_runtime_sha256']==hashlib.sha256(runtime.emit(root).encode()).hexdigest(),
            'actual initialized STREAM4 runtime differs')
    params=link['resolved_parameters']
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
        else:external[str(p)]=h
    required=[TOP_SOURCE,'rtl/qwen_sys/combined/ot_qwen_combined_stream4_rows.sv',base.SUBSYSTEM,
              'rtl/hdc/kv/ot_qwen_hbm_stream4_tagged.sv']
    for pinfile in (base.PIN_SOURCE,'rtl/qwen_sys/combined/stream4_source_pin.json'):
        source=json.loads((root/pinfile).read_text())
        for path,h in source['sources'].items():
            # The retained source book pins the original descriptor-only
            # backend. Its history stays intact; the selected native successor
            # is instead required in the actual model pins above.
            if path=='rtl/hdc/kv/ot_qwen_hbm_stream4_ack.sv':continue
            require(pins.get(path)==h,'required native stream/near engine source absent/changed: '+path)
        pins[pinfile]=sha(root/pinfile)
    require(all(p in pins for p in required),'actual stream row/subsystem/top pins required')
    for p in ('tools/qwen_rom_combined_stream4_runtime_emit.py','tools/qwen_rom_combined_stream4_access.py',
              'tools/qwen_rom_combined_nearbaseline_runtime_emit.py','tools/qwen_rom_combined_runtime_emit.py',
              'tools/qwen_rom_combined_runtime_emit_initialized.py',runtime.initialized.predecessor.BASE,
              'tools/runtime/qwen_combined/stream4_runtime_binding.hpp','tools/runtime/qwen_combined/stream4_memory_binding.hpp',
              'tools/runtime/qwen_combined/stream4_clock_driver.hpp','tools/runtime/qwen_combined/combined_driver.hpp',
              'tools/runtime/qwen_combined/attention_descriptors.py'):
        pins[p]=sha(root/p)
    for domain,port in (('core','clk'),('service','hclk')):
        c=clocks[domain]
        require(c['port']==port and type(c['period_fs']) is int and c['period_fs']>=2
                and type(c['first_rise_fs']) is int and c['first_rise_fs']>0,'actual source clock/phase required')
    require(clocks['core']['period_fs']==params['hbm']['CORE_FS'],'STREAM4 actual core period mismatch')
    exe=link_dir/'qwen_rom_combined';require(sha(exe)==link['executable_sha256'],'linked binary changed')
    book=dict(geometry=dict(tp=4,groups=6144,sw=64,nw=18),real_mem=True,near_hbm_enabled=True,
              stream4_enabled=True,top_source=TOP_SOURCE,runtime_abi=runtime.ABI,maximum_stages=1,maximum_position=8191,
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
