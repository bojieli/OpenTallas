from pathlib import Path
import glob,gzip,hashlib,json,subprocess
base=Path('/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM'); out=Path('/work'); libs=[]; hashes={}
for kind in ['AO','INVBUF','OA','SEQ','SIMPLE']:
 fs=list(base.glob('asap7sc7p5t_'+kind+'_RVT_TT_nldm_*lib*')); assert len(fs)==1,fs
 src=fs[0]; raw=src.read_bytes(); dst=out/(kind+'.lib');dst.write_bytes(gzip.decompress(raw) if src.suffix=='.gz' else raw);libs.append(dst);hashes[str(src)]=hashlib.sha256(raw).hexdigest()
bbs=list(Path('/src/physical/asap7_memory_macros_v2').glob('ctl_sram*/*_bb.v')); assert bbs,bbs
for p in bbs: hashes[str(p)]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'library_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n')
cmds=['read_liberty -lib '+str(p) for p in libs]+['read_verilog -lib '+str(p) for p in bbs]+['read_verilog /work/qkd_kvs_ctl_s32.sv','hierarchy -check -top qkd_kvs_ctl_s32','synth -top qkd_kvs_ctl_s32','check','write_verilog -noattr /work/qkd_kvs_ctl_s32.mapped.v']
with (out/'resynth.log').open('w') as f:rc=subprocess.run(['yosys','-p','; '.join(cmds)],stdout=f,stderr=subprocess.STDOUT).returncode
print('CTL_SAFE32_RESYNTH',rc,flush=True);raise SystemExit(rc)
