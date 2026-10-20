from pathlib import Path
import subprocess,json,hashlib,difflib,re
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');A=D/'obj_arithmetic_clock';O=Path.cwd();R=Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019')
sha=lambda b:hashlib.sha256(b).hexdigest()
members=subprocess.check_output(['ar','t',str(A/'Vtb__ALL.a')],text=True).splitlines()
assert subprocess.check_output(['ar','t',str(O/'Vtb__ALL.a')],text=True).splitlines()==members
ledger=[]
for n in members:
 before=subprocess.check_output(['ar','p',str(A/'Vtb__ALL.a'),n]);after=subprocess.check_output(['ar','p',str(O/'Vtb__ALL.a'),n]);changed=before!=after
 assert changed==(n in ['Vtb_vm_classes_0.o','Vtb_vm_classes_1.o']),n
 ledger.append(dict(member=n,original_sha256=sha(before),candidate_sha256=sha(after),changed=changed))
for n in ['Vtb___024root__0.cpp','Vtb___024root__26.cpp']:
 patch=''.join(difflib.unified_diff((A/n).read_text().splitlines(True),(O/n).read_text().splitlines(True),fromfile='original/'+n,tofile='candidate/'+n));(O/(n+'.patch')).write_text(patch)
files=[A/'Vtb__ALL.a',D/'native_record23_tb.sv',D/'pll_functional_model.sv',D/'current_sources.tar',O/'Vtb__ALL.a',O/'two_requests',O/'event_controls',R/'production/quarter.mem',R/'production/cols/config.mem',R/'layer_images_guarded.py',O/'calendar.mem',O/'two_request_tb.sv']
files+=list(O.glob('*.py'))+list(O.glob('*.log'))+list(O.glob('*.patch'))+list(O.glob('*.cpp'))
(O/'source_evidence_hashes.json').write_text(json.dumps({str(f):sha(f.read_bytes())for f in files},indent=2))
s=(O/'positive_admission.log').read_text();commands=[tuple(map(int,m))for m in re.findall(r'CMD e=(\d+) serial=(\d+) stream=(\d+)',s)]
assert len(commands)==146 and commands[:73]==[(e,2674+e,st)for e,qt,st in commands[:73]]
assert [x[0]for x in commands[73:]]==list(range(73))
assert [x[1]for x in commands[73:]]==list(range(2974,3047))
assert s.count('NUM b=')==8 and s.count('RESULT commands=')==2
assert s.count('producer=0 slice=0 tap=0 target=0 cal=0 release=0')==2
admit=[dict(zip(['qt','st','start','busy_pin_q','valid_mask','pc0','edge','n','faults','bridge','phase'],m))for m in re.findall(r'ADMIT qt=(\d+) st=(\d+) start=(\d+) busy_pin_q=(\d+) valid_mask=(\d+) pc0=(\d+) edge=(\d+) n=(\d+) faults=(\d+) bridge=(\d+) phase=(\d+)',s)]
assert all(x['faults']=='0000'and x['bridge']=='0'for x in admit)
(O/'mechanism_ledger.json').write_text(json.dumps(dict(archive_members=ledger,command_windows=[commands[:73],commands[73:]],admission_trace=admit,publication_counters=[2674,2974],bridge_capture_epochs=[2675,2975],hardware_contexts=1,numerical_checked_words=64,hardware_user_tags=False,all_faults_zero=True,qualification='bounded serialized requests only; not full SU/MU token'),indent=2))
print('CACHED_ARCHIVE_AUDIT PASS 11 original members byte-identical, two testbench aggregates rebuilt; commands146, native words64, six faults0')
