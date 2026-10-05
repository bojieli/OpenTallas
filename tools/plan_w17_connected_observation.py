"""Source-bound successor manifest only. No command in this tool is executed."""
import copy,json,hashlib
from pathlib import Path
import prepare_w17_connected_observation_driver as host
PRIOR='results/rtl/observer_explicit_widths_4e383_20261002/plan.json'

def digest(data):return hashlib.sha256(data).hexdigest()
def build_plan(repo):
    repo=Path(repo);pbytes=(repo/PRIOR).read_bytes();prior=json.loads(pbytes)
    before=(repo/host.BASE).read_text();after,changes=host.transform(before)
    if after!=(repo/host.COPY).read_text() or host.inverse(after,changes)!=before:raise ValueError('host derivative source mismatch')
    source_pins={}
    for mode in prior['modes']:source_pins.update(mode['source_sha256'])
    files=[host.BASE,host.COPY,host.HEADER,'tools/runtime/w17_future_driver_validation.hpp','tools/prepare_w17_connected_observation_driver.py','tools/plan_w17_connected_observation.py','tools/w17_connected_observation_model.py','tools/check_w17_connected_observation_trace.py','tools/w17_connected_token_contract.py']
    source_pins.update({f:digest((repo/f).read_bytes()) for f in files})
    modes=[]
    for mode in prior['modes']:
        ranks=[]
        for rank in range(4):
            args=[]
            for token in mode['argv']:
                if token=='--lint-only':args.append('--cc')
                elif token=='-GRANK=0':args.append('-GRANK='+str(rank))
                else:args.append(token)
            # Fresh future generated classes, never an existing binary/getter.
            args[1:1]=['--prefix','Vdie'+str(rank),'--Mdir','FRESH_MODE_BUILD/die'+str(rank)]
            ranks.append(dict(rank=rank,frontend_argv_template=args,CXX_argv_template=['make','-C','FRESH_MODE_BUILD/die'+str(rank),'-f','Vdie'+str(rank)+'.mk','-j2','Vdie'+str(rank)+'__ALL.a','OPT_FAST=-O2','OPT_SLOW=-O1','OPT_GLOBAL=-O1']))
        modes.append(dict(name=mode['name'],parent_ownership=mode['closure']['ownership'],parameters=mode['parameters'],source_sha256=mode['source_sha256'],future_rank_commands=ranks,host_defines=['W17_FULLTOKEN_OBSERVATION_OPT_IN=1','W17_FUTURE_DRIVER_VALIDATION_OPT_IN=1','W17_FUTURE_BIND_DBG_FS=1','ROM_PHW=6','CL_PW_BITS=547']+(['V41_L20'] if mode['name']=='CKV_source_available' else [])))
    return dict(source_commit=host.SOURCE,base_full_hierarchy_plan_path=PRIOR,base_plan_sha256=digest(pbytes),source_sha256=source_pins,modes=modes,host_copy=host.COPY,source_metadata_only=True,commands_executed=False,launch_allowed=False,blockers=['Fresh independent successor compile/link/run GO not provided.','Source owner/provider retirement and quiescence acknowledgements still unbound.','Exact reused4e FAST1/PP1/CUT379/LAT8 field and attention artifact identity manifests not selected.','Connected all40+norm/head persistent stage transport and physical mapping unbound.','Future native host compile, full group runtime footprint and causal service bounds unavailable.'],runtime_command_template=['FRESH_SUCCESSOR_BINARY','REVIEWED_IMAGE_ROOT','FRESH_OUTPUT_DIR','REVIEWED_MAXC'],environment_template=dict(W17_OBSERVATION_TRACE='FRESH_EXCLUSIVE_TRACE_PATH',RT_THREADS='2',RT_SKIP='0'),existing_driver_defaults_unchanged=True,causal_deadlines='BOUND_MISSING',scope='Executable-source preparation for real current TP4 group capture. Does not supply missing fulltoken engine/stage connections or authorize commands.')

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser();ap.add_argument('--repo',default='.');ap.add_argument('--output',required=True);a=ap.parse_args()
    p=build_plan(a.repo)
    with Path(a.output).open('x') as f:f.write(json.dumps(p,indent=2)+'\n')
