#!/usr/bin/env python3
"""Actual POSTED producer -> generated40 station semantics -> static_c8 PW36.
Related ideal clocks only; the VM array and physical clock tree are outside this gate.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
FILES=['rtl/dsrom_sys/mtp/dsfd_wfc_stg_cl.sv','rtl/common/ot_ratio_cdc_fifo.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_link_pair.sv','rtl/dsrom_sys/mtp/ot_dsrom_mtp_skid.sv','rtl/dsrom_sys/mtp/rtt/ot_dsrom_mtp_rstsync.sv']+['rtl/dsrom_sys/s81_static_control/'+p for p in ['ot_s81_fixed_issue.sv','ot_s81_fixed_mailbox.sv','dsfd_stage_seq_static_c.sv','dsfd_stage_seq_static_c8.sv']]+['tools/s81_vm/wfc_start_bench.sv']
# Measured from the declared fixed source epoch, never selected while executing.
START_PHASE=[1,3,3,0,1,3,3,0]
def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--flat',action='store_true');p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
 paths=[a.root/(Path(f).name if a.flat else f) for f in FILES];pins={f:hashlib.sha256(p.read_bytes()).hexdigest()for f,p in zip(FILES,paths)};rows=[]
 source=paths[0].read_text()
 variants={'positive':source,'dead_start':source.replace('assign t_ks = start_pipe[START_DELAY_S-1];',"assign t_ks = {1'b0,start_pipe[START_DELAY_S-1][SP-1:0]};"),'wrong_token':source.replace('assign t_ks = start_pipe[START_DELAY_S-1];',"assign t_ks = start_pipe[START_DELAY_S-1] ^ ({{SP{1'b0}},1'b1} << NW);"),'one_edge_early':source.replace('assign t_ks = start_pipe[START_DELAY_S-1];','assign t_ks = {posted_doorbell,t_swd[SP-1:0]};')}
 for variant,rtl in variants.items():
  v=a.out/variant;v.mkdir(exist_ok=True);replacement=v/paths[0].name;replacement.write_text(rtl)
  cmd=['iverilog','-g2012','-s','tb_wfc_start','-o',str(v/'sim'),str(replacement),*map(str,paths[1:])]
  r=subprocess.run(cmd,capture_output=True,text=True);(v/'build.log').write_text(r.stdout+r.stderr)
  if r.returncode:raise RuntimeError('compile failed '+variant)
  for phase,sp in enumerate(START_PHASE):
   for fault in ([0,1]if variant=='positive'else[0]):
    r=subprocess.run(['vvp',str(v/'sim'),f'+PHASE={phase}',f'+SP={sp}',f'+FAULT={fault}'],capture_output=True,text=True)
    (v/f'p{phase}_fault{fault}.log').write_text(r.stdout+r.stderr)
    m=re.search(r'^START_RESULT (.*)$',r.stdout,re.M)
    if not m:raise RuntimeError('missing actual consumer result')
    row=dict(variant=variant,phase=phase,fault_injected=fault,rc=r.returncode,result=m.group(1));rows.append(row)
    if (variant=='positive')!=(r.returncode==0):raise RuntimeError('unexpected gate result '+str(row))
 rec=dict(schema='opentallas.s81.posted-start-functional.v1',qualified=False,scope='actual POSTED1 producer and static_c8 PW36,40 exact generated posedge station semantics; no mapped VM or physical clock delivery',source_sha256=pins,compiler_start_phase=START_PHASE,rows=rows,station_count=40,bus_records=41,payload='{start1,user10,token21,pos21}',start_delay_serial_edges=1)
 (a.out/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');print('START_GATE PASS',len(rows),'cases')
if __name__=='__main__':main()
