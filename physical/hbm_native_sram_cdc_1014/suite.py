#!/usr/bin/env python3
"""Actual catalog SRAM functional/boundary gate; no P&R/analog/price inheritance."""
import pathlib,sys,subprocess,json,re,hashlib
ROOT=pathlib.Path(__file__).resolve().parents[2];out=pathlib.Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
cases=[]
for w in [16,280,256,1]:
 for phase in [61,487]:
  for rev in [0,1]:cases.append((f'exact_w{w}_p{phase}_r{rev}',w,phase,rev,0,0,0))
cases += [('simultaneous_edges',280,0,0,0,0,0),('sram_single_correct',280,61,0,0,1,0),('sram_double_poison',280,61,0,0,2,0),('source_rail',280,487,0,0,3,0),('pending_epoch',280,487,0,0,4,0),('held_payload',280,61,0,0,5,0),('ue_bypass_mutant',280,61,0,2,2,1),('slot_overwrite_mutant',280,487,0,1,0,1),('premature_credit_mutant',280,61,0,4,0,1)]
rec=[]
for name,w,phase,rev,mut,mode,negative in cases:
 r=subprocess.run(['bash',str(ROOT/'physical/hbm_native_sram_cdc_1014/bench.sh'),str(out/name),str(w),str(phase),str(rev),str(mut),str(mode)],cwd=ROOT,text=True,capture_output=True)
 log=r.stdout+r.stderr;accepted=(r.returncode!=0 and bool(re.search('PAYLOAD_MISMATCH|LOGICAL_CAPACITY|unexpected consumer fault',log))) if negative else (r.returncode==0 and 'PASS' in log)
 item={'case':name,'W':w,'phase_ps':phase,'reverse':rev,'MUT':mut,'MODE':mode,'expect':'fail' if negative else 'pass','returncode':r.returncode,'expectation_met':accepted,'output':log}
 m=re.search(r'first_access_ps=([\d.]+)',log)
 if m:item['first_access_ps']=float(m[1])
 rec.append(item);print(name,'PASS' if accepted else 'FAIL',r.returncode,flush=True)
 if not accepted:break
macro=ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_64x512_m1_r2c2/ot_sram_1r1w_64x512_m1_r2c2.json';descriptor=json.loads(macro.read_text())
result={'schema':'opentallas.native.sram_cdc.actual_gate.v1','verdict':'PASS' if len(rec)==len(cases) and all(c['expectation_met'] for c in rec) else 'FAIL','source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'physical/hbm_native_sram_cdc_1014').glob('*') if p.is_file()},'macro_descriptor_sha256':hashlib.sha256(macro.read_bytes()).hexdigest(),'macro_claim_boundary':descriptor['claim_boundary'],'cases':rec,'model_price_184_inherited':False,'scope':'ActualsingleclockcatalogSRAMwrites/reads/source8heldcodedslots/protectedepoch/credits andconsumerregisteredlanding. Engine4:VM3 bothdirections/phases; exactpayload/heldstalls/clockwrap/creditconservation/rawSRAMCE/UE/rail/output/epoch boundaries. No actualnativeproductioncomposition/P&R/analogmetastability/siliconclaim.'}
(out/'gate.json').write_text(json.dumps(result,indent=2)+'\n');print('SRAM_CDC_SUITE',result['verdict'],flush=True);sys.exit(0 if result['verdict']=='PASS' else 1)
