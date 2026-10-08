#!/usr/bin/env python3
"""Half-rate fused-head contract sidecar; parent integrates this into uarch_model.

No standalone ctl-only adoption: fixed-cycle tag, hquad and retirement peers
must share logical ticks. Frame traffic is a qualification/integration contract,
not a ready signal retrofitted onto the legacy raw pins.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
CTL = 'rtl/hdc/v41/dspark_fused_head/quad/ot_hdc_v41_fh_ctl.sv'


def ports():
    env = dict(W=16, G=4, AW=24, NW=16)
    env['TW'] = 160
    out = {'input': [], 'output': []}
    for line in (ROOT / CTL).read_text().split(');', 1)[0].splitlines():
        m = re.search(r'\b(input|output)\s+wire\s+(?:\[([^:]+):0\]\s*)?(.+)', line.split('//')[0])
        if not m:
            continue
        width = eval(m[2], {'__builtins__': {}}, env) + 1 if m[2] else 1
        for name in m[3].split(','):
            name = name.strip()
            if name and name not in ('clk', 'rst_n'):
                out[m[1]].append(dict(name=name, width=width))
    return out


def model(head_cycles=14844, invocations=1):
    p = ports()
    iw, ow = [sum(x['width'] for x in p[d]) for d in ('input', 'output')]
    assert (iw, ow) == (464, 460), 'raw controller interface changed; requalify packing'
    return dict(schema='opentallas.fh_half.v1', status='MODEL_ONLY_NOT_ADOPTED',
        ctl_sha256=hashlib.sha256((ROOT / CTL).read_bytes()).hexdigest(), ports=p,
        root_period_ps=833, internal_min_period_ps=1666, setup_uncertainty_ps=60,
        hold_uncertainty_ps=25, replicas=1, macs_per_cycle=0, memory_ports=[],
        payload_storage_bits=2*(iw+ow), queue_depth_each=2,
        input_bits_per_frame=iw, output_bits_per_frame=ow,
        input_max_bytes_per_root_cycle=iw/16, output_max_bytes_per_root_cycle=ow/16,
        payload_muxes={'input':'one 2:1 selector per bit', 'output':'one 2:1 selector per bit'},
        clock_gate='one low-transparent latch plus AND; root phase flop; dynamic empty/full stops only remove edges',
        max_frames_per_root_cycle=0.5,
        trial_slot_um=[400,400], fit='UNMEASURED: synthesis area and routed context required',
        route_tracks={'input':iw,'output':ow,'assumed_signal_pitch_um':0.048,
                      'combined_corridor_um_one_layer':(iw+ow)*0.048,
                      'capacity':'analytical reservation only; actual hub-layer acceptance pending'},
        fanout='phase/gate control plus ctl clock sinks; clock CTS and boundary-enable fanout require measurement',
        latency={'head_baseline_root_cycles':head_cycles,
                 'whole_head_half_root_cycles':2*head_cycles,
                 'added_root_cycles':head_cycles*invocations,
                 'added_us':head_cycles*invocations*833/1e6,
                 'external_boundary':'accepted input -> execution next eligible root edge; capture updated outputs one root edge later; output consumed no earlier than following root edge; queueing/backpressure additional',
                 'whole_region':'multiply every fixed-latency peer delay by two in root cycles; preserve delay in logical ticks'},
        integration={'raw_pins_have_ready':False,
                     'requires':'co-gate ctl, hquad, endpoint and any fixed-latency feedback state, or prove equivalent cycle-coherent elastic adapters',
                     'frame':'one complete raw-input snapshot per logical tick, including idle ticks; never independently decimate pulse fields',
                     'backpressure':'producer holds valid and all 464 payload bits until accepted; receiver holds result_ready low to stop execution losslessly',
                     'feedback':'do not prequeue frames whose peer feedback depends on an uncompleted logical tick',
                     'adoption':'parent region integration and golden token tests mandatory; block scoreboard alone does not qualify full head'},
        timing={'generated_edges':[3,4,7], 'additional_multicycle':False,
                'crossings':'root-to-slow and slow-to-root timed at actual related edges; no false paths',
                'signoff':'propagated root/generated clocks at SS and FF; >=15ps setup/hold, DRC0, gate waveform and IO clock binding proofs'})


if __name__ == '__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    args.out.write_text(json.dumps(model(),indent=2)+'\n')
    print('FH_HALF_MODEL input=464 output=460 payload_flops=1848 head_added_cycles=14844')
