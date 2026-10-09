"""Remote minimum actual-core source completion gate, with a legacy control."""
import argparse,hashlib,json,pathlib,subprocess
ROOT=pathlib.Path(__file__).resolve().parents[1]
SRC=['physical/hbm_accel_die_views/svc/rtl/ot_hbm_svc_core.sv','rtl/hbm_accel/service/ot_hbm_accel_cdc_fifo.sv','rtl/hbm_accel/service/ot_hbm_kport_map.sv','rtl/hbm_accel/ingest/ot_hbm_write_source_ordered.sv','rtl/test/hbm_accel/tb_hbm_svc_write_source.sv']
def main():
 p=argparse.ArgumentParser();p.add_argument('--work',type=pathlib.Path,required=True);p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args()
 if a.out.exists():raise SystemExit('fresh record required')
 a.work.mkdir(parents=True,exist_ok=True);rr=[]
 for name,sa,mut in [('source_ack',1,0),('legacy_ack',0,0),('negative_source_dropped',1,1)]:
  exe=a.work/(name+'.vvp');c=subprocess.run(['iverilog','-g2012','-s','tb_hbm_svc_write_source','-Ptb_hbm_svc_write_source.SA='+str(sa),'-Ptb_hbm_svc_write_source.MUT='+str(mut),'-o',str(exe),*[str(ROOT/s) for s in SRC]],capture_output=True,text=True)
  if c.returncode:raise RuntimeError(c.stderr)
  r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True);rr.append(dict(case=name,returncode=r.returncode,verdict='PASS' if r.returncode==0 else 'FAIL',output=r.stdout,compiler=c.stderr))
 ok=all(x['verdict']=='PASS' for x in rr[:2]) and rr[2]['verdict']=='FAIL'
 d=dict(schema='opentallas.hbm_svc.write_source.v1',verdict='PASS' if ok else 'FAIL',cases=rr,input_sha256={s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SRC+['tools/hbm_svc_write_source_bench.py']},scope='Actual core forwarded source transport and accepted per-PC completion identity; no native read-lease integration or physical signoff',obligations=['Native read hazard must include outer queued and forwarded producer debt','SourceGray counters need actual die crossing collars and endpoints','SS/FF and SRAM protection remain open'])
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2));raise SystemExit(0 if ok else 1)
if __name__=='__main__':main()
