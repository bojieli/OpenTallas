#!/usr/bin/env python3
"""Minimal in-place upgrade of current fleet helpers; preserve admission arithmetic.
OOMADJ_999_1022: die protection is -999, never -1000 (memcg OOM livelock at the cap); run install_oomadj_999.py after this.
Run as root ON host with ot-protect-die alongside this installer. Never stops jobs.
"""
import hashlib, json, os, shutil, subprocess, sys, time
from pathlib import Path
MARK='DIE_WATCHDOG_1021'
def patch_heavy(s):
    if MARK in s:
        return s.replace('if /usr/local/bin/ot-heavy-reconcile --is-die -- "$@"; then',
                         'if /usr/local/bin/ot-heavy-reconcile --is-die -- "$@" || /usr/local/bin/ot-protect-die --is-die -- "$@"; then')
    anchor='LASTRES=""\n'
    if s.count(anchor)!=1: raise ValueError('unknown ot-heavy launch layout')
    s=s.replace(anchor, anchor+'# '+MARK+': use the admission classifier for both priority and hard protection.\nif /usr/local/bin/ot-heavy-reconcile --is-die -- "$@" || /usr/local/bin/ot-protect-die --is-die -- "$@"; then export OT_HEAVY_PRIO=die; fi\n')
    anchor='    exec systemd-run --user --scope'
    if s.count(anchor)!=1: raise ValueError('unknown scope launch')
    s=s.replace(anchor,'    # User scopes cannot set OOMScoreAdjust; set the launching PID as root, then inherit.\n    if [ "${OT_HEAVY_PRIO:-}" = die ]; then\n      sudo -n /usr/local/bin/ot-protect-die --pid "$$" || { echo "ot-heavy: NOT RUN: die protection failed" >&2; exit 70; }\n    fi\n'+anchor)
    return s

def patch_reconcile(s):
    if MARK in s: return s
    anchor='if __name__ == "__main__":\n'
    if s.count(anchor)!=1 or 'def die_like(' not in s: raise ValueError('unknown reconciler layout')
    return s.replace(anchor,anchor+'    # '+MARK+': classifier query only; no reconciliation or admission changes.\n    if sys.argv[1:2] == ["--is-die"]:\n        sys.exit(0 if os.environ.get("OT_HEAVY_PRIO") == "die" or die_like(sys.argv[3:], os.getcwd()) else 1)\n')

def patch_docker(s):
    if MARK in s: return s
    anchor='    --memory=*)'
    if s.count(anchor)!=1: raise ValueError('unknown docker option parser')
    s=s.replace(anchor,'    --oom-score-adj=*) if [ "${OT_HEAVY_PRIO:-}" != die ]; then out+=("$a"); fi;;\n    --oom-score-adj) if [ "${OT_HEAVY_PRIO:-}" != die ]; then out+=("$a" "${rest[$((j+1))]}"); fi; j=$((j+1));;\n'+anchor)
    anchor='exec "$REAL" "${pre[@]}" "--memory-swap=$lim" "${out[@]}"'
    if s.count(anchor)!=1: raise ValueError('unknown docker exec')
    return s.replace(anchor,'# '+MARK+': Docker daemon starts outside the caller scope; explicitly inherit die immunity.\nif [ "${OT_HEAVY_PRIO:-}" = die ]; then out=("--oom-score-adj=-999" "--label=opentallas.priority=die" "${out[@]}"); fi\n'+anchor)

def main():
    if os.geteuid()!=0: raise SystemExit('root required')
    stamp=time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()); backup=Path('/var/tmp/ot-heavy/die-protection-backup-'+stamp); backup.mkdir(parents=True)
    plans=[('/usr/local/bin/ot-heavy',patch_heavy),('/usr/local/bin/ot-heavy-reconcile',patch_reconcile),('/usr/local/lib/ot-heavy/bin/docker',patch_docker)]
    changes=[]
    # Validate every patch before mutating any helper.
    for filename,fn in plans:
        p=Path(filename); before=p.read_text(); after=fn(before); changes.append((p,before,after))
    protector=Path(__file__).with_name('ot-protect-die')
    shutil.copy2(protector,'/usr/local/bin/ot-protect-die'); os.chmod('/usr/local/bin/ot-protect-die',0o755)
    proof=[]
    for p,before,after in changes:
        (backup/p.name).write_text(before)
        temp=p.with_name(p.name+'.die-new'); temp.write_text(after); os.chmod(temp,0o755)
        if p.name=='ot-heavy-reconcile': compile(after,str(p),'exec')
        else: subprocess.run(['bash','-n',str(temp)],check=True)
        os.replace(temp,p)
        proof.append(dict(path=str(p),before=hashlib.sha256(before.encode()).hexdigest(),after=hashlib.sha256(after.encode()).hexdigest()))
    service=Path('/etc/systemd/system/ot-die-protection.service')
    service.write_text('[Unit]\nDescription=Preserve die job OOM immunity\nAfter=docker.service\n[Service]\nType=simple\nExecStart=/usr/local/bin/ot-protect-die --apply --watch\nRestart=on-failure\nRestartSec=5\nOOMScoreAdjust=-999\n[Install]\nWantedBy=multi-user.target\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','enable','--now','ot-die-protection.service'],check=True)
    subprocess.run(['/usr/local/bin/ot-protect-die','--apply'],check=True)
    print(json.dumps(dict(host=os.uname().nodename,backup=str(backup),helpers=proof),sort_keys=True))
if __name__=='__main__': main()
