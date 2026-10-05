#!/usr/bin/env python3
"""Select the real initialized NEAR1 per-layer executable after the sole link.

This successor does not invoke or weaken the frozen NEAR0/HEAD selector. Image
owners supply source-derived descriptor3 images and existing P8191 raw history.
"""
import argparse
import hashlib
import json
from pathlib import Path
import qwen_rom_combined_nearbaseline_runtime_emit as runtime

TOP_SOURCE = 'rtl/qwen_sys/combined/ot_qwen_rom_combined_nearbaseline_die.sv'
SUBSYSTEM = 'rtl/qwen_sys/combined/ot_qwen_combined_nearbaseline_subsystem.sv'
PIN_SOURCE = 'rtl/qwen_sys/combined/nearbaseline_source_pin.json'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(value, message):
    if not value:
        raise ValueError(message)


def create(source_root, compiled_source_root, model_sources, link_dir, clocks, output):
    root, compiled, model_sources, link_dir, output = map(Path,
        (source_root, compiled_source_root, model_sources, link_dir, output))
    require(not output.exists(), 'immutable selection exists')
    model = json.loads(model_sources.read_text())
    require(model['top'] == runtime.TOP and model['parameters']['NEAR_HBM'] == 1,
            'actual compiled mandatory NEAR1 top required')
    require(model['mandatory_baseline']['layer_start_fence'] == 1
            and model['mandatory_baseline']['collective'] == 'one-stream AR256',
            'actual fenced one-stream baseline required')
    link_path = link_dir/'link.json'
    link = json.loads(link_path.read_text())
    require(link['returncode'] == 0 and link['archives_stable'] is True, 'successful stable actual link required')
    params = link['resolved_parameters']
    require(all(params['die'].get(k) == v for k,v in
                dict(NEAR_HBM=1, G=6144, SW=64, NW=18, SNW=18, D=4, NPC=32, REAL_MEM=1).items()),
            'compiled nearbaseline geometry differs')
    require(params['hbm']['MEM_WORDS'] == params['die']['HBM_LAYERS']*131072
            and params['coll']['TAGW'] == 44, 'actual memory extent/collective tag differs')
    pins, external = {}, {}
    for name, digest in model['source_sha256'].items():
        p = Path(name).resolve(strict=True)
        require(sha(p) == digest, 'compiled source changed: '+name)
        if p.is_relative_to(compiled.resolve()):
            relative = str(p.relative_to(compiled.resolve()))
            require(sha(root/relative) == digest, 'selected source differs: '+relative)
            pins[relative] = digest
        else:
            external[str(p)] = digest
    engine = json.loads((root/PIN_SOURCE).read_text())
    for path in (TOP_SOURCE, SUBSYSTEM, *engine['sources']):
        require(path in pins, 'mandatory top/subsystem/pipelined source absent: '+path)
    for path, digest in engine['sources'].items():
        require(pins[path] == digest, 'selected pipelined source differs: '+path)
    require(model['mandatory_baseline']['pipelined_hub_row_engine'] == engine['engine_commit'],
            'selected pipelined engine identity differs')
    extras = (PIN_SOURCE, 'tools/qwen_rom_combined_nearbaseline_runtime_emit.py',
              'tools/qwen_rom_combined_nearbaseline_access.py',
              'tools/qwen_rom_combined_runtime_emit.py',
              'tools/qwen_rom_combined_runtime_emit_initialized.py',
              'tools/runtime/qwen_combined/combined_driver.hpp',
              'tools/runtime/qwen_combined/fullshape_context.hpp',
              'tools/runtime/qwen_combined/hbm_stack_binding.hpp',
              'tools/runtime/qwen_combined/hbm_transport_wiring.hpp',
              'tools/runtime/qwen_combined/attention_descriptors.py', runtime.initialized.predecessor.BASE)
    for path in extras:
        pins[path] = sha(root/path)
    require(link['generated_runtime_sha256'] == hashlib.sha256(runtime.emit(root).encode()).hexdigest(),
            'actual initialized near layer runtime was not linked')
    exe = link_dir/'qwen_rom_combined'
    require(sha(exe) == link['executable_sha256'], 'actual linked executable changed')
    for domain, port in (('core','clk'), ('service','hclk')):
        c = clocks[domain]
        require(c['port'] == port and type(c['period_fs']) is int and c['period_fs'] > 0
                and c['period_fs'] % 2 == 0 and type(c['first_rise_fs']) is int
                and c['first_rise_fs'] > 0, 'actual positive clock stimulus required')
    require(clocks['service']['period_fs'] == params['hbm']['CLK_PS']*1000, 'compiled HBM clock mismatch')
    book = dict(geometry=dict(tp=4,groups=6144,sw=64,nw=18),real_mem=True,
                near_hbm_enabled=True,top_source=TOP_SOURCE,subsystem_source=SUBSYSTEM,
                source_sha256=pins,external_generated_source_sha256=external,
                binding_source='tools/qwen_rom_combined_nearbaseline_runtime_emit.py',
                runtime_abi=runtime.ABI,initialization_abi=runtime.initialized.INITIALIZATION_ABI,
                clocks=clocks,memory_model_clk_ps=params['hbm']['CLK_PS'],
                executable=str(exe.resolve()),executable_sha256=link['executable_sha256'],
                model_source_record=str(model_sources.resolve()),model_source_sha256=sha(model_sources),
                link_record=str(link_path.resolve()),link_record_sha256=sha(link_path),
                maximum_position=8191,maximum_stages=1,descriptor_kind=3,
                scope='Mandatory 8K nearbaseline, one decoder layer; composition and actual measurements separate')
    with output.open('x') as stream:
        stream.write(json.dumps(book,indent=2)+'\n')
    return book


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('source-root','compiled-source-root','model-sources','link-dir','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    for domain in ('core','service'):
        for key in ('period-fs','first-rise-fs'):
            parser.add_argument('--'+domain+'-'+key,type=int,required=True)
    args = parser.parse_args()
    clocks = {d:dict(port='clk' if d=='core' else 'hclk',
                    period_fs=getattr(args,d+'_period_fs'),first_rise_fs=getattr(args,d+'_first_rise_fs'))
              for d in ('core','service')}
    create(args.source_root,args.compiled_source_root,args.model_sources,args.link_dir,clocks,args.output)
