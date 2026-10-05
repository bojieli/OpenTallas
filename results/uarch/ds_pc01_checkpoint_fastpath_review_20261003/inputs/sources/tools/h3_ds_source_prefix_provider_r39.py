"""Source-bound prefix admission over the actual retained r37 provider.
The prefix constructor cannot authorize full-token execution or hardware.
"""
import hashlib,json,gzip
from pathlib import Path
from h3_ds_connected_provider_r37 import composed_class
NATIVE='c65a584c1b1cfafcd00391af216870136a44ec142b0d11106df570db7b8eb264'
def validate_prefix(manifest,native,stop):
    if stop not in (9,10) or type(stop)is not int:raise ValueError('prepared actual PC0-9/PC10 boundary only')
    if manifest.get('prefix_inputs_bound') is not True or manifest.get('prefix_GO') is not True or manifest.get('prefix_stop')!=stop:raise ValueError('source-bound prefix GO absent')
    if manifest['native_program_sha256']!=NATIVE or any(manifest.get(k) for k in ('full_token_GO','full_token_inputs_bound','hardware_admitted')):raise ValueError('prefix/full-token scope separation')
    if len(native['instructions'])!=2213:raise ValueError('complete future-use source required')
    produced={w['version']:o['pc'] for o in native['instructions'] for w in o['writes']}
    initial={r['version'] for r in manifest['initial_versions']}|{manifest['checkpoint_initial_embedding']['version'],manifest['checkpoint_initial_embedding']['initial_pre_version']}
    for op in native['instructions'][:stop+1]:
        for v in op['reads']:
            if v['version'] not in initial and not (v['version'] in produced and produced[v['version']]<op['pc']):raise ValueError('unbound prefix source version '+v['version'])
        for tid,bindings in op['provider_bindings'].items():
            for name,b in bindings.items():
                if b['kind']=='explicit_auxiliary_provider' and not (op['family']=='all_gather' and name=='ownership_mask'):
                    key=f"{op['pc']}/{tid}/{name}"
                    r=manifest['view_bindings'].get(key)
                    if r is None or r['source_binding']!=b or not Path(r['path']).is_file():raise ValueError('unbound prefix auxiliary '+key)
    return True

def create_prefix_provider(manifest,native,dispatch,homes,stop):
    validate_prefix(manifest,native,stop)
    return composed_class()(manifest,native,dispatch,homes)
def create_provider(*args):raise ValueError('this module admits source prefixes only; full-token inputs/GO remain separate')
