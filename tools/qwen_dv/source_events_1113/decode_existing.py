#!/usr/bin/env python3
"""Read existing controller evidence; never synthesize production epochs."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def native_observations(raw):
    latency = re.findall(r'TLOAD_CHECK side=\s*(\w+) loads=(\d+) bad=(\d+) latency=(\d+)',raw)
    if latency != [('flat','36','0','11'),('landed_np','36','0','11')]:
        raise ValueError('actual TLOAD observations changed; rebind native law')
    if 'TLOAD_PRODUCER PASS' not in raw or 'LP_LOCKSTEP PASS' not in raw:
        raise ValueError('native source proof failed')


def decode(root):
    native = root / 'native_fixture_source.sv'
    hb = root / 'hb_fixture_source.sv'
    source = native.read_text()
    # These are source-derived stimulus dates, not measured table output dates.
    required = ['PER = 6200', 'cyc == 16', 'warm >= 20 && warm < 1044',
                'warm >= 1044 && warm < 1052', 'warm >= 1300',
                'st_cyc[ntk] = cyc', 'tk_chk(1, lo_table_req, cyc - 6)',
                '.NU(4)', '.PRIVATE_CALR(1)', '.F16WTN(1)']
    if any(token not in source for token in required):
        raise ValueError('native fixture source changed: rederive dates')
    if '.NU(1)' not in hb.read_text() or '.init_u0(1\'b0)' not in hb.read_text():
        raise ValueError('HB disabled-feature profile changed')
    producer = json.loads((root / 'producer.json').read_text())
    if producer['loads_per_user'] != 36 or producer['verdict'] != 'PASS':
        raise ValueError('native finite producer changed')
    raw = (root/'native_compare_calr2.log').read_text()
    native_observations(raw)
    events = []
    for line in (root / 'log_m0_b0_TB_LANDED.txt').read_text().splitlines():
        m = re.match(r'^(\d+) (CSR|CMD|LOC|ISSUE|ROMRAW|ROM|NAT|XPF|STAGE|CF|END|LANDED_LOCKSTEP)\b\s*(.*)', line)
        if not m:
            raise ValueError('unknown existing log row ' + line)
        events.append(dict(observation_negedge_label=int(m[1]), kind=m[2], value=m[3]))
    stimulus = []
    for line in (root / 'ev_m0_b0_TB_LANDED.txt').read_text().splitlines():
        edge, kind, word = line.split()
        # TB loads ec when cyc+1==ec, on preceding negedge. The following
        # posedge is the input sample with cyc updated to ec by NBA.
        stimulus.append(dict(input_sampling_edge_label=int(edge), kind=int(kind), value_hex=word))
    return dict(schema='opentallas.qwen.existing_source_event_ledger.v1',
        status='FIXTURE_SOURCE_ONLY_PRODUCTION_JOIN_OPEN',
        source_sha256={p.name:digest(p) for p in (native,hb,root/'producer.json')},
        native_tload=dict(clock_period_ns=1, origin='initial clock=0; source loop negedge cyc index',
            reset_release_source_negedge=16, flat_reset_delay_edges=3,
            pw_install_source_negedges=[35,1058], dw_install_source_negedges=[1059,1066],
            stage_starts=[dict(stage=s,user=0,source_negedge=1315+6200*s) for s in range(38)],
            table_req_output_offset_landed_vs_flat=6,
            observed_output_latency=dict(flat=11,landed_normalized=11,landed=17),
            table_request_observation_negedges=[dict(stage=s,user=0,flat=1315+6200*s+11,
                landed=1315+6200*s+17) for s in range(1,37)],
            warning='raw CALRDIR_STATE cf=1; TLOAD/image and lockstep PASS do not prove fault-free controller',
            observed_fault_states=re.findall(r'CALRDIR_STATE warm=(\d+).*?cf=(\d+)',raw),
            observed_source_log_sha256=digest(root/'native_compare_calr2.log')),
        hb=dict(clock_origin='post-reset cyc counter; inputs applied previous negedge; observations at negedge cyc',
            profile=dict(NU=1,OPSEG=False,CTX=False,INIT=False,CALR=False,F16=False),
            production_ROOT_X_HEAD37_dates_qualified=False, observations=events, stimulus=stimulus),
        production_gaps=['selected current programme/image identity', 'ROOT write/commit publication',
                         'X/HEAD lease end and provider lifetimes', 'global clock/reset/START origin'])


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('evidence',type=Path);p.add_argument('output',type=Path)
    a=p.parse_args();a.output.write_text(json.dumps(decode(a.evidence),indent=2)+'\n')
