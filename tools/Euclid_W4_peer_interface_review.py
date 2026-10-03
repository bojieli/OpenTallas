#!/usr/bin/env python3
"""Offline peer interface/source binding; does not run/duplicate the native gate."""
import pathlib,json,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
REC=pathlib.Path('results/uarch/Euclid_W4_RFACK_identity_contract_20261003/integration-handoff-r7')
def review():
 p=ROOT/REC;record=json.loads((p/'interface-source-r7.json').read_text());pins=json.loads((p/'artifact-pins-r7.json').read_text())
 for name,want in pins.items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=want:raise ValueError('packet pin '+name)
 for name,want in record['source_pins'].items():
  if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=want:raise ValueError('source pin '+name)
 if sorted((p/'sources-full-service-r7.f').read_text().splitlines())!=sorted(record['source_pins']):raise ValueError('source selector changed')
 for mod,head in record['exact_module_headers'].items():
  s=(ROOT/'rtl/gpu_w4_euclid_20261003'/f'{mod}.sv').read_text()
  if s[:s.index(');')+2]!=head:raise ValueError('interface drift '+mod)
 if record['owner46']['MSB_to_LSB']!=[['PC',7],['client',3],['original_client_tag',32],['generation',4]]:raise ValueError('owner layout')
 if record['gate']['status']!='LIVE_NOT_QUALIFIED' or record['source_changed']:raise ValueError('pending gate promoted')
 launch=json.loads((p/'launch.json').read_text())
 if launch['sourcefreeze']!=record['live_source_commit'] or not launch['limits_unlimited_CPU_AS_FSIZE']:raise ValueError('launch freeze mismatch')
 rf=(ROOT/'rtl/gpu_w4_euclid_20261003/ot_gpu_rf_service.sv').read_text()
 sm=(ROOT/'rtl/gpu_w4_euclid_20261003/ot_gpu_full_sm_service.sv').read_text()
 for fragment in ['accepted_identity<={wr_owner,wr_addr}','protected_ACK<=w4_encode(accepted_identity)','ack_valid && ack_ready && !decoded_ACK[55]']:
  if fragment not in rf:raise ValueError('source event missing '+fragment)
 for fragment in ['.ack_ready(((state==ACK && SIMD_ACK_match) || (idle && host_ack_ready)) && !identity_fault)','if(SIMD_ACK_mismatch)identity_mismatch_fault<=1','rf_ack_owner==simd_identity[54:9] && rf_ack_slot==dst_q']:
  if fragment not in sm:raise ValueError('sink identity contract changed')
 if record['gate']['RF_leaf_directed_marker']!=(p/'tb_W4_RFACK-run.log').read_text().strip() or 'PASS_W4_RFACK' not in record['gate']['RF_leaf_directed_marker']:raise ValueError('leaf evidence mismatch')
 return {'status':'PASS_FROZEN_PEER_INTERFACE_ONLY','design_source_pins':len(record['source_pins']),'packet_pins':len(pins),'live_source_commit':record['live_source_commit'],'whole_gate_terminal':False,'build_or_solver_launched':False,'caller_CDC_physical_qualification':False}
if __name__=='__main__':print(json.dumps(review(),indent=2,sort_keys=True))
