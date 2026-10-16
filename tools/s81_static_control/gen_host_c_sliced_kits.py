#!/usr/bin/env python3
"""Prepare source-complete HOST leaf specs at a conservative proposed outline.

Parent slots/pin cuts and current-flow native gates remain required before
route admission. The larger native region is deliberate analytical margin.
"""
from pathlib import Path
import json,re,subprocess
P=Path('physical/s81_die_pins/host_sd_sliced_1016');P.mkdir(parents=True,exist_ok=True)
SRC=['rtl/dsrom_sys/s81_ingest/dsfd_host_c_sliced.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd_sliced.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv','rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv','physical/rom_host_ingest/rtl/dsfd_host.sv','rtl/hdc/ingest/ot_rom_host_ingest.sv','rtl/link/ot_link_afifo.sv','rtl/hdc/ingest/ot_hdc_kv_ingest.sv','rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv']
for native in [False,True]:
 name='s81_host_ingest_native_local' if native else 's81_host_ectl_local';top='dsfd_host_native_leaf' if native else 'dsfd_host_c_ectl';w,h=(399.6,77.76) if native else (54.,77.76);pins=[];faces={k:[] for k in ['N','S','E','W']}
 def pin(n,face,at,layer=None):
  ly=layer or ('M5' if face in 'NS' else 'M4');pitch=.036 if ly=='M3' else .048;at=round(at/pitch)*pitch
  x,y={'N':(at,h),'S':(at,0),'E':(w,at),'W':(0,at)}[face];sz='0.024 0.192' if face in 'NS' else '0.192 0.024';pins.append(f'place_pin -pin_name {{{n}}} -layer {ly} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary');base=n.split('[')[0]
  if base not in faces[face]:faces[face].append(base)
 if native:
  for b in range(515):pin(f'host_word[{b}]','E',.144+.096*b)
  pin('t_cr','E',50.0);pin('ck_launch','E',50.4);pin('rst_n','E',50.8)
  for b in range(256):pin(f'o_d[{b}]','S',25.2+1.44*b)
  for b in range(32):pin(f'o_addr[{b}]','S',320.+1.44*b,'M3')
  for b in range(8):pin(f'host_ack_n[{b}]','S',370.+1.44*b,'M3')
  pin('o_cr','S',382.,'M3');pin('o_v','S',395.6);pin('o_we','S',397.)
  for b in range(64):pin(f't_d[{b}]','N',300.+1.44*b)
  pin('t_v','N',393.);pin('fault','N',395.)
  pin('ck_write','N',199.8);pin('ck_core','N',201.24);pin('ck_host','E',51.2)
  ds={'core':dict(ratio=[1,1],ports=['ck_host'],inputs=['rst_n'],outputs=['t_v','t_d','fault']),'launch':dict(ratio=[1,1],ports=['ck_launch'],inputs=['host_word','t_cr'],outputs=[]),'ingest':dict(ratio=[1,1],ports=['ck_core'],inputs=[],outputs=[]),'write':dict(ratio=[1,1],ports=['ck_write'],inputs=['o_cr','host_ack_n'],outputs=['o_v','o_we','o_addr','o_d'])}
  clocks=['ck_host','ck_launch','ck_core','ck_write'];rel=dict(kind='same_pll_fixed_phase',ratio=[1,1],phase_ps=0);paths='related_same_frequency';params={};reset=['rst_n']
 else:
  # Preserve every original E-facing parent pin at the exact connected y.
  old=Path('physical/s81_die_pins/host_boot300_0015/dsfd_host_c.tcl').read_text()
  names={'f_collective','f_sseq_st','f_wfc_ft','t_collective','t_sseq_pw','t_pq_pw','t_sseq_plen'}
  for ln in old.splitlines():
   m=re.search(r'pin_name \{([^}]+)\}.*location \{([\d.]+) ([\d.]+)\}',ln)
   if m and m[1].split('[')[0] in names:pin(m[1],'E',float(m[3]))
  for b in range(515):pin(f'native_host_word[{b}]','W',26.064+.096*b)
  for b in range(32):pin(f'native_oa[{b}]','W',.36+.672*b)
  pin('native_marker[0]','W',22.);pin('native_marker[1]','W',22.7);pin('native_ocr','W',23.4)
  for b in range(8):pin(f'native_ack[{b}]','W',23.7+.192*b)
  for b in range(4):pin(f'data_fault[{b}]','W',75.6+.24*b)
  pin('native_tcr','W',76.8)
  for b in range(64):pin(f'native_td[{b}]','N',.72+.72*b)
  for n,x in [('native_tv',47.5),('native_fault',48.5),('native_ov',49.5),('native_owe',50.5),('ck_return',52.5)]:pin(n,'N',x)
  for b in range(36):pin(f'hw_control[{b}]','S',.72+1.44*b)
  for b in range(9):pin(f'hc[{b}]','S',.72+1.44*b,'M3')
  for b in range(4):pin(f'f_lf[{b}]','S',15.+1.44*b,'M3')
  for n,x in [('rst',21.),('rsv',22.5),('ck',25.92),('ckv',27.36),('ck_boot',28.8)]:pin(n,'S',x,'M3')
  ds={'core':dict(ratio=[1,1],ports=['ck'],inputs=['rst','f_collective','f_lf','hc','f_sseq_st','f_wfc_ft','native_ov','native_owe','native_oa','native_marker','data_fault'],outputs=['t_collective','hw_control','native_host_word','native_tcr','native_ocr','native_ack']),'serial':dict(ratio=[4,3],ports=['ckv'],inputs=['rsv'],outputs=['t_sseq_pw','t_pq_pw','t_sseq_plen']),'boot':dict(ratio=[4,1],ports=['ck_boot'],inputs=[],outputs=[]),'return':dict(ratio=[1,1],ports=['ck_return'],inputs=['native_tv','native_td','native_fault'],outputs=[])}
  clocks=['ck','ckv','ck_boot','ck_return'];rel=dict(kind='same_pll_fixed_phase',phase_ps=0,vco_dividers=dict(core=3,serial=4,boot=12,**{'return':3}));paths='related_pll_dividers';params=dict(NS=1,MUT=0);reset=['rst','rsv']
 tcl=P/(name+'.tcl');tcl.write_text('# PROPOSED v2 parent SLOT REQUEST, not granted physical inheritance\n'+'\n'.join(pins)+'\n')
 s=dict(name=name,top=top,kind='tile',sources=SRC,params=params,defines=['DSFD_HOST_C_STATIC','DSFD_HOST_PQ_BOOT','OT_S81_HOST_PHASESAFE','OT_S81_HOST_BOOT300'],clock='multiple_cts_roots',clock_port=clocks[0],clock_ports=clocks,clock_entry_domains=ds,clock_data_paths=paths,clock_relationship=rel,reset_ports=reset,outline=dict(w=w,h=h,exact=True),layer_cap='M5',pins=faces,io_tcl=str(tcl),recipe=3,inhold=True,outhold=True,keep_pin_regs=True,io_flop_at_pins=dict(cols=4,allow_none=True),pin_regs=dict(enable=False,reason='Actual declared-domain input capture/launch RTL owns every boundary; no generic single-clock wrapper across related roots. Pure-clock source lockups are inside the receiving hardened leaf, not parent result producers.'),slot_change_request='S81-HOST-SD-SPLIT-1016-v2',structural_change='Source-complete actualsixleafHOST: compactEcontrol54x77.76, fourSdata64 leaves95.04x25.92 andnativeingest399.6x77.76 underproposed453.6x103.68 parent. Larger nativeheight based oldwholeHOSTmeasured18612.7um2 and estimatednative14-16kum2, avoiding75-85pctdensity in obsolete51.84highslot. Actualallclockroots/sourcephaseordinary STA, independentrawresetconditioning, no threshold relaxation. Full59989edge/1093mixedCSR+IKEYpacket proof produces544actualnative sectors; corruptedpayload and nativeCSRfilterbypass mutantsfail. Normalexecutioncompiler reservations and nativefulltoken/throughput remainOPEN.',job=dict(owner='Codex:S81-HOST0253',branch='codex/s81-host-recovery-0253',tag='p1',purpose='Actual source/hardened HOST partition; no surrogate compute or nativeclosure claim before actualparent clocks/cuts.',views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}',extra_paths=['rtl/dsrom_sys/s81_ingest','rtl/lib','rtl/link','rtl/hdc/ingest','rtl/dsrom_sys/s81_ctrl','physical/rom_host_ingest/rtl','tools/s81_static_control','tools/rtl_rom_host_ingest_bench.py','tools/rtl_hdc_kv_ingest_campaign.py','tools/kv_ingest_ref.py','tests/s81',str(P)],benches=[dict(name='actual_sixleaf_HOST_mixed_native',cmd='python3 tools/s81_static_control/host_c_sliced_gate.py {RUN}/whole_host',expect='pass',threads=1,peak_ram_gb=4,needs=['iverilog','numpy'],pass_regex='HOST_C_SLICED_GATE PASS')]))
 spec=P/(name+'.spec.json');spec.write_text(json.dumps(s,indent=1)+'\n');subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(spec)],check=True)
