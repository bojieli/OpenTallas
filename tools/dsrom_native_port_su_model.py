#!/usr/bin/env python3
"""Emit ONE bounded model-only S81 HC-pre pair; never execute inference or RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    record = U.dsrom_s81_native_port_hc_pair()
    paths = ('tools/uarch_model.py', 'tools/dshbm_baseline_measure.py',
             'tools/dsrom_1m_su.py', 'tools/dsrom_s81_fulldie.py',
             'rtl/hdc/v41x/ot_hdc_v41x_vec.sv', 'rtl/hdc/v41x/ot_hdc_v41x_vec_lane.sv')
    record['source_sha256'] = {p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}
    # Conservation checks: identical ingress/egress payload; exactly T1's
    # write/read removed. Fixed transport and coefficient costs stay charged.
    c = record['calendar']
    assert sum(c['face_only_baseline_beats'])-sum(c['face_only_candidate_beats']) == 320
    assert c['removed_vm_bytes'] == 40960
    assert record['ports']['new_global_port_bits'] == 0
    assert c['baseline_cycles']-c['candidate_cycles'] == c['same_port_model_saving_cycles']
    assert record['storage']['new_ff_bits'] == 327989
    assert c['current_fused_DAG_incremental_gain_us'] is None
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps({'status':record['status'], 'calendar':c, 'area':record['area']}, indent=2))

if __name__ == '__main__':
    main()
