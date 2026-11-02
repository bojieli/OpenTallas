import pathlib,re,subprocess,time,json
root=pathlib.Path('/srv/opentallas-scratch/claude/qc-l1-lvt-actual-1101')
log=root/'route2.otrun.log'
while True:
 text=log.read_text() if log.exists() else ''
 found=re.search(r'ot-run: RAN on epyc2 .*: exit (\d+)',text)
 if found:break
 if 'NOT RUN:' in text or 'NOT COMPLETED:' in text:
  (root/'signoff_follow_status.json').write_text(json.dumps({'status':'HOLD_FRONTDOOR_NOT_COMPLETED','source_log':str(log)})+'\n');raise SystemExit(1)
 time.sleep(10)
if int(found[1]):
 (root/'signoff_follow_status.json').write_text(json.dumps({'status':'HOLD_ROUTE_FAILED','route_exit':int(found[1])})+'\n');raise SystemExit(1)
cmd=['/home/ubuntu/.local/bin/ot-run','--mem','32','--threads','4','--disk','2','--crit','--hosts','epyc2','--dir','/srv/opentallas-scratch2/claude/codex-qc-l1-lvt-route2-0015','--','bash','./run_signoff.sh']
(root/'signoff_follow_status.json').write_text(json.dumps({'status':'SUBMITTED_RELEASED_P_QC_DIAGNOSTIC','cmd':cmd})+'\n')
with (root/'signoff.otrun.log').open('w') as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
(root/'signoff_follow_status.json').write_text(json.dumps({'status':'TERMINAL','frontdoor_exit':r.returncode,'auto_publication':False})+'\n')
raise SystemExit(r.returncode)
