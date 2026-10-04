import sys,json,random
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_field_native_VM_join as M
CTX=(0,0,0,10,2149580800,0,0,0,66)

def phase(n=576):return M.AffineFrame(CTX,1,398720,n,1,True,[True]*12,True)
def sealed(n=576):
 a=phase(n)
 for r in range(n):a.append(CTX,1,r,0,398720+r,(r*1664525+1013904223)&0xffffffff)
 return a.seal()

@pytest.mark.parametrize('n',[1,16,576,593,594,8192])
def test_affine_frames_finite593_seats_and_native_schedule(n):
 c=M.affine_native_calendar(sealed(n),1)
 assert sum(f['rows'] for f in c['frames'])==n
 assert len(c['frames'])==(n+592)//593
 assert all(f['rows']<=593 and f['winner_compare_edges']==0 for f in c['frames'])
 assert c['serial_edges']==2*n+3*len(c['frames'])
 for f in c['frames']:
  for e in f['events']:
   assert e['macro_visible']==e['issue']+2 and e['visible_ack_capture']==e['issue']+3
   mask=int(e['expanded512bit_mask_hex'],16)
   assert mask.bit_count()==32
   assert sum(int(part,16)<<(128*i) for i,part in enumerate(e['four128bit_masks_hex']))==mask

@pytest.mark.parametrize('fault',['position','bounds','competitors','undrained','lease'])
def test_no_boolean_unique_flag_bypasses_source_admission(fault):
 args=[CTX,1,398720,576,1,True,[True]*12,True]
 if fault=='position':args[4]=2
 if fault=='bounds':args[2]=2**19-500
 if fault=='competitors':args[7]=False
 if fault=='undrained':args[6][3]=False
 if fault=='lease':args[5]=False
 with pytest.raises(ValueError):M.AffineFrame(*args)

@pytest.mark.parametrize('fault',['duplicate','outoforder','wrongaddress','sourceerror','competitor','wronggen','wrongera'])
def test_bad_source_record_keeps_matching_phase_unpublished(fault):
 a=phase(2);a.append(CTX,1,0,0,398720,7)
 args=[CTX,1,1,0,398721,8,False,False]
 if fault=='duplicate':args[2]=0;args[4]=398720
 if fault=='outoforder':args[2]=2;args[4]=398722
 if fault=='wrongaddress':args[4]=398720
 if fault=='sourceerror':args[6]=True
 if fault=='competitor':args[7]=True
 if fault=='wronggen':args[0]=(*CTX[:5],1,*CTX[6:])
 if fault=='wrongera':args[1]=2
 with pytest.raises(ValueError):a.append(*args)
 assert len(a.accepted)==1 and not a.closed

@pytest.mark.parametrize('fault',['incomplete','read','otherwriter'])
def test_only_writeonly_exact_source_phase_seal(fault):
 a=phase(1)
 if fault!='incomplete':a.append(CTX,1,0,0,398720,7)
 with pytest.raises(ValueError):a.seal(reads=[('r',4)] if fault=='read' else (),extra_writes=[('w',4,7)] if fault=='otherwriter' else ())


def test_native_scalar_mask_preserves_other15_words_and_columns():
 rng=random.Random(19)
 for lane in range(16):
  old=rng.getrandbits(512);val=rng.getrandbits(32);mask=((1<<32)-1)<<(32*lane)
  new=(old&~mask)|(val<<(32*lane))
  assert (new&~mask)==(old&~mask) and (new>>(32*lane))&0xffffffff==val
  parts=[(mask>>(128*i))&((1<<128)-1) for i in range(4)]
  assert sum(p.bit_count() for p in parts)==32


def test_reference185us_not_hidden_in_linear_certificate():
 s=sealed();v=M.provider();reference=v.calendar({},[],s.writes,1);linear=M.affine_native_calendar(s,1)
 assert reference['fill_edges']==166176 and reference['winner_compare_edges']==165600
 assert reference['busy_edges']==579 and linear['serial_edges']==1155
 assert sum(f['reference_scan_removed_edges'] for f in linear['frames'])==165600
 assert v.reference().ordered_edge({},[],s.writes)[1]==reference['image']


def test_arbitrary_tuple_or_stale_era_cannot_enter_unique_path():
 s=sealed(2)
 with pytest.raises(ValueError):M.affine_native_calendar(s.writes,1)
 with pytest.raises(ValueError):M.affine_native_calendar(s,2)


def frame():return M.provider().calendar({},[],[(0,398720,7)],1)
@pytest.mark.parametrize('fault',['owner','era','batch','acceptonly'])
def test_native_epoch_ID_alone_cannot_free_full169_owner(fault):
 f=frame();q=M.QualifiedReceipt(f,CTX,1,0);args=[CTX,1,0,'write',0,3,True]
 if fault=='owner':args[0]=(*CTX[:6],1,*CTX[7:])
 if fault=='era':args[1]=2
 if fault=='batch':args[2]=1
 if fault=='acceptonly':args[6]=False
 with pytest.raises(ValueError):q.receipt(*args)
 assert q.native.writes=={0:3}


def test_visible_credit_preF_and_bank_version_are_separate():
 q=M.QualifiedReceipt(frame(),CTX,1,0)
 with pytest.raises(ValueError):q.receipt(CTX,1,0,'write',0,2,True)
 q.receipt(CTX,1,0,'write',0,3,True)
 with pytest.raises(ValueError):q.source_credit(CTX,1,0,0,3)
 q.source_credit(CTX,1,0,0,4)
 with pytest.raises(ValueError):q.rearm(True,4)
 q.rearm(True,5);assert q.native.closed


def test_superseded_write_gets_no_owner_visible_credit():
 f=M.provider().calendar({},[],[('a',3,7),('b',3,7)],1);q=M.QualifiedReceipt(f,CTX,1,0)
 q.receipt(CTX,1,0,'write','a',f['receipts']['a']['at'])
 assert 'a' not in q.visible
 with pytest.raises(ValueError):q.source_credit(CTX,1,0,'a',100)


def test_fullsize_native_provider_and_guard_price_no_geometry_adoption():
 m=M.generate();p=m['native_backend']
 assert p['bits']==16777216 and p['macros']==256 and p['DEPTH_GROUPS']==16
 assert m['I66_affine_publication']['serial_edges']==1155
 assert m['positive_allowed_cell_guard_floor']['body_um2_floor']>0
 assert m['positive_allowed_cell_guard_floor']['guard_pipeline_cycles'] is None
 assert m['physical_contract']['launcher'].endswith('aligned_guarded.py --macro-track-gate')
 assert m['physical_contract']['abstract_selection']=='v1 unchanged'
 assert not m['physical_contract']['v2_selected'] and not m['admission']['engine_RTL_GO']
 assert m['physical_contract']['master_guard_not_actual_instance_census']

@pytest.mark.parametrize('which',[0,1,2])
def test_boolean_row_position_or_address_is_not_a_source_integer(which):
 a=M.AffineFrame(CTX,1,0,1,1,True,[True]*12,True)
 args=[0,0,0];args[which]=False
 with pytest.raises(ValueError):a.append(CTX,1,*args,7)
 assert not a.accepted

def test_boolean_position_count_cannot_enter_P1_certificate():
 with pytest.raises(ValueError):M.AffineFrame(CTX,1,0,1,True,True,[True]*12,True)

def test_control_only_mailbox_cannot_be_a_data_crossing():
 c=M.data_CDC_cost()
 assert c['forward_full_payload_bits']==238+69 and c['reverse_control_payload_bits']==238
 assert c['new_raw_data_bits']==16*69 and c['body_um2_floor']>0
 assert c['added_masters']['DFFHQNx1_ASAP7_75t_R']==1104
 assert not c['actual_CDC_reset_relation_and_registered_timing']

def test_maxpacket_splits_native_frames_and_timeout_keeps_positive_headroom():
 p=M.packet_ACK_native_bound()
 assert p['native_frames']==2 and p['native_publication_serial_edges']==1530
 assert not p['timeout1024_PASS'] and not p['timeout4096_PASS']
 assert p['successful_ACK_wait_stream_edges_excluding_guard_and_arbitration']==7539
 assert p['remaining8192_for_guard_arbitration_stream_edges']==652
 assert p['8192_not_adopted_timeout_or_universal_provider_bound']
