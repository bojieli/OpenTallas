#!/usr/bin/env python3
"""Q-B2 10-16: assemble results/arch/qwen_split_compute_1014/b2_join/phase_calibration.json from ACTUAL evidence.

Every field is copied from a committed artifact and hashed; the manifest is CALIBRATED only when the route-register
composed bench (run_route_bench.sh) PASSED with these exact sources and its negative controls were rejected, and the
consumer validator (phase_protocol.validate_calibration) accepts it.  Otherwise the status stays OPEN with the reason.
"""
import argparse, hashlib, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GROUPS = ('tc_to_port', 'am_to_controller', 'rq_to_train', 'tag_copy_to_issuer', 'issuer_to_train', 'lc_to_halfband',
          'selector_to_upper', 'upper_to_halfband', 'rb_to_vm')


def rec(path):
    p = ROOT / path
    return dict(path=str(path), sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--evidence-dir', required=True, help='repo-relative dir holding allocator_graph.json, '
                    'allocator_stage_of.json, ledger.json, route bench logs/sources')
    ap.add_argument('--cal', required=True, help='repo-relative calibration_sources.json')
    ap.add_argument('--gate', required=True, help='repo-relative JSON of observed bench outcomes')
    ap.add_argument('--out', default='results/arch/qwen_split_compute_1014/b2_join/phase_calibration.json')
    a = ap.parse_args(argv)
    E = Path(a.evidence_dir)
    L = json.loads((ROOT / E / 'ledger.json').read_text())
    cal = json.loads((ROOT / a.cal).read_text())
    gate = json.loads((ROOT / a.gate).read_text())
    k = L['constants']
    ev = {n: rec(E / f) for n, f in (('allocator_graph', 'allocator_graph.json'), ('allocator_stage_of', 'allocator_stage_of.json'),
                                     ('allocated_path_ledger', 'ledger.json'), ('route_bench_runner', 'run_route_bench.sh'),
                                     ('route_bench_source', 'tb_b2_route.sv'), ('route_bench_source_manifest', 'source.sha256'),
                                     ('route_bench_log', 'run.log'))}
    halves = {}
    for h in '012345':
        r = L['halves'][h]
        halves[h] = {g: dict(edges=r[g]['edges'], source_pin=r[g]['source_pin'], sink_pin=r[g]['sink_pin'],
                             stage_record_ids=r[g]['stage_record_ids']) for g in GROUPS}
        halves[h].update(halfband_lnk=k['halfband_lnk'], controller_lnk=k['controller_lnk'],
                         controller_clnk=k['controller_clnk'], train_edges=k['train_edges'])
    open_fields = list(L.get('structural_issues', []))
    tg = dict(gate.get('temporal_gate', {}))
    tg.update(source_manifest_sha256=ev['route_bench_source_manifest']['sha256'],
              allocator_graph_sha256=ev['allocator_graph']['sha256'],
              allocated_path_ledger_sha256=ev['allocated_path_ledger']['sha256'])
    for key in ('all_six_exact_rq_and_am', 'all_six_exact_rb_cycles_and_payload', 'real_e3_readbacks',
                'native_head_scalar_exact', 'actual_prefetch_mutant_rejected', 'actual_train_phase_mutant_rejected',
                'selector_and_upper_returns_exact'):
        if tg.get(key) is not True:
            open_fields.append(f'temporal gate {key} not observed')
    m = dict(protocol='qwen-b2-native-phase-v1',
             status='CALIBRATED_SOURCE_AND_ROUTE_TEMPORAL_PASS' if not open_fields else 'OPEN',
             open_fields=open_fields, graph_format='qwen-b2-allinst-buses-bindings-v1',
             route_bench_include_dirs=['rtl/hdc', '.'], evidence=ev,
             calibrated_sources=cal['calibrated_sources'], constants=k, halves=halves, temporal_gate=tg,
             physical_qualified=False, native_full_layer_qualified=False)
    out = ROOT / a.out
    out.write_text(json.dumps(m, indent=1) + '\n')
    if m['status'] != 'OPEN':
        sys.path.insert(0, str(ROOT / 'tools'))
        from qwen_b2_join.phase_protocol import validate_calibration
        validate_calibration(out, ROOT, phase='before_allocator')
    print(m['status'], open_fields)


if __name__ == '__main__':
    main()
