"""Production TA15 composition before integration RTL/physical build."""
def model():
 return dict(default_enabled=False, adopted=False,
  mechanism='AON ordered qualification -> analog PLL output clocks -> destination reset collars -> synchronized released readiness',
  clock_period_ns=dict(stream=5/6,serial=10/9,hbm=1.024,link=5/6),
  digital_body_successor=dict(top='ot_hbm_production_clock_digital_body',
   area_slot_um=[100.224,99.36],AON_pathfinding_period_ns=3,
   boot_mask='Destination intents remain low across raw POR deassertion until actual sequenced PLL/PHY/link/BIST admission.',
   raw_status_obligations='Analog lock and all provider readiness are explicit inputs; no constant qualification. Recovery/removal remains visible; AON3ns is a provisional external-source contract.',
   added_FF_bits=0,added_token_cycles=0),
  replicas=dict(PHY=4,links=9,reset_collars=17),
  sequential_bits=dict(AON_status=34,AON_state=4,destination_collars=51,AON_ready=2),
  FF_area_floor_um2=91*0.2916,
  readiness_latency='3 destination clock edges after reset intent plus2 AON edges after all actual resets release',
  steady_state_token_latency_cycles=0, MACs_per_cycle=0,memory_bytes_per_cycle=0,
  status_input_bits=19,control_output_bits=23,
  route_tracks='Actual clocks/reset trees and PHY/link status routes require contextual extraction',
  qualification='Composition sizing only; analog macro area and die boundary integration remain unqualified')
