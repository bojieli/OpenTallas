"""Independent closure replay from current canonical checkout bytes.
Historical Git is neither queried during staging nor permitted during execution.
"""
import argparse,contextlib,gzip,hashlib,importlib.util,json,sys,tempfile,time
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[4]
BASE=ROOT/'results/uarch/h3_complete_native_calendar_20261002'
HERE=Path(__file__).resolve().parent
ARCHIVE=HERE/'archive_r3'
spec=importlib.util.spec_from_file_location('calendar',ROOT/'tools/h3_complete_native_calendar.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
parser=argparse.ArgumentParser();parser.add_argument('--canonical-root',type=Path,default=ROOT)
args=parser.parse_args()
index=json.loads((ARCHIVE/'index.json').read_text())
report={'inputs':len(index['inputs']),'historical_Git_calls_during_calendar_execution':0,'historical_Git_calls_during_staging':0,'canonical_native_duplicated_in_commit':False,'runs':{}}
with tempfile.TemporaryDirectory(dir=HERE) as tmp:
    clean=Path(tmp)
    for row in index['inputs']:
        if row['storage']=='canonical_tracked_path':
            raw=(args.canonical_root/row['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==row['sha256']
            path=clean/row['path'];path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
        else:
            raw=gzip.decompress((ARCHIVE/'blobs'/(row['sha256']+'.gz')).read_bytes())
            assert hashlib.sha256(raw).hexdigest()==row['sha256']
    report['all_input_hashes_checked']=True
    commands={
      'provider_V1':['--provider-v1-join'],
      'r33':['--ds-r33-once-reprice','--r33-boundary-cycles',str(BASE/'ds_r33_once_reprice_r1/boundary_cycles.json')],
      'r34':['--ds-r34-group-reprice','--r33-cost-baseline',str(HERE/'r33_portable_r4')],
      'TP96':['--tp96-collective-inputs',str(BASE/'tp96_literal_collective_join_r1/inputs'),
        '--tp96-endpoint-cycles',str(BASE/'tp96_literal_collective_join_r1/endpoint_cycles.json')]
    }
    for name,args in commands.items():
        output=HERE/(name+'_portable_r4')
        started=time.monotonic()
        with patch.object(c,'ROOT',clean), patch.object(c.subprocess,'check_output',side_effect=AssertionError('historical Git lookup forbidden')), patch.object(c.subprocess,'run',side_effect=AssertionError('Git lookup forbidden')):
            for verify in ((True,) if output.exists() else (False,True)):
                argv=['calendar',*args,'--portable-inputs',str(ARCHIVE),'--out',str(output)]
                if verify:argv.append('--verify')
                with patch.object(sys,'argv',argv):c.main()
        report['runs'][name]={'generate_and_byteexact_replay_seconds':round(time.monotonic()-started,3),'outputs_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir()}}
    old=BASE/'provider_v1_mtp_join_r4/final_physical'
    for path in old.iterdir():
        if path.name!='manifest.json':assert path.read_bytes()==(HERE/'provider_V1_portable_r4'/path.name).read_bytes()
    report['provider_V1_six_model_records_byteidentical']=True
    old=BASE/'ds_r33_once_reprice_r1/model'
    for name in ('summary.json','once_reprice_receipt.json','all_PC_native_component_successor.json.gz','initial_LOAD_boundary_reservations.json.gz'):
        assert (old/name).read_bytes()==(HERE/'r33_portable_r4'/name).read_bytes()
    report['r33_all_four_model_records_byteidentical']=True
    old=BASE/'tp96_literal_collective_join_r1/final'
    for name in ('summary.json','full_PC_collective_component.json.gz'):
        assert (old/name).read_bytes()==(HERE/'TP96_portable_r4'/name).read_bytes()
    report['TP96_two_model_records_byteidentical']=True
    r34=json.loads((HERE/'r34_successor/summary.json').read_text())
    report['r34_scope']={k:v for k,v in r34.items() if k!='records'}
(HERE/'independent_no_git_replay_final.json').write_text(json.dumps(report,sort_keys=True,indent=2)+'\n')
print('PASS_FULL_CALENDAR_CLOSURE_WITH_HISTORICAL_GIT_FORBIDDEN')
