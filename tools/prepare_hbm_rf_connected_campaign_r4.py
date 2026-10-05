#!/usr/bin/env python3
"""Additive post-failure proposal. No old source/results edits, builds or launches."""
import hashlib,json,subprocess
from pathlib import Path
import prepare_hbm_rf_connected_gate as B
ROOT=B.ROOT
BASE='36dff032a0506456e9528dbb622b924ca4e1bb89'
OUT=ROOT/'results/uarch/hbm_rf_connected_campaign_r4_20261002'
PROPOSAL='prepared_gate.json'
RUNNER_CAPS=B.RUNNER_CAPS
blob=B.blob
NEW=['tools/run_hbm_rf_connected_campaign_r4.py','tools/prepare_hbm_rf_connected_campaign_r4.py','tools/test_hbm_rf_connected_campaign_r4.py']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prepare():
    prior=B.prepare()
    for path in prior['gate_tool_sha256']:
        if (ROOT/path).read_bytes()!=blob(BASE,path):raise ValueError('preserved tool source changed: '+path)
    for path in prior['source_sha256']:
        if (ROOT/path).read_bytes()!=blob(BASE,path):raise ValueError('preserved RTL source changed: '+path)
    for path in prior['review_pins']:
        if (ROOT/path).read_bytes()!=blob(BASE,path):raise ValueError('preserved model changed: '+path)
    failure_path='results/rtl/hbm_rf_connected_owner_terminal_r1_20261002/verdict.json'
    failure=json.loads((ROOT/failure_path).read_text())
    if (ROOT/failure_path).read_bytes()!=blob(BASE,failure_path):raise ValueError('preserved failed receipt changed')
    p=dict(prior)
    p['prepared_from_commit']=BASE
    p['gate_tool_sha256']={**prior['gate_tool_sha256'],**{f:sha(ROOT/f) for f in NEW}}
    p['runner']=dict(prior['runner'])
    p['runner']['path']=NEW[0]
    p['runner']['argv']=['<pinned-python>',NEW[0],'--proposal','results/uarch/hbm_rf_connected_campaign_r4_20261002/prepared_gate.json','--go','<committed-new-parent-GO.json>','--go-commit','<new-parent-GO-SHA>','--out','<fresh-output>']
    p['preserved_failure_pin']={'path':failure_path,'sha256':sha(ROOT/failure_path),'source_commit':failure['source_commit'],'GO_commit':failure['GO_commit']}
    p['independent_diagnosis']={'failing_source':'a207908e2b7a7872f608163ddeeb997cd40907ba:tools/run_hbm_rf_connected_gate.py:125','parse':"((out / 'progress-') + target) + '-' + name + '.json'",'exception_before_helper':True,'helper_accepts_Path_exclusive_create':True,'corrected_expression':"out / f'progress-{target}-{name}.json'",'prior_fix_commit':BASE,'additive_runner':'New entry point; every existing source/model/receipt retained byte-identical. No change to caps or actual RTL.'}
    p['resource_plan']={'scope':'Fresh parent review only; not admission. Hard caps are budgets, not completion predictions.','CPU_enforcement':'Parent taskset24-27; exact sched_getaffinity verification and observed child/thread masks. No CPU controller/quota assumption.','caps':RUNNER_CAPS,'phase_limits_s':{'DS':{'frontend':300,'CXX':600,'simulation':180,'trace':30},'Qwen':{'frontend':300,'CXX':600,'simulation':180,'trace':30}},'actual_DS_frontend_s':failure['phases'][0]['wall_s'],'remaining_DS_frontend_budget_s':300-failure['phases'][0]['wall_s'],'actual_frontend_output_report':'11383 C++ files /1704.698MB from Verilator report; output preserved. No CXX measurement.','memory_report':'Verilator allocated21264.930MB report; not final cgroup peak. Parent monitor retains final memory; owner samples lower-bound only.','CXX_time_and_memory_measured':False,'Qwen_frontend_time_and_memory_measured':False,'risks':'DS frontend has41.4s margin; CXX600s and nativeQwen300s/32GiB still unqualified. Any cap failure is terminal and preserved; no automatic tuning.','aggregate_output_enforcement':'8GiB sampled1s; transient overshoot possible. FSIZE hard1GiB/file. Disk headroom12GiB.','retained_generated_DS_CXX':'Read-only prior artifacts preserved. This recipe uses fresh output/cold frontend; any reuse needs separate reviewed hashes/source/compiler/argv/GO binding.','launches':0,'GO':False,'no_new_PVE2_PVE3_jobs':True}
    return p
if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True);p=OUT/PROPOSAL;data=(json.dumps(prepare(),indent=2,sort_keys=True)+'\n').encode()
    if p.exists():assert p.read_bytes()==data
    else:
        with p.open('xb')as f:f.write(data)
    print(p)
