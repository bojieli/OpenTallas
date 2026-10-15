"""Real mapped E/W + fixed K256, using actual RTL head logits as boundary input.
This is a component chain: the candidate token is declared input, not a claim
that the whole MTP program or its final acceptance pipeline executed.
"""
import argparse,hashlib,json,subprocess,re
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def run(out,inputs,embed_root,build_work=None,cache=False):
 out.mkdir(parents=True,exist_ok=False)
 upstream=json.loads((inputs/'mtp-actual-main-record.json').read_text())
 if not upstream.get('native_xf_chained')or upstream.get('bad',-1)!=0:raise ValueError('actual HC/head receipt required')
 z=np.load(inputs/'mtp-actual-main-rank0.npz');assert z['seen'][1024:1056].all()
 heads=z['logits'][1024:1056].astype(np.uint32)
 (out/'head.hex').write_text(''.join(f'{int(x):08x}\n'for x in heads))
 w=np.array([list(int(s,16).to_bytes(32,'little'))for s in(inputs/'w.hex').read_text().split()],dtype=np.uint8).reshape(32,512).copy().view('<u2').reshape(32,256)
 terminal_path=inputs/'mtp-main-native-chain.json'
 terminal=json.loads(terminal_path.read_text())
 if terminal.get('gate')!='PASS' or not terminal.get('actual_hc_xf_chained') or not terminal.get('all_field_roots_from_rtl'):raise ValueError('actual head terminal required')
 positive=next(x for x in terminal['terminal']if x['mutant']==0)['stdout']
 match=re.search(r'S81_HEAD PASS token=(\d+)',positive)
 if match is None:raise ValueError('actual terminal positive output required')
 token=int(match[1])
 ep=embed_root/'input/embed.bf16.bin';table=np.memmap(ep,dtype='<u2',mode='r',shape=(129280,256))
 # Independent checker follows released chunk8 order; its values feed checks only.
 wf=(w.astype(np.uint32)<<16).view(np.float32);ef=(np.array(table[token],dtype=np.uint32)<<16).view(np.float32)
 terms=np.multiply(wf,ef,dtype=np.float32).reshape(32,32,8);acc=np.zeros((32,32),dtype=np.float32)
 for k in range(8):acc=np.add(acc,terms[:,:,k],dtype=np.float32)
 while acc.shape[1]>1:acc=np.add(acc[:,0::2],acc[:,1::2],dtype=np.float32)
 golden=np.add(heads.view(np.float32),acc[:,0],dtype=np.float32).view(np.uint32)
 (out/'gold.hex').write_text(''.join(f'{int(x):08x}\n'for x in golden))
 images=out/'images';images.mkdir()
 for p in(embed_root/'evidence/images').glob('macro*.viamap.hex'):(images/p.name).symlink_to(p.resolve())
 if len(list(images.glob('macro*.viamap.hex')))!=506:raise ValueError('all actual E mask ROM images required')
 for p in(inputs/'weights').glob('mk_*.viamap.hex'):(images/p.name).symlink_to(p.resolve())
 tb=out/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,request_slot=0,head_valid=0;
 reg[31:0]head_logit=0;reg[16:0]head_row=0,head_token=TOKEN_ID,token=TOKEN_ID;reg[4:0]local_row=0;
 reg[59:0]identity=0,head_identity=0;wire ev;wire[255:0]ed;wire[3:0]eb;wire[16:0]et;wire[59:0]ei;wire efault;
 wire joined_valid,fault;wire[31:0]joined_bits;wire[16:0]joined_row,joined_token;wire[59:0]joined_identity;
 reg mid=0;wire[59:0]checked_ei=ei^((mid&&eb==7)?60'd1:60'd0);
 ot_dsrom_markov_embed_static u_e(.clk(clk),.rst_n(rst_n),.clk_pair({253{clk}}),.clk_group({16{clk}}),.request_slot(request_slot),.token(token),.identity(identity),
 .word_v(ev),.word_data(ed),.word_beat(eb),.word_token(et),.word_identity(ei),.fault(efault));
 ot_s81_markov_static_row #(.GLOBAL_ROW0(1024))dut(.clk(clk),.rst_n(rst_n),.clk_leaf({38{clk}}),.request_slot(request_slot),
 .head_valid(head_valid),.head_logit(head_logit),.head_row(head_row),.head_token(head_token),.head_identity(head_identity),.local_row(local_row),.token(token),.identity(identity),
 .embed_v(ev),.embed_data(ed),.embed_beat(eb),.embed_token(et),.embed_identity(checked_ei),.joined_valid(joined_valid),.joined_bits(joined_bits),.joined_row(joined_row),.joined_token(joined_token),.joined_identity(joined_identity),.fault(fault));
 reg[31:0]hm[0:31],gm[0:31];string dir;integer n,cyc=0,launch=-1000,got=0;reg[59:0]expected_id;
 always @(posedge clk)begin cyc=cyc+1;if(request_slot)launch=cyc;end
 always @(negedge clk)if(rst_n)begin
  if(joined_valid!==(cyc-launch==183))$fatal(1,"result slot age%0d valid%b",cyc-launch,joined_valid);
  if(joined_valid)begin
   if(joined_bits!==gm[n])$fatal(1,"numeric row%0d actual%h expected%h",n,joined_bits,gm[n]);
   if(joined_row!=1024+n||joined_token!=TOKEN_ID||joined_identity!=expected_id)$fatal(1,"result metadata");
   got=got+1;
  end
  if(efault)$fatal(1,"embedding fault");
  if(fault)begin
   if(mid)begin $display("MARKOV_STATIC_ROW_EXPECTED_METADATA_FAULT");$finish;end
   $fatal(1,"component fault age%0d sched%b w%b k%b",cyc-launch,dut.schedule_fault,dut.wfault,dut.kfault);
  end
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");$readmemh({dir,"/head.hex"},hm);$readmemh({dir,"/gold.hex"},gm);
  mid=$test$plusargs("META_MUTANT");repeat(8)@(negedge clk);#0.001;rst_n=1;repeat(8)@(negedge clk);#0.001;
  for(n=0;n<32;n=n+1)begin
   local_row=5'(n);head_row=17'(1024+n);head_logit=hm[n];head_valid=1;expected_id=60'(1048576+n);identity=expected_id;head_identity=expected_id;request_slot=1;
   @(negedge clk);#0.001;request_slot=0;head_valid=0;
   repeat(183)begin @(negedge clk);#0.001;end
  end
  if(got!=32)$fatal(1,"missing rows %0d",got);
  $display("MARKOV_STATIC_ROW PASS rows32 actual_HEAD_RTL mappedE506_W2 fixedR183 II184");$finish;
 end
 initial begin #30000;$fatal(1,"timeout");end
endmodule
'''.replace('TOKEN_ID',str(token)))
 if cache:
  text=tb.read_text()
  text=text.replace('wire ev;wire[255:0]ed;wire[3:0]eb;wire[16:0]et;wire[59:0]ei;wire efault;', 'wire ev;wire[255:0]ed;wire[3:0]eb;wire[16:0]et;wire[59:0]ei;wire efault; reg preload=0; wire lv,lfault;wire[255:0]ld;wire[3:0]lb;wire[16:0]lt;wire[59:0]li;')
  text=text.replace('.request_slot(request_slot),.token(token),.identity(identity),\n .word_v(ev),.word_data(ed),.word_beat(eb),.word_token(et),.word_identity(ei),.fault(efault));', '.request_slot(preload),.token(token),.identity(identity),\n .word_v(lv),.word_data(ld),.word_beat(lb),.word_token(lt),.word_identity(li),.fault(lfault));\n ot_s81_markov_embed_cache_static cache(.clk(clk),.rst_n(rst_n),.load_v(lv),.load_data(ld),.load_beat(lb),.load_token(lt),.load_identity(li),.request_slot(request_slot),.token(token),.identity(identity),.word_v(ev),.word_data(ed),.word_beat(eb),.word_token(et),.word_identity(ei),.fault(efault));')
  text=text.replace('for(n=0;n<32;n=n+1)begin','identity=60\'(1048576); preload=1; @(negedge clk);#0.001;preload=0;repeat(24)begin @(negedge clk);#0.001;end\n  for(n=0;n<32;n=n+1)begin')
  text=text.replace("expected_id=60'(1048576+n)","expected_id=60'(1048576)")
  text=text.replace('if(efault)$fatal','if(efault||lfault)$fatal')
  text=text.replace('mappedE506_W2 fixedR183','mappedE506_W2 REAL_FF_CACHE fixedR183')
  tb.write_text(text)
 paths=['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv']
 paths+=['rtl/experimental/dsrom_markov_20261008/'+s+'.sv'for s in('ot_s81_markov_k256_native','ot_s81_markov_k256_static','ot_dsrom_markov_embed_static','ot_dsrom_markov_weight32_static','ot_s81_markov_static_row')]
 if cache:paths+=['rtl/experimental/dsrom_markov_20261008/ot_s81_markov_embed_cache_static.sv']
 macro_source=ROOT/'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v';macro=out/'macro.v'
 macro.write_text(macro_source.read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
 obj=(build_work or out)/'obj'
 if build_work:
  old=json.loads((build_work/'record.json').read_text())
  if old['source_sha256']!={x:sha(ROOT/x)for x in paths} or sha(build_work/'tb.sv')!=sha(tb) or sha(build_work/'macro.v')!=sha(macro):raise ValueError('reused actual binary source mismatch')
 else:
  p=subprocess.run(['verilator','--binary','--timing','-j','2','-O1','-Wno-fatal','--top-module','tb','--Mdir',str(obj),*[str(ROOT/x)for x in paths],str(macro),str(tb)],text=True,capture_output=True)
  (out/'build.log').write_text(p.stdout+p.stderr)
  if p.returncode:raise RuntimeError(p.stderr[-2000:])
 results=[]
 # Genuine physical via-mask corruption: first released W BF16 sign; checker unchanged.
 mutant_images=out/'mutant_images';mutant_images.mkdir()
 for p in images.iterdir():
  if p.name!='mk_0.viamap.hex':(mutant_images/p.name).symlink_to(p.resolve())
 lines=(images/'mk_0.viamap.hex').read_text().splitlines();lines[0]=f'{int(lines[0],16)^(1<<(15*8)):0548x}';(mutant_images/'mk_0.viamap.hex').write_text('\n'.join(lines)+'\n')
 for mode in('exact','via_mutant','metadata_mutant'):
  p=subprocess.run([str(obj/'Vtb'),f'+DIR={out}',f'+OT_ROM_DIR={mutant_images if mode=="via_mutant"else images}']+(['+META_MUTANT']if mode=='metadata_mutant'else[]),text=True,capture_output=True)
  (out/(mode+'.log')).write_text(p.stdout+p.stderr);print(mode,p.stdout[-1200:],flush=True)
  ok=(p.returncode==0 and'MARKOV_STATIC_ROW PASS'in p.stdout)if mode=='exact'else((p.returncode!=0 and'numeric row0'in p.stdout)if mode=='via_mutant'else(p.returncode!=0 and'MARKOV_STATIC_ROW_EXPECTED_METADATA_FAULT'in p.stdout))
  results.append(dict(mode=mode,exit=p.returncode,ok=ok))
 rec=dict(gate='PASS'if all(x['ok']for x in results)else'FAIL',results=results,source_sha256={x:sha(ROOT/x)for x in paths},actual_head=dict(npz_sha256=sha(inputs/'mtp-actual-main-rank0.npz'),receipt_sha256=sha(inputs/'mtp-actual-main-record.json'),rows=[1024,1056]),token=dict(value=token,terminal_receipt_sha256=sha(terminal_path),scope='actual main RTL terminal output replayed at component boundary; direct transport and draft recursive composition remain required'),weights=json.loads((inputs/'weights/manifest.json').read_text()),full_native_token_qualified=False,physical_qualified=False,scope='actual mapped E/W and K256 using actual HC->head RTL logit outputs; replayed actual main token/head outputs, upstream operand transport/head physical mapping and full MTP program/acceptance remain open')
 (out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');return rec['gate']=='PASS'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--embed-root',type=Path,required=True);p.add_argument('--build-work',type=Path);p.add_argument('--cache',action='store_true');a=p.parse_args();raise SystemExit(0 if run(a.out.resolve(),a.inputs.resolve(),a.embed_root.resolve(),a.build_work.resolve()if a.build_work else None,a.cache)else 1)
