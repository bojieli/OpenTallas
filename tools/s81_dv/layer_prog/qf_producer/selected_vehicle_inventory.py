#!/usr/bin/env python3
"""Read-only exact six-frame build/storage inventory, not a source hardware grant."""
from pathlib import Path
import collections,hashlib,json,re,subprocess
from head_local_contract import ROOT
ref='ceaed19c4';base=ROOT/'results/rtl/s81_qf_producer_1019/sid6_vehicle'
paths=['rtl/dsrom_sys/s81_dv/frame_l4/col_h9_l4.sv','rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4.sv',
 'rtl/dsrom_sys/s81_dv/frame_l4/col_h9_MX_l4.sv','rtl/v41rom/ot_v41_rom_elem_q_qxpq_w10.sv',
 'rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv','rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv','rtl/v41rom/ot_v41_bf_col.sv',
 'physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v',
 'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v','tools/s81_dv/frame_bench.f']
sources={p:subprocess.check_output(['git','show',ref+':'+p]) for p in paths}
mastercounts={}
for master in ['col_h9_l4','col_h10_l4']:
 s=sources['rtl/dsrom_sys/s81_dv/frame_l4/'+master+'.sv'].decode()
 c=collections.Counter(re.findall(r'^    (\w+)\s+(?:#\(.*?\)\s+)?\w+\s*\(',s,re.M))
 assert c['ot_v41_rom_elem_q_qxpq_w10']==12
 assert c['ot_rom_4096x72_m8']==7*(c['ot_s81_cfg7_seq']+c['ot_s81_cfg7_seq_bfp'])
 for line in s.splitlines():
  if 'ot_v41_rom_elem_q_qxpq_w10 #' in line:assert '.NB(2)' in line and '.PP(1)' in line
 mastercounts[master]=dict(c)
qs=sources['rtl/v41rom/ot_v41_rom_elem_qx_pq_w10.sv'].decode()
assert 'for (mb = 0; mb < NB; mb = mb + 1)' in qs and 'if (PP != 0)' in qs
bf=sources['rtl/dsrom_sys/s81_die_bind/dsfd_bf_col.sv'].decode();assert '.PP(1)' in bf
contract=json.loads((base/'sid6_fixture_contract.json').read_text())
selected=contract['phase_contracts'][0]['frames'];assert len(selected)==6
# h9_MX is a wrapper around exactly one h9, no duplicate frame.
h9=sum(f['master'].startswith('col_h9') for f in selected);h10=sum(f['master']=='col_h10_l4' for f in selected)
assert (h9,h10)==(4,2)
cfg=h9*mastercounts['col_h9_l4']['ot_rom_4096x72_m8']+h10*mastercounts['col_h10_l4']['ot_rom_4096x72_m8']
qpair=72;bfcols=h9*mastercounts['col_h9_l4']['dsfd_bf_col']+h10*mastercounts['col_h10_l4']['dsfd_bf_col']
assert (cfg,bfcols)==(644,40)
qrom=qpair*2*2;bfrom=bfcols*2
storage=dict(cfg4096x72_macros=cfg,q4096x274_macros=qrom,BF4096x274_macros=bfrom,
 total_frame_ROM_macros=cfg+qrom+bfrom,total_frame_ROM_bits=cfg*4096*72+(qrom+bfrom)*4096*274,
 existing_XS_SRAM_macros=24,existing_XS_SRAM_bits=24*128*256,
 existing_five_VP_SRAM_macros=10,existing_five_VP_SRAM_bits=10*512*128,
 existing_quantizer_ring_SRAM_macros=1,existing_quantizer_ring_SRAM_bits=128*256,
 existing_XS_calendar_phase_stream_ROM_macros=7,
 new_physical_macros=0,new_FF=0,new_gates=0,new_physical_area_um2=0,
 qualification='Existing minimum component storage census; not physical source-cone pruning or new free capacity')
inv=json.loads((base/'selected_return_cone_inventory.json').read_text())
rec=dict(schema='opentallas.s81.selected_six_frame_source_inventory.v1',source_ref=ref,
 selected_die_sha256=inv['selected_die_sha256'],frames=selected,masters=mastercounts,storage=storage,
 source_files=[dict(path=p,sha256=hashlib.sha256(v).hexdigest(),bytes=len(v)) for p,v in sources.items()],
 frame_sources_only_bytes=sum(len(sources[p]) for p in paths[:3]),
 required_cone=['Proved genuine raw source and real XS output','2-stage mk +4 actual DX6 copies',
 'Actual selected24 input lane paths/ICG/stations/MX forwarded output clocks',
 'Six exact frame masters/straps/region resets and all real ROM contents',
 'Six real packed return ports/ICG/SN/NS/stations/landK2','DR6 +actual CAP64slot/tree/finish',
 'DL4+five actual VP CW pin/macro commits'],
 selected_source_lines=inv['lines'],
 actual_source_component_resources=dict(max_RSS_KiB=2340380,wall_seconds=64.14,threads=4,
  scope='Measured retained XS component only; cannot extrapolate as six-frame peak'),
 next_build_admission=dict(resource_reservation_candidate_GB=128,threads_candidate=8,unpinned=True,
  qualification='Candidate admission reservation from actual headroom and1012ROM inventory, not process/cgroup hardlimit or measured need; no protective cap/deadline. Frontend CPP/object/RSS census required; preserve useful objects.'),
 native_phase=None,native_regional_reset_dates=None,actual_frame_arrival_dates=None,actual_CAP_CW_commit_dates=None,
 original_deadline_pass=None,
 blocked_claims=['No fullarray/GEN/production imagewriter','No native phase claim from G=R0 functional model',
 'No CFG/RETIRE/END completion credit without actual return+CAP+VP drain',
 'No source read substitution or endpoint/return injection','No production/MU scratch/storage ownership qualification'])
out=base/'selected_vehicle_inventory.json';out.write_text(json.dumps(rec,indent=2)+'\n')
print('SELECTED_VEHICLE_INVENTORY_ONLY sixframes cfgROM',cfg,'qROM',qrom,'bfROM',bfrom,'bits',storage['total_frame_ROM_bits'],'native/ARR/CW/peak NULL; no build')
