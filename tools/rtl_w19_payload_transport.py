#!/usr/bin/env python3
"""W19 compact 136-byte production sector/tag adapter gate (opt-in, not adopted).

Uses existing W13 SM snapshot and real full-K routed-expert operands. Final-line
padding only; sector protocol gate separately exercises duplicates/epochs/stalls.
"""
from __future__ import annotations
import argparse
import ast
import datetime
import hashlib
import json
import pickle
import re
import shlex
import subprocess
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import w19_sm_real_ops as W
import rtl_gpu_sm_exact as S
import rtl_v41_fullshape_layer_campaign as LC
import uarch_model as U

ROOT = Path(__file__).resolve().parents[1]
BENCH = 'rtl/test/tb_w19_payload_transport.sv'
SOURCES = [s for s in S.SMV_SRC if s != 'rtl/test/tb_gpu_sm_v.sv'] + [
    'rtl/hdc/ot_hdc_prefix.sv', 'rtl/gpu/ot_gpu_payload_assemble.sv', 'rtl/gpu/ot_gpu_expert_fetch.sv', 'rtl/hdc/kv/ot_hdc_hbm_model.sv', BENCH]


def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dump', type=Path, default=ROOT / 'results/rtl/w19_sm_operands/ar_L0_oreduce.pkl')
    ap.add_argument('--work', type=Path, required=True)
    ap.add_argument('--record', type=Path, required=True)
    ap.add_argument('--sm-source-commit', help='W13 immutable SM simulation source snapshot; exports without editing RTL')
    ap.add_argument('--jobs', type=int, default=4, help='Independent operand simulations; source builds are serialized')
    ap.add_argument('--limit', type=int, default=0, help='Debug subset, recorded explicitly')
    ap.add_argument('--simulation-host', help='SSH destination for bounded vvp jobs; builds and checkpoint packing stay local')
    ap.add_argument('--ssh-key', type=Path)
    ap.add_argument('--remote-work', default='/home/ubuntu/w19-production-sim')
    args = ap.parse_args()
    if args.jobs < 1 or args.jobs > 4:
        raise SystemExit('Bounded campaign requires 1..4 simulation slots')
    local_run = S.run_sim
    executions = []
    if args.simulation_host:
        ssh = ['ssh'] + (['-i', str(args.ssh_key)] if args.ssh_key else [])
        scp = ['scp', '-q'] + (['-i', str(args.ssh_key)] if args.ssh_key else [])
        def remote_run(exe, directory, gap):
            remote = args.remote_work + '/' + directory.name
            subprocess.run(ssh + [args.simulation_host, 'mkdir -p ' + shlex.quote(remote)], check=True)
            subprocess.run(scp + [str(exe)] + [str(directory / p) for p in ('cfg.hex', 'lines.hex', 'x.hex')]
                + [args.simulation_host + ':' + remote + '/'], check=True)
            command = 'cd ' + shlex.quote(remote) + ' && vvp -n sim.vvp +DIR=. +GAP=0 > sim.log 2>&1'
            outcome = subprocess.run(ssh + [args.simulation_host, command])
            subprocess.run(scp + [args.simulation_host + ':' + remote + '/sim.log', str(directory / 'sim.log')], check=True)
            outcome.check_returncode()
            subprocess.run(scp + [args.simulation_host + ':' + remote + '/out.txt', str(directory / 'out.txt')], check=True)
            executions.append(dict(directory=directory.name, host=args.simulation_host, executable_sha256=digest(exe),
                output_sha256=digest(directory / 'out.txt'), log_sha256=digest(directory / 'sim.log')))
            res, meta = {}, {}
            for line in (directory / 'out.txt').read_text().splitlines():
                if line.startswith('#'):
                    toks = line[1:].split()
                    for i in range(0, len(toks)-1, 2):
                        meta[toks[i]] = int(toks[i+1]) if toks[i+1].lstrip('-').isdigit() else toks[i+1]
                    if 'TIMEOUT' in line: meta['timeout'] = True
                else:
                    row, value = line.split(); res[int(row)] = value
            return res, meta
        S.run_sim = remote_run
    if args.record.exists():
        raise SystemExit('Use a fresh record path; previous verdicts are immutable')
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], cwd=ROOT).strip():
        raise SystemExit('Run from a clean committed worktree')
    args.work.mkdir(parents=True, exist_ok=True)
    # Candidate is already sized/committed in the unified model before this build.
    model = U.hbm_gpu_design('v41')
    preflight = U.gpu_payload_transport_model()
    preflight.update(model_source_sha256=digest(ROOT / 'tools/uarch_model.py'),
        element=model['element'], sm_count=model['sm_count'], bulk_copy=model['bulk_copy'],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip())
    (args.work / 'model_preflight.json').write_text(json.dumps(preflight, indent=2) + '\n')
    proto_src = ['rtl/gpu/ot_gpu_payload_assemble.sv', 'rtl/test/tb_w19_payload_protocol.sv']
    proto_dir = args.work / 'protocol'
    proto_dir.mkdir(exist_ok=True)
    proto_exe = S.compile_tb(proto_src, 'tb_w19_payload_protocol', {}, proto_dir)
    proto_run = subprocess.run(['vvp', str(proto_exe)], check=True, capture_output=True, text=True, timeout=30)
    (proto_dir / 'sim.out').write_text(proto_run.stdout)
    if 'PROTO PASS checks=8' not in proto_run.stdout:
        raise SystemExit('Protocol gate did not complete')
    protocol = dict(status='pass', output=proto_run.stdout.strip(),
        source_sha256={p:digest(ROOT/p) for p in proto_src})
    sources = SOURCES
    sm_snapshot = None
    source_hashes = {p: digest(ROOT / p) for p in SOURCES}
    if args.sm_source_commit:
        pin = subprocess.check_output(['git', 'rev-parse', args.sm_source_commit + '^{commit}'], cwd=ROOT, text=True).strip()
        source_list = subprocess.check_output(['git', 'show', pin + ':tools/rtl_gpu_sm_exact.py'], cwd=ROOT, text=True)
        node = next(n for n in ast.parse(source_list).body if isinstance(n, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == 'SMV_SRC' for t in n.targets))
        paths = [p for p in ast.literal_eval(node.value) if p != 'rtl/test/tb_gpu_sm_v.sv']
        snapshot = args.work / 'sm_snapshot'
        hashes, exported = {}, []
        for path in paths:
            data = subprocess.check_output(['git', 'show', pin + ':' + path], cwd=ROOT)
            dst = snapshot / path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(data)
            hashes[path] = hashlib.sha256(data).hexdigest()
            exported.append(str(dst.resolve()))
        local = ['rtl/gpu/ot_gpu_payload_assemble.sv', 'rtl/gpu/ot_gpu_expert_fetch.sv', 'rtl/hdc/kv/ot_hdc_hbm_model.sv', BENCH]
        sources = exported + [str(ROOT / p) for p in local]
        source_hashes = {p: digest(ROOT / p) for p in local}
        proof_path = 'results/rtl/ot_hdc_prefix_vec_equiv.json'
        if 'rtl/sim/ot_hdc_prefix_vec.sv' in paths:
            proof_bytes = subprocess.check_output(['git', 'show', pin + ':' + proof_path], cwd=ROOT)
            proof = json.loads(proof_bytes)
            if proof.get('status') != 'pass':
                raise SystemExit('W13 prefix simulation view lacks passing equivalence evidence')
            for path, expected in proof['source_sha256'].items():
                actual = hashlib.sha256(subprocess.check_output(['git', 'show', pin + ':' + path], cwd=ROOT)).hexdigest()
                if actual != expected:
                    raise SystemExit('W13 prefix equivalence source pin mismatch: ' + path)
            prefix_equivalence = dict(path=proof_path, sha256=hashlib.sha256(proof_bytes).hexdigest(),
                tested_widths=proof['widths'], claim='Existing W13 proof at its recorded widths only')
        else:
            prefix_equivalence = None
        sm_snapshot = dict(commit=pin, source_sha256=hashes, prefix_equivalence=prefix_equivalence,
            compile_list_sha256=hashlib.sha256(source_list.encode()).hexdigest(),
            claim='Unmodified W13 simulation snapshot; not in-context SS/FF qualification')
    W.V.set_arith('chunk8')
    dump = pickle.loads(args.dump.read_bytes())
    selected = [(key, e) for key, e in dump.items() if '.experts.' in str(e['w'])]
    if args.limit:
        selected = selected[:args.limit]
    if not selected:
        raise SystemExit('No routed expert operands')
    ck = LC.Checkpoint()
    m, _ = LC.build_model(ck, engram=False)
    cache, build_lock = {}, threading.Lock()
    # Lazy checkpoint decoding is not thread safe; materialize every selected
    # matrix before launching independent fixture simulations.
    for _, entry in selected:
        m.w[entry['w']]
    def one(job):
        key, entry, stall, corrupt, row_swap = job
        expert = int(re.search(r'\.experts\.(\d+)\.', entry['w'])[1])
        def runner(params, directory):
            cfg = (directory / 'cfg.hex').read_text().splitlines()
            cfg[6] = f'{expert:08x}'
            (directory / 'cfg.hex').write_text('\n'.join(cfg) + '\n')
            cfg[7] = f'{stall | (corrupt << 1) | (row_swap << 2):08x}'
            (directory / 'cfg.hex').write_text('\n'.join(cfg) + '\n')
            k = tuple(sorted(params.items()))
            with build_lock:
                if k not in cache:
                    cache[k] = S.compile_tb(sources, 'tb_w19_payload_transport', params,
                        tempfile.mkdtemp(prefix='build_', dir=args.work))
            result, meta = S.run_sim(cache[k], directory, 0)
            meta['fixture_sha256'] = {p: digest(directory / p) for p in ('cfg.hex', 'lines.hex', 'x.hex')}
            meta['first_byte_cycles'] = meta.get('first_sector', 0) - meta.get('first_req', 0)
            return result, meta
        try:
            result = W.case(m, key, [entry], str(args.work), sim_runner=runner)
        except (subprocess.CalledProcessError, ValueError, OSError) as error:
            print(key, 'FAIL', str(error), flush=True)
            return dict(op=key, expert_id=expert, stall=stall,
                corrupt_exponent=bool(corrupt), gate_pass=False, error=str(error))
        result.update(expert_id=expert, stall=stall, corrupt_exponent=bool(corrupt), row_swap=bool(row_swap))
        if corrupt or row_swap:
            passed = (not result['exact'] and result['accumulator_mismatches'] > 0
                and result['rtl'].get('fault') == 0 and not result['rtl'].get('timeout'))
        else:
            passed = (result['exact'] and result['rtl'].get('fetched') == (result['rtl']['lines']*136+127)//128
                and (not stall or result['rtl'].get('fetch_stalls', 0) > 0))
        result['gate_pass'] = bool(passed)
        print(key, expert, stall, corrupt, 'PASS' if passed else 'FAIL', result['rtl'], flush=True)
        return result
    jobs = [(key, entry, stall, corrupt, 0) for key, entry in selected
        for stall, corrupt in ((0, 0), (1, 0), (1, 1))]
    jobs += [(key, entry, 1, 0, 1) for key, entry in selected if '.w2.' in entry['w']]
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        cases = list(pool.map(one, jobs))
    record = dict(schema='opentallas.rtl.w19_payload_transport.v1', status='pass' if all(c['gate_pass'] for c in cases) else 'fail',
        generated_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        simulator=subprocess.check_output(['iverilog', '-V'], text=True, stderr=subprocess.DEVNULL).splitlines()[0],
        source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        claim_boundary='RTL simulation: real routed-expert SM rows at full K, HBM model -> expert fetch -> production '
            'opt-in compact sector/tag adapter -> unmodified ot_gpu_sm_v bulk copy, SRAM and arithmetic. Exact accumulator '
            'and rounded outputs checked against golden and ISA dump. Exponent corruption is required to fail '
            'numerically. No router, multi-SM/rank runtime, complete token, adoption or SS/FF claim. Row-swap controls detect row assignment errors.',
        model_preflight=preflight, debug_limit=args.limit, jobs=args.jobs, hbm_clk_ps=833, dump_sha256=digest(args.dump),
        checkpoint_index_sha256=digest(ck.snap / 'model.safetensors.index.json'),
        sm_snapshot=sm_snapshot, protocol=protocol,
        source_sha256=dict(source_hashes, **{p: digest(ROOT / p) for p in ['tools/rtl_w19_payload_transport.py',
            'tools/w19_sm_real_ops.py', 'tools/rtl_gpu_sm_exact.py', 'tools/hdc_golden_v41.py', 'tools/hdc_golden.py', 'tools/rtl_v41_fullshape_layer_campaign.py']}),
        executions=executions, simulation_host=args.simulation_host or 'local',
        cases=cases, dependency='W13 SS/FF SM qualification remains pending; no duplicate hardening launched',
        model_update='Compact adapter service cycles measured; token model/headline adoption remains OFF pending full runtime/SSFF')
    args.record.write_text(json.dumps(record, indent=2) + '\n')
    return 0 if record['status'] == 'pass' else 1


if __name__ == '__main__':
    raise SystemExit(main())
