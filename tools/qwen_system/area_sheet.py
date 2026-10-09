"""Source-derived Qwen AR area ledger; reservation reuse requires placement proof."""
import json

def model():
    budget=858.
    baseline=846.792
    grid=25999.488*32801.76/1e6
    macro=121.824*62.910
    rows=[
      dict(name='r21b base outline',area_mm2=baseline,basis='historical actual outline; includes reservations listed below'),
      dict(name='grid92 column growth',area_mm2=grid-baseline,basis='actual snapped outline25999.488x32801.76'),
      dict(name='embedding stations',area_mm2=2.42,count=716,basis='V19 frame inventory; packing in existing corridors NOT established'),
      dict(name='skid8 separate frames',area_mm2=1536*160*112/1e6,count=1536,basis='actual cfg160x112; includes pins, not merely cell area'),
      dict(name='scale ROM macros',area_mm2=480*macro/1e6,count=480,basis='10banks x48ports; actual ot_rom_4096x266_m8 LEF121.824x62.910',overlap_reservation_mm2=14.359,extra_addition_mm2=None),
      dict(name='CROM frame',area_mm2=.7776,count=1,basis='777.6x1000 model',overlap_reservation_mm2=2.157,extra_addition_mm2=None),
      dict(name='SYSCTL frame',area_mm2=.15,count=1,basis='500x300 model; SRAM included',overlap_reservation_mm2=2.157,shared_reservation_with='CROM, program and sequencer',extra_addition_mm2=None),
      dict(name='host interface',area_mm2=None,basis='source inventory/actual placement required; cannot declare zero'),
      dict(name='PLL/reset clock producer',area_mm2=None,basis='actual abstract and clock plan required; cannot declare zero'),
      dict(name='collective frame',area_mm2=.76032**2,count=1,basis='PR2 cfg760.32square',overlap_reservation_mm2=3.6,extra_addition_mm2=None),
      dict(name='native128PC frames',area_mm2=128*247.536*371.52/1e6,count=128,basis='reservation247.536x371.52; embedding owner actual slots',overlap_reservation='existing controller slots',extra_addition_mm2=None),
    ]
    # These are cell estimates, NOT hardened outlines. Pin capacity prevents
    # shrinking the existing frame merely by changing DEPTH.
    variants=[]
    for depth in (2,4,8):
        cell=6672-(8-depth)*1031*.2916
        variants.append(dict(depth=depth,estimated_cell_um2=cell,
          cell_only_floorplan_lower_bound_mm2=1536*cell/.55/1e6,
          unchanged_pin_frame_mm2=1536*160*112/1e6,
          physical_frame_qualified=False,trace_latency_measured=False))
    additional=2.42+1536*160*112/1e6
    return dict(schema='opentallas.qwen-ar-area-sheet.v1',budget_mm2=budget,
      grid_outline_mm2=grid,remaining_after_grid_mm2=budget-grid,
      rows=rows,skid_variants=variants,
      no_reuse_known_total_mm2=grid+additional,
      no_reuse_over_budget_mm2=grid+additional-budget,
      owner_planning_target_mm2=845.,
      actual_r21c_outline_mm2=baseline,
      minimum_real_outline_compaction_needed_mm2=baseline-845.,
      embedding_rom_already_removed=True,
      freed_embedding_rectangle_um=[4688.928,31216.32,7063.608,1563.816],
      freed_embedding_occupancy_mm2=11.046,
      credit_freed_rectangle_against_outline=False,
      compaction_proved=False,
      host_pll_eco_proposed_reservation_mm2=3.,
      host_pll_eco_actual_fit_proved=False,
      scale_payload=dict(code_rows=20016,code_capacity=20480,
        scale_rows_per_port=40392,scale_capacity_per_port=40960,
        scale_ports=48,scale_banks_per_port=10,scale_macro_count=480,
        raw_scale_macro_area_mm2=480*macro/1e6,
        available_scale_reservation_mm2=14.359,
        physical_join_complete=False,hash_evidence='09432714d'),
      adopted=False,fit_proven=False,
      constraints=['Never add a macro footprint again when packed inside an existing reservation.',
        'Never subtract a reservation until actual master rectangles and channels fit its replacement.',
        '1536 independent skid frames do not fit current outline; freed embedding is occupancy, never a second subtraction.',
        'Depth2/4 cell estimates do not demonstrate smaller pin-access frames or shared queue correctness.',
        '716 stations is historical parallel-bus inventory; new finite trunk/spine alternative must supersede its priced count explicitly.',
        'Host/PLL and native row/context transport remain unpriced, preventing a final fit claim.'])

if __name__=='__main__': print(json.dumps(model(),indent=2))
