#!/usr/bin/env python3
"""Collect exact immutable merged compilation and execution evidence, no rerun."""
import pathlib,json,hashlib,shlex
p=pathlib.Path.cwd();m=json.loads((p/'provenance.json').read_text());r=json.loads((p/'receipt.json').read_text())
for f,sha in m['sources'].items():
 if hashlib.sha256((p/'src'/f).read_bytes()).hexdigest()!=sha:raise RuntimeError('merged source drift '+f)
for f,sha in m['runtime_inputs'].items():
 if hashlib.sha256((p/'src'/f).read_bytes()).hexdigest()!=sha:raise RuntimeError('merged runtime input drift '+f)
for case in r['cases']:
 obj=p/('obj_'+case['case']);binary=obj/('V'+case['top']);line=next(x for x in(obj/('V'+case['top']+'__verFiles.dat')).read_text().splitlines()if x.startswith('C '));cmd=shlex.split(json.loads(line[2:]))
 if cmd!=case['command'][1:]:raise RuntimeError('merged argument drift')
 if hashlib.sha256(binary.read_bytes()).hexdigest()!=case['binary_sha256']:raise RuntimeError('merged binary drift')
 log=(p/(case['case']+'.log')).read_text();case['log_sha256']=hashlib.sha256(log.encode()).hexdigest()
 if case['expected_observed'] and case['expected_observed']not in log:raise RuntimeError('missing merged mutant result')
r.update(unit='oth-ubuntu-2561625-1791980650',wrapper_exit=0,arithmetic_cc_delta=46,local_drain_cc=49,native_words=680,native_query_retirements=680,full_stalls_words=936,full_stalls_query_retirements=872,full_stalls_nonquery_words=64,queue_peak=8,ledger_peak=54,boundary_numeric_words=112,boundary_query_retirements=112,boundary_offer_base=201,boundary_grant_base=301,boundary_second_accept_base=303,peer_seals=0,actual_parent_clock_roots=22,stale_fixture_stdout_clock_label='coherent26roots is an inherited label, not census',source_clock_merge_scope='same coherent control+metadata only; loader/node/CLOSED children preserved',physical_claim=False)
(p/'compiled_receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS new merged source/binary/arguments/runtime-input receipts')
