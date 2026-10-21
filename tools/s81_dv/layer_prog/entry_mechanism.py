#!/usr/bin/env python3
"""Compose the entry_boot.py mechanism receipt from terminal entry-port runs.

Inputs are the immutable gate results of the actual RSTOPT/XRT/DL4/VP entry
cuts: the W cut (gate.py, port ri_w, key measured_local_contract) and the E/VI
cut (gate_ports.py, key by_input_port).  Each port is PASS only when its own
positive passed and its own payload mutant failed.  Ages are the measured
maxima (last HLOAD/GAIN write), never copied between ports.  Source hashes of
all runs must agree on every common file.
"""
import argparse
import hashlib
import json
from pathlib import Path

KEYS = (('target5_pin_to_store_commit_edges', 'target5_pin_to_store_commit_edges'),
        ('hload_pin_to_last_hw_edges', 'hload_pin_to_hw_edges'),
        ('gain_pin_to_last_wl_edges', 'gain_pin_to_wl_edges'))


def port_entry(contract, positive, negative):
    ok = bool(positive.get('passed')) and positive.get('exit_code') == 0 \
        and bool(negative.get('passed')) and negative.get('exit_code') not in (0, None)
    out = dict(status='PASS' if ok else 'FAIL')
    for key, src in KEYS:
        vals = contract.get(src)
        if not isinstance(vals, list) or not vals or not all(type(v) is int and v >= 0 for v in vals):
            out['status'] = 'FAIL'
            continue
        out[key] = max(vals)
    for k in ('sid', 'leaf', 'source_pin', 'clock_scope'):
        if k in contract:
            out[k] = contract[k]
    return out


def compose(w_path, ev_path):
    w = json.loads(Path(w_path).read_text())
    ev = json.loads(Path(ev_path).read_text())
    inputs = {}
    if w.get('status') == 'PASS':
        c = w['checks']
        inputs['ri_w'] = port_entry(w['measured_local_contract'], c['positive'], c['negative_payload'])
        inputs['ri_w'].setdefault('source_pin', 'ot_s81sl_rstopt.ri_w')
    if ev.get('status') == 'PASS':
        for port, contract in ev['by_input_port'].items():
            c = ev['checks']
            inputs[port] = port_entry(contract, c[port], c['negative_' + port])
    src = {}
    for r in (w, ev):
        for name, digest in r['source_sha256'].items():
            if src.setdefault(name, digest) != digest:
                raise ValueError('entry runs disagree on source ' + name)
    for k in ('die_sha256', 'entry_image_sha256', 'fixture_meta_sha256', 'relay_module_sha256'):
        if w.get(k) is not None and ev.get(k) is not None and w.get(k) != ev.get(k):
            raise ValueError('entry runs disagree on ' + k)
    status = 'PASS' if inputs and all(v['status'] == 'PASS' for v in inputs.values()) \
        and {'ri_w', 'ri_e', 'vi'} <= set(inputs) else 'FAIL'
    return dict(schema='opentallas.s81.entry_mechanism_receipt.v1', status=status, inputs=inputs,
                source_sha256=src, die_sha256=ev.get('die_sha256'),
                entry_image_sha256=ev.get('entry_image_sha256'),
                runs={'ri_w': dict(path=str(w_path), sha256=hashlib.sha256(Path(w_path).read_bytes()).hexdigest()),
                      'ri_e+vi': dict(path=str(ev_path), sha256=hashlib.sha256(Path(ev_path).read_bytes()).hexdigest())},
                clock_scope='common bench clock phase0 per port; die route phases remain conditional (entry_boot model)',
                full_token=False)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--w-result', required=True)
    ap.add_argument('--ev-result', required=True)
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    r = compose(a.w_result, a.ev_result)
    Path(a.out).write_text(json.dumps(r, indent=1) + '\n')
    print('ENTRY_MECHANISM', r['status'], {k: v['status'] for k, v in r['inputs'].items()})
    raise SystemExit(0 if r['status'] == 'PASS' else 1)


if __name__ == '__main__':
    main()
