#!/usr/bin/env python3
"""Actual companion local clear cannot reject a delayed same-ID old epoch row."""
import argparse,hashlib,json,pathlib,subprocess,tempfile
from w17_ckv_collector_clear_counterexample import ROOT,PIN,SOURCES,BENCH
COMP='rtl/w17_runtime/chip/ckv_count_clear/ot_chip_v41x_ckv_die_service.sv'
CPIN='3c109848c'
def run(out):
 assert not out.exists();pins={}
 b=BENCH.replace('.K(512),.NSLOT(64)', '.K(512),.NSLOT(64),.COLLECTOR_CLEAR_PRIORITY(1)')
 b=b.replace("rx=(cyc==200)?3'b001:0;", "rx=(cyc==200||cyc==211)?3'b001:0;\n if(cyc==211 && (fault!==1'b0||dut.present!==512'd0||dut.npresent!==11'd0))$fatal(1,\"atomic clear failed before delayed delivery\");")
 b=b.replace('.ag_rx_row(6912\'d0)', ".ag_rx_row({4608'd0,{2304{1'b1}}})")
 b=b.replace("dut.present!==512'd0||dut.npresent!==11'd1", "dut.present[16]!==1'b1||dut.npresent!==11'd1||dut.buf_row[16]!=={2304{1'b1}}")
 b=b.replace('REPRODUCED_CLEAR_FAILURE old_count=1 new_present=0 new_count=1 expected_new_count=0','REPRODUCED_DELAYED_OLD_PEER_FAILURE clear_count=0 delay_cycles=1 new_count=1 present16=1 old_payload_stored=1 fault=0')
 with tempfile.TemporaryDirectory(prefix='w17-old-peer-',dir='/home/ubuntu') as tmp:
  d=pathlib.Path(tmp);files=[]
  for i,p in enumerate(SOURCES):
   commit,path=(CPIN,COMP) if i==0 else (PIN,p)
   raw=subprocess.check_output(['git','show',commit+':'+path],cwd=ROOT);pins[path]=dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest());f=d/f's{i}.sv';f.write_bytes(raw);files.append(str(f))
  tb=d/'tb.sv';tb.write_text(b)
  c=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'gate'),str(tb),*files],capture_output=True,text=True,timeout=30)
  v=subprocess.run(['vvp',str(d/'gate')],capture_output=True,text=True,timeout=30) if c.returncode==0 else c
  marker='REPRODUCED_DELAYED_OLD_PEER_FAILURE clear_count=0 delay_cycles=1 new_count=1 present16=1 old_payload_stored=1 fault=0'
  ok=c.returncode==0 and v.returncode==0 and marker in v.stdout
 r=dict(status='REPRODUCED_ACTUAL_DELAYED_OLD_PEER_FAILURE' if ok else 'FAIL_COUNTEREXAMPLE_FIXTURE',source_pins=pins,bench_sha256=hashlib.sha256(b.encode()).hexdigest(),compile_returncode=c.returncode,run_returncode=v.returncode,log=v.stdout+v.stderr,geometry=dict(K=512,NSLOT=64),scope='Actual seven-module companion interface,512 real IDs. Clear count0 verified before injecting externally held same rank/gid old row one cycle later; payload stored with fault0. Origin epoch cannot be encoded in current rank/gid/row interface. Partial old selection, no force; no peer transport or safe epoch claim.',local_fix_sufficient_for_peer_epoch=False,required='Actual all4 destination stored-row ACK + every hop/reassembly/hostqueue/reversecredit drained barrier, or end-to-end generation with no-wrap outstanding rule. Synthetic empty/ready predicates are not provider evidence.',hardware_admission=False)
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(r,indent=2)+'\n');print(r['status'],r['log']);return ok
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);a=p.parse_args();raise SystemExit(0 if run(a.out) else 1)
