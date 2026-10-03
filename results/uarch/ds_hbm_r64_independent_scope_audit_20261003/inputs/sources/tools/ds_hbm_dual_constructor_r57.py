"""Preflight-only R55 literal producer/cold constructors with R56 priced resources.
Numerical execution is held for separate parent review. No source substitutions,
helper monkeypatches, CPU/affinity/time/memory/file-size caps or arithmetic.
"""
import argparse,json,sys
from pathlib import Path
import ds_hbm_checkpointed_prefix_r55 as original
import ds_hbm_dual_resources_r56 as resources
import ds_hbm_registered_loader_r57 as enrollment
from ds_hbm_connected_prepare_r37 import sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--preflight-only',action='store_true',required=True);args=p.parse_args()
    plan=json.loads(args.plan.read_bytes())
    if plan.get('numerical_GO') is not False or plan.get('preflight_only') is not True:
        raise ValueError('explicit numerical hold and constructor-only scope required')
    pins=plan['source_sha256']
    for name in ('ds_hbm_dual_constructor_r57.py','ds_hbm_dual_resources_r56.py','ds_hbm_registered_loader_r57.py'):
        path=resources.ROOT/'tools'/name
        if sha(path)!=pins.get(str(path.relative_to(resources.ROOT))):raise ValueError('exact R56 source enrollment required')
    projection=json.loads((resources.ROOT/plan['storage_proof']['path']).read_bytes())
    interp=projection['RAM']['interpreter']
    if sys.implementation.name!=interp['implementation'] or sys.version!=interp['version']:
        raise ValueError('source-priced interpreter representation differs')
    raw=bytes(range(256))
    if any(raw[i] is not int(str(i)) for i in range(256)):
        raise ValueError('source-byte cache identity differs; RAM repricing required')
    enrollment.install()
    original.main()

if __name__=='__main__':main()
