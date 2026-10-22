#!/usr/bin/env python3
"""Arbitrary-initial-state reset proof on an exact emitted native endpoint cut.
No full-source reachability claim: victim state is explicitly arbitrary before
reset. The common upstream asynchronous assertion is the same for root/copy.
"""
import hashlib,json,re,sys,pathlib
oldp,newp,rp,outp=sys.argv[1:5];old,new=open(oldp).read(),open(newp).read();rr=json.load(open(rp))
pat=re.compile(r'^\s*(?:\(\*[^*]*\*\)\s*)?(\w+)\s+(c\w+)\s*\((.*)\);\s*$',re.M)
def parse(s):return {n:(m,dict((k,v.strip()) for k,v in re.findall(r'\.(\w+)\(([^()]*)\)',ps))) for m,n,ps in pat.findall(s)}
a,b=parse(old),parse(new);root=rr['roots'][0];cn=root['clones'][0]['name'];victim,pin,_=root['clones'][0]['endpoints'][0]
assert a[victim][0]==b[victim][0]=='DFFASRHQNx1_ASAP7_75t_R'
def polarity(cells,net,target):
 drivers={v:(n,p) for n,(m,ps) in cells.items() for p,v in ps.items() if p in {'Y','QN','Q','H','L','CON','SN'}}
 invert=0
 while net!=target:
  n,p=drivers[net];m,ps=cells[n];assert m.startswith(('BUF','INV','HB'))
  invert^=m.startswith('INV');net=ps['A']
 return int(invert)
op=polarity(a,a[victim][1][pin],a[root['master']][1]['QN'])
np=polarity(b,b[victim][1][pin],b[cn][1]['QN'])
s=['`timescale 1ns/1ps','module reset_witness_tb;','reg clk=0,d=1,rst=1;wire oq,cq,ov,cv;integer checks=0;',
 'DFFASRHQNx1_ASAP7_75t_R root(.CLK(clk),.D(d),.QN(oq),.RESETN(rst),.SETN(1\'b1));',
 'DFFASRHQNx1_ASAP7_75t_R copy(.CLK(clk),.D(d),.QN(cq),.RESETN(rst),.SETN(1\'b1));',
 'wire old_reset='+('~' if op else '')+'oq;', 'wire new_reset='+('~' if np else '')+'cq;',
 'DFFASRHQNx1_ASAP7_75t_R original_victim(.CLK(clk),.D(1\'b0),.QN(ov),.RESETN(old_reset),.SETN(1\'b1));',
 'DFFASRHQNx1_ASAP7_75t_R candidate_victim(.CLK(clk),.D(1\'b0),.QN(cv),.RESETN(new_reset),.SETN(1\'b1));',
 'initial begin',
 'for(int phase=0;phase<16;phase++)for(int seed=0;seed<2;seed++)begin',
 ' clk=0;rst=1;d=1;#0.001;clk=1;#0.001;clk=0;#0.001;',
 ' // Explicit arbitrary pre-reset state, not a claim of functional payload reachability.',
 ' original_victim.IQN=seed[0];candidate_victim.IQN=seed[0];#0.001;',
 ' #(0.001*phase);rst=0;#0.001;',
 ' if(ov!==1\'b1 || cv!==ov)begin $display("RESET32_ARBITRARY_INIT_ASSERT_FAIL phase=%0d seed=%0d old=%b new=%b",phase,seed,ov,cv);$fatal(1);end checks++;',
 ' rst=1;#0.001;if(cv!==ov)$fatal(1,"release changed state");checks++;',
 'end',
 '$display("RESET32_ARBITRARY_INIT_ASSERT_PASS checks=%0d phases=16 initial_states=2",checks);$finish;end','endmodule']
pathlib.Path(outp).write_text('\n'.join(s)+'\n')
print(json.dumps(dict(source_sha256=hashlib.sha256(new.encode()).hexdigest(),master=root['master'],copy=cn,endpoint=victim+'/'+pin,original_polarity=op,candidate_polarity=np,proof_scope='arbitrary initial victim state; shared actual native ASR assertion; stopped common clock')))
