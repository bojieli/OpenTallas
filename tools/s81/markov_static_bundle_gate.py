"""Actual head pin stream -> four static cached Markov consumers, 128 real rows.
Actual HC input and released head images come from the source-pinned native
head proof. Expected logits are independent checker inputs only.
"""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def unpack(path):
 physical=[int(x,16)for x in path.read_text().split()]
 return [sum(((physical[a//8]>>(8*bit+a%8))&1)<<bit for bit in range(256))for a in range(256)]
def run(out,inputs,embed_root):
 out.mkdir(parents=True,exist_ok=False);images=out/'images';images.mkdir()
 head_rec=json.loads((inputs/'head128_record.json').read_text());main_rec=json.loads((inputs/'mtp-actual-main-record.json').read_text())
 if not head_rec['native_xf_chained']or head_rec['bad']or head_rec['xf_sha256']!=main_rec['xf_sha256']:raise ValueError('actual matching HC input/head proof required')
 for p in(inputs/'head128').glob('*.viamap.hex'):(images/p.name).symlink_to(p.resolve())
 for p in(embed_root/'evidence/images').glob('macro*.viamap.hex'):(images/p.name).symlink_to(p.resolve())
 W=[]
 for q in range(4):
  wdir=inputs/f'bundle_w{q}';meta=json.loads((wdir/'manifest.json').read_text())
  if meta['row0']!=32*q or meta['released_rows_copied']!=32:raise ValueError('actual W row geometry')
  halves=[unpack(wdir/f'mk{q}_{h}.viamap.hex')for h in range(2)]
  words=[halves[a%2][a//2]for a in range(512)]
  raw=b''.join(x.to_bytes(32,'little')for x in words)
  if hashlib.sha256(raw).hexdigest()!=meta['payload_sha256']:raise ValueError('W image readback must equal released payload')
  W.append(np.frombuffer(raw,dtype='<u2').reshape(32,256).copy())
  for p in wdir.glob('*.viamap.hex'):(images/p.name).symlink_to(p.resolve())
 terminal=json.loads((inputs/'mtp-main-native-chain.json').read_text());t=re.search(r'S81_HEAD PASS token=(\d+)',terminal['terminal'][0]['stdout']);token=int(t[1])
 heads=np.load(inputs/'mtp-actual-main-rank0.npz')['logits'][:128].astype(np.uint32)
 table=np.memmap(embed_root/'input/embed.bf16.bin',dtype='<u2',mode='r',shape=(129280,256));ef=(np.array(table[token],dtype=np.uint32)<<16).view(np.float32)
 wf=(np.concatenate(W).astype(np.uint32)<<16).view(np.float32);terms=np.multiply(wf,ef,dtype=np.float32).reshape(128,32,8);acc=np.zeros((128,32),dtype=np.float32)
 for k in range(8):acc=np.add(acc,terms[:,:,k],dtype=np.float32)
 while acc.shape[1]>1:acc=np.add(acc[:,0::2],acc[:,1::2],dtype=np.float32)
 gold=np.add(heads.view(np.float32),acc[:,0],dtype=np.float32).view(np.uint32)
 (out/'gold.hex').write_text(''.join(f'{int(x):08x}\n'for x in gold))
 for name in('xa.hex','xb.hex'):(out/name).symlink_to((inputs/'head128'/name).resolve())
 tb=out/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;reg rst_n=0,go=0;reg[255:0]xa=0,xb=0;
 wire[3:0]joined_valid,head_v;wire[127:0]joined_bits,head_d;wire[67:0]joined_row,joined_token,head_row;wire[239:0]joined_identity;
 wire head_max_v,fault;wire[16:0]head_max_row;wire[31:0]head_max_bits;
 ot_s81_markov_static_bundle dut(.clk(clk),.rst_n(rst_n),.go(go),.clk_A({4{clk}}),.clk_leaf({152{clk}}),.clk_E_pair({253{clk}}),.clk_E_group({16{clk}}),
 .xa(xa),.xb(xb),.token(17'dTOKEN),.identity(60'd1048576),.joined_valid(joined_valid),.joined_bits(joined_bits),.joined_row(joined_row),.joined_token(joined_token),.joined_identity(joined_identity),
 .head_max_v(head_max_v),.head_max_row(head_max_row),.head_max_bits(head_max_bits),.head_v(head_v),.head_d(head_d),.head_row(head_row),.fault(fault));
 reg[255:0]ma[0:255],mb[0:63];reg[31:0]gold[0:127];integer seen[0:3];integer q,cyc=0,g0=0,m,total=0;string dir;
 always @(posedge clk)cyc<=cyc+1;
 always @(negedge clk)if(rst_n)begin
  if(fault)$fatal(1,"fault G%0d control%b H%b E%b cache%b row%b",cyc-g0,dut.control_fault,dut.h_fault,dut.e_fault,dut.c_fault,dut.m_fault);
  for(q=0;q<4;q=q+1)if(joined_valid[q])begin
   if(joined_row[17*q+:17]!=32*q+seen[q]||joined_token[17*q+:17]!=TOKEN||joined_identity[60*q+:60]!=1048576)$fatal(1,"metadata");
   if(joined_bits[32*q+:32]!==gold[32*q+seen[q]])$fatal(1,"numeric q%0d row%0d actual%h expected%h",q,seen[q],joined_bits[32*q+:32],gold[32*q+seen[q]]);
   if(cyc-g0!=(q==3?658:656)+256*seen[q])$fatal(1,"calendar q%0d row%0d got%0d",q,seen[q],cyc-g0);
   seen[q]=seen[q]+1;total=total+1;
  end
 end
 initial begin
  for(q=0;q<4;q=q+1)seen[q]=0;
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");$readmemh({dir,"/xa.hex"},ma);$readmemh({dir,"/xb.hex"},mb);$readmemh({dir,"/gold.hex"},gold);
  repeat(8)@(negedge clk);#0.001;rst_n=1;repeat(8)@(negedge clk);#0.001;go=1;g0=cyc;@(negedge clk);#0.001;go=0;
  fork
   begin
    for(m=0;m<8192+7*11+8;m=m+1)begin
     while(cyc-g0!=5+m)begin @(negedge clk);#0.001;end
     xa=ma[m%256];xb=mb[m%64];
    end
   end
   begin
    while(total<128)begin @(negedge clk);#0.001;end
    repeat(4)@(negedge clk);#0.001;
    if(fault)$fatal(1,"late fault");
    $display("MARKOV_STATIC_BUNDLE PASS actual_HEAD_PORTS128 actualE506 W8 FFcaches4 K256x4 fixedG656_658_last8594");$finish;
   end
  join
 end
 initial begin #40000;$fatal(1,"timeout");end
endmodule
'''.replace('TOKEN',str(token)))
 paths=['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/hdc/ot_hdc_delay.sv','rtl/v41rom/ot_dsrom_head_bundle.sv','rtl/v41rom/ot_dsrom_head_elem.sv']
 paths+=['rtl/experimental/dsrom_markov_20261008/'+s+'.sv'for s in('ot_s81_markov_k256_native','ot_s81_markov_k256_static','ot_dsrom_markov_embed_static','ot_dsrom_markov_weight32_static','ot_s81_markov_embed_cache_static','ot_s81_markov_static_row','ot_s81_markov_static_bundle')]
 macro_source=ROOT/'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v';macro=out/'macro.v';macro.write_text(macro_source.read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
 obj=out/'obj';cmd=['verilator','--binary','--timing','-j','2','-O1','-Wno-fatal','--top-module','tb','--Mdir',str(obj),*[str(ROOT/x)for x in paths],str(macro),str(tb)]
 with (out/'build.log').open('w')as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
 if p.returncode:raise RuntimeError('build failed '+str(out/'build.log'))
 results=[]
 mutant=out/'mutant_images';mutant.mkdir()
 for p in images.iterdir():
  if p.name!='mk0_0.viamap.hex':(mutant/p.name).symlink_to(p.resolve())
 lines=(images/'mk0_0.viamap.hex').read_text().splitlines();lines[0]=f'{int(lines[0],16)^(1<<(15*8)):0548x}';(mutant/'mk0_0.viamap.hex').write_text('\n'.join(lines)+'\n')
 for mode in('exact','via_mutant'):
  p=subprocess.run([str(obj/'Vtb'),f'+DIR={out}',f'+OT_ROM_DIR={images if mode=="exact"else mutant}'],text=True,capture_output=True);(out/(mode+'.log')).write_text(p.stdout+p.stderr);print(mode,p.stdout[-1800:],flush=True)
  ok=(p.returncode==0 and'MARKOV_STATIC_BUNDLE PASS'in p.stdout)if mode=='exact'else(p.returncode!=0 and'numeric q0 row0'in p.stdout)
  results.append(dict(mode=mode,exit=p.returncode,ok=ok))
 rec=dict(gate='PASS'if all(x['ok']for x in results)else'FAIL',results=results,source_sha256={x:sha(ROOT/x)for x in paths},actual_head_receipt_sha256=sha(inputs/'head128_record.json'),actual_terminal_receipt_sha256=sha(inputs/'mtp-main-native-chain.json'),scope='actual 128-row head pin stream -> static cached real E/W+K256; fixed production calendar; upstream HC stream replayed actual ROM inputs; whole MTP/VM/physical die remains unqualified',full_native_token_qualified=False,physical_qualified=False)
 (out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');return rec['gate']=='PASS'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--inputs',type=Path,required=True);p.add_argument('--embed-root',type=Path,required=True);a=p.parse_args();raise SystemExit(0 if run(a.out.resolve(),a.inputs.resolve(),a.embed_root.resolve())else 1)
