#!/usr/bin/env python3
"""Exact minimum numerical gate for the physically routed bd30aca exp recut."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
COMMIT='bd30aca4ae85a68de73ffea830c3a60a35418d3c'
OUT=ROOT/'results/rtl/dsrom_softmax_exp_recut_20261007'
WORK=Path('/tmp/dsrom_softmax_exp_recut_20261007')
SOURCES=['rtl/hdc/'+n for n in ['ot_hdc_delay.sv','ot_hdc_cg.sv','ot_hdc_fpu.sv','ot_hdc_fp32_mul_pipe.sv']]+['rtl/proto/ot_fp32_add_rne_pipe.sv']+['rtl/hdc/'+n for n in ['ot_hdc_sfu.sv','ot_hdc_fastfp.sv','ot_hdc_fastfp_lat_f12.sv','ot_hdc_fp32_f12.sv','ot_hdc_fp32_mul_lat.sv','ot_hdc_fp32_add_lat.sv','ot_hdc_prefix.sv']]+['rtl/hdc/v41x/'+n for n in ['ot_hdc_v41x_sfu.sv','ot_dsrom_su_fdiv_f12.sv','ot_dsrom_su_softmax_add6.sv','ot_dsrom_su_softmax_m9.sv','ot_dsrom_su_softmax_add.sv','ot_dsrom_su_softmax_f12r.sv','ot_dsrom_su_softmax_exp6.sv']]
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def prep():
 OUT.mkdir(parents=True,exist_ok=True);WORK.mkdir(parents=True,exist_ok=True)
 hashes={}
 for p in SOURCES+['tools/hdc_golden.py']:
  data=subprocess.check_output(['git','show',COMMIT+':'+p],cwd=ROOT);dst=WORK/'source'/p;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(data);hashes[p]=hashlib.sha256(data).hexdigest()
 sys.path.insert(0,str(WORK/'source/tools'));import hdc_golden as G
 rng=np.random.default_rng(81007)
 directed=np.array([0.,-0.,1.,-1.,88.,-87.,89.,-88.,np.finfo(np.float32).max,-np.finfo(np.float32).max,np.finfo(np.float32).tiny,-np.finfo(np.float32).tiny],np.float32)
 centers=np.arange(-126,128,dtype=np.float32)*np.float32(np.log(2))
 around=np.concatenate([np.nextafter(centers,np.float32(-np.inf)),centers,np.nextafter(centers,np.float32(np.inf))])
 raw=rng.integers(0,2**32,size=1024,dtype=np.uint32);raw[(raw&0x7f800000)==0x7f800000]=0
 x=np.concatenate([directed,around,rng.uniform(-100,100,2048).astype(np.float32),raw.view(np.float32)])
 y=G.exp(x).view(np.uint32);assert np.all(np.isfinite(y.view(np.float32)))
 (OUT/'inputs.hex').write_text(''.join(f'{int(v):08x}\n' for v in x.view(np.uint32)))
 (OUT/'expected.hex').write_text(''.join(f'{int(v):08x}\n' for v in y))
 model=dict(schema='opentallas.softmax_exp_recut_prebuild.v1',source_commit=COMMIT,source_sha256=hashes,top='ot_dsrom_su_softmax_exp_tile',parameters=dict(LM=11,LA=11,NSPLIT=2,ADDX=0),core_depth_cycles=172,tile_latency_cycles=173,initiation_interval=1,delta_vs_SAFE_LM9_LA9_NSPLIT2=30,delta_vs_unwrapped_LM9_LA9_NSPLIT2=31,job_cycles_added31_basis_requires_unwrapped_baseline=True,replicas=272,compute=dict(MACs_per_cycle=0,exp_results_per_cycle_per_replica=1),boundary=dict(input_bits_per_cycle=33,output_bits_per_cycle=34,memory_bytes_per_cycle=0,routing_tracks_per_replica_minimum=67,parent_available_tracks=None),physical=dict(tile_die_width_um=189.195,tile_area_mm2=189.195**2/1e6,parent_model='tools/dsrom_softmax_parent.py',SS_ps=123.11,FF_ps=16.70,DRC=0,parent_boundary_qualified=False,I2R_Infinity_Oport_1e9_not_finite_budget=True),vectors=len(x),golden='Commit-pinned independent hdc_golden.exp FP32 Cody-Waite/Horner/RNE contract',fixtures_sha256={n:digest(OUT/n) for n in ['inputs.hex','expected.hex']},adopted=False,scope='One exact routed source leaf; no272-replica or fullsoftmax numerical simulation. Physical closure and numerical exactness alone do not certify parent input/output or token model.')
 (OUT/'prebuild.json').write_text(json.dumps(model,indent=2)+'\n');print('PREP',len(x),'vectors')
def run(label,mutant):
 pre=json.loads((OUT/'prebuild.json').read_text());bench=ROOT/'rtl/experimental/dsrom_softmax_exp_recut_20261007/tb_exp_recut.sv'
 for p,h in pre['source_sha256'].items():assert digest(WORK/'source'/p)==h
 image=WORK/(label+'.vvp');log=OUT/(label+'.log');record=OUT/(label+'.json')
 if log.exists() or record.exists():raise RuntimeError('Immutable campaign exists')
 cmd=['iverilog','-g2012','-s','tb_exp_recut','-Ptb_exp_recut.N='+str(pre['vectors']),*(['-DSOFTMAX_SAFE_MUTANT'] if mutant else []),'-o',str(image),*[str(WORK/'source'/p) for p in SOURCES],str(bench)]
 with log.open('w') as f:
  c=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,cwd=ROOT)
  r=subprocess.run(['vvp',str(image),'+INPUT='+str(OUT/'inputs.hex'),'+EXPECTED='+str(OUT/'expected.hex')],stdout=f,stderr=subprocess.STDOUT,cwd=ROOT) if c.returncode==0 else None
 content=log.read_text();passed=c.returncode==0 and r is not None and ((r.returncode!=0 and 'EXP_EXACT_MISMATCH' in content) if mutant else (r.returncode==0 and 'PASS_EXP_RECUT' in content))
 data=dict(passed=passed,mutant=mutant,compile=cmd,compile_returncode=c.returncode,run_returncode=r.returncode if r else None,bench_sha256=digest(bench),prebuild_sha256=digest(OUT/'prebuild.json'),source_sha256=pre['source_sha256'],adopted=False)
 record.write_text(json.dumps(data,indent=2)+'\n');print('PASS' if passed else 'FAIL',label);return passed
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['prep','run']);p.add_argument('--label',default='positive');p.add_argument('--mutant',action='store_true');a=p.parse_args()
 if a.mode=='prep':prep()
 else:raise SystemExit(0 if run(a.label,a.mutant) else 1)
