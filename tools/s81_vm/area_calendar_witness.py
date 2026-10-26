#!/usr/bin/env python3
"""Actual compact-ID component timestamps plus declared backend calendar."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
LOCK = Path('/home/ubuntu/claude-takeover-20261007/COORDINATOR.lock')
OUT = ROOT / 'results/arch/s81_vm_area_1417/calendar_witness.json'
SOURCES = ['tools/s81_vm/area_id_candidate.sv', 'tools/s81_vm/area_stripe_bench.sv',
           'tools/s81_vm/area_calendar_witness.py'] + [
               f'rtl/dsrom_sys/s81_ph/vm/{name}.sv' for name in
               ['dsfd_vm_static_wdispatch128', 'dsfd_vm_static_wstage128',
                'dsfd_vm_static_write_capture128']]


def check_lock():
    if json.loads(LOCK.read_text())['owner'] not in ('claude','codex'):
        raise RuntimeError('coordinator ownership changed')


def run(command):
    check_lock()
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    check_lock()
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def check_read(write, read):
    if read['raw_edge'] <= write['raw_edge']:
        raise ValueError('read-before-write SRAM requires raw read strictly after raw write')
    if (read['bank'], read['row']) != (write['bank'], write['row']):
        raise ValueError('dependent read address mismatch')


def check_commit(write, commit):
    if commit['edge'] != write['raw_edge'] + 2:
        raise ValueError('stale or delayed commit edge')
    if any(commit[key] != write[key] for key in ('bank', 'row', 'tag')):
        raise ValueError('commit identity mismatch')


def main():
    original = (ROOT / SOURCES[1]).read_text()
    observation = '''   tick();
   for(s=0;s<53;s=s+1)if(v[s])
    $display("OBS_SRC %0d %0d %0d %0d %0d %0d %032h",cycle,s,row[14*s+:14],lane[2*s+:2],tag[8*s+:8],mask[4*s+:4],data[128*s+:128]);
   for(b=0;b<8;b=b+1)if(ov[b])
    $display("OBS_OUT %0d %0d %0d %0d %0d %032h",cycle,BASE+b,ore[14*b+:14],ot[8*b+:8],om[4*b+:4],od[128*b+:128]);
'''
    if original.count('   tick();\n') != 1:
        raise RuntimeError('bench timestamp insertion point changed')
    bench = original.replace('   tick();\n', observation)
    traces, records = [], []
    mutants = []
    with tempfile.TemporaryDirectory(prefix='s81-calendar-') as temporary:
        temp = Path(temporary)
        check_lock()
        (temp / 'bench.sv').write_text(bench)
        for base in (0, 8, 16, 24):
            executable = str(temp / f'b{base}.vvp')
            run(['iverilog', '-g2012', '-s', 'tb', f'-Ptb.BASE={base}', '-o', executable,
                 SOURCES[0], str(temp / 'bench.sv')] + SOURCES[3:])
            for mode in (0, 4):
                result = run(['vvp', executable, f'+mode={mode}'])
                if 'PASS full53sources' not in result.stdout:
                    raise RuntimeError('missing old-gold pass')
                pending = {}
                local = []
                occupied = set()
                source_ids = set()
                for line in result.stdout.splitlines():
                    fields = line.split()
                    if not fields or fields[0] not in ('OBS_SRC', 'OBS_OUT'):
                        continue
                    kind = fields.pop(0)
                    if kind == 'OBS_SRC':
                        edge, source, row, lane, tag, mask = map(int, fields[:6])
                        data = fields[6]
                        key = (row, tag, mask, data)
                        if key in pending:
                            raise AssertionError('ambiguous full-payload source identity')
                        pending[key] = dict(source_sample_edge=edge, source=source, row=row,
                                            lane=lane, tag=tag, mask=mask, data_hex=data)
                        source_ids.add(source)
                    else:
                        edge, bank, row, tag, mask = map(int, fields[:5])
                        data = fields[5]
                        key = (row, tag, mask, data)
                        if key not in pending:
                            raise AssertionError('unmatched output payload')
                        record = pending.pop(key)
                        source_edge = record['source_sample_edge']
                        lane = record['lane']
                        if edge != source_edge + 5 + lane:
                            raise AssertionError('observed ID component age changed')
                        expected_bank = (row & 31) ^ (((row >> 5) & 7) << 2)
                        if bank != expected_bank:
                            raise AssertionError('observed bank hash mismatch')
                        p = source_edge - 1
                        write = dict(raw_edge=edge + 6, bank=bank, row=row, tag=tag)
                        commit = dict(edge=edge + 8, bank=bank, row=row, tag=tag)
                        q = p + 6 + lane
                        read = dict(issue_edge=q, raw_edge=q + 7, returned_edge=q + 16,
                                    bank=bank, row=row)
                        if write['raw_edge'] != p + 12 + lane or commit['edge'] != p + 14 + lane:
                            raise AssertionError('outer calendar arithmetic mismatch')
                        check_commit(write, commit)
                        check_read(write, read)
                        port = (write['raw_edge'], bank)
                        if port in occupied:
                            raise AssertionError('more than one raw write per bank/edge')
                        occupied.add(port)
                        record.update(base=base, mode=mode, observed_output_edge=edge,
                                      parent_issue_edge=p, composed_write=write,
                                      composed_commit=commit, composed_dependent_read=read)
                        local.append(record)
                if pending or len(local) != (480 if mode == 0 else 1440):
                    raise AssertionError('unmatched/lost records')
                if source_ids != set(range(53)):
                    raise AssertionError('not all 53 sources exercised')
                records.extend(local)
                traces.append(dict(base=base, mode=mode, observed_records=len(local),
                                   all53sources=True, raw_write_port_collisions=0,
                                   stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest(),
                                   gold_pass_line=result.stdout.splitlines()[-1]))
    exemplar = records[0]
    write = exemplar['composed_write']
    same_edge_read = dict(exemplar['composed_dependent_read'], raw_edge=write['raw_edge'])
    stale_commit = dict(exemplar['composed_commit'], edge=write['raw_edge'] + 1)
    delayed_commit = dict(exemplar['composed_commit'], edge=write['raw_edge'] + 3)
    wrong_tag = dict(exemplar['composed_commit'], tag=write['tag'] ^ 1)
    for name, checker, item in [('same_raw_edge_RAW', check_read, same_edge_read),
                                ('stale_commit', check_commit, stale_commit),
                                ('delayed_commit', check_commit, delayed_commit),
                                ('wrong_commit_tag', check_commit, wrong_tag)]:
        try:
            checker(write, item)
        except ValueError as error:
            mutants.append(dict(name=name, rejected=True, reason=str(error)))
        else:
            raise AssertionError(f'calendar mutant survived: {name}')
    stream_residues = sorted({r['source_sample_edge'] % 4 for r in records})
    serial_residues = sorted({((3 * r['source_sample_edge']) // 4) % 3 for r in records})
    if stream_residues != list(range(4)) or serial_residues != list(range(3)):
        raise AssertionError('missing clock phase residues')
    proof = dict(status='PASS_OBSERVED_ID_COMPONENT_PLUS_ANALYTICAL_BACKEND_CALENDAR_ONLY',
                 actual_component_runs=8, observed_records=len(records),
                 observed_scope='full53-source quarter RTL with unchanged old-gold bench; E0 source to E5+lane output',
                 analytical_scope='declared unchanged backend6edges, commit2afterraw; read rawQ+7 returnedQ+16',
                 formulas=dict(parent_issue='P=source_sample-1', raw_write='P+12+lane',
                               commit='P+14+lane', minimum_dependent_read_issue='Q>=P+6+lane',
                               raw_read='Q+7 > raw_write', returned_read='Q+16'),
                 raw_write_bank_ports=list(range(32)), max_writes_per_bank_raw_edge=1,
                 bank_coverage_scope='union of eight independent eight-bank quarter runs; not one shared 53-source/32-bank execution',
                 raw_write_port_check_scope='within each independent run only',
                 integrated_shared53_source_32bank_execution=False,
                 clock_phase_calendar=dict(serial_to_stream='3:4', scope='analytical phase labels; related-clock hardware not simulated',
                                           common_period_quarter_ticks=12,
                                           stream_edges_quarter_ticks=[0, 3, 6, 9],
                                           serial_edges_quarter_ticks=[0, 4, 8],
                                           observed_stream_residues=stream_residues,
                                           observed_serial_phase_residues=serial_residues),
                 flags=dict(ready_credit_retry_implemented=False, actual128_SRAM_read_join_run=False,
                            actual_service_profile_qualified=False, native_qualification=False,
                            full_programme_trace=False, full_token_performance_claim=False),
                 limitations='Finite component witness only; declared backend, commits and dependent reads are analytically composed, not observed hardware events.',
                 sources={name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES},
                 temporary_instrumented_bench_sha256=hashlib.sha256(bench.encode()).hexdigest(),
                 runs=traces, mutants=mutants, records=records)
    check_lock()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    check_lock()
    OUT.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps(dict(status=proof['status'], observed_records=len(records), runs=8,
                         calendar_mutants_rejected=len(mutants))))


if __name__ == '__main__':
    main()
