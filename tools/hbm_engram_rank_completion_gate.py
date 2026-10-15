#!/usr/bin/env python3
"""Actual local completion, retained late fence and real issuer EPOCH tests."""
import argparse,hashlib,json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def run(out,reference,mode):
 out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True);reference=Path(reference).resolve();receipt=json.loads((reference/'receipt.json').read_text());assert receipt['status']=='pass' and receipt['independent_rank_local_hash_programme']
 raw=(reference/'external_hbm_sectors.hex').read_bytes();assert hashlib.sha256(raw).hexdigest()==receipt['source_binding']['external_hbm_sectors.hex'];(out/'external_hbm_sectors.hex').write_bytes(raw)
 paths=list(receipt['source_sha256']);source='rtl/hbm_accel/engram_static_20261015/ot_hbm_engram_rank_fetch.sv'
 for p,h in receipt['source_sha256'].items():
  if p!=source:assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
 text=(reference/'tb.sv').read_text();assert text.count('.FETCH_EDGES(8228)')==8
 if mode=='early':
  text=text.replace('.FETCH_EDGES(8228)','.FETCH_EDGES(64)')
  old='if(prog_fault || hash_fault || fault!=0)$fatal(1,"actualnativehomefault core%0d hash%b homes%h",core_edge,hash_fault,fault);'
  checks=' && '.join(f'!home{h}.home_fault'for h in range(8));assert old in text
  text=text.replace(old,'if(prog_fault || hash_fault || fault!=0)begin if(rank_programme_fault==8\'hff && !hash_fault && done==0 && home0.programme.kernel_age==65 && '+checks+')begin $display("PASS actual8 local native completion barriers reject early64 fence without modeled home_done");$finish;end $fatal(1,"wrong early-fence failure");end')
  text=text.replace('task tick;', 'always @(posedge core_clk)begin #2;if(rst_n && home0.programme.kernel_age==65 && rank_programme_fault==0)$fatal(1,"lost actual local completion check");end\ntask tick;')
 else:
  text=text.replace('.FETCH_EDGES(8228)','.FETCH_EDGES(18944)')
  text=text.replace('integer core_edge=0,','reg[7:0]completion_seen=0;always @(posedge core_clk)if(rst_n)completion_seen<=completion_seen|rank_programme_done;\ninteger core_edge=0,')
  old='if(!prog_done && (|rank_programme_busy))$fatal(1,"actual programme kernel completion");';assert old in text
  text=text.replace(old,'repeat(10720)tick; if(completion_seen!=8\'hff || (|rank_programme_busy))$fatal(1,"retained actual local completion at18944 fence");')
  old='$display("PASS actualhash8homes';assert old in text
  before='\n'.join([f'if(!home{h}.local_complete)$fatal(1,"missing actual retained local completion h{h}");'for h in range(8)])
  before+='\n@(negedge core_clk);prog_launch_v=1;prog_token_v=1;tick;@(negedge core_clk);prog_launch_v=0;prog_token_v=0;repeat(7)tick;\n'
  before+='\n'.join([f'if(home{h}.local_complete)$fatal(1,"actual issuer EPOCH did not clear retained completion h{h}");'for h in range(8)])
  text=text.replace(old,before+'\n$display("PASS late18944 retained local completion and actual8 issuer EPOCH clear");\n'+old)
 tb=out/'tb.sv';tb.write_text(text);runs=[];start=time.monotonic()
 cases=[('baseline',False),('constant_done_mutant',True)]if mode=='early' else [('baseline',False)]
 for name,mut in cases:
  src=[str(ROOT/p)for p in paths]
  if mut:
   top=(ROOT/source).read_text();old='wire[7:0]local_done_vector=(~LOCAL_PARTICIPANT)|({8{done|local_complete}}&LOCAL_PARTICIPANT);';assert old in top
   variant=out/'constant_done.sv';variant.write_text(top.replace(old,"wire[7:0]local_done_vector=8'hff;"));src[paths.index(source)]=str(variant)
  exe=out/name;cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),*src,str(tb)],capture_output=True,text=True);(out/(name+'.build.log')).write_text(cp.stdout+cp.stderr);assert cp.returncode==0,cp.stdout+cp.stderr
  rp=subprocess.run(['vvp',str(exe)],cwd=out,capture_output=True,text=True);(out/(name+'.run.log')).write_text(rp.stdout+rp.stderr);assert (rp.returncode==0)==(not mut),rp.stdout+rp.stderr
  assert 'Unable to open' not in rp.stdout and 'ERROR:' not in rp.stdout,rp.stdout
  if not mut:assert ('PASS actual8 local native completion'if mode=='early'else'PASS late18944 retained local completion')in rp.stdout,rp.stdout
  else:assert 'lost actual local completion check'in rp.stdout,rp.stdout
  runs.append(dict(name=name,returncode=rp.returncode,output=rp.stdout.strip()))
 result=dict(schema='opentallas.hbm.engram.actual_rank_completion.v1',status='pass',mode=mode,early_fence_and_constant_done_mutant_qualified=(mode=='early'),late_fence_and_epoch_clear_qualified=(mode=='late'),runs=runs,programme_FETCH_EDGES=64 if mode=='early' else 18944,physical_home_done_edges=8228,local_participants=1,independent_ranks=8,wall_seconds=time.monotonic()-start,reference_source_sha256=receipt['source_sha256'],actual_rank_source_sha256=hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),scope='Actual independent rank programme/hash/controller/staging hardware. Early fence rejects absent real completion; late production-default18944 fence retains actual local completion and next actual issuer EPOCH clears it. External model only actual DRAM command/data. No universal service timing, wholekernel/96-rank or physical qualification.')
 (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--out',required=True);ap.add_argument('--reference',required=True);ap.add_argument('--mode',choices=['early','late'],required=True);a=ap.parse_args();run(a.out,a.reference,a.mode)
