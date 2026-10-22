import importlib.util,itertools,json,re,sys
from pathlib import Path
sp=importlib.util.spec_from_file_location("native", "native_census.py");m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m)
roles,receipts=m.liberty_roles(list(Path("real5").glob("asap7sc*")))
def evaluate(expr, values):
 toks=re.findall(r"[A-Za-z_][A-Za-z_0-9]*|[01]|[()!~&*|+^']",expr)
 assert re.sub(r"\s+","",expr)=="".join(toks),expr
 pos=0
 def atom():
  nonlocal pos
  t=toks[pos];pos+=1
  if t in ("!","~"):v=not atom()
  elif t=="(":
   v=disj();assert toks[pos]==")";pos+=1
  elif t in ("0","1"):v=t=="1"
  else:v=values[t]
  while pos<len(toks) and toks[pos]=="'":v=not v;pos+=1
  return v
 def conj():
  nonlocal pos
  v=atom()
  while pos<len(toks) and toks[pos] not in (")","|","+","^"):
   if toks[pos] in ("&","*"):pos+=1
   w=atom();v=v and w
  return v
 def xor():
  nonlocal pos
  v=conj()
  while pos<len(toks) and toks[pos]=="^":pos+=1;v=bool(v)^bool(conj())
  return v
 def disj():
  nonlocal pos
  v=xor()
  while pos<len(toks) and toks[pos] in ("|","+"):pos+=1;w=xor();v=v or w
  return v
 v=disj();assert pos==len(toks);return int(v)
# Hand checks exercise precedence, implicit AND, complement and xor separately.
assert evaluate("!A & B + A ^ B",dict(A=0,B=1))==1
assert evaluate("A B'",dict(A=1,B=0))==1
lines=["`timescale 1ns/1ps","module tb_comb;reg[15:0]v=0;"];checks=[];maxi=0;count=0;truth=0
for name,c in sorted(roles.items()):
 if c["sequential"] or any(d["direction"]=="output" and d["function"] is None for d in c["pins"].values()):continue
 ins=sorted(p for p,d in c["pins"].items() if d["direction"]=="input")
 outs=sorted(p for p,d in c["pins"].items() if d["direction"]=="output")
 if not outs:continue
 assert len(ins)<=16
 maxi=max(maxi,len(ins));connections=["."+p+"(v["+str(i)+"])" for i,p in enumerate(ins)]
 for o in outs:
  func=c["pins"][o]["function"];assert func is not None,(name,o)
  tab=[evaluate(func,{p:bool(bits>>i&1)for i,p in enumerate(ins)})for bits in range(1<<len(ins))]
  truth+=len(tab);net="y"+str(count);lines.append("wire "+net+";")
  lines.append("localparam["+str(len(tab)-1)+":0]T"+str(count)+"="+str(len(tab))+"'b"+"".join(map(str,reversed(tab)))+";")
  idx="v["+str(len(ins)-1)+":0]" if ins else "0"
  checks.append("if("+net+"!==T"+str(count)+"["+idx+"])begin $display(\"COMB_MODELS FAIL "+name+"/"+o+" v=%0d\",v);$fatal;end")
  connections.append("."+o+"("+net+")");count+=1
 lines.append(name+" u"+str(count)+"("+",".join(connections)+");")
lines.append("initial begin for(integer k=0;k<"+str(1<<maxi)+";k=k+1)begin v=k;#1;"+"\n".join(checks)+"\nend $display(\"COMB_MODELS PASS outputs="+str(count)+" unique_truth_entries="+str(truth)+"\");$finish;end endmodule")
Path("models/tb_comb.sv").write_text("\n".join(lines)+"\n")
print(json.dumps({"outputs":count,"unique_truth_entries":truth,"max_inputs":maxi,"libs":receipts}))
