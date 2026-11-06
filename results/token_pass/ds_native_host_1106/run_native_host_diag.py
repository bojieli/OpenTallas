from pathlib import Path
import subprocess,json,re,time,os
W=Path('/srv/opentallas-scratch2/claude/codex-ds-native-host-1106');R=W/'diag';R.mkdir(exist_ok=False);assert (W/'top_link.rc').read_text().strip()=='0'
H=Path('/srv/opentallas-scratch2/claude/tok-ds-2/v1stim/job0_s5.memh');cmd=['/usr/bin/stdbuf','-oL','-eL','/usr/bin/time','-v','-o',str(R/'time.txt'),str(W/'Vtb_s81_die'),'+NCYC=11000','+HOSTIN='+str(H),'+HOSTN=2875','+HOST_T0=16','+HOST_AFTER_ALIVE=1','+NATIVE_HOST_LINK'];(R/'command.json').write_text(json.dumps(cmd,indent=2)+'\n');t=time.time()
with (R/'run.log').open('w') as f:q=subprocess.run(cmd,cwd=R,stdout=f,stderr=subprocess.STDOUT)
s=(R/'run.log').read_text(errors='replace');ks=re.findall(r'^NATIVE_KS_RECEIVED (\d+) word ([0-9a-f]+) peer_fault ([0-9a-f]+)',s,re.M);vo=re.findall(r'^PROG VO ([NS]) (\d+) ([0-9a-f]+)',s,re.M)
def events(tag):return [tuple(map(int,x)) for x in re.findall(r'^'+tag+r' index=(\d+) ordinal=(\d+) edge=(\d+) word=',s,re.M)]
a,b,c=events('NATIVE_HOST_ENQUEUE'),events('NATIVE_HOST_LEP_RX'),events('NATIVE_HOST_SEQ_RX');alive=re.findall(r'^NATIVE_HOST_REMOTE_ALIVE edge=(\d+) base=(\d+) status=([0-9a-f]+)',s,re.M);stop=re.findall(r'^NATIVE_FIRST_DISPATCH_STOP first=(\d+) finish=(\d+)',s,re.M);faults=re.findall(r'^.*(?:FAULT|%Error|THOST.*fault 1).*$' ,s,re.M)
profile=[];order_match=True
if len(a)==len(b)==len(c):
 for av,bv,cv in zip(a,b,c):
  if not av[:2]==bv[:2]==cv[:2]:order_match=False;break
  profile.append(dict(index=av[0],ordinal=av[1],queue=av[2],lep=bv[2],seq=cv[2],queue_to_lep=bv[2]-av[2],lep_to_seq=cv[2]-bv[2]))
exp=(1<<52)|(37<<42)|(1000<<21)|5000
ok=q.returncode==0 and 'NATIVE_KS_PERIOD_FS 833000' in s and len(ks)==1 and int(ks[0][1],16)==exp and int(ks[0][2],16)==0 and bool(vo) and bool(alive) and len(a)==len(b)==len(c)==575 and order_match
out=dict(scope='Frozen11-01 receipt-selected LP cohort: actual native HOST programme and KS pads to first dispatch',current_main=False,token_pass=False,physical_release_adopted=False,rtl_changed=True,pin_cycles_added=0,cycles_budget=11000,runtime_rc=q.returncode,elapsed_s=round(time.time()-t,2),native_clock_833ps='NATIVE_KS_PERIOD_FS 833000' in s,host_forced=False,ks_forced=False,host_order_matches=order_match,host_count=dict(queued=len(a),LEP=len(b),SEQ=len(c)),remote_alive=alive,received_KS=ks,first_dispatch=vo[:1],first_dispatch_stop=stop,first_dispatch_verdict='PASS' if ok else 'FAIL',die_summary=re.findall(r'^TB_S81_DIE (?:SUMMARY|PASS|FAIL).*$',s,re.M),fault_details=faults)
(R/'result.json').write_text(json.dumps(out,indent=2)+'\n');(R/'transport_profile.json').write_text(json.dumps(profile,indent=2)+'\n');print(json.dumps(out),flush=True);raise SystemExit(0 if ok else 1)
