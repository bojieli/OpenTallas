import json,gzip,pathlib,copy,re,collections,hashlib,ast
P=pathlib.Path(__file__).resolve().parent
J=json.loads((P/"input/old.json").read_text());old=next(v for k,v in J["modules"].items() if k.startswith("qfd_host"));model=json.loads((P/"input/model.json").read_text());sem=json.load(gzip.open(P/"input/native_semantics.json.gz"))["candidate"];L=sem["all_native_types"];cs=old["cells"];corr=sem["state_correspondence"];pubs=model["all_publications"]
assert hashlib.sha256((P/"input/all.lib").read_bytes()).hexdigest()=="7110a7a75b4d2802053266c170bed511640a53d1c85ba9e43939fd4cb8dfe817"
def groups(text, kind):
 for mt in re.finditer(r"\b"+kind+r"\s*\(([^)]*)\)\s*\{",text):
  depth=1;i=mt.end()
  while depth:depth+=(text[i]=="{")-(text[i]=="}");i+=1
  yield mt[1].strip().strip(chr(34)),text[mt.end():i-1]
def attr(body,key):
 mt=re.search(r"\b"+key+r"\s*:\s*([^;]+);",body)
 return mt[1].strip().strip(chr(34)) if mt else None
native={}
for n,b in groups((P/"input/all.lib").read_text(),"cell"):
 native[n]={"functions":{pn:attr(pb,"function") for pn,pb in groups(b,"pin") if attr(pb,"direction")=="output"},"ff":[{k:attr(fb,k) for k in ["clear","preset","next_state","clocked_on","clear_preset_var1","clear_preset_var2"]} for _,fb in groups(b,"ff")],"pg":{pn:attr(pb,"pg_type") for pn,pb in groups(b,"pg_pin")}}
for t in L:
 for key in ["functions","ff","pg"]:assert native[t][key]==L[t][key],("LIBRARY_SEMANTICS_DRIFT",t,key)
(P/"native_lib_verified.json").write_text(json.dumps({t:native[t] for t in L},indent=2)+"\n")
new=copy.deepcopy(old);new["cells"]={};new["netnames"]={};outmap={};nextbit=2000
for p in pubs:
 r=p["root_bit"];k=int(p["identity"].split("_")[-1]);driver=p["original_driver"]
 if driver and not L[p["master"]]["ff"]:
  n,op=driver;c=copy.deepcopy(cs[n]);b=r if k==0 else nextbit;nextbit+=k!=0;c["connections"][op]=[b];c["attributes"]={"keep":"1","dont_touch":"1","publication_identity":p["identity"]};new["cells"][p["identity"]]=c
 else:b=r
 outmap[(r,k,False)]=b
 if p["negative_publication_INV"]:
  b2=nextbit;nextbit+=1
  # Preserve original inverter identity on cohort zero.
  names=[n for n,c in cs.items() if c["type"]=="INVx1_ASAP7_75t_R" and c["connections"]["A"]==[r]]
  assert len(names)==1,(r,names)
  name=names[0] if k==0 else p["identity"]+"_inv"
  c=copy.deepcopy(cs[names[0]]);c["connections"]={"A":[b],"Y":[b2]};c["attributes"]={"keep":"1","dont_touch":"1"};new["cells"][name]=c;outmap[(r,k,True)]=b2
for n,c in cs.items():
 if L[c["type"]]["ff"]:new["cells"][n]=copy.deepcopy(c)
# Ownership consumes every nontransparent input and every output alias once.
assigned=set()
for p in pubs:
 r=p["root_bit"];k=int(p["identity"].split("_")[-1])
 for s in p["sinks"]:
  b=outmap[(r,k,s["inverted"])];key=(s["owner"],s["pin"]);assert key not in assigned,key;assigned.add(key)
  if s["owner"]=="OUTPUT":
   match=re.fullmatch(r"(.*)\[(\d+)\]",s["pin"]);new["ports"][match[1]]["bits"][int(match[2])]=b
  else:new["cells"][s["owner"]]["connections"][s["pin"]]=[b]
# model normalizes original INV paths only; preserve all state identities/ports.
assert len(new["cells"])==1109
for n in corr:
 for p in ["CLK","RESETN","SETN","QN"]:assert new["cells"][n]["connections"][p]==cs[n]["connections"][p]
assert collections.Counter(c["type"] for c in new["cells"].values())==collections.Counter(model["proposed_master_counts"])
(P/"graph.json").write_text(json.dumps({"modules":{"publication_native":new}},indent=2)+"\n")
def wire(b):return "n"+str(b) if isinstance(b,int) else "1\u0027b"+b
# Exact native instances and blackboxes. Reparse performs no logic optimization.
lines=["module publication_native("+",".join(old["ports"])+");"]
for n,p in new["ports"].items():lines.append(p["direction"]+" wire "+("["+str(len(p["bits"])-1)+":0] " if len(p["bits"])>1 else "")+n+";")
allbits={b for c in new["cells"].values() for bs in c["connections"].values() for b in bs if isinstance(b,int)};lines.append("wire "+",".join(wire(b) for b in sorted(allbits))+";")
for n,p in new["ports"].items():
 for i,b in enumerate(p["bits"]):
  pn=n+("["+str(i)+"]" if len(p["bits"])>1 else "");lines.append("assign "+(wire(b)+" = "+pn if p["direction"]=="input" else pn+" = "+wire(b))+";")
for n,c in new["cells"].items():lines.append("(* keep = 1, dont_touch = 1 *) "+c["type"]+" \\"+n+" ("+",".join("."+p+"("+wire(bs[0])+")" for p,bs in c["connections"].items())+");")
lines.append("endmodule")
for t in sorted(L):
 pins={p:d["direction"] for p,d in L[t]["pins"].items()};lines.append("(* blackbox *) module "+t+"("+",".join(pins)+"); "+" ".join(d+" "+p+";" for p,d in pins.items())+" endmodule")
(P/"publication_native.sv").write_text("\n".join(lines)+"\n")
# Generate exact combinational equations directly from the implementation graph.
prior=(P/"input/prior_proof.sv").read_text();header=re.search(r"module old_next\((.*?)\);",prior,re.S)[1];source=prior[:prior.index("module candidate_native_next")];proof=prior[prior.index("module native_proof"):]
stateout={}
for n,v in corr.items():stateout[old["ports"][v["name"]]["bits"][v["bit"]]]=v["state_index"]
# Four-value primitive expression compilation; 00=0 01=1 10=X 11=Z.
def expr(func,c,encoded):
 text=re.sub(r"!(?!=)","~",func).replace("*","&").replace("+","|")
 tree=ast.parse(text,mode="eval").body
 def visit(x):
  if isinstance(x,ast.Name):return wire(c["connections"][x.id][0])
  if isinstance(x,ast.Constant):return ("2\u0027d" if encoded else "1\u0027b")+str(x.value)
  if isinstance(x,ast.UnaryOp):return ("vnot("+visit(x.operand)+")") if encoded else "~("+visit(x.operand)+")"
  if isinstance(x,ast.BinOp):
   op={ast.BitAnd:("vand","&"),ast.BitOr:("vor","|"),ast.BitXor:("vxor","^")}[type(x.op)]
   return op[0]+"("+visit(x.left)+","+visit(x.right)+")" if encoded else "("+visit(x.left)+op[1]+visit(x.right)+")"
  raise ValueError(ast.dump(x))
 return visit(tree)
funcs="""function [1:0] vnot;input [1:0] a;begin vnot=a[1]?2\u0027d2:{1\u0027b0,~a[0]};end endfunction
function [1:0] vand;input [1:0] a,b;begin vand=(a==0||b==0)?0:((a==1&&b==1)?1:2);end endfunction
function [1:0] vor;input [1:0] a,b;begin vor=(a==1||b==1)?1:((a==0&&b==0)?0:2);end endfunction
function [1:0] vxor;input [1:0] a,b;begin vxor=(a[1]||b[1])?2:{1\u0027b0,a[0]^b[0]};end endfunction
"""
def graphmod(m,name,encoded=False):
 if encoded:
  ports=[n for n,p in old["ports"].items() if p["direction"]=="input" and n!="ck"]
  decl=["input wire ["+str(2*len(old["ports"][n]["bits"])-1)+":0] "+n for n in ports]+["input wire [289:0] state","output wire [611:0] result"]
  rows=["module "+name+"("+",".join(decl)+");",funcs]
 else:rows=["module "+name+"("+header+");"]
 bits={b for c in m["cells"].values() for bs in c["connections"].values() for b in bs if isinstance(b,int)}
 for b in sorted(bits):rows.append("wire "+("[1:0] " if encoded else "")+wire(b)+";")
 def w(b):return wire(b) if isinstance(b,int) else ("2\u0027d" if encoded else "1\u0027b")+b
 for n,p in m["ports"].items():
  if p["direction"]!="input":continue
  for i,b in enumerate(p["bits"]):
   rhs=("2\u0027d0" if encoded else "1\u0027b0") if n=="ck" else (n+f"[{2*i}+:2]" if encoded else n+(f"[{i}]" if len(p["bits"])>1 else ""))
   rows.append("assign "+wire(b)+"="+rhs+";")
 for n,c in m["cells"].items():
  if L[c["type"]]["ff"]:
   v=corr[n];i=v["state_index"];iv=v["output_inverted_from_qn"];s="state"+(f"[{2*i}+:2]" if encoded else f"[{i}]");qn=w(c["connections"]["QN"][0]);d=w(c["connections"]["D"][0]);rst=w(c["connections"]["RESETN"][0]);st=w(c["connections"]["SETN"][0])
   rows.append("assign "+qn+"="+(("vnot("+s+")" if encoded else "~("+s+")") if iv else s)+";")
   if not encoded:
    # Actual active-low asynchronous SETN clear and RESETN preset. Both asserted IQN=L per library.
    nq=f"(!{st} ? 1\u0027b0 : (!{rst} ? 1\u0027b1 : ~{d}))"
    rows.append(f"wire next_{i}; assign next_{i}="+("~("+nq+")" if iv else nq)+";")
  else:
   for op,f in L[c["type"]]["functions"].items():
    cc=copy.deepcopy(c)
    # Constants need expression names replaced after parser.
    e=expr(f,cc,encoded)
    if encoded:e=re.sub(r"1\u0027b([01xz])",lambda z:"2\u0027d"+{"0":"0","1":"1","x":"2","z":"3"}[z[1]],e)
    rows.append("assign "+w(c["connections"][op][0])+"="+e+";")
 outs=[]
 for n in ["accepted_v","host_epoch_valid","host_tag","host_gen","host_fusedcap","host_image_epoch","host_image_digest","fault","host_epoch"]:
  for b in reversed(old["ports"][n]["bits"]):
   if encoded:
    # Compare current native output aliases directly, plus all native D terminals below.
    i=old["ports"][n]["bits"].index(b);outs.append(w(m["ports"][n]["bits"][i]))
   else:outs.append("next_"+str(stateout[b]))
 if encoded:
  outs += [w(m["cells"][n]["connections"]["D"][0]) for n in sorted(corr)]
 assert len(outs)==(306 if encoded else 161)
 rows.append("assign result={"+",".join(outs)+"}; endmodule")
 return "\n".join(rows)
(P/"binary.sv").write_text(source+graphmod(new,"publication_next")+"\n"+proof.replace("candidate_native_next u_b","publication_next u_b"))
# Native-to-native binary comparison additionally retains exact original native module.
native=re.search(r"module candidate_native_next.*?endmodule",prior,re.S)[0]
(P/"native_binary.sv").write_text(native+"\n"+graphmod(new,"publication_next")+"\n"+proof.replace("new_next u_a","candidate_native_next u_a").replace("candidate_native_next u_b","publication_next u_b"))
four=graphmod(old,"old4",True)+"\n"+graphmod(new,"new4",True)
inports=[n for n,p in old["ports"].items() if p["direction"]=="input" and n!="ck"]
decl=[f"input [{2*len(old['ports'][n]['bits'])-1}:0] {n}" for n in inports]+["input [289:0] state","output ok"]
con=",".join("."+n+"("+n+")" for n in inports+["state"])
four+="\nmodule four_proof("+",".join(decl)+"); wire [611:0] a,b;old4 u_a("+con+",.result(a));new4 u_b("+con+",.result(b));assign ok=a==b;endmodule\n"
(P/"four.sv").write_text(four)
(P/"elab.ys").write_text("read_verilog -sv publication_native.sv\nhierarchy -check -top publication_native\nwrite_json elaborated.json\nwrite_verilog -noattr reparsed.sv\n")
for f,top in [("binary","native_proof"),("native_binary","native_proof"),("four","four_proof")]:
 (P/(f+".ys")).write_text(f"read_verilog -formal {f}.sv\nhierarchy -top {top}\nproc\nflatten\nopt_clean\nsat -verify -prove ok 1 -show-inputs -show-outputs\n")
(P/"inventory.json").write_text(json.dumps({"cells":len(new["cells"]),"masters":dict(collections.Counter(c["type"] for c in new["cells"].values())),"states":len(corr),"inputs":sum(len(p["bits"]) for p in old["ports"].values() if p["direction"]=="input"),"outputs":161,"binary_all_next_outputs":161,"four_value_comparisons":306,"four_value_scope":"All 161 current native output aliases plus all 145 native FF D terminals; exact common asynchronous FF relation is preserved structurally, no guessed analog or X-event semantics.","added_gate_inputs":80,"added_INV_inputs":4,"pg_mterms":2218,"pg_bindings":None,"timing":None,"external_load_driver_arrival":None},indent=2)+"\n")
print("GENERATED private native source and finite proof inventory",len(new["cells"]))
# Causal controls modify actual implementation terminal identities.
mutations={}
def mut(label,edit):
 g=copy.deepcopy(new);detail=edit(g);f="mutant_"+label
 (P/(f+".sv")).write_text(native+"\n"+graphmod(g,"publication_next")+"\n"+proof.replace("new_next u_a","candidate_native_next u_a").replace("candidate_native_next u_b","publication_next u_b"))
 (P/(f+".ys")).write_text(f"read_verilog -formal {f}.sv\nhierarchy -top native_proof\nproc\nflatten\nopt_clean\nsat -prove ok 1 -show-inputs -show-outputs -dump_json {f}_witness.json\n")
 mutations[label]=detail
# Change one actual consumer in an owned acceptance cohort.
p=next(p for p in pubs if p["identity"]=="pub_1333_0")
s=next(s for s in p["sinks"] if s["owner"]!="OUTPUT")
def wiremut(g,newbit):
 c=g["cells"][s["owner"]];before=c["connections"][s["pin"]];c["connections"][s["pin"]]=[newbit]
 return {"owner":s["owner"],"pin":s["pin"],"before":before,"after":[newbit]}
mut("polarity",lambda g:wiremut(g,outmap[(1333,0,not s["inverted"])]))
mut("wrong_predicate",lambda g:wiremut(g,outmap[(1109,0,False)]))
def missing(g):
 c=g["cells"]["pub_1109_0"];before=c["connections"]["A"];c["connections"]["A"]=["0"];return {"owner":"pub_1109_0","pin":"A","before":before,"after":["0"]}
mut("missing_contributor",missing)
accepted=next(n for n,v in corr.items() if v["name"]=="accepted_v")
def sticky(g):
 c=g["cells"][accepted];before=c["connections"]["D"];c["connections"]["D"]=copy.deepcopy(c["connections"]["QN"]);return {"owner":accepted,"pin":"D","before":before,"after":c["connections"]["D"]}
mut("early_sticky",sticky)
begin=old["ports"]["program_begin_v"]["bits"][0]
def no_begin(g):
 changed=[]
 for n,c in g["cells"].items():
  for pn,bs in c["connections"].items():
   if c["port_directions"][pn]=="input" and bs==[begin]:changed.append([n,pn]);c["connections"][pn]=["0"]
 assert changed;return {"ignored_actual_BEGIN_inputs":changed}
mut("begin_priority",no_begin)
def reset(g):
 c=g["cells"][accepted];c["connections"]["RESETN"]=["1"];return {"owner":accepted,"pin":"RESETN","after":["1"]}
mut("reset",reset)
def setn(g):
 c=g["cells"][accepted];c["connections"]["SETN"]=old["ports"]["rst_n"]["bits"][:];return {"owner":accepted,"pin":"SETN","after":c["connections"]["SETN"]}
mut("SETN",setn)
# Deliberate merged cohort: exact same equations, structural ownership rejection required.
merged=copy.deepcopy(new);before=outmap[(1109,1,False)];after=outmap[(1109,0,False)];changed=[]
for n,c in merged["cells"].items():
 for pn,bs in c["connections"].items():
  if c["port_directions"][pn]=="input" and bs==[before]:c["connections"][pn]=[after];changed.append([n,pn])
mutations["merged_cohorts"]={"from":before,"to":after,"rewired":changed,"expected":"STRUCTURAL_FANOUT_REJECT"}
(P/"merged_graph.json").write_text(json.dumps({"modules":{"publication_native":merged}})+"\n")
(P/"mutations.json").write_text(json.dumps(mutations,indent=2)+"\n")
# Source/native X diagnostic uses exact original source plus exact Liberty equations.
# Native equations here are combinational sampled next-state scope; async events remain separate.
top=proof[:proof.index("assign ok=")].replace("module native_proof(","module x_assess(")
# Testbench drives exact nominal binary baseline plus one X/Z each; all output differences are retained.
vars=[n for n,p in old["ports"].items() if p["direction"]=="input" and n!="ck"]+["state"]
widths={n:len(old["ports"][n]["bits"]) for n in vars if n!="state"};widths["state"]=145
rows=["module xtest;"]
for n in vars:rows.append("reg "+(f"[{widths[n]-1}:0] " if widths[n]>1 else "")+n+";")
rows += ["wire [160:0] source_result,native_result;", "old_next src("+",".join("."+n+"("+n+")" for n in vars)+",.result(source_result));", "candidate_native_next nat("+",".join("."+n+"("+n+")" for n in vars)+",.result(native_result));", "integer i; initial begin"]
for n in vars:rows.append(n+"=0;")
rows.append("rst_n=1; #1; $display(\"BASE source=%h native=%h diff=%b\",source_result,native_result,source_result!==native_result);")
for n in vars:
 if n in ["state","rx_record","program_digest","program_epoch","head_token","head_position"]:continue
 for v in ["x","z"]:
  rows.append(n+"=1\u0027b"+v+"; #1; $display(\"XCASE "+n+"="+v+" source=%h native=%h diff=%b\",source_result,native_result,source_result!==native_result); "+n+"="+("1" if n=="rst_n" else "0")+";")
rows += ["$finish;end endmodule"]
(P/"x_assess.sv").write_text(source+native+"\n"+"\n".join(rows))
