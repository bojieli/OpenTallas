#!/usr/bin/env python3
from pathlib import Path
import hashlib,json,re
R=Path(__file__).resolve().parent
m=json.loads((R/'build/retained_build_manifest.json').read_text())
s=json.loads((R/'source/source_identity.json').read_text())
v=json.loads((R/'source/verified_source_and_inputs.json').read_text())
assert m['objects']==1077 and len(m['files'])==17882 and not m['bad_objects'] and not m['source_mismatches']
assert len(s['files'])==v['source_files']==903 and not v['mismatches']
assert sum(k.endswith('.o') for k in m['files'])==1077
assert len(m['tools'])==7
scope=(R/'raw/unit_scope.txt').read_text();kernel=(R/'raw/kernel_oom.txt').read_text()
assert 'Result=oom-kill' in scope and 'MemoryPeak=103079215104' in scope and 'RuntimeMaxUSec=infinity' in scope
assert 'CONSTRAINT_MEMCG' in kernel and 'oth-ubuntu-1628119-1792642813.scope' in kernel and 'anon-rss:17634580kB' in kernel
plan=json.loads((R/'build/make_only_plan.json').read_text())
assert plan['remaining_compile_commands']==11 and not plan['frontend_commands'] and len(plan['link_commands'])==1
cmd=json.loads((R/'continuation/continue.command.json').read_text())
assert cmd[cmd.index('--mem')+1]=='192' and cmd[cmd.index('--threads')+1]=='2' and '--hosts' not in cmd
admit=(R/'continuation/continue.otrun.log').read_text()
assert 'admitted on ot-epyc9 as oth-ubuntu-2001896-1792648140' in admit
runner=(R/'continuation/run_b_continue.sh').read_text()
assert 'make -C "$O/obj_b" -f Vtb_s81hd_diecut.mk -j2' in runner and '--build-jobs 2' in runner
assert 'head_cut_report.py' in runner and 'b_mut_rec.log' in runner and 'b_mut_slice.log' in runner
assert 'ot_s81_kp4_dec' in (R/'raw/preflight_missing_autoload/build_b.log').read_text()
receipt=dict(schema='opentallas.connected_cut_b.preservation_checkpoint.v1',status='INCOMPLETE',functional_pass=False,
 original_scope='oth-ubuntu-1628119-1792642813.scope',original_result='oom-kill',original_peak_bytes=103079215104,
 continuation_scope='oth-ubuntu-2001896-1792648140',continuation_host='ot-epyc9',continuation_client=2653861,
 source_files=903,retained_objects=1077,generated_build_files=17882,estimated_memory_GiB=192,compiler_jobs=2,
 qualification='Infrastructure preservation and admitted exact-object continuation only; numerical verdicts pending',
 hashes={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ('raw','source','inputs','build','continuation') for p in sorted((R/folder).rglob('*')) if p.is_file()})
(R/'checkpoint.json').write_text(json.dumps(receipt,indent=2)+'\n')
print('PASS preservation checkpoint; CUT-B functional evidence remains INCOMPLETE')
