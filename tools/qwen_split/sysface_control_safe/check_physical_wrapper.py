#!/usr/bin/env python3
"""Independent source re-read proof of every paid boundary state equation.

Input families all sample the same external pin on the same edge, so equality
holds after one edge from arbitrary initial states. No zero-init premise. The
reference has input+1/output+1 and synchronous reset assertion/release+2.
Core sequential correspondence is separately checked by check_graph.py.
"""
import argparse,json
from pathlib import Path

def check(original,compiled,receipt):
 ports=original['modules']['qfd_sys_face']['ports'];assert receipt['public_ports']==ports
 mods=compiled['modules'];m=mods[receipt['public_top']];core=m['cells']['core']
 assert core['type']==receipt['core_top'] or mods[core['type']].get('attributes',{}).get('hdlname')==receipt['core_top']
 def bit(name,k=0):return m['netnames'][name]['bits'][k]
 expected=[];bindings={};copies=receipt['input_capture_copies']
 for name,p in ports.items():
  assert m['ports'][name]['direction']==p['direction']
  assert len(m['ports'][name]['bits'])==len(p['bits'])
  if name=='ck':bindings[name]=m['ports'][name]['bits'];continue
  w=len(p['bits']);face=[bit('face_'+name,k) for k in range(w)];bindings[name]=face
  if name=='rst_n':expected.extend([(bit('rst_n'),bit('face_reset_first')),(bit('face_reset_first'),face[0])])
  else:
   for k in range(w):
    a=m['ports'][name]['bits'][k];b=face[k]
    expected.append((a,b) if p['direction']=='input' else (b,a))
 for cp in copies:
  q=bit('capture_'+cp['port']);d=m['ports'][cp['original_port']]['bits'][cp['original_index']]
  expected.append((d,q));bindings[cp['port']]=[q]
 assert core['connections']==bindings,'core boundary sample binding changed'
 actual=[]
 for name,c in m['cells'].items():
  if name=='core':continue
  sub=mods[c['type']];prims=list(sub['cells'].values())
  assert len(prims)==1 and prims[0]['type']=='$_DFF_P_','unpriced boundary state or reset/enable change'
  p=prims[0];alias={b:c['connections'][pin][k] for pin,pp in sub['ports'].items() for k,b in enumerate(pp['bits'])}
  con={pin:[b if isinstance(b,str) else alias[b] for b in bb] for pin,bb in p['connections'].items()}
  assert con['C']==m['ports']['ck']['bits'] and set(con)=={'C','D','Q'}
  actual.append((con['D'][0],con['Q'][0]))
 assert sorted(actual)==sorted(expected),'lost, duplicated or changed paid boundary equation'
 return {'status':'PASS','all_public_bits':sum(len(p['bits']) for p in ports.values()),'boundary_ff':len(actual),'extra_same_edge_input_ff':len(copies),'input_cycles':1,'output_cycles':1,'reset_assert_release_cycles':2,'arbitrary_initial_input_copies_converge_edges':1,'zero_init_assumed':False,'qualification_precondition':'all input families converge before landed reset reaches core; core correspondence separately requires actual reset/first sampling contract','core_bindings':len(bindings)}
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('original');ap.add_argument('compiled');ap.add_argument('receipt');ap.add_argument('--out',required=True);a=ap.parse_args()
 r=check(*(json.loads(Path(x).read_text()) for x in [a.original,a.compiled,a.receipt]));Path(a.out).write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
