"""Prepare explicit long-position native window bridge, homes and RoPE images.
Metadata/source constant generation only. No full-token launch or golden operator.
"""
import argparse,copy,gzip,hashlib,importlib.util,json,math
from collections import Counter
from importlib.machinery import SourceFileLoader
from pathlib import Path
import numpy as np
from ds_hbm_window_contract_r33 import canonical,lower_full_native,initial_home_directory
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_hbm_window_retirement_r33_20261002'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rope_bindings(native,cfg,source,output):
    loader=SourceFileLoader('source_r33_rope',str(source));spec=importlib.util.spec_from_loader(loader.name,loader);V=importlib.util.module_from_spec(spec);loader.exec_module(V)
    out={};cache={};output.mkdir()
    for op in native['instructions']:
        for key,bs in op['provider_bindings'].items():
            for name,b in bs.items():
                if b['kind']!='explicit_auxiliary_provider' or name not in ('rope_cos','rope_sin'):continue
                position=b['position'];layer=b['layer'];yarn=cfg['compress_ratios'][layer]>0;ck=(yarn,position,name)
                if ck not in cache:
                    freqs=V.rope_freqs(cfg['rope_head_dim'],cfg['original_seq_len'] if yarn else 0,cfg['compress_rope_theta'] if yarn else cfg['rope_theta'],cfg['rope_factor'],cfg['beta_fast'],cfg['beta_slow'])
                    values=V.rope_cs(freqs,position)[0 if name=='rope_cos' else 1]
                    path=output/f'{int(yarn)}_{position}_{name}.npy';np.save(path,values,allow_pickle=False)
                    cache[ck]=(path,values)
                path,values=cache[ck];sp=native['templates'][key]['providers'][name]
                if sp['shape']!=list(values.shape) or sp['dtype']!='F32':raise ValueError('source coefficient LOAD shape/type')
                out[f"{op['pc']}/{key}/{name}"]=dict(path=str(path.resolve()),sha256=sha(path),shape=list(values.shape),dtype='F32',source_binding=b,generation=1,checkpoint_revision='dba1be0a40aa45a94ad051997016db3960a90277',source_function_sha256=sha(source),source_config_sha256=sha(D/'inputs/inference_config.json'),scope='exact pinned source immutable coefficient initializer; no synthetic context/activation')
    return out
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--native',type=Path,required=True);ap.add_argument('--dispatch',type=Path,required=True);ap.add_argument('--produced-homes',type=Path,required=True);ap.add_argument('--position',type=int,required=True);ap.add_argument('--representation',choices=['pretrimmed127','full_ring128'],required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise ValueError('fresh immutable output required')
    native=json.loads(gzip.decompress(a.native.read_bytes()));homes=json.loads(a.produced_homes.read_bytes());original=sha(a.native)
    if homes['source_native_sha256']!=original:raise ValueError('produced home native source pin')
    if any(b['position']!=a.position for o in native['instructions'] for bs in o['provider_bindings'].values() for b in bs.values() if b['kind']=='explicit_auxiliary_provider'):raise ValueError('explicit source program position mismatch')
    lowered,witness=lower_full_native(native,a.position,a.representation);initial=initial_home_directory(native,homes,a.position,a.representation)
    a.out.mkdir();raw=gzip.compress(canonical(lowered),mtime=0);(a.out/'lowered_native.json.gz').write_bytes(raw)
    dispatch=json.loads(gzip.decompress(a.dispatch.read_bytes()))
    if dispatch['source_program_sha256']!=original:raise ValueError('dispatch source pin')
    joined=copy.deepcopy(dispatch);joined['source_program_sha256']=hashlib.sha256(raw).hexdigest()
    for row in witness:
        old,new=row['old_template'],row['new_template'];entry=joined['PC_dispatch'][row['PC']]
        model=copy.deepcopy(dispatch['templates'][old])
        if model['execution_path']!='source_order_live_range_stages':raise ValueError('source window dispatch path changed')
        counts=Counter()
        for n in lowered['templates'][new]['code']:counts[n['op']]+=max(1,math.prod(n['shape']))
        for field in ['baseline_once_scalar_evaluations','executed_primitive_scalar_projection']:model[field]=dict(counts)
        model['baseline_once_total']=sum(counts.values());model['forward_total']=sum(counts.values())
        model['window_source_bridge']='explicit127 source LOAD, no invented expired row; movement-only change'
        joined['templates'][new]=model
        for call in entry['calls']:
            if call['template']==old:call['template']=new
        source=lowered['instructions'][row['PC']]
        entry['rank_bindings']=source['rank_bindings'];entry['provider_bindings']=source['provider_bindings']
        for field in ['baseline_once_scalars','projected_executed_primitive_scalars']:
            if field in entry:entry[field]={op:count*len(entry['calls']) for op,count in counts.items()}
        entry['window_source_bridge_reprice_required']=True
        entry['provider_transfer_projection_scope']='original128-input reservations retained as conservative upper bound; actual source LOAD count corrected, no bandwidth credit'
    (a.out/'lowered_dispatch.json.gz').write_bytes(gzip.compress(canonical(joined),mtime=0))
    cfg=json.loads((D/'inputs/inference_config.json').read_bytes());bindings=rope_bindings(lowered,cfg,D/'inputs/source_rope_functions.py.source',a.out/'rope')
    records=dict(original_native_sha256=original,original_dispatch_sha256=sha(a.dispatch),lowered_native_sha256=hashlib.sha256(raw).hexdigest(),lowered_dispatch_sha256=sha(a.out/'lowered_dispatch.json.gz'),representation=a.representation,position=a.position,changed_window_PCs=len(witness),arithmetic_instruction_changes=0,explicit_window_shape_and_slice_changes=True,window_template_joins=witness,source_owned_RoPE_bindings=len(bindings),retained_window_payloads_available=False,full_token_GO=False,calendar_reprice='source count and native/dispatch template IDs joined; Sagan/Dewey physical service costs remain positive/unmeasured; no clock or rate credit')
    for name,value in [('bridge.json',records),('initial_window_homes.json',initial),('rope_bindings.json',bindings)]:
        (a.out/name).write_bytes(canonical(value)+b'\n')
if __name__=='__main__':main()
