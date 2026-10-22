import pathlib,subprocess,json,hashlib,re,sys,datetime,zoneinfo,shutil
r=pathlib.Path(__file__).resolve().parents[2];out=r/'results/arch/s81_hwin_private_package_1019'/sys.argv[1];out.mkdir()
base='/srv/opentallas-scratch/claude/s81-hwin-private-package-1019'; runs=json.loads(pathlib.Path('/home/ubuntu/artifacts/s81-hwin-private-package-1019/RUNS.json').read_text());records=[]
for x in runs:
 local=pathlib.Path(x['log']);txt=local.read_text();name=local.stem.removeprefix('s81-hwin-private-');dest=out/name;dest.mkdir();shutil.copyfile(local,dest/'admission.log');terminal=re.findall(r'RAN on .*exit (\d+)',txt)
 remote_name={'core02':'core02','core01':'core01'}.get(name,name)
 # Completed receipt objects only; object trees and executables never copied.
 p=subprocess.run(['rsync','-am','--exclude=obj*','--include=*/','--include=*.log','--include=*.json','--include=*.sha256','--include=*.txt','--include=*.sv','--include=*.diff','--exclude=*',f"{x['host']}:{base}/{remote_name}/",str(dest)+'/'],capture_output=True,text=True)
 if p.returncode: (dest/'collection_note.txt').write_text('Remote directory absent or partial: '+p.stderr)
 verdicts=[]
 for log in dest.rglob('run*.log'):
  text=log.read_text(errors='replace');passline=re.findall(r'^(?:MUWIN|EC_MEM|PRIMITIVE_PROBE|EARLY_MITER|EARLY_X_CAUSAL|EARLY_X).*',text,re.M)
  fatal=re.findall(r'^.*(?:FATAL|%Error|Aborting|Assertion failed).*',text,re.M)
  verdicts.append({'path':str(log.relative_to(out)),'has_PASS':bool(re.search(r'(?:MUWIN .*PASS|EC_MEM PASS)',text)),'causal_or_failure_lines':fatal[-4:],'scope_lines':passline[-4:],'may_be_live_partial':not terminal and not bool(re.search(r'(?:MUWIN .*PASS|EC_MEM PASS|FATAL|%Error)',text))})
 records.append({**x,'current_terminal_exit':terminal[-1] if terminal else None,'receipts':verdicts})
manifest={str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*') if p.is_file()}
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
(out/'summary.json').write_text(json.dumps({'at':datetime.datetime.now(zoneinfo.ZoneInfo('America/Los_Angeles')).isoformat(),'source':'06f8ca8dc','runs':records,'caution':'Live jobs are partial; terminal0 alone not wholephase qualification. Expected actualcausal FAIL logs retained. Default original source.sha list supplemented by frozen source_manifest defaultbench SHA; no altered benchmark.'},indent=2)+'\n')
print(out)
