from pathlib import Path
import subprocess,sys
p=Path(sys.argv[1] if len(sys.argv)>1 else '../full_proof_r2');exe=(p/'obj/Vtb_qwen_a0_rr9_n32').resolve()
for mut in [60,61,62,63,64]:
 log=p/f'run_{mut}.log'
 with log.open('w') as f:r=subprocess.run([str(exe),f'+MUT={mut}'],stdout=f,stderr=subprocess.STDOUT)
 text=log.read_text();assert r.returncode!=0 and 'A0_RR9_FAIL' in text,(mut,r.returncode,text[-700:])
 print('FULL_LAND32_MUTANT_CAUGHT',mut,flush=True)
