#!/usr/bin/env python3
"""Read-only bb65 audit. No model edits, rate recalculation, or hardware admission."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import subprocess
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tools'))
import uarch_model_qwen_rom_calibrated_calendar as C
import arch_budget_qwen3 as Q
import hdc_timing as T

def sha(p):
    return hashlib.sha256((ROOT / p).read_bytes()).hexdigest()

def build():
    records = {n: json.loads((C.OUT / n).read_text()) for n in C.RECORDS}
    baseline, stream, near = (records[n] for n in C.RECORDS[:3])
    inputs, l0, _, _, _, nh, _ = C.load_inputs()
    assert C.check_production_pins() == 57
    source_pins = dict(baseline['pins']['repo_sources_sha256'])
    source_pins.update(baseline['pins']['review_inputs_sha256'])
    old = json.loads((ROOT / 'results/uarch/qwen_rom_kv_credit_allocator_20261002/model-r4.json').read_text())
    for p, h in old['source_sha256'].items():
        assert p not in source_pins or source_pins[p] == h
        source_pins[p] = h
    for p in ('tools/arch_budget_qwen3.py', 'tools/hdc_timing.py',
              'rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv',
              'tests/test_qwen_rom_calibrated_calendar.py',
              'results/uarch/qwen_rom_calibrated_calendar_20261003/REPLAY.md',
              'results/uarch/qwen_rom_calibrated_calendar_20261003/PROPOSED_DOC_CHANGES.md'):
        source_pins.setdefault(p, sha(p))
    for n in C.RECORDS:
        p = str((C.OUT / n).relative_to(ROOT)); source_pins[p] = sha(p)
    for p, h in source_pins.items():
        assert sha(p) == h, p
    trace_spec = 'a17a3c79:results/rtl/qwen_rom_w12_runtime/layer0_tp4_g6144_sw64_itrace.txt'
    trace = subprocess.check_output(['git','show',trace_spec], cwd=ROOT)
    assert b'ITR cyc=14 fetch=0' in trace and b'ITR cyc=445 fetch=11' in trace
    manifest = json.loads((ROOT / 'results/rtl/qwen_rom_TP4_terminal_20261002/terminal_manifest.json').read_text())
    assert manifest['current_source_joined'] is False
    trace_inventory = dict(git_object=trace_spec, sha256=hashlib.sha256(trace).hexdigest(),
        byte_count=len(trace), observed_fetch0=14, observed_fetch11=445,
        cited_span_cycles=445-14, accepted_KV_write_visibility_export=False,
        retained_terminal_current_source_joined=False,
        remaining_terminal_gates=manifest['remaining_gates'])
    prefix = {}
    nhd, kv = C.U.QWEN_TP_SHAPE[4]
    shape = dict(Q.Q, NH=nhd, KV=kv, FF=-(-Q.Q['FF']//4), V=-(-Q.Q['V']//4))
    for extra in (55,112,167):
        saved = dict(T.K)
        try:
            T.K['me_lat'] = saved['me_lat'] + extra
            layer = Q.as_built(8192, groups=6144, su_width=64, shape=shape, ucie=False)['layer_chain']
            prefix[str(extra)] = layer['stages'][0]
        finally:
            T.K.clear(); T.K.update(saved)
    assert [prefix[str(x)]['cycles'] for x in (55,112,167)] == [451,508,563]
    comp = C.measured_compute(l0, nh)
    assert (comp['prefix_cycles'], comp['measured']['layer_L1_L35'], comp['attention_8k_delta_cycles']) == (451,4668,1220)
    assert near['composition']['body_cycles'] == 2599
    assert near['composition']['body_position_independent_assumed'] is True
    assert near['admission']['selected_for_build'] is True
    assert near['admission']['adoption'] is False
    rtl = (ROOT / 'rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv').read_text()
    assert 'else if(n==0&&!(qv&&qr)&&cyc>=next_ref)' in rtl
    assert 'if(cyc>=next_ref)begin refresh_only<=1;refresh_resume<=1;state<=SCHEDULE;end' in rtl
    cal = (ROOT / 'tools/uarch_model_qwen_rom_calibrated_calendar.py').read_text()
    assert 'while now >= s[\'nextref\']' in cal or "while now>=s['nextref']" in cal
    findings = [
      dict(id='F1_PREFIX_CALIBRATION_JOIN', severity='claim_blocker',
           evidence=['tools/uarch_model_qwen_rom_calibrated_calendar.py:PREFIX_CYCLES/measured_compute',
                     'tools/uarch_model_qwen_kv_credit17.py:composed calendar',
                     'tools/arch_budget_qwen3.py:as_built/layer_chain',
                     'inputs/l0cal/l0_reconciliation.json'],
           finding='451 is reproduced by the old helper at ME extra 55. Full 167 gives 563; 112 gives 508. The cited trace QKV span is 431. None alone proves current K/V accepted-write visibility. The retained terminal explicitly has current_source_joined=false and lists the +55/source-current bridge as a remaining gate. bb65 retains 4668 measured cycles and subtracts 451 to partition that total; 167 is applied to the unmeasured 8K-minus-pos0 delta only.',
           required='Join the actual instruction/producer acceptance and visibility journal to the measured arithmetic configuration and prefix. Keep 4668 as its original measured basis; do not silently represent it as full-167 measured compute or substitute 563 without the dependency join.'),
      dict(id='F2_POSITION_TRANSFER', severity='claim_blocker',
           evidence=['inputs/l0cal/l0_reconciliation.json', 'near-hbm-selected-r1.json:composition/sensitivities', 'baseline-r1.json:identity/headline'],
           finding='2599 = 4668 - 87 - 1982 is assumed position independent. 87 is a trace span, not proof of all replaceable attention dependencies. The alternative modeled ctx1 share is 522; the +1220 long-context delta and single-segment AR 620/490 are unmeasured. Baseline uses ctx8191 cold service with pos0 compute, not an observed ctx8191 production token.',
           required='Retain calibration/body-transfer labels and source inventory; establish the same-program long-context compute, address availability and dependency boundary before a calibrated rate claim.'),
      dict(id='F3_REFRESH_SOURCE_EQUIVALENCE', severity='claim_blocker',
           evidence=['rtl/model_ready_hbm_r14/ot_hbm_r14_pc.sv:IDLE/RESERVE/SCHEDULE', 'tools/uarch_model_qwen_rom_calibrated_calendar.py:StrictREFab/refresh_debt', 'baseline-r1.json:calendar'],
           finding='RTL checks due refresh in IDLE and RESERVE, not IDLE alone. Accepted queue scans, held scheduling, command readiness and timing can delay it. StrictREFab is invoked on column calls and schedules from due; it is a conditional replacement calendar, not demonstrated source-state equivalence. Baseline records lateness 102/106 service edges; end-of-token due refresh is counted but not charged. Outstanding-return timing is not proven by this replacement.',
           required='Correct literal due-edge/IDLE-only claims in the owning successor; bind controller arbitration and outstanding-return safety, plus carried refresh debt in a continued-token finite calendar before sustainable service qualification.'),
      dict(id='F4_NEAR_HBM_COMPARABILITY', severity='claim_blocker',
           evidence=['near-hbm-selected-r1.json:identity_notes/unqualified_inputs/area', 'summary-r1.json:comparisons'],
           finding='The 20-field comparison explicitly declares calibration and service changes; this is not a common-service qualification. Near-HBM removes global fill but assumes 0.9 TB/s/stack against the documented LEN1/II5 204.8 GB/s/stack ceiling. New striping, owner writes, strict refresh and mutable protection are not fully priced or source joined; 13.85-15.81 mm2 versus 19.67 mm2 is not complete slot/route/clock admission.',
           required='Keep 5237 as an analytical candidate assumption only. Require finite controller accepts/bursts, PHY, write/read contention, refresh, protection, source-owned layout and composed physical slot/clock before comparison or hardware admission.'),
      dict(id='F5_SELECTION_AUTHORITY', severity='scope_blocker',
           evidence=['near-hbm-selected-r1.json:status/admission', 'REPLAY.md', 'PROPOSED_DOC_CHANGES.md'],
           finding='selected_for_build=True and SELECTED FOR BUILD are peer proposal labels. Existing model_only=True/new_RTL=False/new_PnR=False/adoption=False do not supply root selection or full G0. Proposed current-rate wording must not be promoted to adopted or measured product headlines.',
           required='Parent intake must interpret this as proposal-only, not session adoption or permission to launch. Preserve the rejected streaming record and all calibration evidence; no hardware until composed gates.')]
    return dict(schema='qwen-calibrated-calendar-independent-review.v1',
       candidate_commit='bb65ae0dcfa7a33a98781e46b547e29f18597f24',
       verdict='REPRODUCIBILITY_SEPARATE_FROM_ADMISSION_CALIBRATION_AND_SERVICE_JOINS_OPEN',
       scope='Read-only candidate audit; no main/docs/tools/model/RTL changes; no policy sweep.',
       admission=dict(root_adoption=False, hardware_permission=False, candidate_selection='peer_proposal_only'),
       pin_counts=dict(review_inputs=15, repository_pins=11, production_pins=57, unique_review_sources=len(source_pins)),
       source_sha256=dict(sorted(source_pins.items())), raw_trace_inventory=trace_inventory, prefix_helper=prefix,
       preserved_compute=comp, findings=findings,
       rejected_streaming_preserved=dict(status=stream['status'], rejection=stream['rejection']),
       baseline_refresh={k:{n:v for n,v in row.items() if 'refresh' in n or 'REFab' in n} for k,row in baseline['calendar'].items()})

def main():
    p=argparse.ArgumentParser(); p.add_argument('--write', action='store_true'); args=p.parse_args()
    text=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    dest=HERE/'findings-r2.json'
    if args.write:
        with dest.open('x') as f:f.write(text)
        print('WROTE findings-r2.json')
    else:
        assert dest.read_text()==text, 'review receipt mismatch'
        print('IDENTICAL findings-r2.json; source pins and prefix helper PASS')
if __name__=='__main__':main()
