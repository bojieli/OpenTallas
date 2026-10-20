from pathlib import Path
import subprocess,json,hashlib,time,re
r=Path.cwd();ys='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys';res={}
for mut in range(4):
 script=f"read_verilog -sv -DOT_MEM_NO_INIT actual.v\nrename ot_sram_1r1w_32x128_m1 gold\nread_verilog -sv model.v\nchparam -set MUT {mut} gate\nproc\nmemory -nomap\nmemory_map\nopt_clean\nwrite_json pre_m{mut}.json\nequiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple -seq 1\nequiv_induct -seq 2\nequiv_status -assert\n"
 (r/f'm{mut}.ys').write_text(script);start=time.monotonic()
 with (r/f'm{mut}.out').open('w') as f:p=subprocess.run([ys,'-l',f'm{mut}.log','-s',f'm{mut}.ys'],stdout=f,stderr=subprocess.STDOUT)
 text=(r/f'm{mut}.log').read_text();d=json.loads((r/f'pre_m{mut}.json').read_text());gold=d['modules']['gold'];gate=d['modules']['gate'];words=[k for k in gold['netnames'] if re.fullmatch(r'arr\[\d+\]',k)];rd=gold['netnames']['rd_out'];counts=[int(x) for x in re.findall(r'Found (\d+) unproven \$equiv cells',text)];ini=[(m,n,v['attributes'].get('init')) for m,mo in d['modules'].items() for n,v in mo['netnames'].items() if v['attributes'].get('init') is not None]
 row={'mut':mut,'rc':p.returncode,'seconds':time.monotonic()-start,'array_words':len(words),'array_bits':sum(len(gold['netnames'][k]['bits']) for k in words),'read_bits':len(rd['bits']),'init_constraints':ini,'log_sha256':hashlib.sha256((r/f'm{mut}.log').read_bytes()).hexdigest(),'proven':p.returncode==0 and 'Equivalence successfully proven!' in text,'unproven_final':counts[-1] if counts else None};res[str(mut)]=row;(r/'SUMMARY.json').write_text(json.dumps(res,indent=2)+'\n');print(json.dumps(row),flush=True)
 if mut==0 and not row['proven']:raise SystemExit('positive setup/proof failed; preserve before causals')
 if row['array_bits']!=4096 or row['read_bits']!=128 or ini:raise SystemExit('state/initial relation mismatch')
 if mut and p.returncode==0:raise SystemExit('ineffective mutant')
