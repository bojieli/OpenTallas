"""Four-stack wide CPU exactness, native raw roof, and full nominal-rate gate."""
import argparse, hashlib, json, pathlib, re, subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=['rtl/ot_hbm_svc_dma_pc_tile_wide.sv','rtl/ot_hbm_svc_dma_stream_wide.sv','rtl/test/hbm_accel/tb_hbm_svc_dma_stream_wide.sv','tools/hbm_svc_dma_stream_wide_bench.py']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True)
 p.add_argument('--read-latency',type=int,default=104);p.add_argument('--credit-rtt',type=int,default=192);p.add_argument('--rate-commands',type=int,default=512);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh immutable source-pinned record required')
 a.work.mkdir(parents=True,exist_ok=True);hashes={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest()for s in SRC};cases=[]
 for name,mut in [('baseline',0),('data_mutant',1),('index_mutant',2),('fault_mutant',3),('rtl_pc_map_mutant',4),('rtl_drop_mutant',5),('rtl_data_mutant',6),('response_tag_mutant',7),('response_beat_mutant',8),('raw_roof_mutant',9)]:
  exe=a.work/(name+'.vvp');c=subprocess.run(['iverilog','-g2012','-s','tb_hbm_svc_dma_stream_wide','-Ptb_hbm_svc_dma_stream_wide.MUT='+str(mut),'-Ptb_hbm_svc_dma_stream_wide.READ_LATENCY='+str(a.read_latency),'-Ptb_hbm_svc_dma_stream_wide.CREDIT_RTT='+str(a.credit_rtt),'-Ptb_hbm_svc_dma_stream_wide.RATE_COMMANDS='+str(a.rate_commands),'-o',str(exe),*[str(ROOT/s)for s in SRC[:3]]],capture_output=True,text=True)
  if c.returncode:cases.append(dict(case=name,verdict='COMPILE_FAIL',output=c.stdout+c.stderr));break
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);cases.append(dict(case=name,verdict='PASS'if r.returncode==0 else'FAIL',returncode=r.returncode,output=r.stdout+r.stderr))
 rates=[]
 if cases:
  for stack,size,cycles,raw in re.findall(r'WIDE_BANDWIDTH stack=(\d+) bytes=(\d+) cycles=(\d+) raw_sectors=(\d+)',cases[0]['output']):
   rate=int(size)/int(cycles);rates.append(dict(stack=int(stack),bytes=int(size),cycles=int(cycles),raw_sectors=int(raw),bytes_per_cycle=rate,nominal_utilization=rate/(10000/12),sustained_utilization=rate/(9500/12)))
 stable=all(hashlib.sha256((ROOT/s).read_bytes()).hexdigest()==v for s,v in hashes.items());exact=len(cases)==10 and cases[0]['verdict']=='PASS'and all(x['verdict']=='FAIL'for x in cases[1:])and 'RAW_ROOF' in cases[9]['output']
 aggregate=sum(r['bytes_per_cycle']for r in rates)if len(rates)==4 else 0
 bandwidth=len(rates)==4 and aggregate>=3000
 rawroof=len(rates)==4 and all(r['raw_sectors']*32==r['bytes']for r in rates)and aggregate<=9500/3
 ok=stable and exact and bandwidth and rawroof
 d=dict(schema='opentallas.hbm_svc.dma_stream_wide.v1',verdict='PASS'if ok else'FAIL',correctness='PASS'if exact else'FAIL',bandwidth='PASS'if bandwidth else'FAIL',raw_roof='PASS'if rawroof else'FAIL',sources_unchanged=stable,read_latency_cycles=a.read_latency,credit_rtt_cycles=a.credit_rtt,initial_credits=256,lanes=32,tag_bits=6,window_sectors=16384,native_leases_per_pc=32,write_commit_cycles=3,read_publication_cycles=5,rate_commands=a.rate_commands,backend_calendar_sectors_per_24_cycles_per_stack=593,aggregate_bytes_per_cycle=aggregate,nominal_bytes_per_cycle=10000/3,sustained_bytes_per_cycle=9500/3,gate_bytes_per_cycle=3000,stack_rates=rates,cases=cases,input_sha256=hashes,scope='Wide central CPU data-array baseline with actual RTL write-commit/read-publication pipelines, finite32nativeCAM leases, out-of-order tagged returns and conservative raw backend calendar. Actual SRAM/cache integration and physical closure remain separate; no zero-latency bank claim.')
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
