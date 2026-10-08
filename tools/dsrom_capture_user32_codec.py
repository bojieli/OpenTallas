#!/usr/bin/env python3
"""Default-off user32 codec/state pricing; no RTL or context slot freebies."""
import argparse,json,hashlib,math
from pathlib import Path
import dsrom_capture_home_r49 as H
from dsrom_capture_publication_credit import FIELDS,identity
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_capture_user32_codec_20261002'
def source():
 p=json.loads((BASE/'inputs/origin.json').read_text());raw=(BASE/'inputs/fff6.json').read_bytes()
 if hashlib.sha256(raw).hexdigest()!=p['sha256']:raise ValueError('fff6 input drift')
 return json.loads(raw)
def fields():
 p=source()['ports'];h=dict(p['packet_header_fields']);c=dict(p['command_fields'])
 if sum(h.values())!=128 or sum(c.values())!=221 or h['user']!=16 or c['user']!=16:raise ValueError('old field widths')
 h['user']=32;c['user']=32
 return h,c

def encode(values,widths):
 if set(values)!=set(widths):raise ValueError('exact fields required')
 word=shift=0
 for name,width in sorted(widths.items()):
  n=values[name]
  if type(n) is not int or not 0<=n<1<<width:raise ValueError('field width')
  word|=n<<shift;shift+=width
 if shift>256:raise ValueError('oneflit overflow')
 return word

def decode(word,widths):
 if type(word) is not int or word<0 or word>=1<<sum(widths.values()):raise ValueError('noncanonical spare bits')
 out={};shift=0
 for name,width in sorted(widths.items()):out[name]=(word>>shift)&((1<<width)-1);shift+=width
 return out

def enrollment_fields():
 return {**dict(FIELDS),'operation_sequence':32,'physical_shard':1,'token_valid':1}

def enrollment_word(context,sequence,shard):
 identity(context)
 return encode({**context,'operation_sequence':sequence,'physical_shard':shard,'token_valid':1},enrollment_fields())

class Association:
 """Proposed sole fullcontext slot; needs explicit enrollment packet/provider.
 Direct assignment is a software contract test, not a native RTL callback.
 """
 def __init__(self,context,sequence,shard):
  identity(context)
  if type(sequence) is not int or not 0<=sequence<1<<32 or type(shard) is not int or shard not in (0,1):raise ValueError('sequence/route')
  self.ctx=dict(context);self.sequence=sequence;self.shard=shard
 @classmethod
 def from_enrollment(cls,word,expected_context,sequence,shard):
  values=decode(word,enrollment_fields());context={n:values[n] for n,w in FIELDS}
  if identity(context)!=identity(expected_context) or values['operation_sequence']!=sequence or values['physical_shard']!=shard or values['token_valid']!=1:raise ValueError('fullcontext expected source lease/sequence/shard enrollment')
  return cls(context,sequence,shard)
 def match(self,header,command,shard):
  h,c=fields()
  encode(header,h);encode(command,c)
  expected={'generation':self.ctx['generation'],'user':self.ctx['user'],'operation_sequence':self.sequence,'owner_stage':self.ctx['stage'],'rank':self.ctx['rank']}
  if shard!=self.shard or any(header[n]!=v or command[n]!=v for n,v in expected.items()):raise ValueError('association identity')
  if (command['EID'],command['phase'],command['key'])!=(self.ctx['expert'],self.ctx['phase'],self.ctx['key_word']):raise ValueError('command phase/expert/key')
  return True

def build():
 f=source();h,c=fields();hd,_=H.H.inputs();facts=hd['capture.json']['source_cell_facts'];tie=hd['capture.json']['SETN_TIEHI_LEF_area_um2']/1483
 header_bits=sum(h.values());command_bits=sum(c.values());association_bits=169+32+1+1
 gross_direction=header_bits+command_bits+association_bits;FF=2*gross_direction
 tree=[];n=FF
 while n>1:n=math.ceil(n/8);tree.append(n)
 # Conservative dedicated async metadata on TX and RX. Packet memories and
 # existing metadata containment are never subtracted without instance proof.
 compare=169+32+1;NAND=3*FF+2*(5*compare-1);INV=2*FF+2*(2*compare-1);BUF=2*FF+2*sum(tree)
 counts={'DFFASRHQNx1_ASAP7_75t_R':FF,'INVx1_ASAP7_75t_R':INV,'NAND2x1_ASAP7_75t_R':NAND,'BUFx4_ASAP7_75t_R':BUF,'TIEHIx1_ASAP7_75t_R':FF}
 body=sum(n*(tie if m.startswith('TIEHI') else facts[m]['SS']['area_um2']) for m,n in counts.items())
 L=f['spatial']['forward_route_CDC_PHY_envelope_edges'];R=f['spatial']['reverse_route_CDC_PHY_envelope_edges']
 return dict(schema='DS_CAPTURE_USER32_CODEC_PROPOSAL_1',candidate=f['candidate'],source_commit='fff6dc9c0b609955b2db2ac8565eb6ab0baadaf2',
   header=dict(source128=128,new144=header_bits,fields=h,one256flit=True,unused_flit_bits=256-header_bits),command=dict(source221=221,new237=command_bits,fields=c,one256flit=True,unused_flit_bits=256-command_bits),
   frozen_context169_unchanged=True,user32_no_65535_restriction=True,physical_route_shard_separate=True,
   no_extra_packet_memory_FF_from_width_change=True,TX_RX256word_256bit_CRC_and_boundary684_unchanged=True,
   header_and_command_width_increase_total32=True,semantic_codec_is_new_not_source_RTL_qualified=True,
   context_association=dict(full169_context_plus_sequence32_route1_valid1=association_bits,PC14_Xversion32_not_in_fff6_header_or_command=True,
       selected_software_proposal='explicit fullcontext enrollment before any command GO; exact stage/rank/expert/phase/key/gen/user/Xversion/PC and sequence/shard bound to one live context until visibility+returnedcredit/source/packet fences',
       context_enrollment_payload_bits=association_bits,enrollment_packet_flits=2,enrollment_header144_oneflit=True,
       full169_clones_or_local_existing_context_containment_not_free=True,reset_wrap_old_debt_fence_unimplemented=True),
   metadata_gross_FF_per_direction=gross_direction,TXplusRX_metadata_gross_FF=FF,codec_allowedcell_proposal_counts=counts,
   body_um2=body,reserve50pct_mm2_per_neighbor_endpoint=2*body/1e6,
   existing128assemblerheader_containment_not_subtracted=True,owner_context46_extra_is_already_separate_and_not_recharged_as169=True,
   shared_onephase_owner_slot_replacement_credit=None,port_replica_scope='gross TX/RX codec per neighbor endpoint; two neighbor endpoints on busiest owner conditional; physical homes unbound',
   busiest_twoport_gross_reserve_mm2=4*body/1e6,clock_RESETN_SETN_additional_loads_fF={corner:{p:FF*facts['DFFASRHQNx1_ASAP7_75t_R'][corner]['pins'][p]['cap_fF'] for p in ('CLK','RESETN','SETN')} for corner in ('SS','FF')},
   equality_compare_bits202_per_direction=compare,equality_compare_gate_depth_timing_and_codec_capture_pipeline_unqualified=True,
   conditional_context_enrollment_next_packet_credit_occupied_edges=3*2+L+R+1,
   conditional_enrollment_WAIT_ACK_edges=2+L+R+1,
   width_change_alone_extra_payload_flits=0,additional_context_enrollment_packet_not_free=True,
   additional_codec_validation_capture_edges=None,actual_fullphase_consumer_and_currentprogram_origin=None,
   C_stations_and_visibility_credit_provider_unselected=True,net_pin_site_PG_clock_reset_legal_geometry=None,
   physical_build_admitted=False,fulltoken_rate_credit=False,new_jobs=[])
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(build(),indent=2,sort_keys=True)+'\n')
