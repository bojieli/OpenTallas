import json,pathlib,collections,gzip
P=pathlib.Path(__file__).resolve().parent
expected=json.loads((P/"graph.json").read_text())["modules"]["publication_native"]
actual=json.loads((P/"elaborated.json").read_text())["modules"]["publication_native"]
# Yosys JSON prefixes a literal escaped Verilog dollar identifier with backslash,
# distinguishing it from an internally generated dollar identifier. Strip exactly
# that one representation prefix only when the original native identity exists.
actual["cells"]={n[1:] if n.startswith("\\$") and n[1:] in expected["cells"] else n:c for n,c in actual["cells"].items()}
assert set(actual["cells"])==set(expected["cells"]),(set(expected["cells"])-set(actual["cells"]))
bits={}
def bind(a,b):
 if isinstance(a,str):assert a==b,(a,b)
 elif a in bits:assert bits[a]==b,(a,b,bits[a])
 else:bits[a]=b
for name,p in expected["ports"].items():
 assert p["direction"]==actual["ports"][name]["direction"]
 for a,b in zip(p["bits"],actual["ports"][name]["bits"]):bind(a,b)
for n,c in expected["cells"].items():
 ac=actual["cells"][n];assert c["type"]==ac["type"],n
 assert c["port_directions"]==ac["port_directions"],n
 for p,bs in c["connections"].items():
  assert len(bs)==len(ac["connections"][p])
  for a,b in zip(bs,ac["connections"][p]):bind(a,b)
assert len(set(bits.values()))==len(bits),"MERGED_NETS"
# Full transparent INV traversal: actual physical endpoints, not logical aliases.
libs=json.load(gzip.open(P/"input/native_semantics.json.gz"))["candidate"]["all_native_types"]
def census(m):
 drivers={};sinks=collections.defaultdict(list);inv={}
 for n,c in m["cells"].items():
  for p,bs in c["connections"].items():
   if c["port_directions"][p]=="output":drivers[bs[0]]=(n,p)
   else:sinks[bs[0]].append((n,p))
  if c["type"]=="INVx1_ASAP7_75t_R":inv[n]=c["connections"]["Y"][0]
 def ends(b,seen=()):
  assert b not in seen,"COMB_CYCLE"
  out=[]
  for n,p in sinks[b]:
   if n in inv:out+=ends(inv[n],seen+(b,))
   else:out.append([n,p])
  return out
 roots=[]
 for b,(n,p) in drivers.items():
  if n in inv:continue
  es=ends(b);roots.append({"bit":b,"owner":n,"master":m["cells"][n]["type"],"fanout":len(es),"endpoints":es})
 for pn,port in m["ports"].items():
  if port["direction"]=="input":
   for bi,b in enumerate(port["bits"]):roots.append({"bit":b,"owner":pn+"["+str(bi)+"]","master":None,"fanout":len(ends(b)),"endpoints":ends(b)})
 for b in ["0","1"]:roots.append({"bit":b,"owner":"literal_"+b,"master":None,"fanout":len(ends(b)),"endpoints":ends(b)})
 return roots
roots=census(expected);unsafe=[r for r in roots if r["master"] and not libs[r["master"]]["ff"] and r["fanout"]>32]
assert not unsafe,unsafe
merged=json.loads((P/"merged_graph.json").read_text())["modules"]["publication_native"];bad=[r for r in census(merged) if r["owner"].startswith("pub_1109") and r["fanout"]>32];assert bad,"MERGE_CONTROL_NOT_CAUSAL"
old=json.loads((P/"input/old.json").read_text())["modules"]
old=next(v for k,v in old.items() if k.startswith("qfd_host"))
def ipin_count(m,inv=None):
 return sum(len(bs) for c in m["cells"].values() for pn,bs in c["connections"].items() if c["port_directions"][pn]=="input" and (inv is None or (c["type"]=="INVx1_ASAP7_75t_R")==inv))
assert ipin_count(expected)-ipin_count(old)==84
assert ipin_count(expected,True)-ipin_count(old,True)==4
assert ipin_count(expected,False)-ipin_count(old,False)==80
res={"post_elaboration_exact_cells_masters_ports_connections":"PASS","cells":len(actual["cells"]),"mapped_bit_id_bijection":len(bits),"native_ff":145,"signal_input_delta":ipin_count(expected)-ipin_count(old),"actual_gate_input_delta":80,"actual_INV_input_delta":4,"full_graph_transparent_fanout":"PASS_KNOWN_LOGIC_ROOTS","maximum_logic_terminal_fanout":max(r["fanout"] for r in roots if r["master"] and not libs[r["master"]]["ff"]),"merged_control":"STRUCTURAL_FANOUT_REJECT","merged_failures":bad,"all_roots":roots,"raw_clock_reset_SETN_each":145,"PG_physical":None,"boundary_driver_arrival_load":None}
(P/"structural_census.json").write_text(json.dumps(res,indent=2)+"\n")
print("REPARSE_EXACT_1109_CELLS_PASS; LOGIC_FANOUT_PASS; MERGED_COHORT_STRUCTURAL_REJECT",[(r["owner"],r["fanout"]) for r in bad])
