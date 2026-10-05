"""Prepare a current-source model-qualified measurement preflight, with no launch."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
import w15_tp96_preflight as P
import w15_tp96_exact as C
import w15_tp96_measurement_admission as A

ROOT=Path(__file__).resolve().parents[1]

def prepare():
    r=P.preflight()  # Calls the actual current v41_hbm_n(96,4,...) unified model.
    paths=set(r['source_sha256'])|set(C.SOURCES)|{
        'tools/w15_tp96_exact.py','tools/w15_tp96_preflight.py',
        'tools/w15_tp96_measurement_preflight.py','tools/w15_tp96_measurement_admission.py',
        'results/rtl/w15_tp96_w19_prerequisites_input_20261001.json'}
    r['schema']='w15_tp96_measurement_preflight_v1'
    r['source_tree_base']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    r['source_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sorted(paths)}
    bounds={c['name']:c['composed_serial_cycles_upper_bound'] for c in r['cases']}
    r['measurement']=dict(bits=64,protocol_bits=16,effective_core_period_ps=1112,
                         max_round_cycles=max(bounds.values()),max_round_required_bits=max(bounds.values()).bit_length(),
                         campaign_sum_cycles=sum(bounds.values()),campaign_sum_required_bits=sum(bounds.values()).bit_length(),
                         nominal_timeout_cycles=7200000,timeout_required_bits=23,
                         overflow='fatal',integer_time='elapsed_ps = elapsed_cycles * 1112',
                         legacy_latency='pending_unqualified; never repaired by this preflight',
                         model_clock_basis='ideal0.9GHz serial; existing1ps simulation rounds bench period to1112ps. No physical constraint change.')
    r['negative_contract']=dict(required_rejecting_endpoints=96,operations=['order','tag'],
                               coverage='Exactly once per die0..95, op0,index0, plus matching NEG_DONE and nonzero expected fatal. Partial/duplicate/wrong-kind/timeout rejected.',
                               order='Swap both valid and records on existing switch ports1,2. Witness native1(0x3f800000) vs swapped2(0x40000000) binary32 on every lane; each endpoint checks actual arriving result.',
                               tag='Flip operation bit on leader0 before native CRC TX; expectedop1 arrives through existing switch multicast and partner forwarding at everyendpoint; payload still golden-exact.',
                               normal_default='BAD_ORDER=0 and BAD_TAG=0; no datapath, rounding or transport changes',
                               actual_RTL_negative_gate='pending_not_run')
    r['admission']='prepared_not_admitted'
    r['campaign_launched']=False
    r['admission_prerequisites']=['all equivalent local/remote jobs absent; allAGI newdispatch disabled',
                                 'legacy250 campaign terminal, independently validated and committed archive; failed functional gate blocks measurement-only retry',
                                 'clean new source pin and all current model/HDL/golden/runner hashes match this preflight',
                                 'new immutable output/build paths; parent coordination required for fleet resources']
    r['legacy_source_commit']=A.LEGACY_SOURCE
    r['fixture_scope']='Synthetic production-shaped FP32 collective operands, not checkpoint matvec or connected full96 SM runtime. W19 old prerequisites snapshot is retained audit input only; Euler owns accepted256B descriptors and actual producer/result composition.'
    r['hardware_change']='none; only testbench counters, negative checker coverage and admission prerequisites'
    return r

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    assert not a.out.exists(),'new immutable preflight output required'
    r=prepare();a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
    print('MEASUREMENT_PREFLIGHT_PREPARED_NOT_ADMITTED',r['ranks'],len(r['source_sha256']))
