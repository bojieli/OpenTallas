"""Infrastructure-only descriptor admission for unchanged r37 source prefix.
No CPU-time, memory, file-size or wall-clock limits introduced. An explicit
--execute is required. The failed r37 launch is retained; no automatic retry.
"""
import argparse,gzip,hashlib,json,os,resource,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
D=ROOT/'results/uarch/ds_hbm_connected_source_r37_20261002'
def descriptor_model(manifest):
    initial=manifest['initial_versions'];history=[r for r in manifest['history_images'] if r['kind'] in (1,2)]
    return dict(initial_locked_views=len(initial),distinct_initial_files=len({(r['path'],r['sha256']) for r in initial}),history_locked_views=len(history),auxiliary_unique_files=len({(r['path'],r['sha256']) for r in manifest['view_bindings'].values()}),initial_retained_descriptors=2*len(initial),LockedArray_descriptors_per_instance=2,
      note='Actual source opens one locked fd plus one np.load mmap fd per image; no sharing credit; history and lazy auxiliary images are additional')
def main():
    p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if not a.execute:raise ValueError('explicit prefix invocation only; default off')
    manifest=json.loads(gzip.decompress((D/'inputs/prefix_input_manifest.json.gz').read_bytes()))
    projection=json.loads((D/'prefix_model.json').read_bytes());fds=descriptor_model(manifest);soft,hard=resource.getrlimit(resource.RLIMIT_NOFILE)
    if hard==resource.RLIM_INFINITY:target=hard
    elif hard<fds['initial_retained_descriptors']+2*fds['history_locked_views']+2*fds['auxiliary_unique_files']+128:raise ValueError('actual OS hard descriptor limit below source retained inventory')
    else:target=hard
    # Lift inherited shell soft1024 to the existing OS hard allowance; no
    # arbitrary new cap and no changes to retained owners/images or arithmetic.
    resource.setrlimit(resource.RLIMIT_NOFILE,(target,hard))
    args=[sys.executable,str(ROOT/'tools/ds_hbm_checkpoint_prefix_r37.py'),'--native','/tmp/kepler-ds-r34-provider-joined-sealed/native.json.gz','--dispatch','/tmp/kepler-ds-r34-provider-joined-sealed/dispatch.json.gz','--homes',str(D/'inputs/actual_DeepSeek_homes.json.gz'),'--manifest',str(D/'inputs/prefix_input_manifest.json.gz'),'--out',str(a.out)]
    receipt=a.out.with_suffix('.admission.json')
    if receipt.exists() or a.out.exists():raise ValueError('fresh corrected invocation identity')
    record=dict(status='ADMITTED_EXACT_SOURCE_INFRASTRUCTURE_CORRECTION',pid=os.getpid(),RLIMIT_NOFILE_before=[soft,hard],RLIMIT_NOFILE_after=list(resource.getrlimit(resource.RLIMIT_NOFILE)),descriptor_inventory=fds,source_prefix_sha256=hashlib.sha256((ROOT/'tools/ds_hbm_checkpoint_prefix_r37.py').read_bytes()).hexdigest(),journal_projection=projection,cpu_time_limit=list(resource.getrlimit(resource.RLIMIT_CPU)),address_space_limit=list(resource.getrlimit(resource.RLIMIT_AS)),file_size_limit=list(resource.getrlimit(resource.RLIMIT_FSIZE)),full_token_GO=False,hardware_qualified=False,argv=args)
    receipt.write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');os.execv(sys.executable,args)
if __name__=='__main__':main()
