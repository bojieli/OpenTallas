#!/usr/bin/env python3
"""Actual-packet integration checks without a die build or physical job."""
import copy
from dataclasses import dataclass
import gzip
import json
from pathlib import Path
import unittest
from capture_import import ROOT, DEFAULT_PACKET, expand

@dataclass
class Inst:
 name:str;master:str;x:float;y:float;w:float;h:float;orient:str='R0';kind:str='';region:str='';domain:str='stream_1p2'
 def d(self):return vars(self).copy()

class CaptureImport(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.packet=json.loads(gzip.decompress((ROOT/DEFAULT_PACKET).read_bytes()))
 def model(self,orient='R0'):
  parent=Inst('sp_capture','dsfd_sp_capture_c',100,200,1727.976,561.576,orient)
  ports={}
  for pin,p in self.packet['die_ports'].items():
   base=pin.split('[')[0];index=int(pin.split('[')[1][:-1]) if '[' in pin else 0
   ports.setdefault(base,[]).append((index,p['direction']))
  buses=[]
  for p,entries in ports.items():
   width=len(entries);ep=('sp_capture',p);other=('peer_'+p,'p')
   buses.append(('external_'+p,'test',width,[ep,other] if entries[0][1]=='output' else [other,ep]))
  return {'insts':[parent],'buses':buses,'hub':{'capture':parent}}
 def test_actual_packet_r0_my_and_peer_bits(self):
  for orient in ('R0','MY'):
   m=self.model(orient);before=copy.deepcopy(m);r=expand(m,packet=self.packet)
   self.assertEqual(r['counts']['children'],70);self.assertEqual(r['counts']['literal_clock_contacts'],86)
   self.assertEqual(len(m['insts']),70);self.assertEqual(m['hub']['capture'],before['hub']['capture'])
   json.dumps(r)  # import metadata remains serializable for committed GEN receipts
   self.assertNotIn('sp_capture',{i.name for i in m['insts']})
   peers=[ep for b in m['buses'] for ep in b[3] if ep[0].startswith('peer_')]
   self.assertEqual(len(peers),sum(b[2] for b in before['buses']))
   expected={(eps[1 if eps[0][0]=='sp_capture' else 0][0],f'p[{i}:{i}]' if width>1 else 'p') for _,_,width,eps in before['buses'] for i in range(width)}
   self.assertEqual(set(peers),expected)
   pin='g_t[0].u_x0.u_s';c=self.packet['children'][pin];it=next(i for i in m['insts'] if i.name==r['children'][pin])
   self.assertAlmostEqual(it.x,100+(1727.976-c['at_um'][0]-c['outline_um'][0] if orient=='MY' else c['at_um'][0]))
   self.assertTrue(all(i.orient==orient for i in m['insts']))
   drivers={}
   for bid,_,_,eps in m['buses']:
    for ep in eps:
     if ep[0].startswith('sp_capture__'):
      self.assertNotIn(ep,drivers,('leaf pin appears on multiple nets',ep))
      drivers[ep]=bid
 def test_shared_actual_clock_trunks(self):
  m=self.model()
  clock_buses=[b for b in m['buses'] if b[0].startswith('external_ck')]
  m['buses']=[b for b in m['buses'] if b not in clock_buses]
  expected={}
  for serial in (False,True):
   bid='clk_serial' if serial else 'clk_stream';eps=[('clock_source',bid)];count=0
   for b in clock_buses:
    parent=next(ep for ep in b[3] if ep[0]=='sp_capture')
    if parent[1].startswith('ckv')!=serial:continue
    for i in range(b[2]):
     ep=(parent[0],f'{parent[1]}[{i}:{i}]' if b[2]>1 else parent[1])
     eps.append(ep);count+=1
   m['buses'].append((bid,'clock',1,eps));expected[bid]=count
  before_reset={b[0] for b in m['buses'] if b[0] in ('external_rst','external_rsv')}
  r=expand(m,packet=self.packet)
  self.assertEqual(r['counts']['literal_clock_contacts'],86)
  actual={b[0]:b for b in m['buses'] if b[0] in expected}
  self.assertEqual(set(actual),set(expected))
  contacts=[]
  for bid,b in actual.items():
   self.assertEqual(b[2],1);self.assertEqual(b[3][0],('clock_source',bid))
   contacts.extend(ep for ep in b[3] if ep[0].startswith('sp_capture__'))
  self.assertEqual(len(contacts),86);self.assertEqual(len(set(contacts)),86)
  self.assertEqual(sum(ep[1]=='ckvb[0:0]' for ep in contacts),16)
  self.assertTrue(before_reset.issubset({b[0] for b in m['buses']}))
  self.assertFalse(any(n=='sp_capture' for b in m['buses'] for n,p in b[3]))
 def test_shared_data_endpoints_refused(self):
  m=self.model();b=next(b for b in m['buses'] if b[0]=='external_t_cd')
  b[3].append(('sp_capture','t_vm[0:11]'));before=copy.deepcopy(m)
  with self.assertRaisesRegex(ValueError,'multiple capture data'):expand(m,packet=self.packet)
  self.assertEqual(m,before)
 def test_unknown_port_atomic_refusal(self):
  m=self.model();m['buses'].append(('bad','test',1,[('peer','p'),('sp_capture','unknown')]))
  before=copy.deepcopy(m)
  with self.assertRaisesRegex(ValueError,'unknown capture'):expand(m,packet=self.packet)
  self.assertEqual(m,before)
 def test_missing_external_bit_atomic_refusal(self):
  m=self.model();m['buses']=[b for b in m['buses'] if b[0]!='external_t_cd'];before=copy.deepcopy(m)
  with self.assertRaisesRegex(ValueError,'unbound capture'):expand(m,packet=self.packet)
  self.assertEqual(m,before)
 def test_bad_hash_and_orientation_refused(self):
  bad=copy.deepcopy(self.packet);key=next(iter(bad['source_sha256']));bad['source_sha256'][key]='0'*64
  with self.assertRaisesRegex(ValueError,'hash mismatch'):expand(self.model(),packet=bad)
  with self.assertRaisesRegex(ValueError,'orientation'):expand(self.model('MX'),packet=self.packet)
 def test_partial_peer_offset(self):
  m=self.model();b=next(b for b in m['buses'] if b[0]=='external_t_cd');b[3].append(('tap','q[8:10]@2'))
  expand(m,packet=self.packet)
  actual=[(bid,ep) for bid,_,_,eps in m['buses'] for ep in eps if ep[0]=='tap']
  self.assertEqual(actual,[(f'external_t_cd__captbit{i}',('tap',f'q[{i+6}:{i+6}]')) for i in (2,3,4)])

if __name__=='__main__':unittest.main()

def test_nonzero_local_orientation_and_inserted_stage_refused():
 import pytest
 from capture_import import validate_native_connectivity
 CaptureImport.setUpClass();fixture=CaptureImport()
 bad=copy.deepcopy(fixture.packet);next(iter(bad['children'].values()))['orient']='MY'
 m=fixture.model();before=copy.deepcopy(m)
 with pytest.raises(ValueError,match='local orientation'):expand(m,packet=bad)
 assert m==before
 m=fixture.model();expand(m,packet=fixture.packet);validate_native_connectivity(m)
 bus=next(b for b in m['buses'] if b[1]=='capture_internal')
 original=list(bus[3]);bus[3][1]=('unpriced_stage','d')
 m['buses'].append(('unpriced_stage_out','capture_internal',1,[('unpriced_stage','q'),original[1]]))
 with pytest.raises(ValueError,match='fixed-cycle edge retimed'):validate_native_connectivity(m)
