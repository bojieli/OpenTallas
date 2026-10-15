#!/usr/bin/env python3
"""Actual generated hstn 759-bit stage vs three same-edge register bands.
Functional proof only: clock delivery, physical roots, hop cuts and timing are
outside this component bench. No production credits or stalls are introduced.
"""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=True)
 sys.path.insert(0,str(ROOT/'tools'));import dsrom_s81_fulldie as D
 widths={'dsfd_hstn_proof_original759':759,'dsfd_hstn_proof_low276':276,'dsfd_hstn_proof_mid276':276,'dsfd_hstn_proof_high207':207}
 m={'pdir':{name:{'ck':('input',1),'di':('input',w),'dq':('output',w)} for name,w in widths.items()},'glue':{}}
 generated=D.glue_rtl(m)
 # Mutate the actual middle band's captured input: exchange local bits0/1,
 # preserving its width, clock, instance count and every other band.
 start=generated.index('module dsfd_hstn_proof_mid276 ');end=generated.index('endmodule',start)
 mid=generated[start:end];needle='.i_d(di[275:0])';assert mid.count(needle)==1
 mutant=generated[:start]+mid.replace(needle,".i_d({di[275:2], di[0], di[1]})")+generated[end:]
 src=ROOT/'rtl/common/ot_fwd_link_stage.sv';tb=Path(__file__).with_name('tb_hstn_split.sv')
 runs=[]
 for label,rtl in [('exact',generated),('middle_bit_swap',mutant)]:
  sv=out/(label+'.sv');sv.write_text(rtl);binary=out/(label+'.vvp')
  c=subprocess.run(['iverilog','-g2012','-s','tb_hstn_split','-o',str(binary),str(src),str(sv),str(tb)],capture_output=True,text=True)
  (out/(label+'_build.log')).write_text(c.stdout+c.stderr)
  if c.returncode:raise RuntimeError('Icarus build failed: '+label)
  r=subprocess.run(['vvp',str(binary)],capture_output=True,text=True);(out/(label+'_run.log')).write_text(r.stdout+r.stderr)
  ok=(r.returncode==0 and 'HSTN_SPLIT PASS cycles=5616' in r.stdout) if label=='exact' else (r.returncode!=0 and 'HSTN_SPLIT FAIL split mapping/capture/latency' in r.stdout)
  assert ok,(label,r.returncode,r.stdout,r.stderr)
  runs.append({'kind':label,'exit':r.returncode,'expected':'pass' if label=='exact' else 'fail','observed_expected_result':ok,'generated_rtl_sha256':sha(sv),'run_log_sha256':sha(out/(label+'_run.log'))})
 source=[src,tb,Path(__file__),ROOT/'tools/dsrom_s81_fulldie.py']
 receipt={'schema':'opentallas.s81.hstn_banded_equivalence.v1','status':'PASS','scope':'Actual generator glue_rtl hstn path + real ot_fwd_clk_inv/ot_fwd_link_stage RTL. Common ideal bench clock, same rising capture edge; no physical clock/root/CTS, die hopcut or timing qualification.', 'width':759,'original_primitive_slices':[512,247],'split_bands':[276,276,207],'split_clock_entries':3,'registered_data_bits_each':759,'additional_capture_cycles':0,'positive_capture_edges':5616,'stimuli':'Zeros, ones, all 759 walking-one and walking-zero patterns, 4096 full-width xorshift patterns; output stability between capture edges','mutant':'Swap middle-band local input bits 0/1 before the actual generated stage; same clock and width','sources_sha256':{str(x.relative_to(ROOT)):sha(x) for x in source},'base_git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'runs':runs,'iverilog_version':subprocess.run(['iverilog','-V'],capture_output=True,text=True).stdout.splitlines()[0]}
 (out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt,indent=1))
if __name__=='__main__':main()
