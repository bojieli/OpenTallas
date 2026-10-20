from pathlib import Path
import json,re,hashlib,collections,csv
p=Path('/home/ubuntu/scratch/codex-qw-tload-native-1020/clock_endpoint_audit');n=Path('/home/ubuntu/wt/codex-qw-tload-safe-recovery-0040-1020/results/arch/qw_tload_recovery_1020/ns4_gate_native');s=json.loads((n/'summary.json').read_text());rows=json.loads((n/'rows.json').read_text());roles=json.loads((p/'actual_lib_roles.json').read_text());seq=roles['sequential_actual_lib_roles'];norm=lambda x:x.replace('\\','');bydrv={r['driver']:r for r in rows};instmaster={r['driver'].rsplit('/',1)[0]:r['master']for r in rows if r['master']!='PORT'};ports=list(csv.DictReader((p/'ot_pin_regs.tsv').open(),delimiter='\t'));errors=[];cover=[];derive=set()
def clockpin(inst,master):
 meta=seq.get(master)
 if not meta:errors.append('nonsequentialmaster '+master);return None
 if meta['next_state']not in ['D','!D',"D'"]:errors.append('foreignnextstate '+master);return None
 cp=[k for k,v in meta['pins'].items()if v.get('clock')]
 if len(cp)!=1 or meta['clocked_on']!=cp[0]:errors.append('ambiguousactualLibclock '+master);return None
 return norm(inst+'/'+cp[0])
expected_in=set();expected_out=set()
for port in ports:
 if port['why']=='clock':continue
 bits=[port['port']]if int(port['width'])==1 else[f"{port['port']}[{i}]"for i in range(int(port['width']))]
 for bit in bits:
  rec={'port_bit':bit,'direction':port['dir'],'role':port['why']}
  if port['dir']=='input':
   expected_in.add('PORT/'+bit);r=bydrv.get('PORT/'+bit)
   if r is None or r['terminals']!=1:errors.append('inputendpointcount '+bit);continue
   ep=r['endpoints'][0];inst,pin=ep.rsplit('/',1);master=instmaster.get(inst,'?')
   if pin!='D':errors.append('inputnotfirstD '+ep)
   cp=clockpin(inst,master);rec.update(first_capture_data_pin=norm(ep),first_capture_master=master,native_clock_pin=cp,max_native_pin_bbox_L1_um=r['max_L1_pin_bbox_upper_um'])
  else:
   expected_out.add('PORT/'+bit);rr=[r for r in rows if 'PORT/'+bit in r['endpoints']and r['master']in seq]
   if len(rr)!=1:errors.append('outputlastseqcount '+bit+':'+str(len(rr)));continue
   r=rr[0];inst,pin=r['driver'].rsplit('/',1);cp=clockpin(inst,r['master']);rec.update(last_launch_output_pin=norm(r['driver']),last_launch_master=r['master'],native_clock_pin=cp,max_native_pin_bbox_L1_um=r['max_L1_pin_bbox_upper_um'])
  if cp:derive.add(cp)
  cover.append(rec)
actual_inputs={r['driver']for r in rows if r['master']=='PORT'}-{'PORT/ck'};actual_outputs={e for r in rows for e in r['endpoints']if e.startswith('PORT/')}
if actual_inputs!=expected_in:errors.append('actualinputsetmismatch')
if actual_outputs!=expected_out:errors.append('actualoutputsetmismatch')
r={'source':'ccb102bce','native_grt_odb_sha256':s['odb_sha256'],'native_lib_sources':s['lib_sources'],'covered_port_bits':len(cover),'input_bits_including_reset':len(expected_in),'output_bits':len(expected_out),'unique_boundary_FF_clocks':len(derive),'errors':errors,'per_port_bit':cover,'scope':'Actualnativebuffer/INVtransparentfirstdataFF andlastlaunchFF. NativeLibff/unarynext_stateD-or-!D(recordedactualpolarity)/clocked_on andclock:trueboundroles, no masternamefilter/no sequentialfunctionalmodel. ALLactualnonPGfunctionalBTermbits+reset, exactidentitysets compared to original unfilteredclockhelperstructuralboundary.'}
for c in ['tt','ff']:
 eps=json.loads((p/f'{c}_all.json').read_text());eb={norm(x['pin'])for x in eps if x.get('boundary')};epm={norm(x['pin']):x for x in eps};mac=[x for x in eps if x['macro_master']];missing=sorted(derive-eb);extra=sorted(eb-derive);r[c]={'same_original_helper_boundary_set':eb==derive,'missing_from_helper_boundary':missing,'extra_original_helper_boundary':extra,'macro_clocks':mac};sel=[epm[x]for x in derive if x in epm]+mac;lo=min(sel,key=lambda x:x['arrival_ps']);hi=max(sel,key=lambda x:x['arrival_ps']);r[c]['complete_boundary_plus_realROM_pin_envelope']={'count':len(sel),'min':lo,'max':hi,'spread_ps':hi['arrival_ps']-lo['arrival_ps'],'within80':hi['arrival_ps']-lo['arrival_ps']<=80}
 if missing or extra or len(mac)!=4:errors.append(c+'boundaryormacrocoverageFAIL')
r['PASS']=not errors and all(r[c]['same_original_helper_boundary_set']and r[c]['complete_boundary_plus_realROM_pin_envelope']['within80']for c in ['tt','ff']);(p/'boundary_coverage.json').write_text(json.dumps(r,indent=2)+'\n');print({k:r[k]for k in ['covered_port_bits','input_bits_including_reset','output_bits','unique_boundary_FF_clocks','errors','PASS']});print({c:{'same_original_helper_boundary_set':r[c]['same_original_helper_boundary_set'],'complete_envelope':r[c]['complete_boundary_plus_realROM_pin_envelope']}for c in ['tt','ff']});assert r['PASS']
