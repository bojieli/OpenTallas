#!/usr/bin/env python3
"""Size the actual staging root using existing die ledger and real SRAM before RTL build."""
import json,hashlib
from pathlib import Path
r=Path(__file__).resolve().parents[3];out=r/'results/physical/hbm_die_abstracts_20261006/memory_control'
m=r/'physical/asap7_memory_macros/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.json'
j=json.loads(m.read_text());payload=2063;owner=192;codes=(payload+owner+63)//64;macros=(codes*72+255)//256
book=r/'results/rtl/die_top_lint_20261006/hbm_die_abstract_list.json';b=json.loads(book.read_text());vm=next(f for f in b['families'] if f['family']=='hfd_vm')
rec={'schema':'opentallas.hbm.vm-root-prebuild.v1','authority':str(book.relative_to(r)),'authority_sha256':hashlib.sha256(book.read_bytes()).hexdigest(),'ledger_mm2':vm['ledger'][0],
 'top':'ot_hbm_die_vm_multicast_root','ENABLE_default':0,'banks':2,'depth_each':128,'payload_bits':payload,'owner_bits':owner,'identity_source':'ot_hbm_r14_pkg.identity_t actual192 bits',
 'coded_words_each_row':codes,'coded_bits_each_row':codes*72,'macros_each_bank':macros,'macro_count':2*macros,
 'actual_macro_area_um2':2*macros*j['area']['macro_area_um2'],'macro_model_sha256':hashlib.sha256(m.read_bytes()).hexdigest(),
 'read_bits_per_cycle':2*macros*256,'write_bits_per_cycle':macros*256,'multicast_bits_per_cycle':4*payload,
 'port_contract':'one owned write/read at a time; 4 held multicast streams and 4 matching192bit reverse ACKs',
 'mutable_sram_protection':'encode64/decode64 on data+owner; actual SRAM readback required before write ACK; protected validity/control/publication seats',
 'period_ps':833.333,'SS_setup_uncertainty_ps':60,'FF_hold_uncertainty_ps':25,
 'macro_SS_clk_to_q_ps':j['timing']['ss']['clk_to_q_ps'],
 'capacity_reservation_um2':vm['size_um'][0][0]*vm['size_um'][0][1],
 'utilization_target':0.55,'RTL_measurement_required':True,'physical_closed':False,'parent_connections_bound':False,
 'provisional_latency_edges':{'write_accept_to_verified_ack':5,'read_accept_to_publication':4,'release_after_all_reverse_ACK':1},
 'whole_VM_parent_complete':False,'result_publication_and_SU_index_ports':'sourceowner binding required; this root implements activation staging/multicast only',
 'gain_or_adoption_credit':False,'route_launch_allowed':False}
out.mkdir(parents=True,exist_ok=True);(out/'vm_root_prebuild.json').write_text(json.dumps(rec,indent=2)+'\n');print(json.dumps(rec))
