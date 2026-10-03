"""Source serializer allocation/alias controls; no runtime checkpoint claim."""
import sys,json,math
from pathlib import Path
import pytest,numpy as np
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import ds_hbm_checkpoint_phase_ram_r61 as R
import ds_producer_checkpoint_resume_v3 as V
from ds_hbm_dual_resources_r56 import heap
from ds_hbm_held_resume_r61 import admission,start_ticks

@pytest.mark.parametrize('n',[0,1,8,128,4096])
def test_actual_writer_tagged_metadata_heap_bound_and_no_array_payload(n,tmp_path):
    a=np.arange(n,dtype=np.uint32)
    state={'a':a,'zero':0,'negative':-1,'wide':2**64-1,'none':None,'bool':True,'rows':[('DeepSeek',i,2**64-1) for i in range(min(n,128))]}
    writer=V.Writer(tmp_path);tree=writer.tree(state);writer.close()
    encoded=V.canonical(tree)
    assert heap(tree)<=64*len(encoded)
    assert writer.array_temporary_bytes==0 # np.ascontiguousarray returns same buffer.
    assert np.ascontiguousarray(a) is a
    assert (tmp_path/'payload.bin').stat().st_size==a.nbytes
    assert V.read_tree(tree,np.memmap(tmp_path/'payload.bin',dtype=np.uint8,mode='r') if n else b'')['a'].tobytes()==a.tobytes()


def test_actual_sector_writer_streams_alias_and_restored_mapping_shallow_copy(tmp_path):
    from hbm_bound_event_journal_r30 import BoundSectorProvider,JournalBudget,CompactSectors
    budget=JournalBudget(tmp_path/'journal',1<<20)
    p=BoundSectorProvider({('DeepSeek',0):[{'base':0,'bytes':64}]},journal_budget=budget)
    p.backing[('DeepSeek',0,0)]=list(range(32));p.backing[('DeepSeek',0,1)]=[1,None]+[None]*30
    wrapped=V.SectorBacking(p);assert wrapped.values is p.backing
    dest=tmp_path/'cp';dest.mkdir();w=V.Writer(dest);tree=w.tree(wrapped);w.close()
    assert len(V.canonical(tree))<256 and len(p.backing)==2
    saved=V.read_tree(tree,np.memmap(dest/'payload.bin',dtype=np.uint8,mode='r'))
    copied=CompactSectors(saved)
    assert copied is not saved
    assert copied[('DeepSeek',0,0)] is saved[('DeepSeek',0,0)]
    assert copied[('DeepSeek',0,1)] is saved[('DeepSeek',0,1)]


def test_phase_separation_preserves_existing_guard_and_full_other_prices():
    base=json.loads(R.BASE.read_bytes());m=R.phase_model(base,[])
    assert m['existing_R58_guard_bytes']==90877389572
    assert m['existing_guard_changed'] is False and m['source_RSS_lowering_credit_bytes']==0
    assert m['allocator_return_credit_bytes']==0 and m['whole_producer_release_credit_bytes']==0
    assert m['cold_restore_candidate_with_all_other_components_retained_bytes']==70476249358
    assert m['preserved_original_components']==base['RAM']['components']


def test_exact_both_RF_copy_future_words_and_state_bytes():
    base=json.loads(R.BASE.read_bytes())
    homes=[dict(birth_pc=8,rank_group=[0,1],home={'class':'RF','vectors':1},word_count=32),dict(binding={'PC':9,'bytes':33},rank_group=[0],home={'class':'HBM_NATIVE_STATE'})]
    m=R.phase_model(base,homes)
    assert m['future_PC8_9_sector_upper']==18


def test_source_sized_admission_boundary_no_margin_magic():
    assert admission(100,100) and not admission(99,100)
    with pytest.raises(ValueError):admission(100,0)


def test_start_ticks_from_actual_controller_process():
    import os
    assert start_ticks(Path('/proc')/str(os.getpid()))>0
