#!/usr/bin/env python3
"""Hierarchical real index arithmetic mapping; area evidence only, no STA closure."""
import argparse,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SRC=['rtl/hdc/v41x/ot_hdc_v41x_idx_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_arith_lat.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv','rtl/hdc/ot_hdc_delay.sv','rtl/hdc/ot_hdc_fastfp.sv','rtl/hdc/ot_hdc_fp32_add_lat.sv','rtl/hdc/ot_hdc_prefix.sv']
def model(kind):
 return dict(scope='prebuild actual arithmetic hierarchy; no headline area or timing until mapped results',shape=dict(dot_products_per_cycle=1 if kind=='dot' else 512,MACs_per_cycle=32 if kind=='dot' else 16384,keys_per_cycle=0 if kind=='dot' else 4,heads=32,head_blocks=4),ports=dict(dot_input_bits=272,dot_output_bits=33,bytes_per_operand=17,memory_ports=0),replication=dict(dots_per_NK4_slice=512,dots_per_L16_stack=2048,stacks_per_die=4,fanout_and_mux='existing actual RTL; hierarchical mapping preserves all instances'),latency=dict(dot_cycles=5,added_cycles=0,source='QL5 full NK4 exact gate1152 golden keys'),area=dict(mapping='hierarchical synth, no flatten; every RTL instance counted recursively',slot='parent four-slice L16 scorer2000x3000um at55%; fullglue/FIFO fit pending',mapped_um2=None),resource=dict(old_flattened_NK4_OOM_peak_KiB=481352416,new_dot_admission_GiB=4,reason='one32-MAC dot versus512 replicated dots in failed fullNK4 flatten; no process memory cap',hierarchical_fullshape_admission='decide after actual leaf+elaboration inventory; no guessed flat retry'))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--work',type=Path,required=True);ap.add_argument('--kind',choices=['dot','array'],default='dot');ap.add_argument('--libdir',type=Path,required=True);ap.add_argument('--source-commit',required=True);a=ap.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=True)
 (w/'prebuild_model.json').write_text(json.dumps(model(a.kind),indent=2)+'\n')
 libs=sorted(a.libdir.glob('*_RVT_TT_*.lib'));seq=next(x for x in libs if '_SEQ_'in x.name)
 top='ot_hdc_v41x_q4dot_l'if a.kind=='dot'else'ot_hdc_v41x_idx_score_array_l'
 params='-chparam QL 5'if a.kind=='dot'else'-chparam NS 1 -chparam NK 4 -chparam IW 20 -chparam FPL 7 -chparam FML 5 -chparam QL 5 -chparam SAFE_QUERY_GATE 1'
 la=' '.join('-liberty '+str(x)for x in libs)
 flow=f"read_verilog -sv -DSYNTHESIS {' '.join(str(ROOT/x)for x in SRC)}; hierarchy -top {top} {params}; synth -noshare -top {top}; dfflibmap -liberty {seq}; abc -D 833 {la}; opt_clean; stat -json {la}"
 (w/'flow.ys').write_text(flow+'\n')
 cmd=['/usr/bin/time','-v','-o',str(w/'time.txt'),'yosys','-Q','-l',str(w/'yosys.log'),'-s',str(w/'flow.ys')]
 with(w/'stdout.log').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 (w/'exit').write_text(str(r.returncode)+'\n')
 record=dict(source_commit=a.source_commit,kind=a.kind,exit=r.returncode,model=model(a.kind),source_sha256={x:hashlib.sha256((ROOT/x).read_bytes()).hexdigest()for x in SRC},library_sha256={str(x):hashlib.sha256(x.read_bytes()).hexdigest()for x in libs},scope='realhierarchy mappedarea inventory only; requires fullwrapper physical SS sensitivity/TTsetup/FFhold and DRC0')
 (w/'record.json').write_text(json.dumps(record,indent=2)+'\n');return r.returncode
if __name__=='__main__':raise SystemExit(main())
