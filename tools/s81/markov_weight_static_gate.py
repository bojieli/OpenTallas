"""Released mapped Markov W32 ROM, fixed response-slot gate (no arithmetic)."""
import argparse,hashlib,json,struct,subprocess,sys,shutil
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dsrom_markov_head_weight_image import generate,KEY
ROOT=Path(__file__).resolve().parents[2]
def run(snapshot,out):
 out.mkdir(parents=True,exist_ok=False)
 manifest=generate(snapshot,out/'images',1024,32,'mk')
 shutil.copytree(out/'images',out/'mutant_images')
 mp=out/'mutant_images/mk_0.viamap.hex';lines=mp.read_text().splitlines()
 # Actual first weight BF16 sign bit in the via-programmed array; oracle untouched.
 lines[0]=f'{int(lines[0],16)^(1<<(15*8)):0548x}';mp.write_text('\n'.join(lines)+'\n')
 idx=json.loads((snapshot/'model.safetensors.index.json').read_text())['weight_map']
 with (snapshot/idx[KEY]).open('rb')as f:
  n=int.from_bytes(f.read(8),'little');h=json.loads(f.read(n))[KEY]
  f.seek(8+n+h['data_offsets'][0]+1024*512);raw=f.read(32*512)
 expected=[f'{int.from_bytes(raw[i:i+32],"little"):064x}'for i in range(0,len(raw),32)]
 (out/'expected.hex').write_text('\n'.join(expected)+'\n')
 source=ROOT/'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_weight32_static.sv'
 macro_source=ROOT/'physical/asap7_memory_macros/ot_rom_4096x274_m8/ot_rom_4096x274_m8.v'
 macro=out/'macro.v';macro.write_text(macro_source.read_text().replace('rd_out <= word_read(addr_in)','rd_out <= #0.744 word_read(addr_in)'))
 tb=out/'tb.sv';tb.write_text('''`timescale 1ns/1ps
module tb;
 reg clk=0;always #0.4165 clk=~clk;
 reg rst_n=0,request_slot=0;reg[4:0]row=0;reg[16:0]token=31;reg[59:0]identity=0;
 wire word_v,fault;wire[255:0]word_data;wire[3:0]word_beat;wire[16:0]word_row,word_token;wire[59:0]word_identity;
 ot_dsrom_markov_weight32_static #(.GLOBAL_ROW0(1024))dut(.*);
 reg[255:0]expected[0:511];string dir;integer cyc=0,launch=-100,rownum=0,seen=0,checked=0;reg[59:0]eid;
 always @(posedge clk)begin cyc=cyc+1;if(rst_n&&request_slot)begin launch=cyc;eid=identity;end end
 always @(negedge clk)if(rst_n)begin
  if(word_v!==(cyc-launch>=6&&cyc-launch<22))$fatal(1,"slot mismatch age%0d v%b",cyc-launch,word_v);
  if(word_v)begin
   if(word_data!==expected[16*rownum+seen])$fatal(1,"payload row%0d beat%0d got%h expect%h",rownum,seen,word_data,expected[16*rownum+seen]);
   if(word_beat!=seen||word_row!=1024+rownum||word_token!=31||word_identity!=eid)$fatal(1,"metadata");
   seen=seen+1;checked=checked+1;
  end
  if(fault)$fatal(1,"unexpected fault");
 end
 initial begin
  if(!$value$plusargs("DIR=%s",dir))$fatal(1,"DIR");$readmemh({dir,"/expected.hex"},expected);
  repeat(5)@(negedge clk);#0.001;rst_n=1;
  for(rownum=0;rownum<32;rownum=rownum+1)begin
   seen=0;row=5'(rownum);identity=60'(129280+rownum);request_slot=1;
   @(negedge clk);#0.001;request_slot=0;
   while(seen<16)begin @(negedge clk);#0.001;end
   repeat(2)begin @(negedge clk);#0.001;end
  end
  $display("MARKOV_WEIGHT_STATIC PASS checked=%0d fixed_latency=6 beats=16 rows=32",checked);$finish;
 end
 initial begin #20000;$fatal(1,"timeout");end
endmodule
''')
 obj=out/'obj';cmd=['verilator','--binary','--timing','-j','2','-Wno-fatal','--top-module','tb','--Mdir',str(obj),str(source),str(macro),str(tb)]
 p=subprocess.run(cmd,text=True,capture_output=True);(out/'build.log').write_text(p.stdout+p.stderr)
 if p.returncode:raise RuntimeError(p.stderr[-2000:])
 results=[]
 for mut in (0,1):
  p=subprocess.run([str(obj/'Vtb'),f'+DIR={out}',f'+OT_ROM_DIR={out/("mutant_images" if mut else "images")}'],text=True,capture_output=True)
  (out/f'run{mut}.log').write_text(p.stdout+p.stderr);print(p.stdout[-1500:],flush=True)
  results.append(dict(mutant=mut,exit=p.returncode,ok=('payload row0 beat0' in p.stdout and p.returncode!=0)if mut else('MARKOV_WEIGHT_STATIC PASS' in p.stdout and p.returncode==0)))
 rec=dict(gate='PASS'if all(x['ok']for x in results)else'FAIL',results=results,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(source,macro_source,Path(__file__))},released=manifest,rows=32,beats=512,latency=6,full_native_token_qualified=False,physical_qualified=False,scope='actual released W32 mapped mask-ROM and fixed slots only; all 4040 row blocks/full-head static composition remain required')
 (out/'record.json').write_text(json.dumps(rec,indent=2)+'\n');return rec['gate']=='PASS'
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--snapshot',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();raise SystemExit(0 if run(a.snapshot,a.out.resolve())else 1)
