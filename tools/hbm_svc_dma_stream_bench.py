"""Full-shape four-stack CPU service DMA scoreboard and mandatory bandwidth gate."""
import argparse, hashlib, json, pathlib, re, subprocess
ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC = ['rtl/ot_hbm_svc_dma_pc_tile.sv', 'rtl/ot_hbm_svc_dma_stream.sv', 'rtl/test/hbm_accel/tb_hbm_svc_dma_stream.sv']

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--work', type=pathlib.Path, required=True)
    p.add_argument('--out', type=pathlib.Path, required=True)
    p.add_argument('--initial-credits', type=int, default=8)
    p.add_argument('--credit-rtt', type=int, default=0)
    p.add_argument('--read-latency', type=int, default=1)
    p.add_argument('--request-gap', type=int, default=1)
    p.add_argument('--rate-commands', type=int, default=128)
    p.add_argument('--window', type=int, default=1024)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit('fresh immutable evidence record required')
    a.work.mkdir(parents=True, exist_ok=True)
    input_hashes = {s: hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC + ['tools/hbm_svc_dma_stream_bench.py']}
    cases = []
    for name, mutant in [('baseline', 0), ('data_mutant', 1), ('index_mutant', 2), ('fault_mutant', 3), ('rtl_pc_map_mutant', 4), ('rtl_drop_mutant', 5), ('rtl_data_mutant', 6), ('response_tag_mutant', 7), ('response_beat_mutant', 8)]:
        obj = a.work / (name + '.vvp')
        c = subprocess.run(['iverilog', '-g2012', '-s', 'tb_hbm_svc_dma_stream',
                            '-Ptb_hbm_svc_dma_stream.MUT=' + str(mutant),
                            '-Ptb_hbm_svc_dma_stream.INITIAL_CREDITS=' + str(a.initial_credits),
                            '-Ptb_hbm_svc_dma_stream.CREDIT_RTT=' + str(a.credit_rtt),
                            '-Ptb_hbm_svc_dma_stream.READ_LATENCY=' + str(a.read_latency),
                            '-Ptb_hbm_svc_dma_stream.REQUEST_GAP=' + str(a.request_gap),
                            '-Ptb_hbm_svc_dma_stream.RATE_COMMANDS=' + str(a.rate_commands),
                            '-Ptb_hbm_svc_dma_stream.WINDOW=' + str(a.window), '-o', str(obj),
                            *[str(ROOT / s) for s in SRC]], capture_output=True, text=True)
        if c.returncode:
            cases.append(dict(case=name, verdict='COMPILE_FAIL', output=c.stdout + c.stderr))
            break
        r = subprocess.run(['vvp', str(obj)], capture_output=True, text=True, cwd=a.work)
        cases.append(dict(case=name, verdict='PASS' if r.returncode == 0 else 'FAIL',
                          returncode=r.returncode, output=r.stdout + r.stderr))
    rates = []
    if cases:
        for stack, size, cycles in re.findall(r'BANDWIDTH stack=(\d+) bytes=(\d+) cycles=(\d+)', cases[0]['output']):
            rates.append(dict(stack=int(stack), bytes=int(size), cycles=int(cycles),
                              bytes_per_cycle=int(size)/int(cycles),
                              efficiency=int(size)/(256*int(cycles))))
    correctness = len(cases) == 9 and cases[0]['verdict'] == 'PASS' and all(x['verdict'] == 'FAIL' for x in cases[1:])
    bandwidth = len(rates) == 4 and all(x['efficiency'] >= .90 for x in rates)
    sources_unchanged = all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest() == digest for s, digest in input_hashes.items())
    evidence = dict(schema='opentallas.hbm_svc.dma_stream.v1',
                    verdict='PASS' if correctness and bandwidth and sources_unchanged else 'FAIL', sources_unchanged=sources_unchanged,
                    correctness='PASS' if correctness else 'FAIL', bandwidth='PASS' if bandwidth else 'FAIL',
                    initial_credits=a.initial_credits, credit_rtt_cycles=a.credit_rtt,
                    read_latency_cycles=a.read_latency, request_gap_cycles=a.request_gap, backend_outstanding_bursts_per_pc=16,
                    rate_commands=a.rate_commands, window_sectors=a.window,
                    bandwidth_measurement=f'Four full stacks, {a.rate_commands} consecutive 256-sector commands; all command startup/drain included; 1024 bytes/cycle aggregate peak',
                    stack_rates=rates, cases=cases,
                    input_sha256=input_hashes,
                    scope='Transaction-exact CPU memory backend; physical closure and mutable-state ECC not established by this bench')
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(evidence, indent=2) + '\n')
    print(json.dumps(evidence, indent=2))
    raise SystemExit(0 if evidence['verdict'] == 'PASS' else 1)

if __name__ == '__main__':
    main()
