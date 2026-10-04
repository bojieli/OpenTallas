import sys,json,random,copy
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import dsrom_field_parent_component as M
CTX=(0,0,0,10,2149580800,0,0,0,66)

def configured(n=2):
 s=M.Sequencer();s.reset_release(1,1,True)
 s.reserve(CTX,n,[(CTX,1,0),(CTX,1,1)],[True]*12,True,0)
 s.cfg_accept(CTX,True);s.launch(CTX,CTX);return s

def finish(s,n=2):
 for row in range(n):s.publish(CTX,row,True,True,True);s.credit(CTX,row,11,12)
 s.retire(CTX,0,True,0,0,0)

@pytest.mark.parametrize('bit',range(9))
def test_full169_bounds(bit):
 c=list(CTX);c[bit]=1<<(6,2,9,10,32,32,32,32,14)[bit]
 s=M.Sequencer();s.reset_release(1,1,True)
 with pytest.raises(ValueError):s.reserve(c,2,[(tuple(c),1,0),(tuple(c),1,1)],[True]*12,True,0)

@pytest.mark.parametrize('debt',range(4))
def test_ready_cannot_substitute_for_actual_drain(debt):
 s=configured()
 for row in range(2):s.publish(CTX,row,True,True,True);s.credit(CTX,row,11,12)
 args=[True,0,0,0];args[debt]=False if debt==0 else 1
 with pytest.raises(ValueError):s.retire(CTX,0,*args)
 assert s.ctx==CTX

def test_reset_era_cannot_erase_active_or_VM_read_debt():
 s=configured()
 with pytest.raises(ValueError):s.reset_release(2,2,True)
 finish(s)
 with pytest.raises(ValueError):s.reset_release(2,2,True)
 s.su_read(0,CTX,20)
 with pytest.raises(ValueError):s.su_tag_retire(0,CTX,20,21,True)
 s.su_tag_retire(0,CTX,20,22,True);s.reset_release(2,2,True)

def test_stale_visible_and_sameedge_credit_do_not_free_seat():
 s=configured();s.publish(CTX,0,True,True,True)
 with pytest.raises(ValueError):s.credit(CTX,0,10,10)
 assert not s.credits
 bad=list(CTX);bad[6]=1
 with pytest.raises(ValueError):s.credit(bad,0,10,11)

@pytest.mark.parametrize('n',[1,256,762,763,4096])
def test_full4096_finite_framing_and_CRC_timeout(n):
 c=M.crc_construction(M.crc_matrix());p=M.packet(n,c)
 assert sum(x['rows'] for x in p['packets'])==n
 assert all(x['header_flits']==2 and x['flits']<=256 for x in p['packets'])
 assert p['timeout8192_PASS']
 if n==4096:
  assert not all(x['previous4096_PASS'] for x in p['packets'])
  assert all(not x['timeout1024_PASS'] for x in p['packets'])

def test_CRC_basis_exact_and_packet_feedback_not_II1():
 matrix=M.crc_matrix();assert M.crc_proof(matrix)['PASS']
 rng=random.Random(16);state=0xffffffff
 for i in range(17):
  data=rng.getrandbits(256);linear=M.crc_linear(state,data,matrix)
  assert linear==M.crc_step(state,data);state=linear
 c=M.crc_construction(matrix)
 assert c['engines']==8 and c['accepted_to_terminal_cycles']==10 and c['ordered_packet_extend_II']==11
 bad=list(matrix);bad[0]^=1
 assert M.crc_linear(1,0,bad)!=M.crc_step(1,0)

def backend(reads,writes,pub=(),**kw):
 return M.VMGrantBatch({3:7,35:9},reads,writes,CTX,1,pub,True,kw.get('L',2),kw.get('G',1))
def drain(b):
 for edge in range(100):
  if b.step(edge,CTX,1):return edge
 raise AssertionError('finite service did not drain')

def test_preedge_snapshot_before_write_with_literal_last_winner():
 b=backend([('r0',3),('r1',35)],[('w0',0,0,3,8),('w1',11,3,3,10)])
 drain(b)
 assert b.read_values=={'r0':7,'r1':9} and b.image[3]==10
 assert b.superseded=={'w0'} and set(b.visible)=={'w1'}
 assert min(e for e,k,i in b.events if k=='write_grant')>=max(e for e,k,i in b.events if k=='read_response')
 for e,k,i in b.events:
  if k=='visible':assert e>next(x for x,t,j in b.events if t=='write_grant' and j==i)

def test_equalbits_superseded_publication_is_rejected():
 with pytest.raises(ValueError):backend([], [('w0',1,0,3,10),('w1',11,0,3,10)],['w0'])

def test_wrongera_preserves_pending_native_request():
 b=backend([('r',3)],[])
 with pytest.raises(ValueError):b.step(0,CTX,2)
 assert b.read_debt==1 and b.last_edge==-1

@pytest.mark.parametrize('fault',['missing_grants','zero_latency','bad_address','missing_image','unsorted_family','no_exclusions'])
def test_native_provider_or_address_gap_failclosed(fault):
 args=[{3:7},[('r',3)],[],CTX,1,(),True,2,1]
 if fault=='missing_grants':args[-1]=None
 if fault=='zero_latency':args[-2]=0
 if fault=='bad_address':args[1]=[('r',2**19)]
 if fault=='missing_image':args[1]=[('r',4)]
 if fault=='unsorted_family':args[2]=[('a',11,0,3,7),('b',1,0,3,8)]
 if fault=='no_exclusions':args[6]=False
 with pytest.raises(ValueError):M.VMGrantBatch(*args)

def test_no_stall_free_samebank_read_parallelism():
 b=backend([('r0',3),('r1',35)],[],L=2,G=3);drain(b)
 assert [e for e,k,i in b.events if k=='read_grant']==[0,3]
 assert b.read_values=={'r0':7,'r1':9}

def test_no_silent_VM_macro_or_physical_rate_credit():
 m=M.vm_contract()
 assert m['native_source_VM_capacity_bits']==16777216
 assert m['source_port_envelope']['read_element_ports']==1520
 assert m['source_port_envelope']['write_element_ports']==593
 assert m['proposed_backend']['actual_macro_abstract'] is None
 assert m['proposed_backend']['maximum_grant_interval'] is None
 assert not m['native_VM_grant_admission']

def test_all_cell_runs_grid_count_and_no_known_inventory_overlap():
 c=M.crc_construction(M.crc_matrix());sections,areas,clock=M.sections(c);p=M.placement(sections,areas)
 assert p['known_inventory_nonoverlap_PASS'] and p['reticle33000x26000_um_rotated26x33_PASS']
 assert p['old_capture_credit_taken']==0
 for sec in p['sections']:
  from collections import Counter
  counts=Counter()
  for r in sec['runs']:
   for member in r['members']:counts[member['master']]+=r['count']
  assert counts==sections[sec['section']]
  for r in sec['runs']:
   assert r['cell_width_DBU']%54==0
   assert (r['rows']-1)*r['per_row']+r['last_row_cells']==r['count']
   assert r['per_row']*r['cell_width_DBU']<=round((p['width_um']-25.92)*1000)
 assert sections['CRC_metadata_memory'][M.C.HQ]==16384
 assert clock['clock_leaf_FO']==4

def test_loaded_local_screen_includes_hold_buffers_not_old20NAND_cut():
 e=M.electrical_screen()
 assert e['three_forward_BUF_SS_delay_included']
 for path in e['registered_local_data_paths'].values():
  assert path['conditional_setup_screen_PASS']
  assert sum(s['master']==M.C.BUF for s in path['steps'])==3
  assert all(s['positive_wire_ceiling_um']>0 for s in path['steps'])
 assert not e['SS_setup_closed'] and not e['FF_hold_closed']
 assert e['local_branch_clock']['four_sink_pin_load_fF']+e['local_branch_clock']['conservative_wire_cap_fF']<5.76
 assert e['local_branch_clock']['upper_branch_wire_length_ceiling_um']<6.2

def test_selected_root_capture_keeps_W2_and_wholeprogram_gate_false():
 m=json.loads((M.OUT/'model.json').read_text())
 assert m['fixed_capacity']['raw69_records_per_shard']==4096
 assert m['service']['wholeprogram_token_delta'] is None
 assert not m['defaultoff_RTL_preparation_ready'] and not m['HDL_build_GO'] and not m['context_PnR_GO']
 assert m['service']['I66_added_rearm_dependency_edges']==9466
 assert m['reticle_accounting']['old_capture_or_packet_memory_containment_credit_mm2']==0
 assert m['reticle_accounting']['new_VM_macro_body_and_parent_route_area_unbound']
 assert not m['native_VM_order_and_finite_grant_join']['native_VM_grant_admission']
