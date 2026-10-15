#!/usr/bin/env python3
import argparse,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--work',type=Path,required=True);p.add_argument('--mut',choices=['PHW','SAW','CALGO','PQSLOT','PRIME']);p.add_argument('--calcap',action='store_true');p.add_argument('--produced',action='store_true');p.add_argument('--sequenced',action='store_true',help='real host CSR/FIFO -> c9 engine13 -> actual PHW10 PQ + mapped memories');p.add_argument('--rom4',action='store_true',help='DSFD_PQ_ROM4: die stream ROM = four 4096-row macros, select in dsfd_sp_pq_n');a=p.parse_args();
if a.sequenced:a.produced=True;a.calcap=True;a.rom4=True
a.work.mkdir(parents=True,exist_ok=True)
v=os.environ.get('OT_VERILATOR',str(Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'))
src=[str(p) for p in (ROOT/'physical/s81_pq_hier/pinned').rglob('*.sv') if p.name!='ot_sram_1r1w_128x256_m1_r2c2.sv']
src += [str(p) for p in (ROOT/'rtl/dsrom_sys/s81_ph/pq').glob('*.sv')]
src += [str(ROOT/p) for p in ['rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv','rtl/test/dsrom_sys/tb_s81_pq_canonical_pins.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v','physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']]
if a.produced:
 src=[x.replace('tb_s81_pq_canonical_pins.sv','tb_s81_pq_produced_pins.sv') for x in src]
 src += [str(ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_produced.sv')]
 src += [str(ROOT/'rtl/dsrom_sys/s81_static_control'/f) for f in ['ot_s81_pq_command_endpoint.sv','ot_s81_pq_calendar_reader.sv','ot_s81_pq_calendar_rom.sv']]
 os.environ['OT_ROM_DIR']=str(a.work.resolve())
 import sys
 sys.path.insert(0,str(ROOT/'tools/s81_static_control'))
 from pq_calendar import action_word,viamap
 rows=[(8,{'cfg':1}),(12,{'stream_req':1,'stream_addr':16383}),(30,{'retire_mask':1}),(40,{'phase_end':1})]
 packed=[(time<<75)|action_word(fields,action_bits=75) for time,fields in rows]
 for name,words in [('action',[w&((1<<72)-1) for w in packed]),('time',[w>>72 for w in packed])]:
  (a.work/f'pq_calendar_{name}.viamap.hex').write_text(viamap(words))
if a.sequenced:
 src=[x.replace('tb_s81_pq_produced_pins.sv','tb_s81_pq_sequenced_pins.sv')for x in src]
 host_sources=['rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv','rtl/lib/ot_async_fifo.sv','rtl/lib/ot_reset_sync.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv','rtl/lib/ot_rst_relay.sv','rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv','rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv','rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv','physical/rom_host_ingest/rtl/dsfd_host.sv','rtl/hdc/ingest/ot_rom_host_ingest.sv','rtl/link/ot_link_afifo.sv','rtl/hdc/ingest/ot_hdc_kv_ingest.sv','rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv']
 src += [str(ROOT/x)for x in host_sources]
 src += [str(ROOT/'rtl/dsrom_sys/s81_static_control'/x)for x in ['dsfd_stage_seq_static_c9.sv','dsfd_stage_seq_static_c.sv','ot_s81_fixed_issue.sv','ot_s81_fixed_mailbox.sv','ot_s81_pq_boot_control.sv']]
 from pq_stage import compile_stage
 descriptors=[dict(ph=514,np=0,xbase=0,xps=0,obase=0,ops=0,fmt=0,observed_end_edges=35,native_tag=0)]
 rows=[dict(engine=13,arg=0,issue=0,done=38,pin_to_pin=37,native_tag=0),dict(engine=14,arg=0,issue=39,done=0),dict(engine=15,arg=0,issue=40,done=0)]
 events=[dict(timestamp=1,action=dict(accept_tag=0)),dict(timestamp=10,action=dict(cfg=1)),dict(timestamp=14,action=dict(stream_req=1,stream_addr=16383)),dict(timestamp=32,action=dict(retire_mask=1)),dict(timestamp=42,action=dict(phase_end=1))]
 image=compile_stage(rows,descriptors,events,7,0)
 packets=image['host_packets']
 # Declared external initialization CSR words exercise the real HOST h/i
 # async FIFO; all22 programming packets above are intentionally intercepted.
 packets=sorted(packets+[dict(host_stream_cycle=600+8*i,cls=0,data=0)for i in range(12)],key=lambda x:x['host_stream_cycle'])
 (a.work/'host_words.hex').write_text(''.join(f"{x['data']:0128x}\n"for x in packets))
 (a.work/'host_cycles.hex').write_text(''.join(f"{x['host_stream_cycle']:08x}\n"for x in packets))
 for name in ['action','time']:(a.work/f'pq_calendar_{name}.viamap.hex').write_text(image[f'calendar_{name}_viamap'])
 import json
 (a.work/'image.json').write_text(json.dumps(image,indent=2)+'\n')
 defs_extra=['DSFD_HOST_C_STATIC','DSFD_HOST_PQ_BOOT']
else:defs_extra=[]
defs=['OT_PQ_ROM_PORTS' ,'OT_PQ_CTL_STATIC','OT_PQ_QB_PIPE','OT_PQ_QB_PHYS_SPLIT','OT_PQ_AQ_PHYS_SPLIT','OT_PQ_IX_PHYS_SPLIT','OT_PQ_IX_BANK_SPLIT','OT_PQ_BC_SLICED','DSFD_PQ_STATIC_X2']
defs+=defs_extra
if a.produced:defs+=['OT_PQ_CTL_STATE_PINS','OT_PQ_CTL_INCAP','OT_PQ_AQ_PIN_LAUNCH']  # captured-input ctl leaf; AQ leaves launch from its registered aq_vin
if a.calcap:defs.append('OT_PQ_CTL_CALCAP')
if a.rom4:defs.append('DSFD_PQ_ROM4')
if a.mut=='PQSLOT':defs.append('OT_SSEQS_MUT_PQ_ABSENT')
elif a.mut=='PRIME':defs.append('OT_SSEQS_MUT_PQ_PRIME')
elif a.mut=='CALGO':defs.append('OT_S81_PQ_CALCAP_MUT_GO')
elif a.mut:defs.append('OT_S81_PQ_STATIC_MUT_'+a.mut)
if a.produced and a.mut=='PHW':defs.append('OT_S81_PQ_PRODUCER_MUT_PHW')
cmd=[v,'--binary','--timing','--top-module',('tb_s81_pq_sequenced_pins' if a.sequenced else 'tb_s81_pq_produced_pins' if a.produced else 'tb_s81_pq_canonical_pins'),'--Mdir',str(a.work.resolve()/'obj'),'-j','8','-Wno-fatal','-Wno-lint','-Wno-style',*[f'+define+{d}' for d in defs],*src]
with (a.work/'build.log').open('w') as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
with (a.work/'run.log').open('w') as f:rc=subprocess.run([str(a.work.resolve()/('obj/Vtb_s81_pq_sequenced_pins' if a.sequenced else 'obj/Vtb_s81_pq_produced_pins' if a.produced else 'obj/Vtb_s81_pq_canonical_pins')), *(['+OT_ROM_DIR='+str(a.work.resolve())] if a.produced else []), *(['+packets='+str(len(packets))] if a.sequenced else [])],stdout=f,stderr=subprocess.STDOUT,cwd=a.work.resolve()).returncode
if a.mut:
 if rc==0 or ('SEQUENCED FAIL' if a.sequenced else 'PRODUCED FAIL' if a.produced else 'CANONICAL_PINS FAIL') not in (a.work/'run.log').read_text():raise SystemExit('mutant did not fail the native pin gate')
elif rc:raise SystemExit(rc)
if a.sequenced and not a.mut:
 for ph,pi in [(1,4),(4,1)]:
  log=a.work/f'run.phase{ph}_{pi}.log'
  with log.open('w')as f:
   prc=subprocess.run([str(a.work.resolve()/'obj/Vtb_s81_pq_sequenced_pins'),'+OT_ROM_DIR='+str(a.work.resolve()),'+packets='+str(len(packets)),f'+phase_h={ph}',f'+phase_i={pi}'],stdout=f,stderr=subprocess.STDOUT,cwd=a.work.resolve()).returncode
  if prc:raise SystemExit(log.read_text())
  print(log.read_text())
print((a.work/'run.log').read_text())
