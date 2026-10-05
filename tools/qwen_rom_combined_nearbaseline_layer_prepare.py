#!/usr/bin/env python3
"""Prepare ONE P8191 layer from existing cached bytes, without executing a DUT.

Images must already be derived by attention_descriptors.emit. Raw history is
checked byte-for-byte against the pinned NPY payload; no inference, arithmetic,
conversion, new history export, model build or runtime launch occurs here.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import numpy as np
import qwen_rom_combined_nearbaseline_selection as selected
import qwen_rom_combined_nearbaseline_runtime_emit as runtime

ROOT = Path(__file__).resolve().parents[1]


def raw_matches_npy(raw, source):
    array = np.load(source, mmap_mode='r', allow_pickle=False)
    selected.require(array.dtype == np.dtype('<u4') and array.flags.c_contiguous
                     and array.nbytes == 16777216 and Path(raw).stat().st_size == array.nbytes,
                     'actual u32 contiguous full KV extent required')
    view = memoryview(array).cast('B')
    with Path(raw).open('rb') as stream:
        for offset in range(0, len(view), 1048576):
            selected.require(stream.read(1048576) == view[offset:offset+1048576],
                             'existing raw KV bytes differ from cached NPY')


def prepare(selection, oracle_root, oracle_sha256, history, images, layer, output, root=ROOT):
    selection, oracle_root, history, output = map(Path, (selection, oracle_root, history, output))
    root = Path(root)
    selected.require(not output.exists() and type(layer) is int and 0 <= layer < 36,
                     'one decoder layer and fresh output required')
    selected.require(len(images) == 4, 'all four actual rank image directories required')
    book = json.loads(selection.read_text())
    selected.require(book.get('near_hbm_enabled') is True and book.get('real_mem') is True
                     and book.get('top_source') == selected.TOP_SOURCE
                     and book.get('runtime_abi') == runtime.ABI
                     and book.get('maximum_stages') == 1, 'actual NEAR1 per-layer selection required')
    for p,h in book['source_sha256'].items():
        selected.require(selected.sha(root/p) == h, 'selected runtime/model source changed: '+p)
    for p,h in book['external_generated_source_sha256'].items():
        selected.require(selected.sha(p) == h, 'generated model source changed: '+p)
    linked = json.loads(Path(book['link_record']).read_text())
    selected.require(selected.sha(book['link_record']) == book['link_record_sha256']
                     and linked['returncode'] == 0 and linked['archives_stable'] is True
                     and linked['generated_runtime_sha256'] == hashlib.sha256(runtime.emit(root).encode()).hexdigest()
                     and selected.sha(book['executable']) == book['executable_sha256'] == linked['executable_sha256'],
                     'actual initialized nearbaseline executable changed')
    selected.require(linked['resolved_parameters']['die']['NEAR_HBM'] == 1,
                     'compiled NEAR1 required')
    oracle_path = oracle_root/'oracle.json'
    selected.require(selected.sha(oracle_path) == oracle_sha256, 'existing oracle pin differs')
    oracle = json.loads(oracle_path.read_text())
    selected.require(oracle['status'] == 'ISA_golden_only' and oracle['tp'] == 4
                     and oracle['groups'] == 6144 and layer < oracle['layers'], 'existing actual TP4 oracle required')
    frame = oracle['per_position']['8191'];position_dir=oracle_root/'P8191'
    # A layer run begins with the cached producer's X. It is not a token run.
    preload = position_dir/('x_preload.hex' if layer == 0 else f'L{layer-1:02d}_die0_x.hex')
    preload_pin = frame['x_preload_sha256'] if layer == 0 else frame['layer_x_sha256'][f'L{layer-1}_die0']
    selected.require(selected.sha(preload) == preload_pin, 'actual entering-layer X changed')
    if layer:
        reference = preload.read_bytes()
        for rank in range(1,4):
            p=position_dir/f'L{layer-1:02d}_die{rank}_x.hex'
            selected.require(selected.sha(p) == frame['layer_x_sha256'][f'L{layer-1}_die{rank}']
                             and p.read_bytes() == reference, 'rank entering-X differs; single preload cannot bind it')
    pins={str(p.resolve()):selected.sha(p) for p in (selection,oracle_path,preload,Path(book['link_record']))}
    raw_bindings={};image_pins={};directories=[]
    sys.path.insert(0,str(root))
    try:
        from tools.runtime.qwen_combined import attention_descriptors as descriptors
    finally:
        sys.path.pop(0)
    for rank, directory in enumerate(images):
        directory=Path(directory).resolve(strict=True);directories.append(str(directory))
        binding=directory/'descriptor_binding.json';b=json.loads(binding.read_text())
        source=Path(b['source'])
        selected.require(b['schema']=='opentallas.qwen-rom-near-descriptor-images.v1'
                         and descriptors.sha(source/'program.hex')==b['source_program_sha256']
                         and descriptors.sha(source/'segments.hex')==b['source_descriptors_sha256'],
                         'actual f2a5 source descriptor pins required')
        words,desc,_=descriptors.derive(
            [int(x,16) for x in (source/'program.hex').read_text().split()],
            [int(x,16) for x in (source/'segments.hex').read_text().split()],enable=True)
        selected.require(words==[int(x,16) for x in (directory/'program.hex').read_text().split()]
                         and desc==[int(x,16) for x in (directory/'segments.hex').read_text().split()],
                         'descriptor3 program differs from literal source derivation')
        for filename in ('matrix_int8.hex','matrix_scale_bf16.hex','crom.hex'):
            selected.require((directory/filename).resolve()==(source/filename).resolve(),
                             'immutable matrix/constants must retain original source homes')
        for filename in ('program.hex','segments.hex','matrix_int8.hex','matrix_scale_bf16.hex','crom.hex','descriptor_binding.json'):
            p=directory/filename;image_pins[str(p)]=selected.sha(p)
        raw=history/f'L{layer}_die{rank}.bin';npy=position_dir/'kv_pre'/f'L{layer}_die{rank}.npy'
        selected.require(selected.sha(npy)==frame['kv_pre_sha256'][f'L{layer}_die{rank}'], 'cached source history changed')
        raw_matches_npy(raw,npy)
        raw_bindings[f'L{layer}_die{rank}']=dict(raw=str(raw.resolve()),raw_sha256=selected.sha(raw),
                                              source=str(npy.resolve()),source_sha256=selected.sha(npy))
    output.mkdir();(output/'run').mkdir()
    stages=output/'stages.txt';stages.write_text(' '.join([f'L{layer}',*directories,'1'])+'\n')
    command=[book['executable'],'--stages',str(stages.resolve()),str((output/'run').resolve()),str(preload.resolve()),
             '--pos','8191','--token',str(frame['token']),'--kv-dir',str(history.resolve()),'--kv-ideal','0']
    for domain in ('core','service'):
        for k in ('period_fs','first_rise_fs'):
            command+=['--'+domain+'-'+k.replace('_','-'),str(book['clocks'][domain][k])]
    record=dict(status='prepared',scope='One P8191 decoder layer; token latency by composition, no full-token PASS',
                position=8191,token=frame['token'],layers=[layer],command=command,selection=book,
                input_sha256=pins,stage_payload_sha256=image_pins,kv_history=raw_bindings,
                entering_X='cached per-layer boundary only; no continuous token execution claimed',
                numerical_oracle_sha256=oracle_sha256)
    (output/'launch.json').write_text(json.dumps(record,indent=2)+'\n')
    return command,record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('selection','oracle-root','history','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--oracle-sha256',required=True);p.add_argument('--layer',type=int,required=True)
    p.add_argument('--images',type=Path,nargs=4,required=True)
    args=p.parse_args();command,_=prepare(**vars(args));print(json.dumps(dict(command=command,status='prepared')))
