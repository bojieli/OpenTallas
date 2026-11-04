"""Expose ordered SOURCE0 refill work without converting a verify trace into an AR rate.

The full ordered count is staged source work; only the canary is measured.
An aggregate SOURCE0 bandwidth must be supplied explicitly to price a bandwidth
floor. A per-SM model bandwidth is not silently treated as a per-stack rate.
"""
import argparse
import hashlib
import json
import math
import re
from pathlib import Path


def refill_cost(spec, canary, log, baseline_reads, read_bytes, aggregate_bytes_per_edge=None):
    for s in (spec, canary):
        if not (s['source_stack'] == 0 and s['original_source_order'] and
                s['BODY_barriers_encoded'] and not s['source_aliases'] and
                not s['production_target_allocation']):
            raise ValueError('exact ordered SOURCE0 component scope required')
    if spec['clock_ps'] != 833 or canary['clock_ps'] != 833:
        raise ValueError('833ps source profile required')
    if read_bytes != 32 or baseline_reads <= 0:
        raise ValueError('native256-bit PC column-read contract and positive historical count required')
    match = re.search(r'HBM_MODEL stack0 reads=(\d+) writes=(\d+).*first_cmd=(\d+) last_cmd=(\d+)', log)
    if match is None or int(match[2]) != 0:
        raise ValueError('native read-only canary counter required')
    observed = int(match[1])
    # The owned window fills all32PCs x32 column words. This is accepted
    # column-read work, not the READ29 latency multiplied by every read.
    reads_per_epoch = 32 * 32
    if observed != canary['windows'] * reads_per_epoch:
        raise ValueError('native canary does not corroborate the epoch read count')
    candidate_reads = spec['windows'] * reads_per_epoch
    result = dict(
        qualification='STAGED ordered-source count + MEASURED canary; no full ordered execution, resident arithmetic or token/rate qualification',
        scope='SOURCE_STACK0 of selected N6MTP_VERIFY programme; not one AR token or one layer',
        clock_ps=833, read_bytes=read_bytes, reads_per_ownership_epoch=reads_per_epoch,
        candidate=dict(ownership_epochs=spec['windows'], runs=spec['descriptors'],
                       accepted_PC_reads=candidate_reads, HBM_payload_bytes=candidate_reads*read_bytes,
                       delivered_VM_words=spec['words'], delivered_VM_bytes=spec['words']*4,
                       source_sha256=spec['source_sha256']),
        historical_grouped=dict(accepted_PC_reads=baseline_reads, HBM_payload_bytes=baseline_reads*read_bytes,
                                scope='different grouped programme; not an arithmetic-order equivalence baseline'),
        canary=dict(ownership_epochs=canary['windows'], accepted_PC_reads=observed,
                    HBM_payload_bytes=observed*read_bytes, first_cmd_edge=int(match[3]),last_cmd_edge=int(match[4]),
                    source_sha256=canary['source_sha256']),
        additional_PC_reads=candidate_reads-baseline_reads,
        additional_HBM_payload_bytes=(candidate_reads-baseline_reads)*read_bytes,
        read_work_ratio=candidate_reads/baseline_reads,
        bandwidth_floor_edges=None, incremental_bandwidth_work_edges=None,
        aggregate_SOURCE0_bytes_per_edge=aggregate_bytes_per_edge,
        exposed_global_cycles=None, accepted_token_rate=None,
        remaining=['map N6 verify trace to actual model workload',
                   'qualify aggregate SOURCE0 bandwidth (per-SM45.03 is not automatically this rate)',
                   'price actual ownership/drain/configuration and resident arithmetic dependencies',
                   '192 indexed loads are outside this static-source receipt',
                   'actual physical/global publication and overlap schedule'])
    if aggregate_bytes_per_edge is not None:
        if not math.isfinite(aggregate_bytes_per_edge) or aggregate_bytes_per_edge <= 0:
            raise ValueError('positive finite aggregate SOURCE0 bandwidth required')
        result['bandwidth_floor_edges'] = math.ceil(candidate_reads*read_bytes/aggregate_bytes_per_edge)
        result['incremental_bandwidth_work_edges'] = math.ceil((candidate_reads-baseline_reads)*read_bytes/aggregate_bytes_per_edge)
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--spec',type=Path,required=True);p.add_argument('--canary-spec',type=Path,required=True)
    p.add_argument('--canary-log',type=Path,required=True);p.add_argument('--historical-grouped-reads',type=int,required=True)
    p.add_argument('--read-bytes',type=int,required=True);p.add_argument('--aggregate-source0-bytes-per-edge',type=float)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    result=refill_cost(json.loads(a.spec.read_text()),json.loads(a.canary_spec.read_text()),a.canary_log.read_text(),
                       a.historical_grouped_reads,a.read_bytes,a.aggregate_source0_bytes_per_edge)
    result['inputs_sha256']={str(x):hashlib.sha256(x.read_bytes()).hexdigest() for x in (a.spec,a.canary_spec,a.canary_log)}
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n')
    print('SOURCE0_REFILL_WORK',result['candidate']['HBM_payload_bytes'],'bytes; global cycles/rate OPEN')


if __name__=='__main__':main()
