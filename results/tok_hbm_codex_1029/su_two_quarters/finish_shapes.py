"""Resolve only the measured two-quarter store failures and price emitted spans."""
from pathlib import Path
from types import SimpleNamespace
import contextlib,io,json,sys
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
sys.path[:0]=[str(root/'tools/hbm_static'),str(root/'tools/hbm_static/toksim_su/suvop')]
import prod_compile as C
import su_native_vm_calendar as CAL
from su_two_quarter_phases import plan
result={'scope':'actual two-quarter static compiler components; no native arithmetic/whole-programme adoption',
 'clock_ps':833,'profiles':{},'remaining_native_obligations':['actual input/output publication and reload between phases','actual NW/NE interquarter RF paths','current native source/canonical FP profile and bank-frontdoor selection']}
for profile,mlat,alat,wcopy in [('minimal4_4_0',4,4,0),('alternate5_4_1',5,4,1)]:
 d=out/profile;C.MLAT,C.ALAT,C.WCOPY=mlat,alat,wcopy
 a=SimpleNamespace(out=str(d/'qw_bf16_p'),rec='qw_bf16_p',quarters=2,pin_reg=1,full_side=True,
  rr=25,wr=22,fill_slack=1,drain_slack=2,side_ii=0,rfd_slack=1,pretree=True,qpr=1)
 with contextlib.redirect_stdout(io.StringIO()):C.compile_rec(a)
 man=json.loads((d/'qw_bf16_p/programme.json').read_text())
 native=[int(x,16) for x in (d/'qw_bf16_p/native_prog.mem').read_text().split()]
 slots,meta=CAL.compile_calendar(native,2,[2,3],2470)
 assert all((x&0xffff)==0 and ((x>>32)&0xffff)==0 for x in slots),'inactive SW/SE slots claimed'
 for row in (d/'qw_bf16_p/expw.mem').read_text().split():assert int(row[8],16) in(2,3),'wrong physical QID'
 controls=[]
 for qids,width in [([0,1],2470),([2,2],2470),([2,3],2422)]:
  try:bad,_=CAL.compile_calendar(native,2,qids,width)
  except ValueError:controls.append(dict(qids=qids,width=width,verdict='CAUGHT'))
  else:
   assert bad!=slots,'wrong producer shape survived'
   controls.append(dict(qids=qids,width=width,verdict='DIFFERENT_CONTROL_TRACE'))
 phases=[]
 for rec in ['qw_softmax_exp_sum_r2','qw_softmax_exp_sum_r3','qw_softmax_exp_sum_r4']:
  r=plan(rec,d/rec,mlat,alat,wcopy)
  assert sum(p['rows'] for p in r['phases'])==r['rows']
  assert all(p['golden'] and 'PASS' in p['golden'] for p in r['phases'])
  phases.append({k:r[k] for k in ['record','rows','component_service_edges','retained_component_edges','added_publication_or_reload_edges','installable']}|{'phase_rows':[p['rows'] for p in r['phases']]})
 result['profiles'][profile]=dict(bf16_full512rows=dict(emitted_edges=man['edges'],dispatch_service_edges=man['cycles_serial'],
  output_words=65536,expected_sector_writes=man['expected_vm_writes'],native_bits=man['native_programme_bits'],selectors=meta),
  physical_identity_controls=controls,softmax_phases=phases)
 (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 print(profile,json.dumps(result['profiles'][profile]),flush=True)
print('FINITE_SHAPES_DONE',flush=True)
