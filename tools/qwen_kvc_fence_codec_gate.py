#!/usr/bin/env python3
import argparse,random,json,subprocess,hashlib
from pathlib import Path

def crc(body):
 rem=(0xffffffff<<478)^(body<<32);poly=(1<<32)|0x04c11db7
 for n in range(rem.bit_length()-1,31,-1):
  if(rem>>n)&1:rem^=poly<<(n-32)
 return rem^0xffffffff

def packet(op=1,epoch=7,pc=31,seq=4,tag=3,sec=123,data=456,version=1,reserved=0):
 b=0
 for v,w in [(version,4),(op,4),(epoch,8),(pc,7),(seq,16),(tag,9),(sec,24),(data,256),(reserved,150)]:
  assert 0<=v<(1<<w);b=(b<<w)|v
 return (b<<32)|crc(b)

def ackdata(mask,entries):
 d=mask
 for i,e in enumerate(entries):
  if (mask>>i)&1:d|=e<<(8+25*i)
 return d

p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);r=Path(__file__).resolve().parents[1];src=r/'rtl/physical/ot_qwen_kvc_packet_codec_fence.sv';rng=random.Random(833)
legal=[packet(),packet(op=2,sec=0,data=0)]
for exhausted in [0,1]:
 legal += [packet(op=3,seq=65535,tag=exhausted,sec=8,data=0),packet(op=4,seq=65535,tag=exhausted,sec=8,data=0),packet(op=4,seq=65535,tag=exhausted,sec=8,data=ackdata(255,[((65528+i)<<9)|i for i in range(8)]))]
for _ in range(120):
 op=rng.randrange(1,5);epoch=rng.randrange(256);pc=rng.randrange(128);seq=rng.randrange(65536);tag=rng.randrange(512) if op in [1,2] else rng.randrange(2);sec=rng.randrange(1<<24) if op==1 else 0 if op==2 else (epoch+1)%256
 data=rng.getrandbits(256) if op==1 else ackdata(rng.randrange(256),[rng.randrange(1<<25) for _ in range(8)]) if op==4 else 0
 legal.append(packet(op,epoch,pc,seq,tag,sec,data))
encbad=[packet(op=5),packet(op=2,sec=1,data=0),packet(op=2,sec=0,data=1),packet(op=3,tag=2,sec=8,data=0),packet(op=3,tag=0,sec=256,data=0),packet(op=3,tag=0,sec=8,data=1),packet(op=4,tag=2,sec=8,data=0),packet(op=4,tag=0,sec=256,data=0),packet(op=4,tag=0,sec=8,data=1<<208),packet(op=4,tag=0,sec=8,data=1<<8)]
vectors=[(x,1) for x in legal]+[(legal[-1]^(1<<b),0) for b in range(510)]+[(x,0) for x in encbad]+[(packet(version=2),0),(packet(reserved=1),0)]
for name,words in [('packets',[x for x,g in vectors]),('legal',legal),('encbad',encbad)]: (a.out/(name+'.hex')).write_text(''.join(f'{x:0128x}\n' for x in words))
(a.out/'expected.hex').write_text(''.join(f'{g:x}\n' for x,g in vectors))
basis=[0]+[1<<i for i in range(478)]+[(1<<478)-1]
(a.out/'basis.hex').write_text(''.join(f'{b:0120x}\n' for b in basis))
(a.out/'basis_crc.hex').write_text(''.join(f'{crc(b):08x}\n' for b in basis))
bench='''`timescale 1ns/1ps
module tb;
parameter integer ENABLE=1;
reg clk=0,rst_n=0,v=0;always #1 clk=~clk;
reg[509:0] pkt=0;wire dv,db,ev,eb;wire[509:0] dout,eout;wire[3:0] op;wire[7:0] epoch;wire[6:0] pc;wire[15:0] seq;wire[8:0] tag;wire[23:0] sec;wire[255:0] data;
ot_qwen_kvc_packet_decode_fence #(.ENABLE(ENABLE)) d(.clk(clk),.rst_n(rst_n),.i_v(v),.i_packet(pkt),.o_v(dv),.o_bad(db),.o_packet(dout),.o_op(op),.o_epoch(epoch),.o_pc(pc),.o_seq(seq),.o_tag(tag),.o_sec(sec),.o_data(data));
ot_qwen_kvc_packet_encode_fence #(.ENABLE(ENABLE)) e(.clk(clk),.rst_n(rst_n),.i_v(v),.i_op(pkt[505:502]),.i_epoch(pkt[501:494]),.i_pc(pkt[493:487]),.i_seq(pkt[486:471]),.i_tag(pkt[470:462]),.i_sec(pkt[461:438]),.i_data(pkt[437:182]),.o_v(ev),.o_bad(eb),.o_packet(eout));
reg[477:0] bodies[0:479];reg[31:0] basis_crc[0:479];
reg[509:0] packets[0:NDEC-1],legal[0:NENC-1],encbad[0:NBAD-1];reg good[0:NDEC-1];integer i,bad=0;
initial begin
 $readmemh("packets.hex",packets);$readmemh("expected.hex",good);$readmemh("legal.hex",legal);$readmemh("encbad.hex",encbad);
 $readmemh("basis.hex",bodies);$readmemh("basis_crc.hex",basis_crc);
 for(i=0;i<480;i=i+1)begin
  if(d.crc32(bodies[i])!==basis_crc[i] || e.crc32(bodies[i])!==basis_crc[i])bad=bad+1;
 end
 repeat(2)@(negedge clk);rst_n=1;
 for(i=0;i<NDEC;i=i+1)begin
  @(negedge clk);pkt=packets[i];v=1;@(posedge clk);#0.1;
  if(dv!==((ENABLE!=0)&&good[i])||db!==((ENABLE!=0)&&!good[i]))bad=bad+1;
  if(ENABLE!=0&&(dout!==pkt||{op,epoch,pc,seq,tag,sec,data}!==pkt[505:182]))bad=bad+1;
 end
 for(i=0;i<NENC;i=i+1)begin
  @(negedge clk);pkt=legal[i];v=1;@(posedge clk);#0.1;
  if(ev!==(ENABLE!=0)||eb!==0)bad=bad+1;
  if(ENABLE!=0&&eout!==pkt)bad=bad+1;
 end
 for(i=0;i<NBAD;i=i+1)begin
  @(negedge clk);pkt=encbad[i];v=1;@(posedge clk);#0.1;
  if(ev!==0||eb!==(ENABLE!=0))bad=bad+1;
 end
 @(negedge clk);v=0;@(posedge clk);#0.1;if(dv!==0||db!==0||ev!==0||eb!==0)bad=bad+1;
 @(negedge clk);rst_n=0;#0.1;if(dv!==0||db!==0||ev!==0||eb!==0)bad=bad+1;
 if(bad==0)$display("PASS fence_codec decode=%0d encode=%0d bad_encode=%0d enable=%0d",NDEC,NENC,NBAD,ENABLE);else $fatal(1,"FAIL fence_codec bad=%0d",bad);
 $finish;
end
endmodule
'''.replace('NDEC',str(len(vectors))).replace('NENC',str(len(legal))).replace('NBAD',str(len(encbad)));(a.out/'tb.sv').write_text(bench);rows=[]
mutants=[('enabled',1,None),('disabled',0,None),('crc_mutant',1,('crc32[0] = ^(body','crc32[0] = ~^(body')),('ack_invalid_slot_mutant',1,("if(!data[j] && (data[8+25*j +:25]!=0))", "if(1'b0)")),('fence_metadata_mutant',1,('(tag[8:1]==0)',"1'b1")),('reserved_mutant',1,('(i_packet[181:32]==0)',"1'b1"))]
for name,en,mut in mutants:
 s=src.read_text()
 if mut:
  changed=s.replace(*mut);assert changed!=s;s=changed
 v=a.out/(name+'.sv');v.write_text(s);exe=a.out/(name+'.vvp');c=subprocess.run(['iverilog','-g2012','-s','tb','-Ptb.ENABLE='+str(en),'-o',str(exe),str(a.out/'tb.sv'),str(v)],capture_output=True,text=True);assert c.returncode==0,c.stderr
 z=subprocess.run(['vvp',str(exe)],cwd=a.out,capture_output=True,text=True);(a.out/(name+'.log')).write_text(z.stdout+z.stderr);passed=z.returncode==0 and 'PASS fence_codec' in z.stdout;expected=mut is None;rows.append(dict(case=name,expected_pass=expected,observed_pass=passed,gate_pass=expected==passed));print(name,z.stdout.strip())
x={'pass_all':all(q['gate_pass'] for q in rows),'cases':rows,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'legal_vectors':len(legal),'decoder_vectors':len(vectors),'malformed_encoder_vectors':len(encbad),'single_bit_positions':510,'CRC_affine_basis_vectors':480,'golden':'Independent integer polynomial division; canceledmask layout explicit; exhausted65535 watermark variants included.','scope':'Codec framing only; exact cancellation-set/epoch readiness validation belongs to bridge. No physical or mutable-storage qualification.'};(a.out/'result.json').write_text(json.dumps(x,indent=2)+'\n');assert x['pass_all']
