#!/usr/bin/env python3
"""Write the actual initialized-HEAD selection book after the sole real link.

No compiler, runtime, image/oracle generation or admission is performed here.
"""
import argparse
import importlib
import json
from pathlib import Path
import sys


def create(source_root, compiled_source_root, model_sources, link_dir, inputs, clocks, output):
    source_root,compiled_source_root,model_sources,link_dir,inputs,output=map(Path,
        (source_root,compiled_source_root,model_sources,link_dir,inputs,output))
    source_root=source_root.resolve(strict=True)
    compiled_source_root=compiled_source_root.resolve(strict=True)
    sys.path.insert(0,str(source_root/'tools'))
    owner=importlib.import_module('qwen_rom_combined_head_launch_initialized')
    if Path(owner.__file__).resolve()!=source_root/'tools/qwen_rom_combined_head_launch_initialized.py':
        raise ValueError('selection imported from a different selected source root')
    base=owner.predecessor.predecessor
    base.require(not output.exists(),'immutable selection output exists')
    record=json.loads(model_sources.read_text())
    cache=json.loads(inputs.read_text())
    base.require(record['parameters']['HBM_LAYERS']==36 and record['parameters']['NEAR_HBM']==0,
                 'actual baseline full36 compiled model source required')
    link_path=link_dir/'link.json'
    link=json.loads(link_path.read_text())
    base.require(link['returncode']==0 and link['archives_stable'] is True,'actual successful stable link required')
    base.require(link['compiled_params_sha256']==cache['compiled_extent']['sha256'],
                 'linked extent differs from cached input extent')
    params=link['resolved_parameters']
    base.require(params['die']['HBM_LAYERS']==36 and params['hbm']['MEM_WORDS']==4718592,
                 'actual linked full36 HBM aperture required')
    pins,external={},{}
    for source,digest in record['source_sha256'].items():
        path=Path(source).resolve(strict=True)
        base.require(base.sha(path)==digest,'compiled model source changed: '+str(path))
        if path.is_relative_to(compiled_source_root):
            relative=str(path.relative_to(compiled_source_root))
            base.require(base.sha(source_root/relative)==digest,'selected runtime/model source differs: '+relative)
            pins[relative]=digest
        else:
            external[str(path)]=digest
    extras=[base.DRIVER,base.CONTEXT,'tools/qwen_rom_combined_runtime_emit.py',
            'tools/runtime/qwen_combined/hbm_stack_binding.hpp',
            'tools/runtime/qwen_combined/hbm_transport_wiring.hpp',
            'tools/runtime/qwen_combined/tile_capture_wiring.hpp',
            *owner.SOURCES]
    for path in extras:pins[path]=base.sha(source_root/path)
    executable=(link_dir/'qwen_rom_combined').resolve(strict=True)
    base.require(base.sha(executable)==link['executable_sha256'],'linked executable changed')
    book=dict(geometry=dict(tp=4,groups=6144,sw=64,nw=18),real_mem=True,near_hbm_enabled=False,
              memory_service_source=base.CANONICAL_SERVICE,
              crossing_sources=['rtl/qwen_sys/combined/ot_qwen_combined_hbm_cdc.sv',
                                'rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv'],
              top_source='rtl/qwen_sys/combined/ot_qwen_rom_combined_die.sv',
              binding_source='tools/qwen_rom_combined_head_runtime_emit_initialized.py',
              source_sha256=pins,external_generated_source_sha256=external,
              clocks=clocks,memory_model_clk_ps=params['hbm']['CLK_PS'],
              executable=str(executable),executable_sha256=link['executable_sha256'],
              driver_abi='combined-driver-v1',head_host_abi=owner.composed.HEAD_ABI,
              initialization_abi=owner.composed.INITIALIZATION_ABI,
              head_link_record=str(link_path.resolve()),head_link_record_sha256=base.sha(link_path),
              model_source_record=str(model_sources.resolve()),model_source_record_sha256=base.sha(model_sources),
              cached_inputs=str(inputs.resolve()),cached_inputs_sha256=base.sha(inputs),
              scope='Actual initialized full38 host selection; no numerical or physical verdict from book creation')
    owner.validate_selection(book,source_root)
    with output.open('x') as stream:stream.write(json.dumps(book,indent=2)+'\n')
    return book


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('source-root','compiled-source-root','model-sources','link-dir','inputs','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    for domain in ('core','service'):
        for key in ('period-fs','first-rise-fs'):
            parser.add_argument('--'+domain+'-'+key,type=int,required=True)
    args=parser.parse_args()
    clocks={d:dict(port='clk' if d=='core' else 'hclk',
                   period_fs=getattr(args,d+'_period_fs'),first_rise_fs=getattr(args,d+'_first_rise_fs'))
            for d in ('core','service')}
    book=create(args.source_root,args.compiled_source_root,args.model_sources,args.link_dir,args.inputs,clocks,args.output)
    print(json.dumps(dict(selection=str(args.output),executable=book['executable'],scope=book['scope'])))


if __name__=='__main__':main()
