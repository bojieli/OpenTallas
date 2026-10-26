#!/usr/bin/env python3
"""S81 VM A2 storage join, HOP1 candidate (S-VM 2210): the b4 quarter relays are removed and the b8 bridge drives its
eight bank128 directly (tools/s81_vm/area_a2_storage_join_hop1.sv, module s81_a2_storage_join_hop1).

Same actual 128-SRAM component bench as area_a2_storage_gate.py (imported, not edited: its pinned receipts stay
byte-identical), with the fixed-cycle expectations moved by exactly one register per direction:
  raw write  P+12+lane -> P+11+lane     raw read Q+3 -> Q+2     read return Q+6 -> Q+4
  returned commit = raw + 2 -> raw + 1 (P+14+lane -> P+12+lane)
Cases: gold (mode 0 burst, mode 4 full 1 MiB) + the original mutants (early commit, mask, scatter address, capacity
alias, wrong same-edge expectation) + HOP2_EXPECTATION: the unchanged hop-2 bench run on the hop-1 RTL must FAIL (the
bench observes the cycle change).  Outputs go to results/arch/s81_vm_hop1_2210 (or --out).
Run from a full source tree: python3 tools/s81_vm/area_a2_storage_hop1_gate.py [--out DIR]
"""
import argparse
import hashlib
import inspect
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import area_a2_storage_gate as G  # noqa: E402

ROOT = G.ROOT
JOIN = 'tools/s81_vm/area_a2_storage_join_hop1.sv'


def hop1_bench(b):
    rep = [('s81_a2_storage_join dut(', 's81_a2_storage_join_hop1 dut('),
           ('due=cycle+12+ln;', 'due=cycle+11+ln;'),
           ('erv[cycle+3][bank]=1;era[cycle+3][9*bank+:9]=a;ert[cycle+3][8*bank+:8]=cycle;',
            'erv[cycle+2][bank]=1;era[cycle+2][9*bank+:9]=a;ert[cycle+2][8*bank+:8]=cycle;'),
           ('esv[cycle+3][bank]=1;est[cycle+3][8*bank+:8]=ert[cycle][8*bank+:8];',
            'esv[cycle+2][bank]=1;est[cycle+2][8*bank+:8]=ert[cycle][8*bank+:8];'),
           ('esa[cycle+3][9*bank+:9]=era[cycle][9*bank+:9];', 'esa[cycle+2][9*bank+:9]=era[cycle][9*bank+:9];'),
           ('esd[cycle+3][512*bank+:512]=model[bank][era[cycle][bank*9+:9]];',
            'esd[cycle+2][512*bank+:512]=model[bank][era[cycle][bank*9+:9]];'),
           ('esd[cycle+3][bank*512+j*32+:32]=ewd[cycle][bank*512+j*32+:32];',
            'esd[cycle+2][bank*512+j*32+:32]=ewd[cycle][bank*512+j*32+:32];'),
           ('$display("OBS_READ %0d %0d %0d %0d %0d %0d %032h",cycle,cycle-3,',
            '$display("OBS_READ %0d %0d %0d %0d %0d %0d %032h",cycle,cycle-2,'),
           ('raw_age12 returnedcommit14 directread_raw3_return6', 'HOP1 raw_age11 returnedcommit12 directread_raw2_return4')]
    for a, c in rep:
        assert b.count(a) == 1, a
        b = b.replace(a, c)
    # Keep read trace age separate from the commit index substitutions below.
    b = b.replace('cycle,cycle-2,bank,sl,', 'cycle,READ_RAW_AGE,bank,sl,')
    # commit = raw + 1: every 'cycle-2' / 'cycle>=2' in the commit checks
    n = b.count('cycle-2') + b.count('cycle>=2')
    assert n == 14, n
    b = b.replace('cycle>=2', 'cycle>=1').replace('cycle-2', 'cycle-1')
    return b.replace('READ_RAW_AGE', 'cycle-2')


def hop2_on_hop1_bench(b):
    a = 's81_a2_storage_join dut('
    assert b.count(a) == 1
    return b.replace(a, 's81_a2_storage_join_hop1 dut(')


def hop1_trace():
    src = inspect.getsource(G.trace)
    for a, c in (("edge!=origin+12+lane", "edge!=origin+11+lane"),
                 ("edge!=raw+2 or edge!=origin+14+lane", "edge!=raw+1 or edge!=origin+12+lane"),
                 ("launch_edge=edge-6", "launch_edge=edge-4")):
        assert src.count(a) == 1, a
        src = src.replace(a, c)
    ns = dict(G.__dict__)
    exec(compile(src, G.__file__, 'exec'), ns)
    return ns['trace']


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', default=str(ROOT / 'results/arch/s81_vm_hop1_2210'))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    G.OUT = out
    G.HARD_COUNTS = dict(G.HARD_COUNTS, dsfd_vm_static_relay128_b4=0)
    sources = [JOIN] + G.SOURCES[1:]
    trace = hop1_trace()
    census_src = inspect.getsource(G.census).replace('sum(clocks.values())!=421', 'sum(clocks.values())!=357')
    ns = dict(G.__dict__)
    exec(compile(census_src, G.__file__, 'exec'), ns)
    census = ns['census']
    bench_h1 = hop1_bench(G.BENCH)
    bench_h2 = hop2_on_hop1_bench(G.BENCH)
    (out / 'hop1_bench.sv').write_text(bench_h1)
    (out / 'hop2_expectation_bench.sv').write_text(bench_h2)
    records, elaborations = [], []
    with tempfile.TemporaryDirectory(prefix='s81-a2-hop1-') as tmp:
        variants = [('gold', None, bench_h1), ('early_commit', 'OT_VM_BANK_MUT_EARLY_COMMIT', bench_h1),
                    ('mask', 'OT_VM_BANK_MUT_MASK', bench_h1), ('scatter_addr', 'OT_VM_DIRECT_SCATTER_MUT_ADDR', bench_h1),
                    ('hop2_expectation', None, bench_h2)]
        for variant, define, bench in variants:
            bp = Path(tmp) / (variant + '_bench.sv')
            bp.write_text(bench)
            exe = str(Path(tmp) / (variant + '.vvp'))
            cmd = ['iverilog', '-g2012', '-s', 'tb', '-o', exe] + (['-D' + define] if define else [])
            r = G.run(cmd + sources + [str(bp)], out / f'hop1_{variant}_compile.log')
            if r.returncode:
                raise RuntimeError(r.stdout + r.stderr)
            elaborations.append(dict(variant=variant, **census(exe)))
            cases = ([(0, 'gold', None), (4, 'gold', None), (4, 'capacity_alias', 'CAPACITY_ALIAS'),
                      (4, 'wrong_read_before_write_expectation', 'EXPECT_NEW_SAMEEDGE')]
                     if variant == 'gold' else [(4, variant, None)])
            for mode, case, flag in cases:
                cmd = ['vvp', exe, f'+mode={mode}'] + (['+' + flag] if flag else [])
                r = G.run(cmd, out / f'hop1_{case}_mode{mode}.log')
                passed = r.returncode == 0 and 'PASS actual128SRAM' in r.stdout
                rejected = r.returncode != 0 and 'FATAL:' in r.stdout
                if not (passed if case == 'gold' else rejected):
                    raise RuntimeError(f'{case}/{mode}: {r.stdout[-4000:]}{r.stderr}')
                obs = None
                if case == 'gold':
                    obs = trace(r.stdout, out / f'hop1_gold_mode{mode}_trace.jsonl.gz', require_full=mode == 4)
                    exp = (1060 if mode == 0 else 16416) * 4
                    if obs['records'].get('raw_write', 0) != exp or obs['records'].get('returned_commit', 0) != exp:
                        raise AssertionError('raw/commit observation counts mismatch')
                records.append(dict(variant=case, compile_variant=variant, mode=mode, returncode=r.returncode,
                                    exact_pass=passed, mutant_rejected=rejected,
                                    stdout='\n'.join(l for l in r.stdout.splitlines() if not l.startswith('OBS_'))[-3000:],
                                    complete_observations=obs))
    proof = dict(schema='opentallas.s81.vm-a2-hop1-storage-proof.v1',
                 status='PASS_ACTUAL_A2_128SRAM_HOP1_COMPONENT_ONLY_NOT_FULL_VM_OR_PHYSICAL',
                 sources={n: hashlib.sha256((ROOT / n).read_bytes()).hexdigest() for n in sources + [
                     'tools/s81_vm/area_a2_storage_gate.py', 'tools/s81_vm/area_a2_storage_hop1_gate.py']},
                 write_age=dict(raw_macro='P+11+lane', returned_commit='P+12+lane', delta_vs_hop2=-1, commit_delta=-2),
                 read_age=dict(raw_macro='Q+2', returned='Q+4', delta_vs_hop2=-2),
                 hard_leaves=dict(G.HARD_COUNTS), clock_pins=357, elaborations=elaborations, runs=records,
                 flags=dict(whole_VM_elaborated=False, physical_qualification=False, production_adopted=False))
    (out / 'hop1_storage_proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(dict(status=proof['status'], runs=[(r['variant'], r['mode'], r['exact_pass'], r['mutant_rejected'])
                                                         for r in records])))


if __name__ == '__main__':
    main()
