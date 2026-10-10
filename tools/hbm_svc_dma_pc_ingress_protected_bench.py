"""Minimum protected ingress actual-codec and paired-state fault gate."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=['rtl/common/ot_secded.sv','rtl/common/ot_secded_cols.svh','rtl/ot_hbm_svc_dma_pc_ingress_protected.sv','rtl/test/hbm_accel/tb_hbm_svc_dma_pc_ingress_protected.sv','tools/hbm_svc_dma_pc_ingress_protected_bench.py','rtl/test/hbm_accel/tb_hbm_svc_dma_pc_ingress_protected_latency.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh immutable record required')
 a.work.mkdir(parents=True,exist_ok=True);hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SRC}
 plans=[('baseline',0,0,0,'PASS'),('disabled',13,0,0,'PASS')]
 plans += [(n,m,0,0,'PASS')for n,m in [('overreservation',1),('unreserved_return',2),('zero_burst',3),('overflow',4),('control_pair',7),('held_publication_pair',8)]]
 plans += [('wrong_bank_identity',5,0,0,'FAIL')]
 plans += [('metadata_pair_bit'+str(bit),6,0,bit,'PASS')for bit in range(16)]
 plans += [('data_single_lane'+str(l)+'_bit'+str(bit),9,l,bit,'PASS')for l in range(4)for bit in [0,63]]
 plans += [('ECC_single_lane'+str(l)+'_bit'+str(bit),10,l,bit,'PASS')for l in range(4)for bit in range(8)]
 plans += [('double_UE_lane'+str(l),11,l,0,'PASS')for l in range(4)]
 plans += [('latency_first_constant_zero_word',14,0,0,'PASS')]
 cases=[]
 for name,mut,lane,bit,expected in plans:
  exe=a.work/(name+'.vvp')
  top='tb_hbm_svc_dma_pc_ingress_protected_latency'if mut==14 else'tb_hbm_svc_dma_pc_ingress_protected'
  params=[]if mut==14 else['-P'+top+'.MUT='+str(mut),'-P'+top+'.ERR_LANE='+str(lane),'-P'+top+'.ERR_BIT='+str(bit)]
  sources=[SRC[0],SRC[2],SRC[5]if mut==14 else SRC[3]]
  c=subprocess.run(['iverilog','-g2012','-I',str(ROOT/'rtl/common'),'-s',top,*params,'-o',str(exe),*[str(ROOT/s)for s in sources]],capture_output=True,text=True)
  if c.returncode:cases.append(dict(case=name,verdict='COMPILE_FAIL',expected=expected,output=c.stdout+c.stderr));break
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(case=name,verdict='PASS'if r.returncode==0 else'FAIL',expected=expected,returncode=r.returncode,output=r.stdout+r.stderr))
 stable=all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()==v for s,v in hashes.items());ok=stable and len(cases)==len(plans)and all(x['verdict']==x['expected']for x in cases)
 d=dict(schema='opentallas.hbm_svc.dma_pc_ingress_protected.v1',verdict='PASS'if ok else'FAIL',sources_unchanged=stable,cases=cases,input_sha256=hashes,scope='One actual protected RTL PC ingress, four32deep288bit SECDED banks, real four64b encoder1/decoder2 codecs, paired16bit epoch metadata and controls, four finite paired publication slots; measured native-to-bankwrite5cycles including first constant-zero payload. Full occupancy/wrapped pointers/partial unbalanced banks, unbackpressured128returns, sticky immediate pair-fault containment, single-bit data+all32ECC-bit correction and double-bit UE zero-sector/fault. Physical mapping and complete native CAM/epoch integration remain unqualified.')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
