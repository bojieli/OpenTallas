#!/usr/bin/env python3
"""Reproduce canonical SRAM bank vs explicit read-root candidate lockstep."""
import argparse, hashlib, json, pathlib, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[2]
SOURCES=['tests/s81/tb_qb_bank_readroot.sv','rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_pipe_native.sv','rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_qb_readroot_candidate.sv','physical/s81_pq_hier/pinned/rtl/ot_rst_relay.sv','physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v']
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True);p.add_argument('--parent',action='store_true');a=p.parse_args();out=pathlib.Path(a.out).resolve();out.mkdir(parents=True,exist_ok=True)
 sources=list(SOURCES)
 top='tb_qb_bank_readroot';positive='QB_READROOT PASS';negative='QB_READROOT FAIL';mutant='-DOT_QB_READROOT_MUT_STOP'
 if a.parent:
  sources[0]='tests/s81/tb_s81_pq_qb_pipe_readroot.sv'
  sources+=['physical/s81_pq_hier/pinned/rtl/v41die/ot_v41_pqc_tiles.sv','rtl/v41rom/ot_v41_kreg.sv','rtl/common/ot_prefix.sv']
  top='tb_s81_pq_qb_pipe_readroot';positive='PQ_QB_PIPE PASS';negative='PQ_QB_PIPE FAIL';mutant='-DOT_QB_PARENT_MUT_STOP'
 cases=[]
 for name,defines in [('positive',[]),('stopped_read_root',[mutant])]:
  exe=out/(name+'.vvp')
  subprocess.run(['iverilog','-g2012','-s',top,*defines,'-o',str(exe),*[str(ROOT/f) for f in sources]],check=True)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);(out/(name+'.log')).write_text(r.stdout+r.stderr)
  ok=(r.returncode==0 and positive in r.stdout) if not defines else (r.returncode!=0 and negative in r.stdout)
  if not ok:raise SystemExit(f'{name} violated exact/mutant contract: {r.returncode}')
  cases.append(dict(name=name,returncode=r.returncode,expected_outcome=True))
 (out/'gate.json').write_text(json.dumps(dict(source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in sources},cases=cases,physical_qualified=False),indent=2)+'\n')
if __name__=='__main__':main()
