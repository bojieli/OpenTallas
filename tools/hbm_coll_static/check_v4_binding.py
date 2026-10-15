#!/usr/bin/env python3
"""Complete reviewed V3->V4 parent/host/ISA delta and all-input capture binding."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'rtl/hbm_accel/generic/collective/p2p'
def norm(s):
 s=re.sub(r'//[^\n]*','',s);s=re.sub(r'/\*.*?\*/','',s,flags=re.S)
 return re.sub(r'\s+','',s)
def check():
 old=(P/'ot_hfd_coll_q_static_v3.sv').read_text()
 new=(P/'ot_hfd_coll_q_static_v4.sv').read_text()
 expected=old.replace('static_v3','static_v4').replace('ctl_v3','ctl_v4').replace('ot_hgi_coll_static_link_pinreg u_link','ot_hgi_coll_static_link_capture u_link')
 assert norm(new)==norm(expected),'unreviewed V4 parent mechanism delta'
 for q in (2,3):
  a=(P/f'ot_hfd_coll_q{q}_static_host_v3.sv').read_text()
  b=(P/f'ot_hfd_coll_q{q}_static_host_v4.sv').read_text()
  assert norm(b)==norm(a.replace('static_v3','static_v4').replace('host_v3','host_v4'))
 a=json.loads((P/'static_uop_layout_v3.json').read_text());b=json.loads((P/'static_uop_layout_v4.json').read_text())
 for k in ('fields','ar_fields','ring_fields'):assert a[k]==b[k]
 assert b['link_contract']['reservation_read_to_tx_pin_edges']==6
 assert b['link_contract']['rx_pin_to_rx_publication_edges']==2
 cap=(P/'ot_hgi_coll_static_capture_ctl.sv').read_text()
 for pin in ('epoch_begin','epoch','wr_v','wr_observed_v','wr_seq','wr_flit','rd_v','rd_seq','rx_expect_v','rx_expect_seq','phy_up','rx_pin_v','rx_pin_flit'):
  assert f'.{pin}({pin}_pin)' in cap, f'{pin} bypasses capture'
  assert re.search(r'\b'+pin+'_pin\s*<=\s*'+pin+r'\s*;',cap), f'{pin} lacks first register'
 names=['ot_hfd_coll_q_static_v4.sv','ot_hfd_coll_q2_static_host_v4.sv','ot_hfd_coll_q3_static_host_v4.sv','ot_hgi_coll_static_link_capture.sv','ot_hgi_coll_static_capture_ctl.sv','ot_hgi_coll_static_pinreg_ctl.sv','ot_hgi_coll_static_pinreg_store.sv','ot_hgi_coll_static_seq_ctl.sv','ot_hgi_coll_static_program_target.sv']
 return {'status':'PASS','allowed_delta':['versioned names','all-input-capture TX6/RX2 child'],
 'source_sha256':{n:hashlib.sha256((P/n).read_bytes()).hexdigest() for n in names},
 'scope':'Complete normalized parent/host delta, unchanged ISA positions, actual endpoint capture wiring; runtime/physical qualifications separate'}
if __name__=='__main__':print(json.dumps(check(),indent=2))
