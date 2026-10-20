import pathlib,sys,json,copy
sys.path.insert(0,str(pathlib.Path.cwd()))
from forward_clock_guard import validate_native_forwarding
D=pathlib.Path('evidence');rows=[]
for variant in ['buf','inv','chain','defaultbuf','defaultinv']:
 p=D/variant/'export35e931766'
 if variant.startswith('default'):continue # different scalar contract intentionally not admitted to ck:ck_o consumer
 for c in ['ss','ff','tt']:
  lib=(p/f'fc_coupon_{c}.lib').read_text()
  read=lambda name: (p/name).read_text() if (p/name).exists() else None
  assert validate_native_forwarding('fc_coupon',c,lib,read)
  rows.append([variant,c,'PASS'])
p=D/'inv/export35e931766';lib=(p/'fc_coupon_tt.lib').read_text();a={f.name:f.read_text() for f in p.iterdir() if f.is_file()}
def reject(label,mutate):
 files=copy.deepcopy(a);text=mutate(files,lib)
 try:validate_native_forwarding('fc_coupon','tt',text,files.get)
 except (ValueError,KeyError,TypeError):rows.append([label,'EXPECTED_REJECT']);return
 raise AssertionError(label)
reject('missing_metadata',lambda f,s:(f.pop('forwarded_clock.json'),s)[1])
reject('missing_native_raw',lambda f,s:(f.pop('forwarded_tt.lib.raw'),s)[1])
reject('source_raw_changed',lambda f,s:(f.__setitem__('sequential_tt.lib.raw',f['sequential_tt.lib.raw']+' '),s)[1])
reject('lib_relation_relabel',lambda f,s:s.replace('related_pin : "ck"','related_pin : "ck_o"'))
def phase(f,s):
 r=json.loads(f['forwarded_clock.json']);r['corners']['tt']['output_rise_input_edge']='rise';f['forwarded_clock.json']=json.dumps(r);a=json.loads(f['abstract.json']);a['forwarded_clock']=r['corners'];f['abstract.json']=json.dumps(a);return s
reject('phase_metadata_changed',phase)
reject('source_tcl_changed',lambda f,s:(f.__setitem__('export_tt.tcl',f['export_tt.tcl']+' '),s)[1])
# Historical actual bound SELF view has no native receipts: must fail before admission.
s=(D/'legacy/dsfd_dvrlyh_276_EW.lib').read_text()
try:validate_native_forwarding('dsfd_dvrlyh_276_EW','tt',s,lambda _:None)
except ValueError:rows.append(['actual_frozen_SELF','EXPECTED_REJECT'])
else:raise AssertionError('actual frozen SELF admitted')
print(json.dumps(rows));pathlib.Path('guard_results.json').write_text(json.dumps(rows,indent=2))
