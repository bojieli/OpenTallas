"""Nine actual matched layer observations; no extrapolated headline rates."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE='results/uarch/qwen_real_memory_measured_contexts_20261003/'
HELPER=BASE+'inputs/matched_pair_helper.py'
INPUT='results/rtl/qwen_rom_real_memory_20261003/frozen_v2/runs/'
OUT=BASE+'model.json'


def load_helper(root=ROOT):
    p=root/HELPER
    if hashlib.sha256(p.read_bytes()).hexdigest()!='01d93d7f683b2924c32876a2b0c22e538ba6df68388e3780295c596b9ff6a843':
        raise ValueError('immutable matched-pair verifier changed')
    spec=importlib.util.spec_from_file_location('_frozen_matched_pair',p)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    return m


def build(root=ROOT):
    helper=load_helper(root); rows=[]; pairs=[]; pins={}; source=None;binary=None
    for pos in (0,255,1023):
        runs=[]
        for mode in ('ideal','real'):
            name=INPUT+f'{mode}2_p{pos}.json';data=(root/name).read_bytes()
            pins[name]=hashlib.sha256(data).hexdigest();runs.append(json.loads(data))
        ideal,real=runs
        rows.extend(helper.matched_pair(ideal,real,pos))
        if source is not None and (source!=ideal['source_sha256'] or binary!=ideal['binary_sha256']):
            raise ValueError('positions do not share source and binary authority')
        source=ideal['source_sha256'];binary=ideal['binary_sha256']
        sums=[sum(r['stages'][k]['cycles'] for k in ('L0','L1','L2')) for r in runs]
        pairs.append(dict(position=pos,matched_identity={k:ideal[k] for k in helper.MATCH},
            actual_service=real['memory_services'],ideal_layer_sum_cycles=sums[0],
            real_layer_sum_cycles=sums[1],observed_layer_sum_extra_cycles=sums[1]-sums[0]))
    for name in [HELPER,'tools/qwen_real_memory_measured_contexts.py']:
        pins[name]=hashlib.sha256((root/name).read_bytes()).hexdigest()
    return dict(schema='opentallas.qwen.actual-real-memory-contexts.v1',
        status='MEASURED_FUNCTIONAL_NINE_LAYER_OBSERVATIONS_ONLY',rows=rows,pairs=pairs,
        verifier_source_commit='b4c331a72eb98d100afdadb31d1a395898e14ff3',
        low_observed_overhead_percent=min(r['overhead_percent'] for r in rows),
        high_observed_overhead_percent=max(r['overhead_percent'] for r in rows),
        adopted=False,physical_clock_qualified=False,full_token_latency_us=None,
        published_token_rate=None,posted_write_gain=None,
        composition_rule='use only same source, layer, position, home/service geometry; never add overlapping counters or delivery already priced in a calendar',
        historical_records_modified=False,
        scope='P0/P255/P1023 L0..L2, four-die exact outputs and real KV writeback; no36-layer,8K or physical extrapolation',
        input_sha256=pins)


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--verify',action='store_true')
    args=ap.parse_args();payload=json.dumps(build(),indent=2,sort_keys=True)+'\n';p=ROOT/OUT
    if args.verify:
        if p.read_text()!=payload:raise ValueError('record drift')
    else:p.parent.mkdir(parents=True,exist_ok=True);p.write_text(payload)
    print('PASS nine measured layers; no full-token or physical headline')
