#!/usr/bin/env python3
"""Measured successor receipt; preserves original storage sizing and selected model."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def packet_storage_receipt():
 root=ROOT/'results/rtl/hbm_collective_matched_e9cbc1c4e'
 records=[json.loads((root/f'packet{i}'/'record.json').read_text()) for i in (0,1)]
 m=json.loads((root/'matched_comparison.json').read_text())
 if records[0]['source_sha256']!=records[1]['source_sha256'] or records[0]['traffic_calendar']!=records[1]['traffic_calendar']:
  raise ValueError('unmatched source/calendar cannot establish latency delta')
 if not all(r['passed'] and all(c['passed'] for c in r['checks'].values()) for r in records):
  raise ValueError('every exactness/negative gate must pass')
 delta=m['packet1']['elapsed']-m['packet0']['elapsed']
 return dict(status='MEASURED_ENDPOINT_CANDIDATE_NOT_ADOPTED',source_commit='e9cbc1c4e',
  shape=dict(lanes=16,pf=384,own_results=24,peer_flits=336,rx_depth=256,q_depth=64,cdc_depth=64),
  baseline_cycles=m['packet0']['elapsed'],packet_sram_cycles=m['packet1']['elapsed'],added_endpoint_cycles=delta,
  core_period_ps=833.333333,added_endpoint_latency_ns=delta*833.333333/1000,
  comparison='identical contributor-major hot-column inputcalendar, same source, PACKET_SRAM0 versus1',
  token_delta_cycles=None,physical_adoption=False,
  limits=['old CDC implementation retained','one owned-reduction endpoint fixture; not network/token calendar','no physical clock/area closure credit'])
if __name__=='__main__':print(json.dumps(packet_storage_receipt(),indent=2))
