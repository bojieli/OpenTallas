from pathlib import Path
import subprocess,re,json,hashlib,shutil,sys
r=Path.cwd().resolve();out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=True)
for x in ['w','x','head','gold']:shutil.copy2(r/f'results/rtl/dsrom_markov_row_20261008/{x}.hex',out/f'{x}.hex')
src=[r/x for x in ['rtl/common/ot_prefix.sv','rtl/v41rom/ot_v41_bmul2.sv','rtl/v41rom/ot_dsrom_bmul3.sv','rtl/v41rom/ot_v41_fadd.sv','rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv','rtl/experimental/dsrom_markov_20261008/ot_s81_markov_k256_native.sv']]
results=[]
modes=[('exact',0),('join_mut',1),('delay_mut',0),('ctl_mut',0),('mul_mut',0),('pair_mut',0),('fold_mut',0)]+[(f'chunk{k}_mut',0)for k in range(8)]+[('fault',0)]
if len(sys.argv)>2:
 dut=sys.argv[2].endswith('!')  # '<leaf>!': the mutant alone as the DUT (closure-loop expect=fail bench)
 selected=sys.argv[2].rstrip('!')+'_mut';modes=[m for m in modes if m[0]in(([selected])if dut else['exact','fault',selected])]
 assert len(modes)==(1 if dut else 3),'unknown owned-master mode'
 if dut:
  kind,mut=modes[0]
for kind,mut in modes:
 oldname='tb_markov_fault'if kind=='fault'else'tb_markov_row'
 tb=(r/f'rtl/test/dsrom_markov_20261008/{oldname}.sv').read_text()
 header='ot_s81_markov_k256_native #(.MUTANT_FOLD('+('0'if kind=='fault'else'MUTANT')+')) dut('
 tb=re.sub(r'ot_dsrom_markov_row\s*#\(.*?\)\s*dut\s*\(',header,tb,count=1,flags=re.S)
 tb=tb.replace('.clk(clk),.rst_n(rst_n)', '.clk(clk),.clk_leaf({38{clk}}),.rst_n(rst_n)',1)
 # Add the unchanged PINREG1 reference and every-cycle interface comparison using existing signal names.
 m=re.search(r'ot_s81_markov_k256_native.*?dut\((.*?)\);',tb,re.S);conns=dict(re.findall(r'\.(\w+)\(([^()]*)\)',m[1]));outs=['start_ready','in_ready','out_valid','out_bits','fault']
 decl='\nwire ref_sr,ref_ir,ref_ov,ref_fault;wire[31:0] ref_bits;\n'
 refnames={'start_ready':'ref_sr','in_ready':'ref_ir','out_valid':'ref_ov','out_bits':'ref_bits','fault':'ref_fault'}
 links=[]
 for p,z in conns.items():
  if p=='clk_leaf':continue
  links.append(f'.{p}({refnames.get(p,z)})')
 decl+='ot_dsrom_markov_row #(.K(256),.PINREG(1),.CUT(511),.SPLIT9(1),.RINGDLY(0)) u_reference ('+','.join(links)+');\n'
 decl+='always @(negedge clk) if(rst_n) begin\n'
 for p in outs:decl+=f' if({conns[p]} !== {refnames[p]}) $fatal(1,"MARKOV_NATIVE_EPOCH_MISMATCH {p}");\n'
 decl+='end\n'
 tb=tb.replace('endmodule',decl+'endmodule',1);tp=out/f'{kind}.sv';tp.write_text(tb);exe=out/f'{kind}.vvp'
 cmd=['iverilog','-g2012','-s',oldname,f'-P{oldname}.PINREG=1']
 if kind!='fault':cmd.append(f'-P{oldname}.MUTANT={mut}')
 if kind=='delay_mut':cmd+=['-DOT_S81_MARKOV_DELAY_MUT_STAGE=3']
 if kind in ['ctl_mut','mul_mut','pair_mut','fold_mut']:cmd+=['-DOT_S81_MARKOV_'+kind.split('_')[0].upper()+'_MUT']
 if kind.startswith('chunk'):cmd+=['-DOT_S81_MARKOV_CHUNK_MUT_STAGE='+kind[5]]
 with (out/f'{kind}_build.log').open('w')as f:rc=subprocess.run(cmd+['-o',str(exe),*map(str,src),str(tp)],stdout=f,stderr=subprocess.STDOUT).returncode
 if rc:print('BUILDFAIL',kind,(out/f'{kind}_build.log').read_text()[-1800:],flush=True);raise SystemExit(rc)
 p=subprocess.run(['vvp',str(exe),f'+DIR={out}'],text=True,capture_output=True);(out/f'{kind}.log').write_text(p.stdout+p.stderr)
 if len(sys.argv)>2 and sys.argv[2].endswith('!'):
  print('MARKOV_NATIVE_DUT','FAIL' if p.returncode!=0 else 'PASS',kind,p.stdout[-300:],flush=True);raise SystemExit(1 if p.returncode!=0 else 0)
 positive=kind in ['exact','fault'];ok=(p.returncode==0)if positive else(p.returncode!=0)
 results.append({'kind':kind,'rc':p.returncode,'expected': 'pass'if positive else'functionalfail','ok':ok,'stdout':p.stdout[-600:]});print(results[-1],flush=True)
 if not ok:raise SystemExit(2)
(out/'receipt.json').write_text(json.dumps({'native':'K256PINREG1CUT511SPLIT9,RING1exactlysameepochs asRING0','clocks':39,'results':results,'source_sha256':{str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest()for p in src},'scope':'48released/stress fullK rows+all3faultcases, every-cycle interface eq against unchanged nativePIN1 reference; physical views/parent integration still owed'},indent=2)+'\n')

print('all_native_checks_PASS',flush=True)
