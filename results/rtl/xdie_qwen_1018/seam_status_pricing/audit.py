#!/usr/bin/env python3
"""Source-pinned DIAG max-barrier overlay. Does not modify production composition."""
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE / 'baseline23314a50c'
ROOT = HERE.parents[3]
PROOF = HERE.parent / 'seam_boot_fix/proof1'

def load(rel):
    return json.loads((BASE / rel).read_text())

def measured(log):
    line = re.search(r'^\s*XQ_E (.*)$', log, re.M).group(1)
    return {k: int(v) for k, v in re.findall(r'(\w+)=(-?\d+)', line)}

inp = load('results/token_pass/measured_qwen_1019/inputs.json')
cycles = load('results/token_pass/measured_qwen_1019/cycles.json')['result']
ledger = load('results/token_pass/measured_qwen_1019/sched/ledger.json')
old = measured((BASE / 'results/token_pass/measured_qwen_1019/link/d2d_1u/pair_img_SUMMARY.txt').read_text())
now = measured((PROOF / 'cur_pair/run.log').read_text())
stages = cycles['1u']['layer']['stages']
ret = next(s for s in stages if s['stage'].startswith('attention return:'))
assert ret['cycles'] == 98
old_r31 = old['roundtrip_cmd_issue_to_r31_land']
new_r31 = now['roundtrip_cmd_issue_to_r31_land']
old_first, new_first = old_r31 - 31, new_r31 - 31
old_done = old_r31 + old['compute_done_after_r31_land']
new_done = new_r31 + now['compute_done_after_r31_land']
old_att, new_att = old_first + 16, new_first + 16
assert old_att == inp['attention']['round_trip_plan_cycles'] == 1825
old_ret_end, new_ret_end = old_att + ret['cycles'], new_att + ret['cycles']
old_gate, new_gate = max(old_ret_end, old_done), max(new_ret_end, new_done)
data_delta = new_ret_end - old_ret_end
extra_wait = new_gate - new_ret_end
assert old_gate == old_ret_end  # baseline completion already hidden under return
per_layer = new_gate - old_gate
assert (data_delta, extra_wait, per_layer) == (2, 136, 138)
native_ret = [e for e in ledger['die_edges'] if 'native_ret input' in e['label']]
assert len(native_ret) == 1 and native_ret[0]['cycles'] == 6 and native_ret[0]['cycles_asbuilt'] == 0
result = dict(
    schema='opentallas.qwen.seam-status-pricing-diag.v1', grade='DIAG', adopted=False,
    baseline_commit='23314a50c18e3fc0d01b3309dd96eca9f27bde2e', proof_commit='880c8c651',
    scope='conditional 1u serial native-completion barrier overlay; no full-token RTL or release qualification',
    clock_ps=833, raw_status_tail=213,
    old=dict(cmd_to_first_result=old_first, cmd_to_last_result=old_r31, cmd_to_completion=old_done,
             composer_attention=old_att, attention_return=ret['cycles'], data_return_end=old_ret_end,
             release_gate=old_gate),
    current=dict(cmd_to_first_result=new_first, cmd_to_last_result=new_r31, cmd_to_completion=new_done,
                 composer_attention_equivalent=new_att, attention_return_unchanged_diag=ret['cycles'],
                 data_return_end=new_ret_end, completion_gate=new_gate),
    delta=dict(data= data_delta, completion_wait_after_data_return=extra_wait, per_layer=per_layer,
               layers=36, per_token=36 * per_layer),
    native_ret='Existing +6 successor / +0 asbuilt pre_o ledger term retained once; not added again.',
    status20='No explicit 20-cycle STATUS serial charge exists in exact23314 inputs/composer/ledger; no subtraction invented.',
    assumptions=['The existing composer CMD anchor and 98-cycle return span remain the DIAG baseline.',
                 'Dependent o_proj waits for both returned operands and native completion.',
                 'Existing dependency gap and die edge charges apply after this max gate unchanged.',
                 'No next-layer/4u OVL credit: current bound master/sysface overlap is unproven.'],
    holds=['Both die DCALs must adopt matched r17 codec2/TX_SHIFT1/STATUS_DELAY213 law.',
           'Bound-image/compute-codec1 cases remain failing causal negatives.',
           'KV K22 natural13>image9 geometry is unresolved.',
           '98-cycle return span and complete token remain DIAG; new complete schedule must be qualified.'],
    variants={})
for key in ['1u', 'variant_asbuilt']:
    b=cycles[key]['cycles_per_token']
    c=b + 36*per_layer
    result['variants'][key]=dict(baseline_token_cycles=b, conditional_token_cycles=c,
                                conditional_tok_s=round(1e12/833/c,1),
                                rate_delta_pct=round(100*(b/c-1),3))
result['sources']={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in BASE.rglob('*') if p.is_file()}
result['proof_log_sha256']=hashlib.sha256((PROOF/'cur_pair/run.log').read_bytes()).hexdigest()
(HERE/'record.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(delta=result['delta'],variants=result['variants'])))
