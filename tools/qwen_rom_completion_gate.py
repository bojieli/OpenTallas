#!/usr/bin/env python3
"""Replay source-bound Qwen completion dependencies without building hardware."""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from qwen_rom_source_gate import replay
from qwen_rom_integration_preflight import prepare


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def assess(exact, preflight, baseline, successor, successor_pin_current):
    """Keep analytical readiness, runtime exactness and physical qualification distinct."""
    stages = exact['completed_stages']
    expected = [f'L{i}' for i in range(36)] + ['head']
    analytical = (baseline['selected_arithmetic_extra'] == 54
                  and successor['selected_arithmetic_extra'] == 55
                  and successor['model_price_joined']
                  and baseline['program_sha256'] == successor['program_sha256']
                  and successor['body_plus_kv_prep_cycles'] - baseline['body_plus_kv_prep_cycles'] == 217)
    chain = not any(preflight['missing_arithmetic_paths'].values())
    gates = [
        dict(id='original_terminal', ready=exact['full_token_exact_at_runtime_scope'],
             requires='Original 36 layers plus head, oracle token/logit and process-exit/source/binary/image joins'),
        dict(id='seven_runtime_sources', ready=exact['current_source_joined'],
             requires='After original terminal, integrate the seven actual reviewed diffs in isolated namespaces; rerun connected exactness'),
        dict(id='analytical_plus55', ready=analytical,
             requires='Opted-in successor uses the same program and prices all 217 ME issues; preserve the legacy +54 FAIL'),
        dict(id='publisher_generator_pin', ready=successor_pin_current,
             requires='Publisher replays against its own generator and pre-successor predecessor; concurrent model edits require new pins'),
        dict(id='whole_arithmetic_chain', ready=chain,
             requires='Driver->die->generated core->spine and driver->tile propagate ACC7/TREE7/MUL6/FAST1/KV_PREP3 together'),
        dict(id='macro_local_kv', ready=False,
             requires='Connected macro read/fill/mask and read-before-write collision exactness at TP4 heads2/base131072, MEM_EXTRA1'),
        dict(id='unified_physical_sizing', ready=False,
             requires='Compose hub/fill latency, track demand/capacity, replica mux/demux/fanout, slot fit and macro SS clk-to-q in unified model'),
        dict(id='connected_measured_latency', ready=False,
             requires='Parent GO then one matched-source connected gate measures body/collective/service cycles and re-prices the full program'),
        dict(id='element_context_ss_ff', ready=False,
             requires='Actual arithmetic and macro element at SS setup/FF hold, 0.833333ns and 60ps/25ps; committed final LEF/ETM'),
        dict(id='spine_collective_die', ready=False,
             requires='Matched spine/collective/root/hub routing-layer acceptance, zero overflow and actual-element power/IR; compose token latency'),
    ]
    return dict(status='blocked', adoption=False, physical_build_ready=False,
                whole_36_layer_head_completion=exact['full_token_exact_at_runtime_scope'],
                completed_stages=stages, missing_stages=[s for s in expected if s not in stages],
                exact_vector_count=len(exact['checks']), analytical_successor_ready=analytical,
                measured_plus55_latency_ready=False, successor_record_generator_current=successor_pin_current,
                gates=gates, next_ready_action='Replay successor and source dependencies; complete model sizing before any build. Preserve original live token until terminal.',
                dependencies={'seven_runtime_sources': ['original_terminal'],
                              'whole_arithmetic_chain': ['analytical_plus55', 'unified_physical_sizing', 'seven_runtime_sources'],
                              'connected_measured_latency': ['whole_arithmetic_chain', 'macro_local_kv', 'unified_physical_sizing'],
                              'element_context_ss_ff': ['connected_measured_latency'],
                              'spine_collective_die': ['element_context_ss_ff']})


def generate(package_path, successor_path, source_root):
    package_raw = package_path.read_bytes()
    successor_raw = successor_path.read_bytes()
    original = source_root / 'results/rtl/qwen_rom_model_propagation_20261002/price_join_fail.json'
    fail_raw = original.read_bytes()
    packet = json.loads(package_raw)
    exact = replay(packet, source_root)
    preflight = prepare(packet, source_root)
    # prepare imports the selected root's unified model before this lookup.
    import uarch_model as U
    if Path(U.__file__).resolve() != (source_root / 'tools/uarch_model.py').resolve():
        raise ValueError('Loaded model belongs to a different source root')
    baseline = U.qwen_rom_physical_successor()
    successor = U.qwen_rom_physical_successor(enabled=True)
    model_raw = (source_root / 'tools/uarch_model.py').read_bytes()
    record = assess(exact, preflight, baseline, successor,
                    json.loads(successor_raw)['successor_model_sha256'] == sha(model_raw))
    pins = preflight['source_sha256']
    if any(sha((source_root / p).read_bytes()) != h for p, h in pins.items()):
        raise ValueError('Sources changed during replay')
    if original.read_bytes() != fail_raw or json.loads(fail_raw)['status'] != 'fail':
        raise ValueError('Historical FAIL changed')
    record.update(schema='opentallas.qwen-rom-completion-gate.v1',
                  at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  source_ref=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source_root, text=True).strip(),
                  source_sha256=pins, package_sha256=sha(package_raw), successor_record_sha256=sha(successor_raw),
                  original_fail_sha256=sha(fail_raw), current_model_sha256=sha(model_raw),
                  source_reconciliation=preflight['source_reconciliation'],
                  missing_arithmetic_paths=preflight['missing_arithmetic_paths'], sizing=preflight['sizing'],
                  macro_local_geometry=preflight['kv'], successor=successor,
                  heavy_jobs_launched=0, claim_boundary='Analytical/source replay only; existing checkpoint exactness is scoped to its captured runtime. No hardware, source mutation or measured successor timing.')
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--package', type=Path, required=True)
    ap.add_argument('--successor', type=Path, required=True)
    ap.add_argument('--source-root', type=Path, default=ROOT)
    ap.add_argument('--result', type=Path, required=True)
    a = ap.parse_args()
    if a.result.exists():
        ap.error('Refusing to overwrite evidence')
    try:
        record = generate(a.package, a.successor, a.source_root)
    except (FileNotFoundError, ValueError, AttributeError) as exc:
        record = dict(schema='opentallas.qwen-rom-completion-gate.v1', status='blocked',
                      error=str(exc), source_ref=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=a.source_root, text=True).strip(),
                      current_model_sha256=sha((a.source_root / 'tools/uarch_model.py').read_bytes()),
                      adoption=False, physical_build_ready=False, analytical_successor_ready=False,
                      measured_plus55_latency_ready=False, successor_record_generator_current=False, completed_stages=[],
                      at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    record['verifier_sha256'] = sha(Path(__file__).read_bytes())
    a.result.parent.mkdir(parents=True, exist_ok=True)
    with a.result.open('x') as f:
        json.dump(record, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({k: record[k] for k in ('status', 'source_ref', 'completed_stages', 'analytical_successor_ready', 'measured_plus55_latency_ready', 'successor_record_generator_current')}, indent=2))
    return 1 if record['status'] == 'blocked' else 0


if __name__ == '__main__':
    sys.exit(main())
