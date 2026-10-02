#!/usr/bin/env python3
"""Data-only Peirce driver home bridge. Default preparation; run opt-in.
No source operator/rounding edits and no RF workspace->Sagan shared relabel.
Full run requires supplied real context/aux/provider semantics, not synthetic KV.
"""
import argparse,gzip,hashlib,importlib.util,json,sys
from pathlib import Path
from ds_hbm_finite_state_homes_r30 import compile_directory,patch_homes
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,v):
    with p.open('x') as f:json.dump(v,f,indent=2,sort_keys=True);f.write('\n')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--driver-source',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--run-full-token',action='store_true');a=ap.parse_args()
    if a.out.exists():raise ValueError('immutable fresh output required')
    a.out.mkdir(parents=True);m=json.loads(a.manifest.read_bytes());module=ROOT/'tools/h3_ds_checkpoint_provider_r30.py'
    sys.path.append(str(a.driver_source.parent));spec=importlib.util.spec_from_file_location('Peirce_pinned_driver',a.driver_source);T=importlib.util.module_from_spec(spec);spec.loader.exec_module(T)
    native,dispatch,homes=T.load_programs();native_sha=T.sha(T.ROOT/T.PROGRAM)
    if m['native_program_sha256']!=native_sha:raise ValueError('original full-program pin')
    directory=compile_directory(native,native_sha);joined,homes=patch_homes(native,list(homes),directory)
    assert joined['templates'] is native['templates'] and len(joined['instructions'])==2213
    # No original opcode/source/operand/dependency/rank/output node changed.
    for original,new in zip(native['instructions'],joined['instructions']):
        for key in original:
            if key!='writes':assert original[key]==new[key],key
        for before,after in zip(original['writes'],new['writes']):
            assert {k:v for k,v in before.items() if k!='home_indices'}=={k:v for k,v in after.items() if k!='home_indices'}
    m.update(provider_module_sha256=sha(module),journal_root=str(a.out.resolve()/'journal'),journal_capacity_bytes=8<<30,persistent_fragment_extent=dict(AW=27,base=32<<20,bytes=32<<20,capacity_charge_bytes_all96_ranks=96*(32<<20)))
    inputs=ROOT/'results/uarch/ds_hbm_checkpoint_finite_homes_r30_20261002/inputs'
    recipe=m['checkpoint_initial_embedding'];recipe.update(initializer_source=str(inputs/'initializer.py.snapshot'),initializer_sha256=sha(inputs/'initializer.py.snapshot'),token_history_source=str(inputs/'initial_token_history.json'),token_history_sha256=sha(inputs/'initial_token_history.json'),initial_pre_version='DeepSeek.-1.pre.1')
    write(a.out/'provider_manifest.json',m);write(a.out/'finite_state_home_directory.json',directory)
    record=dict(status='PREPARED_SOURCE_OPERATOR_IDENTICAL_HOME_BRIDGE_FULL_TOKEN_INPUTS_OPEN',original_native_sha256=native_sha,driver_sha256=sha(a.driver_source),provider_sha256=sha(module),source_home_count=286114,joined_home_count=len(homes),added_rank_fragment_homes=len(directory['rows']),new_nonempty_source_write_bindings=56,source_operator_changes=0,initial_embedding_and_pre_source_bound=True,shared_C0_bridge='Sagan-owned native64KiB/64B movement bridge remains distinct from this32MiB state extent and32MiB scratch',full_token_launched=False,physical_qualified=False,ready_for_full_token=False)
    write(a.out/'prepared_record.json',record)
    if not a.run_full_token:return
    if not m.get('full_token_inputs_bound',False):raise ValueError('actual retained-context/aux/route/views not bound; do not launch known missing inputs')
    import h3_ds_checkpoint_provider_r30 as P
    emergency_reserve=bytearray(1048576) # host-only failure receipt reserve
    try:
        provider=P.create_provider(m,joined,dispatch,homes)
        write(a.out/'record.json',T.TokenDriver(joined,dispatch,provider,m['checkpoint_revision'],m['generation'],homes).run())
    except Exception as exc:
        emergency_reserve=None
        write(a.out/'record.json',dict(status='FAIL_CLOSED_FULL_NATIVE_PROVIDER',reason=repr(exc),full_token_completed=False));raise
if __name__=='__main__':main()
