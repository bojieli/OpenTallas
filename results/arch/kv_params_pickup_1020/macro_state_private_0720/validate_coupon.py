from pathlib import Path
import json,re,hashlib,sys
r=Path(sys.argv[1] if len(sys.argv)>1 else '.');p=r/'SUMMARY.json'
if not p.exists():raise SystemExit('PENDING: no proof verdict')
s=json.loads(p.read_text());out={};ok=True
for mut in range(4):
 key=str(mut)
 if key not in s:out[key]={'status':'PENDING'};ok=False;continue
 row=s[key];log=(r/f'm{mut}.log').read_text();arrnames=set(re.findall(r'Presumably equivalent wires:.*?arr\[(\d+)\]',log));setup=all(x in log for x in ['Executing EQUIV_MAKE','Executing EQUIV_STATUS'])
 # Zero explicit init constraints and all original memory/read state bits mandatory.
 state_ok=row['array_bits']==4096 and row['read_bits']==128 and not row['init_constraints'];verdict=(row['rc']==0 and 'Equivalence successfully proven!' in log) if mut==0 else (row['rc']!=0 and bool(re.search(r'Found [1-9][0-9]* unproven \$equiv cells',log)))
 # Recipe allows up to depth2; before calling this a one-step coupon, require actual proof trace never needed2.
 depth2=bool(re.search(r'(?:Trying|prove|Proving).*?(?:step|depth)\s+2',log,re.I));out[key]={'setup_complete':setup,'state_exact_no_zero_init':state_ok,'expected_formal_verdict':verdict,'array_word_correspondences_in_log':len(arrnames),'depth2_trace_detected':depth2,'one_step_coupon_qualified':mut==0 and setup and state_ok and verdict and not depth2,'log_sha256':hashlib.sha256((r/f'm{mut}.log').read_bytes()).hexdigest()};ok &= setup and state_ok and verdict
(r/'COUPON_VALIDATION.json').write_text(json.dumps({'all_four_expected_results':bool(ok),'checks':out,'scope':'PRIVATEmacrostatecompositiononly; notleafreceipt and does notremove1076failedcutcomparisons','one_step_note':'If proof uses depth2 or trace ambiguous, rerun positive from same pre_m0.json with equiv_induct-seq1 before claiming exactone-step coupon; no source edit or droppedstate.'},indent=2)+'\n');print(json.dumps(out,indent=2))
