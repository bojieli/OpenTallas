#!/usr/bin/env python3
"""Check the complete V2->V3 source delta and real issuer feedback wiring."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/hbm_accel/generic/collective/p2p'
def norm(s):
 s=re.sub(r'//[^\n]*','',s);s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
 return re.sub(r'\s+','',s)
def check():
 old=(P/'ot_hfd_coll_q_static_v2.sv').read_text()
 new=(P/'ot_hfd_coll_q_static_v3.sv').read_text()
 expected=old.replace('static_v2','static_v3').replace('ctl_v2','ctl_v3')
 expected=expected.replace('ot_hgi_coll_static_link_seq u_link','ot_hgi_coll_static_link_pinreg u_link')
 expected=expected.replace(' output wire hgi_fault,',' output wire hgi_fault,\n output wire issuer_busy,issuer_fault,issuer_uop_v,\n output wire [5:0] issuer_uop_pc,')
 expected=expected.replace(' wire [5:0] uop_pc;',''' wire [5:0] uop_pc;
 assign issuer_busy=hgi_busy;
 assign issuer_fault=issue_fault;
 assign issuer_uop_v=uop_v;
 assign issuer_uop_pc=uop_pc;''')
 assert norm(expected)==norm(new),'V3 contains an unreviewed mechanism change beyond registered endpoint/issuer feedback'
 for name in ['ot_hfd_coll_q_static_v3','ot_hfd_coll_q3_static_v3','ot_hfd_coll_q2_static_v3','ot_hgi_coll_q_static_ctl_v3']:
  assert 'module '+name in new
 assert 'ot_hgi_coll_static_link_pinreg u_link' in new
 assert 'ot_hgi_coll_static_link_seq u_link' not in new
 layout=json.loads((P/'static_uop_layout_v3.json').read_text())
 oldlayout=json.loads((P/'static_uop_layout_v2.json').read_text())
 for field in ['fields','ar_fields','ring_fields']:assert layout[field]==oldlayout[field]
 return {'status':'PASS','allowed_delta':['new versioned module names','actual pinregistered TX5/RX1 endpoint child','nine direct actual issuer feedback bits'],
  'parent_sha256':hashlib.sha256(new.encode()).hexdigest(),
  'endpoint_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in ['ot_hgi_coll_static_link_pinreg.sv','ot_hgi_coll_static_pinreg_ctl.sv','ot_hgi_coll_static_pinreg_store.sv','ot_hgi_coll_static_seq_ctl.sv']},
  'scope':'complete RTL textual mechanism delta plus unchanged ISA field map; no new fullq3 runtime/physical qualification'}
if __name__=='__main__':print(json.dumps(check(),indent=2))
