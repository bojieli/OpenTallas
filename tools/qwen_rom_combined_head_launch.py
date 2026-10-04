#!/usr/bin/env python3
"""Explicit additive head launcher hooks; the existing three-layer path is unchanged.

Confucius can consume layers_from_stages() and validate_head_runtime() in the
full-36 cached-input hook. main retains the predecessor's frozen-PASS requirement;
it never fabricates a full-token baseline from E-only or a three-layer PASS.
"""
import json
from pathlib import Path
import qwen_rom_combined_launch as predecessor
import qwen_rom_combined_head_runtime_emit as head

ROOT=Path(__file__).resolve().parents[1]
BASE_VALIDATE=predecessor.validate_selection


def layers_from_stages(path):
    stages=[]
    for line in Path(path).read_text().splitlines():
        words=line.split()
        if not words or words[0].startswith('#'):continue
        predecessor.require(len(words)==6,'head stage ABI requires four actual rank paths and reset')
        name,*directories,reset=words
        predecessor.require(reset in ('0','1'),'invalid stage reset')
        predecessor.require(all(Path(p).is_dir() for p in directories),'missing released stage image directory')
        if name in ('E','head'):predecessor.require(reset=='0','E/head have no KV reset')
        stages.append(name)
    predecessor.require(stages==['E']+[f'L{l}' for l in range(36)]+['head'],
                        'full token requires E, L0..L35, head exactly once in order')
    return list(range(36))


def validate_head_runtime(book, root=ROOT):
    binary=BASE_VALIDATE(book,root)
    predecessor.require(book.get('head_host_abi')==head.HEAD_ABI,'compiled head host selection required')
    emitter='tools/qwen_rom_combined_head_runtime_emit.py'
    predecessor.require(book['source_sha256'].get(emitter)==predecessor.sha(root/emitter),'head emitter source pin required')
    path=Path(book['head_link_record'])
    predecessor.require(predecessor.sha(path)==book['head_link_record_sha256'],'head link record changed')
    link=json.loads(path.read_text())
    import hashlib
    expected=hashlib.sha256(head.emit(root).encode()).hexdigest()
    predecessor.require(link.get('returncode')==0 and link.get('archives_stable') is True
                        and link.get('generated_runtime_sha256')==expected
                        and link.get('executable_sha256')==book['executable_sha256'],
                        'actual linked head source/binary identity required')
    return binary


def prepare_from_inputs(book_path, inputs_path, output, root=ROOT):
    """Connect Confucius's pinned cache receipt to the actual head executable.

    Pending/failed single-stage RTL baselines remain diagnostics. This prepares
    the first measured combined run, never claims a prior composed PASS and
    never exports/recomputes history or builds/launches anything.
    """
    book_path,inputs_path,output=map(Path,(book_path,inputs_path,output))
    book=json.loads(book_path.read_text())
    binary=validate_head_runtime(book,root)
    inputs=json.loads(inputs_path.read_text())
    predecessor.require(inputs.get('schema')=='opentallas.qwen-rom-full36-inputs.v1',
                        'Confucius existing full36 cache receipt required')
    predecessor.require(not output.exists(),'immutable fulltoken output exists')
    oracle_path=Path(inputs['oracle']['root'])/'oracle.json'
    predecessor.require(predecessor.sha(oracle_path)==inputs['oracle']['sha256'],'cached full oracle changed')
    oracle=json.loads(oracle_path.read_text())
    predecessor.require(oracle.get('status')=='ISA_golden_only' and oracle.get('layers')==36
                        and oracle.get('head') is True and oracle.get('tp')==4
                        and oracle.get('groups')==6144 and oracle.get('kv_format')=='fp8',
                        'completed full36/head TP4 oracle required')
    position,token=inputs['position'],inputs['token']
    frame=oracle['per_position'][str(position)]
    predecessor.require(frame['token']==token,'fulltoken oracle frame differs')
    predecessor.require([s['name'] for s in inputs['stages']]==['E']+[f'L{l}' for l in range(36)]+['head'],
                        'fulltoken stage order differs')
    compiled=inputs['compiled_extent']
    predecessor.require(compiled['hbm_layers']==36 and compiled['memory_words_per_stack']==4718592
                        and predecessor.sha(compiled['path'])==compiled['sha256'],'compiled full36 extent changed')
    linked=json.loads(Path(book['head_link_record']).read_text())
    predecessor.require(linked.get('compiled_params_sha256')==compiled['sha256'],
                        'head binary compiled extent differs from input receipt')
    preload=Path(inputs['preload']['path']).resolve(strict=True)
    predecessor.require(predecessor.sha(preload)==inputs['preload']['sha256']==frame['x_preload_sha256'],
                        'cached fulltoken preload differs')
    embedding=inputs['embedding']
    embed_args=predecessor.embedding_argument(embedding['raw'],embedding['sha256'],token)
    wanted={f'L{l}_die{r}' for l in range(36) for r in range(4)}
    predecessor.require(set(inputs['history'])==wanted,'all144 existing history bindings required')
    history_dir=Path(inputs['history_directory']).resolve(strict=True)
    history_pins={}
    for key,binding in inputs['history'].items():
        raw=Path(binding['raw']).resolve(strict=True)
        alias=history_dir/(key+'.bin')
        predecessor.require(alias.resolve(strict=True)==raw and raw.stat().st_size==16777216,
                            'cached raw history path/extent differs: '+key)
        predecessor.require(binding['source_sha256']==frame['kv_pre_sha256'][key],
                            'cached history source pin differs: '+key)
        predecessor.require(predecessor.sha(raw)==binding['raw_sha256'],
                            'cached raw history changed: '+key)
        # The input owner bit-checked raw against NPY. Revalidate the raw bytes
        # at actual launch preparation and preserve its post-run binding.
        history_pins[key]=dict(binding)
    lines=[]
    payload_pins={}
    for stage in inputs['stages']:
        predecessor.require(predecessor.sha(stage['source_stage_list'])==stage['source_sha256'],
                            'source stage list changed: '+stage['name'])
        words=Path(stage['source_stage_list']).read_text().split()
        expected=[stage['name'],*stage['directories'],str(stage['kv_reset'])]
        predecessor.require(words==expected and len(words)==6,'source stage tuple differs')
        if stage['name'] in ('E','head'):
            predecessor.require(stage['kv_reset']==0,'E/head must have no KV reset')
        predecessor.require(len(stage['image_sha256'])==20,'allfive image files/allfour rank pins required')
        for rank,directory in enumerate(stage['directories']):
            directory=Path(directory).resolve(strict=True)
            for filename in ('matrix_int8.hex','matrix_scale_bf16.hex','crom.hex','program.hex','segments.hex'):
                path=directory/filename
                predecessor.require(path.is_file(),'missing cached image: '+str(path))
                pin=stage['image_sha256'][f"{stage['name']}/die{rank}/{filename}"]
                predecessor.require(predecessor.sha(path)==pin,'cached image changed: '+str(path))
                payload_pins[str(path)]=pin
        lines.append(' '.join([stage['name'],*(str(Path(d).resolve()) for d in stage['directories']),str(stage['kv_reset'])]))
    output.mkdir(parents=True)
    stages=output/'stages.txt'
    stages.write_text('\n'.join(lines)+'\n')
    layers_from_stages(stages)
    (output/'run').mkdir()
    command=[str(binary),'--stages',str(stages.resolve()),str((output/'run').resolve()),str(preload),
             '--pos',str(position),'--token',str(token),'--kv-dir',str(history_dir),'--kv-ideal','0',*embed_args]
    for domain in ('core','service'):
        for key in ('period_fs','first_rise_fs'):
            command+=['--'+domain+'-'+key.replace('_','-'),str(book['clocks'][domain][key])]
    record=dict(schema='opentallas.qwen-rom-combined-fulltoken-launch.v1',status='prepared',
                scope='First actual full36/head combined measurement; no preexisting composed PASS implied',
                selection=book,position=position,token=token,layers=list(range(36)),head_enabled=True,
                command=command,kv_history=history_pins,stage_payload_sha256=payload_pins,
                input_sha256={str(p.resolve()):predecessor.sha(p) for p in
                              (book_path,inputs_path,oracle_path,preload,Path(embed_args[1]),
                               Path(compiled['path']),Path(book['head_link_record']))},
                embedding=dict(embedding),baseline_references=inputs['baselines'],
                baseline_pending=inputs['baseline_pending'],input_diagnostics=inputs['gaps'])
    (output/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
    return command,record


def main():
    old_layers,old_validate=predecessor.layers_from_stages,predecessor.validate_selection
    try:
        predecessor.layers_from_stages=layers_from_stages
        predecessor.validate_selection=validate_head_runtime
        return predecessor.main()
    finally:
        predecessor.layers_from_stages=old_layers
        predecessor.validate_selection=old_validate


if __name__=='__main__':raise SystemExit(main())
