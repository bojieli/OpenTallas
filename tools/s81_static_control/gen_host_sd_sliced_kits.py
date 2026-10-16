import json,pathlib,subprocess
P=pathlib.Path('physical/s81_die_pins/host_sd_sliced_1016');src=['rtl/dsrom_sys/s81_ingest/dsfd_host_sd_sliced.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv','rtl/lib/ot_reset_sync.sv','rtl/lib/ot_rst_relay.sv']
for k in range(5):
 data=k<4;name=f's81_host_sd_data64_s{k}' if data else 's81_host_sd_control';top='dsfd_host_sd_data64' if data else 'dsfd_host_sd_control';w,h=(93.96,25.92) if data else (54.0,51.84)
 pins=[]
 def pin(n,face,at):
  x,y={'N':(at,h),'S':(at,0),'E':(w,at),'W':(0,at)}[face];layer='M5' if face in 'NS' else 'M4';sz='0.024 0.192' if face in 'NS' else '0.192 0.024';pins.append(f'place_pin -pin_name {{{n}}} -layer {layer} -location {{{x:.3f} {y:.3f}}} -pin_size {{{sz}}} -force_to_die_boundary')
 if data:
  for i in range(64):pin(f'hw_data[{i}]','S',1.44*(i+1));pin(f'o_d[{i}]','N',1.44*(i+1))
  pin('hw_valid','S',0.36);pin('ck','N',93.0);pin('rst_n','N',0.36);pin('hc_cr','N',93.6)
  east=[f'o_addr[{i}]' for i in range(32)]+['o_v','o_we','marker_class[0]','marker_class[1]']
  for i,n in enumerate(east):pin(n,'E',0.72+i*0.672)
  pin('fault','W',h/2)
 else:
  north=[f'o_addr[{i}]' for i in range(32)]+['o_v','o_we','marker_class[0]','marker_class[1]']
  south=[f'hw_control[{i}]' for i in range(36)]+['o_cr']+[f'host_ack_n[{i}]' for i in range(8)]+['fault']
  for i,n in enumerate(north):pin(n,'N',1.44*(i+1))
  for i,n in enumerate(south):pin(n,'S',1.08*(i+1))
  for i in range(9):pin(f'hc[{i}]','E',2.16*(i+1))
  pin('ck','W',h/2);pin('rst_n','W',h/2+1.08)
 tcl=P/(name+'.tcl');tcl.write_text('# PROPOSED source-bound split pins; parent slot request S81-HOST-SD-SPLIT-1016\n'+'\n'.join(pins)+'\n')
 s=dict(name=name,top=top,kind='tile',sources=src,params=dict(NS=1,KVS=1,**({'SLICE':k} if data else {})),clock='ck',clock_port='ck',reset_ports=['rst_n'],outline=dict(w=w,h=h,exact=True),layer_cap='M5',pins={'N':['o_d','ck','rst_n','hc_cr'] if data else ['o_addr','o_v','o_we','marker_class'],'S':['hw_data','hw_valid'] if data else ['hw_control','o_cr','host_ack_n','fault'],'E':['o_addr','o_v','o_we','marker_class'] if data else ['hc'],'W':['fault'] if data else ['ck','rst_n']},io_tcl=str(tcl),recipe=3,inhold=True,outhold=True,keep_pin_regs=True,io_flop_at_pins=dict(cols=2,allow_none=True),pin_regs=dict(enable=False,reason='Actual projected decoder captures native inputs and clocks output pins; shared local replica state; no extra pipeline stages.'),structural_change='Source-backed HOST split: each64-bit S-face datapath localizes prior hw full425um spread to <=93.96um; original decoder projected by output observability with local equal pointers, independently conditioned reset and die phi-R clock. STATIC1 head-service faults instead of waiting for credits. Source-specific exact256/header/calendar +4 mutants +missingcredit no-reschedule proof. WholeHOST/native die qualification remains OPEN.',slot_change_request='S81-HOST-SD-SPLIT-1016',job=dict(owner='Codex:S81-HOST0253',branch='codex/s81-host-recovery-0253',tag='s1',purpose='Harden actual projected HOST local clock leaf; native pin timing/TT/FF/DRC required.',views_to=f'physical/ref_tile/{name}/views',record_to=f'results/rtl/ref_tile/{name}',extra_paths=['rtl/dsrom_sys/s81_ingest','rtl/lib','tests/s81','tools/s81_static_control',str(P)],benches=[dict(name='actual_sliced_sd_exact',cmd='bash tools/s81_static_control/host_sd_sliced_gate.sh {RUN}/sd_split',expect='pass',threads=1,peak_ram_gb=2,needs=['iverilog'],pass_regex='HOST_SD_SLICED_GATE PASS')]))
 spec=P/(name+'.spec.json');spec.write_text(json.dumps(s,indent=1)+'\n');subprocess.run(['python3','tools/ref_tile/ref_tile.py','gen',str(spec)],check=True)
