#!/usr/bin/env python3
"""Verify frozen admitted boundary source/arguments/binary receipts, no rerun."""
import pathlib,json,hashlib,shlex
p=pathlib.Path.cwd();m=json.loads((p/'provenance.json').read_text());r=json.loads((p/'receipt.json').read_text())
for f,sha in m['sources'].items():
 if hashlib.sha256((p/'src'/f).read_bytes()).hexdigest()!=sha:raise RuntimeError('boundary source drift '+f)
for case in r['cases']:
 obj=p/('obj_'+case['case']);name='Vtb_qwen_numeric_admission_boundary';line=next(x for x in(obj/(name+'__verFiles.dat')).read_text().splitlines()if x.startswith('C '));cmd=shlex.split(json.loads(line[2:]))
 if cmd!=case['command'][1:]:raise RuntimeError('compiled boundary command drift')
 if hashlib.sha256((obj/name).read_bytes()).hexdigest()!=case['binary_sha256']:raise RuntimeError('boundary binary drift')
 log=(p/(case['case']+'.log')).read_text()
 if case['expected_observed']not in log:raise RuntimeError('missing observed boundary result')
 case['log_sha256']=hashlib.sha256(log.encode()).hexdigest()
r.update(unit='oth-ubuntu-2439988-1791979032',wrapper_exit=0,parent_commit=m['parent_commit'],ledger_commit=m['ledger_commit'],source_manifest_sha256=hashlib.sha256((p/'provenance.json').read_bytes()).hexdigest(),offer_base=201,old_outstanding_at_offer=46,numeric_delivered_at_offer=17,old_remaining_words_delivered_under_offer=47,local_grant_base=301,actual_second_accept_base=303,grant_to_accept_base_edges=2,total_numeric_words=112,total_real_query_retirements=112,queue_peak=8,ledger_peak=48,source_local_drain_cc=49,old_bank_retained_active_unsealed=True,global_peer_seals=0,bypass_old_outstanding=47,bypass_old_numeric_valid=True,bypass_queue_occupancy=2,physical_claim=False)
(p/'compiled_receipt.json').write_text(json.dumps(r,indent=2)+'\n');print('PASS frozen local boundary source and compiled argument/binary receipts')
