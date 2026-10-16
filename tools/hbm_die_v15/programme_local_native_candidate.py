#!/usr/bin/env python3
"""Recovered RF36 302/476 programme composition; no canonical source adoption.

The original combined9752 and historic301/474 fixtures remain separate.
Build and simulation execute only via fleet admission.
"""
import argparse,hashlib,json,re,shlex,shutil,subprocess,concurrent.futures
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S='a89a10d1fc2200a6f6d556dda2efc905cecbac77'
P='rtl/hbm_accel/generic/adapters/static_su/'
LOCAL_HASH='7ff140b4063c86ba48956588f8443435b3f2f36bb7b829b2d7610c8408a8606b'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def checked_replace(text,old,new):
 assert text.count(old)==1,old
 return text.replace(old,new)
def emit_bench():
 t=(ROOT/(P+'programme/tb_hbm_su_native_multirate_top.sv')).read_text()
 t=checked_replace(t,'module tb_hbm_su_native_multirate_top;','module tb_hbm_su_local_native_candidate;')
 start=t.index(' ot_hbm_su_programme #(.LINE_BITS(9688)')
 end=t.index(' ot_hbm_su_programme #(.LINE_BITS(64)',start)
 old=t[start:end]
 ref=old.replace('serial_programme(', 'serial_programme_reference(').replace('.start(serial_start)', '.start(reference_start)')
 for name in ['busy','valid','done','fault','edge','command']:
  ref=ref.replace('(serial_'+name+')','(reference_'+name+')')
 replacement=''' reg reference_start=0;bit baseline_mode,mut_local_prime,mut_busy;
 wire reference_busy,reference_valid,reference_done,reference_fault;
 wire [15:0] reference_edge;wire[9687:0]reference_command;
 wire candidate_busy,candidate_valid,candidate_done,candidate_fault;
 wire[15:0]candidate_edge;wire[9687:0]candidate_command;
 assign serial_busy=baseline_mode?reference_busy:candidate_busy;
 assign serial_valid=baseline_mode?reference_valid:candidate_valid;
 assign serial_done=baseline_mode?reference_done:candidate_done;
 assign serial_fault=baseline_mode?reference_fault:candidate_fault;
 assign serial_edge=baseline_mode?reference_edge:candidate_edge;
 assign serial_command=baseline_mode?reference_command:candidate_command;
'''+ref+''' ot_hbm_su_programme_local #(.LINE_BITS(9688),.EDGES(NE),.COLS(SERIAL_COLS),
 .DICT_BANKS(SERIAL_DICT_BANKS),.GLOBAL_MACROS(SERIAL_MACROS),.LOCAL_MACROS(476),.LOCAL_COLS(41)) local_programme(
 .clk_ctl({4{serial_clk}}),.clk_cmd({41{serial_clk}}),.clk_macro({476{serial_clk}}),.rst_n(rst_n),
 .cfg_we(serial_cfg_we),.cfg_bank(serial_cfg_bank),.cfg_row(serial_cfg_row),.cfg_data(serial_cfg_data),
 .start(serial_start),.length(16'(NE)),.busy(candidate_busy),.valid(candidate_valid),.done(candidate_done),
 .fault(candidate_fault),.edge_index(candidate_edge),.command(candidate_command));
'''
 t=t[:start]+replacement+t[end:]
 start=t.index(' ot_hbm_su_bridge_release u_bridge_release(')
 end=t.index(' always_comb begin',start)
 t=t[:start]+''' wire reference_release,reference_release_fault,good_release,good_release_fault,bad_release,bad_release_fault;
 ot_hbm_su_bridge_release reference_release_leaf(.clk_serial(serial_clk),.clk_stream(stream_clk),.rst_n(rst_n),
 .rst_stream_n(rst_n),.prog_busy(reference_busy),.bridge_rst_n(reference_release),.fault(reference_release_fault));
 ot_hbm_su_bridge_release_local_candidate #(.DELAY(2)) candidate_release_leaf(
 .clk_serial(serial_clk),.clk_stream(stream_clk),.rst_n(rst_n),.rst_stream_n(rst_n),.prog_busy(candidate_busy),
 .bridge_rst_n(good_release),.fault(good_release_fault));
 ot_hbm_su_bridge_release_local_candidate #(.DELAY(0)) mutant_release_leaf(
 .clk_serial(serial_clk),.clk_stream(stream_clk),.rst_n(rst_n),.rst_stream_n(rst_n),.prog_busy(candidate_busy),
 .bridge_rst_n(bad_release),.fault(bad_release_fault));
 assign leaf_bridge_rst_n=baseline_mode?reference_release:(mut_busy?bad_release:good_release);
 assign leaf_bridge_fault=baseline_mode?reference_release_fault:(mut_busy?bad_release_fault:good_release_fault);
 wire dut_bridge_rst_n=leaf_bridge_rst_n;
'''+t[end:]
 marker=' initial begin\n  string dir;reg[255:0]data;reg[15:0]sec;'
 monitor=''' integer local_start_half=-1,reference_start_half=-1,last_vm_commit=-1,vm_commits=0,command_checks=0,release_checks=0;
 wire[31:0]actual_vm_commit;
 for(genvar q=0;q<4;q=q+1)begin:g_vmobserve
  for(genvar b=0;b<8;b=b+1)begin:g_b
   assign actual_vm_commit[q*8+b]=native_vm.g_q[q].g_b[b].bank.m_wB;
  end
 end
 always @(posedge serial_clk)begin
  if(serial_start)local_start_half=half_tick;
  if(reference_start)reference_start_half=half_tick;
  if(rst_n && epoch_half>=0 && half_tick>=epoch_half)begin
   if({candidate_valid,candidate_done,candidate_fault,candidate_edge}!=={reference_valid,reference_done,reference_fault,reference_edge})fail("candidate/reference programme flags/index");
   if(candidate_valid && candidate_command!==reference_command)fail("candidate/reference actual command");
   if(candidate_valid)command_checks=command_checks+1;
  end
 end
 always @(posedge stream_clk)if(rst_n && epoch_half>=0)begin
  #1;
  if(good_release!==reference_release)fail("candidate/reference real release");
  release_checks=release_checks+1;
 end
 always @(posedge stream_clk)if(rst_n && epoch_half>=0 && half_tick>=epoch_half)begin
  if(|actual_vm_commit)last_vm_commit=(half_tick-epoch_half)/6;
  vm_commits=vm_commits+$countones(actual_vm_commit);
 end
'''
 t=checked_replace(t,marker,monitor+marker)
 t=checked_replace(t,'  string dir;reg[255:0]data;reg[15:0]sec;', '''  string dir;reg[255:0]data;reg[15:0]sec;
  baseline_mode=$test$plusargs("BASELINE");mut_local_prime=$test$plusargs("MUT_LOCAL_PRIME");mut_busy=$test$plusargs("MUT_BUSY");''')
 t=checked_replace(t,'bridge_leaf=$test$plusargs("BRIDGE_LEAF");','bridge_leaf=1;')
 t=checked_replace(t,'  if(SERIAL_BITS!=9688||STREAM_BITS!=64)$fatal(1,"programme plane width");', '''  if(SERIAL_BITS!=9688||STREAM_BITS!=64||SERIAL_MACROS!=302||STREAM_MACROS!=6||STREAM_INDEX_PACK!=16)$fatal(1,"recovered RF36 plane dimensions");''')
 old='''  wait(half_tick==epoch_half-33);serial_start=1;
  wait(half_tick==epoch_half-31);serial_start=0;'''
 new='''  wait(half_tick==epoch_half-(mut_local_prime?33:49));serial_start=1;
  wait(half_tick==epoch_half-(mut_local_prime?31:47));serial_start=0;
  if(!mut_local_prime)wait(half_tick==epoch_half-33);
  else wait(half_tick==epoch_half-30); // negative control deliberately breaks the reference phase too
  reference_start=1;
  wait(half_tick==epoch_half-31 || (mut_local_prime && half_tick==epoch_half-23));reference_start=0;'''
 # Keep the negative control's reference schedule fixed as well: independent
 # process below avoids any data-dependent polling or reordered epoch waits.
 new='''  fork
   begin
    wait(half_tick==epoch_half-(mut_local_prime?33:49));serial_start=1;
    wait(half_tick==epoch_half-(mut_local_prime?31:47));serial_start=0;
   end
   begin
    wait(half_tick==epoch_half-33);reference_start=1;
    wait(half_tick==epoch_half-31);reference_start=0;
   end
  join'''
 t=checked_replace(t,old,new)
 # fork join ends at E0-31; the stream start at E0-25 remains fixed.
 old='''  if(errors)$fatal(1,"SU_NATIVE_MULTIRATE_TOP FAIL errors=%0d",errors);'''
 new='''  if(command_checks!=NE || vm_commits!=NW)fail("complete command/actual SRAM commit count");
  if(!mut_local_prime && reference_start_half-local_start_half!=16)fail("exact two serial priming edges");
  $display("LOCAL_PROGRAMME_COST baseline=%0d local_start_half=%0d reference_start_half=%0d epoch_half=%0d last_vm_commit_stream=%0d last_lg_ack_stream=%0d last_bridge_ack_serial=%0d command_checks=%0d release_checks=%0d vm_commits=%0d local_MACROS=476 reference_MACROS=302 stream_MACROS=6",baseline_mode,local_start_half,reference_start_half,epoch_half,last_vm_commit,last_lg_ack,last_bridge_ack,command_checks,release_checks,vm_commits);
  if(errors)$fatal(1,"SU_NATIVE_MULTIRATE_TOP FAIL errors=%0d",errors);'''
 t=checked_replace(t,old,new)
 t=t.replace('SERIAL_MACROS+STREAM_MACROS,NE,PE','476+SERIAL_MACROS+STREAM_MACROS,NE,PE')
 t=t.replace('serial_prime_edges','reference_serial_prime_edges')
 return t

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--fixture',type=Path,required=True);ap.add_argument('--local-rtl',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--jobs',type=int,default=4);ap.add_argument('--prepare-only',action='store_true');a=ap.parse_args()
 assert sha(a.local_rtl)==LOCAL_HASH
 fixture=a.fixture.resolve();serial=json.loads((fixture/'serial/manifest.json').read_text());stream=json.loads((fixture/'stream/manifest.json').read_text())
 assert (serial['edges'],serial['line_bits'],serial['total_macros'])==(7116,9688,302)
 assert (stream['edges'],stream['line_bits'],stream['total_macros'],stream['index_pack'])==(9489,64,6,16)
 assert sha(fixture/'serial/expected.mem')==serial['source_sha256']=='ef51677866608d14c080d0aef73939220f5e18230a566a015d511c0f07daff2a'
 assert sha(fixture/'stream/expected.mem')==stream['source_sha256']=='fcba67807bbf4d3be28ae2f3fcd063b547f09248ef095d22c06fd3bac098363d'
 out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);vec=out/'vec';shutil.copytree(fixture,vec)
 # Only the parameter declaration syntax changes: packed low-column-first.
 for prefix in ['serial','stream']:
  m=json.loads((vec/prefix/'manifest.json').read_text());p=vec/prefix/'programme_params.svh';before=p.read_text();name=prefix.upper();db=m['dictionary_banks']
  new='localparam [32*'+name+'_COLS-1:0] '+name+'_DICT_BANKS={'+','.join("32'd"+str(v) for v in reversed(db))+'};'
  after=re.sub(r'localparam integer '+name+r'_DICT_BANKS\[0:'+name+r"_COLS-1\]='\{[^;]+;",new,before);assert after!=before
  (vec/prefix/'programme_params.original.svh').write_text(before);p.write_text(after)
 bench=out/'tb_hbm_su_local_native_candidate.sv';bench.write_text(emit_bench());local=out/'ot_hbm_su_programme_local.sv';shutil.copyfile(a.local_rtl,local)
 runner=(ROOT/'tools/hbm_static/su_multirate_native_run.sh').read_text();inside=runner.split('sources=(\n',1)[1].split('\n)',1)[0]
 sources=[s.replace('$S',P.rstrip('/')) for s in shlex.split(inside)]
 sources.remove(P+'programme/tb_hbm_su_native_multirate_top.sv')
 sources+=['rtl/test/hbm_programme_local_1016/ot_hbm_su_bridge_release_local_candidate.sv',str(bench),str(local)]
 pins=[s for s in sources if not Path(s).is_absolute()]
 consumed=[p for p in vec.rglob('*') if p.is_file() and p.suffix in ['.mem','.svh','.json']]
 manifest=dict(scope='RF36 actual component composition; not full-die/native/physical/throughput adoption',generating_source=S,local_source_commit='4cceac7f5',local_source_sha256=LOCAL_HASH,reference_macros=302,local_macros=476,local_column_roots=41,stream_macros=6,serial_prime_edges=dict(reference=4,candidate=6),source_hashes={s:sha(ROOT/s) for s in pins},generated_bench_sha256=sha(bench),fixture_hashes={str(p.relative_to(vec)):sha(p) for p in consumed},sources=sources)
 (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 if a.prepare_only:print('LOCAL_NATIVE_CANDIDATE PREPARED');return
 cmd=['verilator','--binary','--timing','--hierarchical','-O1','-j',str(a.jobs),'-CFLAGS','-O0','-Wno-fatal','-Wno-lint','-Wno-style','--top-module','tb_hbm_su_local_native_candidate','-I'+str(vec),'-GNE=7116','-GPE=9489','-GNW=135184','-GNS=9','-GRF_RELAY=36','-GPIN_REG=0','-GMLAT=4','-GALAT=3','-GLEAF=1','--Mdir',str(out/'obj')]+sources
 with (out/'build.log').open('w') as f:subprocess.run(cmd,cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,check=True)
 cases=[('candidate',[]),('baseline',['+BASELINE']),('late_prime',['+MUT_LOCAL_PRIME']),('busy_bypass',['+MUT_BUSY'])]
 def run(case):
  name,args=case;p=subprocess.run([str(out/'obj/Vtb_hbm_su_local_native_candidate'),'+DIR='+str(vec)]+args,cwd=ROOT,capture_output=True,text=True);log=p.stdout+p.stderr;(out/(name+'.log')).write_text(log)
  ok=(p.returncode==0 and 'SU_NATIVE_MULTIRATE_TOP PASS' in log) if name in ['candidate','baseline'] else (p.returncode!=0 and 'SU_NATIVE_MULTIRATE_TOP FAIL' in log)
  return dict(case=name,exit=p.returncode,passed=ok)
 with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(run,cases))
 (out/'receipt.json').write_text(json.dumps(dict(manifest=manifest,cases=rows),indent=2)+'\n');assert all(r['passed'] for r in rows),rows
 print('LOCAL_NATIVE_CANDIDATE PASS')
if __name__=='__main__':main()
