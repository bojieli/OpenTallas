"""Finite exact rank-ordered FP32 winner merge, model before RTL."""
def model():
 return dict(schema='opentallas.dshbm.mtp.rank_argmax.model.v1',default_enabled=False,
  macs_per_cycle=0,compute_intensity='finite FP32 score compare, lowest global token on ties',
  memory_bytes_per_cycle=0,boundary_bits_per_cycle={'rank_input':135,'winner_output':123},
  replica_count={'SM_row_fold':3072,'die_SM_merge':96,'global_die_merge':1},
  mux_fanout='one held winner,32 ordered SM winners per die,96 ordered die winners globally',
  routing_tracks_required=449,channel_capacity='selected existing rank transport; actual pins pending',
  area={'flop_bits_per_instance':150,'added_macros':0},floorplan_slot='unqualified local result/collective epilogue',
  clock_domain='stream1.2GHz; comparison only; upstream stored-DLOG FP32 addition requires its actual priced domain',
  latency_cycles={'SM_fold_max_rows':43,'die_rank_merge':32,'global_rank_merge':96,'publication_each_merge':1},
  latency_composition='concurrent SM fold plus ordered die merge plus actual transport plus global merge; no whole-array simulation',
  arithmetic='no score arithmetic/reduction reorder; exact finite compare and lower-id tie',
  obligations=['real released stored-DLOG plus Markov scores before comparison',
               'rank source counts/identities from actual selected partition','negative missing/duplicate rank and wrong-owner gates',
               'actual interdomain queues and in-context timing before adoption'],
  physical_qualification=False)
