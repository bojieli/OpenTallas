"""Fail-closed zero-only compatibility for mixed native preferred source closure."""
import hashlib,json,pathlib,re,subprocess,tempfile
ROOT=pathlib.Path(__file__).resolve().parents[2];BASE=ROOT/'physical/die_plan/hbm_arch_cores';HERE=pathlib.Path(__file__).parent
raw=(BASE/'native_1030/ot_hbm_su_static_replicated_bank.sv').read_text();old='parameter integer READERS=6,RB=9,MUT_COHERENCE=0';new=old+',WCOPY=0'
assert raw.count(old)==1
needle=' initial if(RB!=9)';guard=' initial if(WCOPY!=0)$fatal(1,"Native zero-only provider rejects WCOPY!=0");\n'
assert raw.count(needle)==1
fixed=raw.replace(old,new).replace(needle,guard+needle)
assert fixed.replace(new,old).replace(guard,'')==raw
out=BASE/'wrappers/ot_hbm_su_static_replicated_bank__native_zero.sv';out.write_text(fixed)
# Qualified native Yosys elaboration tests parameter guard; zero body remains byte-identical.
results=[]
for val in [0,1]:
 cmd=['yosys','-Q','-T','-p',f'read_verilog -sv {out}; hierarchy -top ot_hbm_su_static_replicated_bank -chparam WCOPY {val}; proc']
 r=subprocess.run(cmd,capture_output=True,text=True);assert (r.returncode==0)==(val==0),(val,r.stdout,r.stderr)
 results.append(dict(WCOPY=val,rc=r.returncode,output=r.stdout+r.stderr))
(HERE/'zero_wcopy_receipt.json').write_text(json.dumps(dict(status='PASS_ZERO_BODY_IDENTITY_NONZERO_MUTANT_REJECTED',original_sha256=hashlib.sha256(raw.encode()).hexdigest(),fixed_sha256=hashlib.sha256(fixed.encode()).hexdigest(),proof='Removing added parameter declaration and fail-closed initial guard exactly restores full original module bytes; WCOPY0 elaborates same body with no state/logic/timing/cycle change. Actual native cut and pinned bank setWCOPY0.',test_scope='Actual Yosys parameter elaboration only, no SRAM behavior claim',results=results),indent=1)+'\n');print('PASS zero-only WCOPY source identity + nonzero mutant')
