import os,signal,json,time
from pathlib import Path
pid=1342245;root='/srv/opentallas-scratch2/claude/codex-recip-native-fp-0640';p=Path('/proc')
def argv(n):
 try:return (p/str(n)/'cmdline').read_bytes().split(b'\0')[:-1]
 except FileNotFoundError:return []
a=argv(pid);assert b'/usr/local/bin/ot-heavy' in a and root.encode()+b'/run_fp.sh' in a,a
fd=os.pidfd_open(pid);signal.pidfd_send_signal(fd,signal.SIGSTOP)
# Frozen gate controller cannot dispatch. Check no physical step has started.
base=Path(root)/'kit/run/results/asap7/hc_ot_qkh_recip_leaf__216x216/base';assert not list(base.glob('2_*.odb'))
children=[]
for d in p.iterdir():
 if not d.name.isdigit():continue
 try:
  pp=int((d/'stat').read_text().split(') ',1)[1].split()[1])
 except (FileNotFoundError,ProcessLookupError):continue
 if pp==pid:children.append(int(d.name))
# Only the explicitly frozen own waiter is cancelled; normal trap owns its children.
signal.pidfd_send_signal(fd,signal.SIGTERM);signal.pidfd_send_signal(fd,signal.SIGCONT);os.close(fd)
print(json.dumps({'cancelled_exact_waiter':pid,'owned_gate_children_at_stop':children,'stage2_outputs_before_cancel':0,'source':root,'reason':'Intel1 normal invariant blocked; Intel2 identical capsule/image admits4GB; no progressing CAD interrupted'}))
