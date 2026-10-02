import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import dsrom_capture_identity_slot_join as J

def test_exact_new_identity_and_buffer_debit():
 m=J.build();c=m['cell_counts']
 assert c['DFFASRHQNx1_ASAP7_75t_R']==46
 assert c['BUFx4_ASAP7_75t_R']==92+14
 assert m['global_frozen_bits']==m['baseline_bits']+m['mandatory_extra_bits']==169
 assert m['reserve50pct_mm2']>0
 assert m['incremental_whole_reticle_enclosure_mm2']==0

def test_disjoint_strip_does_not_admit_controls_or_routes():
 m=J.build()
 assert m['common_remaining_reservation_mm2']>0
 assert m['proposed_strip_mm2']>=m['reserve50pct_mm2']
 assert m['remote_context_copy_added_bits'] is None
 assert m['actual_consumer_deadline'] is None
 assert not m['physical_build_admitted']
 assert all(c['actual_instance_name'] is None for c in m['source_cell_proposal'])
