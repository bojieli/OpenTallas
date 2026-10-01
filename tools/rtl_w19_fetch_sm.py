#!/usr/bin/env python3
"""W19 bounded expert-fetch/HBM/SM arithmetic composition gate; no production adapter.

The bench transports each SM weight payload as two physical 128-B lines. This
intentionally padded transport is a correctness fixture, never a bandwidth fit.
Uses full K and the busiest SM's actual TP-96 row slice from a pinned ISA dump.
"""
from __future__ import annotations
import argparse
import datetime
import hashlib
import json
import pickle
import re
import subprocess
import tempfile
from pathlib import Path

import w19_sm_real_ops as W
import rtl_gpu_sm_exact as S
import rtl_v41_fullshape_layer_campaign as LC
import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]
BENCH = 'rtl/test/tb_w19_fetch_sm.sv'
SOURCES = [s for s in S.SMV_SRC if s != 'rtl/test/tb_gpu_sm_v.sv'] + [
    'rtl/hdc/ot_hdc_prefix.sv', 'rtl/gpu/ot_gpu_expert_fetch.sv', 'rtl/hdc/kv/ot_hdc_hbm_model.sv', BENCH]


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dump', type=Path, default=ROOT / 'results/rtl/w19_sm_operands/ar_L0_oreduce.pkl')
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--record', type=Path, required=True)
    ap.add_argument('--limit', type=int, default=0, help='Debug subset, recorded explicitly')
    args = ap.parse_args()
    if args.record.exists():
        raise SystemExit('Use a fresh record path; previous verdicts are immutable')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT).strip():
        raise SystemExit('Run from a clean committed worktree')
    args.work.mkdir(parents=True, exist_ok=True)
    # Existing unified-model element, before any RTL build. No engine added.
    model = U.hbm_gpu_design('v41')
    preflight = dict(model_source_sha256=digest(ROOT / 'tools/uarch_model.py'),
        element=model['element'], sm_count=model['sm_count'], bulk_copy=model['bulk_copy'],
        scope='Existing model-sized SM, one rank/SM slice per case; bench-only transport adapter',
        physical_line_bytes=128, sm_payload_bytes=136, fixture_bytes_per_payload=256,
        performance_adoption=False, token_cycle_count_available=False,
        production_transport_and_SSFF='W13 dependency; not established by this gate')
    (args.work / 'model_preflight.json').write_text(json.dumps(preflight, indent=2) + '\n')
    W.V.set_arith('chunk8')
    dump = pickle.loads(args.dump.read_bytes())
    selected = [(key, e) for key, e in dump.items() if '.experts.' in str(e['w'])]
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        raise SystemExit('No routed expert operands')
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    cache, cases = {}, []
    for key, entry in selected:
        expert = int(re.search(r'\.experts\.(\d+)\.', entry['w'])[1])
        for stall, corrupt in ((0, 0), (1, 0), (1, 1)):
            def runner(params, directory):
                cfg = (directory / 'cfg.hex').read_text().splitlines()
                cfg[6] = f'{expert:08x}'
                (directory / 'cfg.hex').write_text('\n'.join(cfg) + '\n')
                cfg[7] = f'{stall | (corrupt << 1):08x}'
                (directory / 'cfg.hex').write_text('\n'.join(cfg) + '\n')
                k = tuple(sorted(params.items()))
                if k not in cache:
                    cache[k] = S.compile_tb(SOURCES, 'tb_w19_fetch_sm', params,
                        tempfile.mkdtemp(prefix='build_', dir=args.work))
                result, meta = S.run_sim(cache[k], directory, 0)
                meta['fixture_sha256'] = {p: digest(directory / p) for p in ('cfg.hex', 'lines.hex', 'x.hex')}
                meta['first_byte_cycles'] = meta.get('first_sector', 0) - meta.get('first_req', 0)
                return result, meta
            try:
                result = W.case(m, key, [entry], str(args.work), sim_runner=runner)
            except (subprocess.CalledProcessError, ValueError, OSError) as error:
                cases.append(dict(op=key, expert_id=expert, stall=stall,
                    corrupt_exponent=bool(corrupt), gate_pass=False, error=str(error)))
                print(key, 'FAIL', str(error), flush=True)
                continue
            result.update(expert_id=expert, stall=stall, corrupt_exponent=bool(corrupt))
            if corrupt:
                passed = (not result['exact'] and result['accumulator_mismatches'] > 0
                    and result['rtl'].get('fault') == 0 and not result['rtl'].get('timeout'))
            else:
                passed = (result['exact'] and result['rtl'].get('fetched') == 2*result['rtl']['lines']
                    and (not stall or result['rtl'].get('fetch_stalls', 0) > 0))
            result['gate_pass'] = bool(passed)
            cases.append(result)
            print(key, expert, stall, corrupt, 'PASS' if passed else 'FAIL', result['rtl'], flush=True)
    record = dict(schema='opentallas.rtl.w19_fetch_sm.v1', status='pass' if all(c['gate_pass'] for c in cases) else 'fail',
        generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        simulator=subprocess.check_output(['iverilog', '-V'], text=True, stderr=subprocess.DEVNULL).splitlines()[0],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        claim_boundary='RTL simulation: real routed-expert SM rows at full K, HBM model -> expert fetch -> bench '
            'payload/tag adapter -> unmodified ot_gpu_sm_v bulk copy, SRAM and arithmetic. Exact accumulator '
            'and rounded outputs checked against golden and ISA dump. Exponent corruption is required to fail '
            'numerically. No router, multi-SM/rank runtime, complete token, production transport or SS/FF claim.',
        model_preflight=preflight, debug_limit=args.limit, dump_sha256=digest(args.dump),
        checkpoint_index_sha256=digest(ck.snap / 'model.safetensors.index.json'),
        source_sha256={p: digest(ROOT / p) for p in SOURCES + ['tools/rtl_w19_fetch_sm.py',
            'tools/w19_sm_real_ops.py', 'tools/rtl_gpu_sm_exact.py', 'tools/hdc_golden_v41.py', 'tools/hdc_golden.py']},
        cases=cases, dependency='W13 SS/FF SM qualification remains pending; no duplicate hardening launched',
        model_update='Diagnostic per-op cycles only; padded fixture cycles are excluded from token repricing')
    args.record.write_text(json.dumps(record, indent=2) + '\n')
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
