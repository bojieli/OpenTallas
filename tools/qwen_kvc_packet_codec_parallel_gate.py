#!/usr/bin/env python3
"""Independent polynomial-division golden vs registered RTL packet codec."""
import argparse,json,random,subprocess,hashlib
from pathlib import Path

def crc(body):
    rem=(0xffffffff<<478)^(body<<32)
    poly=(1<<32)|0x04c11db7
    for n in range(rem.bit_length()-1,31,-1):
        if (rem>>n)&1: rem^=poly<<(n-32)
    return rem^0xffffffff

def packet(op,epoch,pc,seq,tag,sec,data,version=1,reserved=0):
    fields=[(version,4),(op,4),(epoch,8),(pc,7),(seq,16),(tag,9),(sec,24),(data,256),(reserved,150)]
    b=0
    for v,w in fields: assert 0<=v<(1<<w);b=(b<<w)|v
    return (b<<32)|crc(b)

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--parallel',action='store_true');a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
r=Path(__file__).resolve().parents[1];src=r/('rtl/physical/ot_qwen_kvc_packet_codec_parallel.sv' if a.parallel else 'rtl/physical/ot_qwen_kvc_packet_codec.sv');rng=random.Random(417)
legal=[packet(op,ep,pc,s,t,sec,data) for op,ep,pc,s,t,sec,data in [(1,0,0,0,0,0,0),(1,255,127,65535,511,0xffffff,(1<<256)-1),(2,255,127,65535,511,0,0)]]
for _ in range(125):
 op=rng.choice([1,2]);legal.append(packet(op,rng.randrange(256),rng.randrange(128),rng.randrange(65536),rng.randrange(512),rng.randrange(1<<24) if op==1 else 0,rng.getrandbits(256) if op==1 else 0))
# Single-bit corruption at EVERY packet position, plus fresh valid CRC on illegal semantics.
vectors=[(w,1) for w in legal]+[(legal[1]^(1<<bit),0) for bit in range(510)]
vectors += [(packet(1,3,4,5,6,7,8,version=2),0),(packet(3,3,4,5,6,7,8),0),(packet(1,3,4,5,6,7,8,reserved=1),0),(packet(2,3,4,5,6,1,0),0),(packet(2,3,4,5,6,0,1),0)]
(a.out/'packets.hex').write_text(''.join(f'{w:0128x}\n' for w,g in vectors));(a.out/'expected.hex').write_text(''.join(f'{g:x}\n' for w,g in vectors));(a.out/'legal.hex').write_text(''.join(f'{w:0128x}\n' for w in legal))
bench='''`timescale 1ns/1ps
module tb;
parameter integer ENABLE=1;
reg clk=0,rst_n=0,v=0;always #1 clk=~clk;
reg[509:0] pkt=0;wire dv,db,ev,eb;wire[509:0] dout,eout;wire[3:0] op;wire[7:0] epoch;wire[6:0] pc;wire[15:0] seq;wire[8:0] tag;wire[23:0] sec;wire[255:0] data;
ot_qwen_kvc_packet_decode #(.ENABLE(ENABLE)) d(.clk(clk),.rst_n(rst_n),.i_v(v),.i_packet(pkt),.o_v(dv),.o_bad(db),.o_packet(dout),.o_op(op),.o_epoch(epoch),.o_pc(pc),.o_seq(seq),.o_tag(tag),.o_sec(sec),.o_data(data));
ot_qwen_kvc_packet_encode #(.ENABLE(ENABLE)) e(.clk(clk),.rst_n(rst_n),.i_v(v),.i_op(pkt[505:502]),.i_epoch(pkt[501:494]),.i_pc(pkt[493:487]),.i_seq(pkt[486:471]),.i_tag(pkt[470:462]),.i_sec(pkt[461:438]),.i_data(pkt[437:182]),.o_v(ev),.o_bad(eb),.o_packet(eout));
reg[509:0] packets[0:NDEC-1];reg good[0:NDEC-1];reg[509:0] legal[0:NENC-1];integer i,bad=0;
initial begin
 $readmemh("packets.hex",packets);$readmemh("expected.hex",good);$readmemh("legal.hex",legal);
 repeat(2) @(negedge clk);rst_n=1;
 for(i=0;i<NDEC;i=i+1) begin
  @(negedge clk);pkt=packets[i];v=1;@(posedge clk);#0.1;
  if(dv !== ((ENABLE!=0)&&good[i]) || db !== ((ENABLE!=0)&&!good[i])) bad=bad+1;
  if(ENABLE!=0 && (dout!==pkt || {op,epoch,pc,seq,tag,sec,data}!==pkt[505:182])) bad=bad+1;
 end
 for(i=0;i<NENC;i=i+1) begin
  @(negedge clk);pkt=legal[i];v=1;@(posedge clk);#0.1;
  if(ev!== (ENABLE!=0) || eb!==0)bad=bad+1;
  if(ENABLE!=0 && eout!==pkt)bad=bad+1;
 end
 // Last illegal semantic vectors have bad opcode or DONE payload; encoder must not publish.
 for(i=NDEC-4;i<NDEC;i=i+1) begin
  if(i!=NDEC-3) begin
   @(negedge clk);pkt=packets[i];v=1;@(posedge clk);#0.1;
   if(ev!==0 || eb!==(ENABLE!=0))bad=bad+1;
  end
 end
 @(negedge clk);v=0;@(posedge clk);#0.1;if(dv!==0||db!==0||ev!==0||eb!==0)bad=bad+1;
 @(negedge clk);rst_n=0;#0.1;if(dv!==0||db!==0||ev!==0||eb!==0)bad=bad+1;
 if(bad==0)$display("PASS codec decode=%0d encode=%0d enable=%0d",NDEC,NENC,ENABLE);else $fatal(1,"FAIL codec bad=%0d",bad);
 $finish;
end
endmodule
'''.replace('NDEC',str(len(vectors))).replace('NENC',str(len(legal)))

if a.parallel: bench=bench.replace('ot_qwen_kvc_packet_encode','ot_qwen_kvc_packet_encode_parallel').replace('ot_qwen_kvc_packet_decode','ot_qwen_kvc_packet_decode_parallel')
(a.out/'tb.sv').write_text(bench);results=[]
for name,enabled,mut in [('enabled',1,None),('disabled',0,None),('crc_polynomial_mutant',1,("32'h04c11db7","32'h04c11db6")),('reserved_check_mutant',1,('(i_packet[181:32]==0)','1\'b1')),('done_check_mutant',1,('&& (i_packet[437:182]==0)',''))]:
 source=src.read_text()
 if mut:
  if a.parallel and name=='crc_polynomial_mutant': source=source.replace("crc32[0] = ^(body","crc32[0] = ~^(body")
  else: source=source.replace(*mut)
 variant=a.out/(name+'.sv');variant.write_text(source);exe=a.out/(name+'.vvp')
 c=subprocess.run(['iverilog','-g2012','-s','tb','-Ptb.ENABLE='+str(enabled),'-o',str(exe),str(a.out/'tb.sv'),str(variant)],capture_output=True,text=True);assert c.returncode==0,c.stderr
 z=subprocess.run(['vvp',str(exe)],cwd=a.out,capture_output=True,text=True);(a.out/(name+'.log')).write_text(z.stdout+z.stderr)
 passed=z.returncode==0 and 'PASS codec' in z.stdout;expected=mut is None
 results.append(dict(case=name,observed_pass=passed,expected_pass=expected,gate_pass=passed==expected));print(name,z.stdout.strip())
x={'pass_all':all(q['gate_pass'] for q in results),'cases':results,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'decoder_vectors':len(vectors),'legal_encoder_vectors':len(legal),'all_single_bit_positions_tested':510,'golden':'Independent integer polynomial long division; RTL uses serial feedback recurrence.','scope':'Exact packet contents/pulses and malformed rejection. CDC, epoch ownership, mutable-state protection and physical timing not qualified.'};(a.out/'result.json').write_text(json.dumps(x,indent=2)+'\n');assert x['pass_all']
