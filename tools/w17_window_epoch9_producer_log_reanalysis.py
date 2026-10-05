#!/usr/bin/env python3
"""Additive source-bound offline correction; never builds or reruns RTL."""
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import subprocess
import textwrap
import w17_window_epoch9_producer_prediction as model
import w17_window_epoch9_producer_run as runner

ROOT = Path(__file__).resolve().parents[1]
FAIL = ROOT / 'results/rtl/w17_window_epoch9_producer_single_run_20261002'
PRED = ROOT / runner.PRED
PREP = ROOT / 'results/rtl/w17_window_epoch9_producer_prepared_20261002/prepared.json'
ACT_ANCHOR = "s['actok'][bk]=act+t['RAS_PS']+t['RP_PS'];s['preok'][bk]=act+t['RAS_PS']"


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def source_contract(idx, prefetch, fixture):
    # Exact pins are checked separately. These controls explain the semantic binding.
    branch = idx[idx.index('if (b_open[p][bk] && b_row[p][bk] == row) begin', idx.index('function automatic longint schedule')):idx.index('// a column command is never earlier')]
    assert branch.count('st_act[p] = st_act[p] + 1;') == 1
    assert branch.index('end else begin') < branch.index('st_act[p] = st_act[p] + 1;')
    assert "WS_DONE: if (done_write) begin" in prefetch
    assert "if (bidx == 4'd15) row_valid[slot] <= 1'b1;" in prefetch
    assert 'always @(posedge clk) if(rst_n)' in fixture
    assert 'if(wwdone[2])begin' in fixture and 'acks=acks+1;last_ack=mem.cyc;' in fixture
    assert 'if(acks==32&&logical_publish<0)begin logical_publish=mem.cyc;' in fixture
    assert '#0.001;' in fixture and 'if(logical_publish>=0&&!win.u_window.row_valid[127])' in fixture


def corrected_schedule():
    # Add only the source-owned counter in the same bank-miss branch, after refresh.
    # Do not replace timing calculations, edge identities, dataflow or any old file.
    src = textwrap.dedent(inspect.getsource(model.WriteBackend.schedule))
    assert src.count(ACT_ANCHOR) == 1 and "s['acts']" not in src
    src = src.replace(ACT_ANCHOR, ACT_ANCHOR + ";s['acts']+=1")
    ns = {}
    exec(compile(src, '<source-bound ACT accounting overlay>', 'exec'), model.__dict__, ns)
    return ns['schedule']


def corrected_compare():
    src = inspect.getsource(runner.compare)
    old = 'actual=[list(map(int,x)) for x in re.findall(pattern,log)]'
    assert src.count(old) == 1
    src = src.replace(old, 'actual=[list(map(int,x.groups())) for x in re.finditer(pattern,log)]')
    ns = {}
    exec(compile(src, '<regex group tuple correction>', 'exec'), runner.__dict__, ns)
    return ns['compare']


def verify_provenance():
    pred = json.loads((PRED/'prediction.json').read_bytes())
    record = json.loads((FAIL/'record.json').read_bytes())
    assert digest(PRED/'prediction.json') == record['prediction_sha256']
    assert digest(PREP) == record['prepared_manifest_sha256']
    for p, h in json.loads((FAIL/'evidence_sha256.json').read_bytes()).items():
        assert digest(FAIL/p) == h
    assert record['verdict'] == 'FAIL_PRESERVED_NO_RETRY'
    for key in ('source_sha256', 'candidate_sha256', 'dependency_sha256', 'prepared_fixture_sha256'):
        for p, h in pred[key].items():
            assert digest(ROOT/p) == h
            if key == 'source_sha256':
                assert hashlib.sha256(subprocess.check_output(['git','show',model.PIN+':'+p],cwd=ROOT)).hexdigest() == h
    assert digest(ROOT/'tools/w17_window_epoch9_producer_prediction.py') == pred['generator_sha256']
    for item in record['results']:
        for k in ('compile','runtime'):
            assert item[k]['status'] == 0
            assert digest(FAIL/(item['case']+'_'+k+'.log')) == item[k]['log_sha256']
    prep = json.loads(PREP.read_bytes())
    snapshot = Path('/tmp/window-epoch9-producer-prepared-20261001-r1')
    for p, h in prep['snapshot_sha256'].items():
        assert digest(snapshot/p) == h
        assert digest(ROOT/prep['source_origins'][p]) == h
    idx = (ROOT/model.IDX).read_text()
    pf = (ROOT/'rtl/test/w17_window_epoch9_candidate/ot_chip_v41x_window_kv_prefetch.sv').read_text()
    tb = (ROOT/'rtl/test/w17_window_epoch9_producer/tb.sv').read_text()
    source_contract(idx, pf, tb)
    return pred, record


def reanalyse():
    pred, record = verify_provenance()
    compare = corrected_compare()
    prior_method = model.WriteBackend.schedule
    model.WriteBackend.schedule = corrected_schedule()
    result = {}
    try:
        for name in ('L0_no_retain','L0_retain','source_COUNT1_boundary'):
            old = pred['cases'][name]
            summary, events = model.replay(pred['params'], old['rows'], old['retain'])
            expected_events = [json.loads(x) for x in (PRED/(name+'_events.jsonl')).read_text().splitlines()]
            assert events == expected_events
            # Only ACT accounting may change. All old numerical timing is immutable.
            a = json.loads(json.dumps(summary)); b = json.loads(json.dumps(old))
            for obj in (a,b):
                for pc in obj['per_PC']: pc.pop('activations')
            assert a == b
            case = dict(events_identical=True, all_other_prediction_fields_identical=True,
                        per_PC=summary['per_PC'], corrected_ACT_sum=sum(x['activations'] for x in summary['per_PC']))
            if old['rows'] == 128:
                log = (FAIL/('retain'+str(old['retain'])+'_runtime.log')).read_text()
                checks = compare(log, summary, events)
                assert not checks['mismatches']
                # Controls use unchanged logs: next-edge publication and omitted ACT must fail.
                bad_edge = [dict(e, cycle=e['cycle']+1) if e['kind']=='logical_publish' else e for e in events]
                edge_m = compare(log,summary,bad_edge)['mismatches']
                act_m = compare(log,old,events)['mismatches']
                assert [x['kind'] for x in edge_m] == ['logical_publish']
                assert [x['kind'] for x in act_m] == ['per_PC']
                case.update(comparison=checks, controls={'next_edge_publication':edge_m,'omitted_ACT':act_m})
            else:
                case['scope'] = 'Model-only COUNT1 boundary; no RTL execution or runtime qualification.'
            result[name] = case
    finally:
        model.WriteBackend.schedule = prior_method
    return dict(schema='opentallas.window_epoch9.producer_retained_log_reanalysis.v1',
        verdict='PASS_OFFLINE_REANALYSIS_ALL_DECLARED_CHECKS', original_verdict=record['verdict'],
        original_failure_record_sha256=digest(FAIL/'record.json'), original_prediction_sha256=digest(PRED/'prediction.json'),
        correction_tool_sha256=digest(Path(__file__)), source_commit=model.PIN,
        source_sha256=pred['source_sha256'],candidate_sha256=pred['candidate_sha256'],
        prepared_fixture_sha256=pred['prepared_fixture_sha256'],dependency_sha256=pred['dependency_sha256'],
        original_generator_sha256=pred['generator_sha256'],cases=result,
        contract='Publication log uses pre-NBA cycle on final ack posedge; row_valid checked after NBA on same edge. ACT increment belongs to schedule bank miss after refresh; no timing/event changes.',
        scope='Retained runtime logs only. No build/run, source/old generator/old prediction change, adoption/admission claim, physical clock, fault recovery, QE arithmetic, payload checkpoint or full-token qualification.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    result=reanalyse()
    out=Path(a.out);out.mkdir(parents=True,exist_ok=False)
    (out/'record.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['verdict'])


if __name__ == '__main__': main()
