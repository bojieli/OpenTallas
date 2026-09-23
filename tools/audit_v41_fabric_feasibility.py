#!/usr/bin/env python3
"""Static expert-local fabric service envelope, not a vendor link benchmark."""
import hashlib
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def payload(hidden=5120, selected=6, layers=40, output_bytes=2, multicast=False):
    if min(hidden, selected, layers, output_bytes) <= 0:
        raise ValueError('Positive geometry required')
    # Only source injection is saved by multicast. Fabric leaf delivery is not.
    dispatch = hidden * 2 * (1 if multicast else selected)
    returns = hidden * output_bytes * selected
    return {'source_dispatch_bytes_per_layer': dispatch,
            'merge_ingress_bytes_per_layer': returns,
            'endpoint_bytes_per_layer': dispatch + returns,
            'endpoint_bytes_per_token': (dispatch + returns) * layers,
            'leaf_delivered_bytes_per_layer': hidden * selected * (2 + output_bytes)}


def fabric_us(bytes_per_layer, layers, one_way_us, delivered_GB_s):
    if min(bytes_per_layer, layers, delivered_GB_s) <= 0 or one_way_us < 0:
        raise ValueError('Invalid service inputs')
    # Two non-overlapped transfers around expert compute per layer. Endpoint
    # serialization and fixed delivery delay are separate, with no contention.
    return layers * (2 * one_way_us + bytes_per_layer / (delivered_GB_s * 1000))


def main():
    names = ['compiler/models/deepseek-v4.1-flash/inference_config.json',
             'tools/audit_v41_fabric_feasibility.py']
    m = json.loads((ROOT/names[0]).read_text())
    h,e,l = m['dim'],m['n_activated_experts'],m['n_layers']
    cases = []
    for output_bytes, multicast in [(2,False),(2,True),(4,False)]:
        p = payload(h,e,l,output_bytes,multicast)
        cases.append({'return_bytes_per_element':output_bytes,'source_multicast':multicast,
                      'payload':p,
                      'sensitivity':[
                          {'delivered_endpoint_GB_s_per_direction':bw,
                           'one_way_fixed_delivery_us':lat,
                           'expert_fabric_us':fabric_us(p['endpoint_bytes_per_layer'],l,lat,bw),
                           'remaining_of_100us_for_all_other_work':100-fabric_us(p['endpoint_bytes_per_layer'],l,lat,bw)}
                          for bw in (100,400,900) for lat in (.1,.25,.5,1,2)]})
    p = payload(h,e,l)
    out = {'schema':'opentallas.v41-fabric-feasibility.v1',
           'status':'conditional_expert_fabric_screen_no_physical_rate_claim',
           'cases':cases,
           'unicast_bf16_average_endpoint_GB_s_at_100us':p['endpoint_bytes_per_token']/100/1000,
           'max_one_way_us_with_400GB_s_and_20us_expert_fabric_budget':(20/l-p['endpoint_bytes_per_layer']/400000)/2,
           'zero_serialization_fixed_latency_limit_us_for_100us':100/(2*l),
           'limits':[
               'Expert-local weights; no expert tensor sharding. Dispatch and return only, not full model communication.',
               'BF16 input and BF16 expert output candidate follow pinned Expert final Linear output; FP32 return sensitivity is separately priced. Route metadata, headers, acknowledgements, errors and padding are excluded.',
               'Vendor accumulates expert outputs in FP32 and performs distributed reduction. Proposed central ordered merge needs numerical qualification; no in-network reassociation is credited.',
               'BF16 expert dispatch is one collapsed hidden vector, not four hyper-connection residual streams. Cross-layer residual transport is separate.',
               'Rates are delivered payload per direction at source/merge, not summed bidirectional or switch bandwidth. Latencies are end-to-end fixed delivery, excluding separately priced serialization.',
               'No measured wafer or NVLink rates are assumed. Same equations apply to both, with different qualified parameters.',
               'No contention, retries, competing traffic or activation readiness delay. Communication is not overlapped with compute in this screen.',
               'Multicast saves source injection only; topology-dependent hop bytes, bisection, energy and expert leaf delivery still need accounting.',
               'Cases that exceed 100us reject this serial placement, not every possible architecture. Passing leaves all omitted work unproven.'],
           'input_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}}
    (ROOT/'results/architecture/v41_fabric_feasibility.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(p)
    for lat in (.1,.25,.5,1,2):
        print(lat, fabric_us(p['endpoint_bytes_per_layer'],l,lat,400))
    print('20us fixed-latency allowance:',out['max_one_way_us_with_400GB_s_and_20us_expert_fabric_budget'])


if __name__ == '__main__':
    main()
