from pathlib import Path
import json,subprocess,hashlib,time
root=Path.cwd();raw=json.loads((root/'receipt.json').read_text());prefix=raw['args'][:raw['args'].index('--unread-review')]
records={}
for variant,tool in [('baseline','tools/die_port_bind_baseline.py'),('candidate','tools/die_port_bind.py')]:
    args=list(prefix);args[1]=tool;args+=['--out',f'default_{variant}.json'];t=time.time()
    with open(f'default_{variant}.log','w')as out:p=subprocess.run(args,stdout=out,stderr=subprocess.STDOUT)
    records[variant]=dict(rc=p.returncode,elapsed_s=time.time()-t,tool_sha256=hashlib.sha256(Path(tool).read_bytes()).hexdigest())
old=json.loads((root/'diagnostic.json').read_text());current=json.loads((root/'candidate.json').read_text())
shared={k:current['summary'][k] for k in old['summary']}
added={k:v for k,v in current['summary'].items() if k not in old['summary']}
byte_identical=(root/'default_baseline.json').read_bytes()==(root/'default_candidate.json').read_bytes()
default=json.loads((root/'default_candidate.json').read_text())
passed=byte_identical and all(r['rc']==1 for r in records.values()) and shared==old['summary'] and all(v==0 for v in added.values()) and current['summary']['unread_net_bits']==5254 and default['summary']['unread_net_bits']==70320
proof=dict(default_records=records,default_report_byte_identical=byte_identical,shared_summary_fields_identical=shared==old['summary'],additional_cli_structural_fields=added,default_unread=default['summary']['unread_net_bits'],reviewed_unread=current['reviewed_unread'],residual_unread=current['summary']['unread_net_bits'],child_modules=current['child_closure']['modules'],strict_original_command_rc=raw['returncode'],qualified_die=False,pass_=passed,note='Original worker diagnostic used check() directly; full CLI additionally reports child-closure zero counts. First strict harness comparison retained in receipt.json; this comparison explicitly accounts for those additional zero fields.')
(root/'comparison.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2));raise SystemExit(0 if passed else 1)
