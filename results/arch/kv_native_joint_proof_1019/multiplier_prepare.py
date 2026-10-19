from pathlib import Path
import shutil,json,hashlib
r=Path(__file__).resolve().parent/'multiplier';r.mkdir(exist_ok=True)
src=Path('/srv/opentallas-scratch/claude/kv-params-1019/src/rtl/hdc')
for n in ['ot_hdc_fp32_add_lat.sv','ot_hdc_prefix.sv','ot_hdc_delay.sv']:
 shutil.copy2(src/n,r/n)
for n in ['current_mul.sv','closed_mul.sv']:
 shutil.copy2(Path(__file__).parent/n,r/n)
shutil.copy2(Path('/srv/opentallas-scratch/claude/kv-params-1019/src/physical/ref_tile/ot_qkh_ktree_m5/src/rtl/hdc/ot_hdc_fastfp.sv'),r/'ot_hdc_fastfp.sv')
deps='ot_hdc_fastfp.sv ot_hdc_fp32_add_lat.sv ot_hdc_prefix.sv ot_hdc_delay.sv'
y=''
for file,side in [('closed_mul.sv','gold'),('current_mul.sv','gate')]:
 y+='design -reset\nread_verilog -sv -DSYNTHESIS '+deps+' '+file+'\n'
 y+='hierarchy -check -top ot_hdc_fp32_mul_lat -chparam LAT 6\nproc\nflatten\nopt_clean\nrename ot_hdc_fp32_mul_lat '+side+'\ndesign -stash '+side+'\n'
y+='design -reset\ndesign -copy-from gold -as gold gold\ndesign -copy-from gate -as gate gate\nasync2sync\nequiv_make gold gate equiv\nhierarchy -top equiv\nequiv_simple -seq 2\nequiv_induct\nequiv_status -assert\n'
(r/'default_equiv.ys').write_text(y)
(r/'hashes.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in r.glob('*.sv')},indent=2)+'\n')
