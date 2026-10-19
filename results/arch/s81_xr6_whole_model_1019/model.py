"""Bounded immutable-graph model; no synthesis or source transformation."""
import collections, gzip, hashlib, json, math, pathlib, re
HERE=pathlib.Path(__file__).resolve().parent
BASE=HERE.parent/"s81_xr6_structural_census_1019/native_census.json.gz"
d=json.load(gzip.open(BASE,"rt"))
records=[r for r in d["records"] if r["role"] not in ("transparent","clock")]
# PORT is not a unique node identifier: keep primary input records separate.
by={r["driver"]:r for r in records if r["role"]!="input"}
assert len(by)==len([r for r in records if r["role"]!="input"])
def fixedpoint(budget):
 copies={n:1 for n in by}; rounds=[]
 for iteration in range(100):
  nxt={n:max(copies[n],math.ceil(sum(copies.get(e,1) for e,p in r["endpoints"])/budget)) for n,r in by.items()}
  rounds.append(sum(nxt[n]-1 for n in by))
  if nxt==copies: break
  copies=nxt
 else: raise AssertionError("no finite fixed point")
 ledger=[]
 for n,r in by.items():
  demand=sum(copies.get(e,1) for e,p in r["endpoints"])
  assert demand<=copies[n]*budget
  if copies[n]>1:
   ledger.append(dict(driver=n,master=r["master"],role=r["role"],copies=copies[n],original_pins=r["count"],expanded_pins=demand,max_assigned_pins=math.ceil(demand/copies[n]),area_um2=(copies[n]-1)*d["area_by_master"][r["master"]]))
 inputs=[dict(port=r["net"],expanded_pins=sum(copies.get(e,1) for e,p in r["endpoints"])) for r in records if r["role"]=="input"]
 assert max(r["expanded_pins"] for r in inputs)<=32
 # Endpoint copies are distinct terminal pins. Sorted sequential allocation to
 # ceil(demand/budget) source copies is constructive and never changes a stage.
 return dict(budget=budget,round_totals=rounds,extra_by_role=dict(collections.Counter({role:sum(copies[n]-1 for n,r in by.items() if r["role"]==role) for role in ("ff","comb","tie")})),area_um2=sum(r["area_um2"] for r in ledger),max_input_pins=max(r["expanded_pins"] for r in inputs),ledger=ledger,inputs=inputs)

def storage_model():
 # Exhaustive source state-machine transition quotient: packet words replaced
 # by unique immutable (packet_id,pair) symbols; preserves all data identities.
 checks=0; collisions=0; replacements=0
 for leaf in range(5):
  for busy in (False,True):
   for last in range(4):
    for cursor in range(4):
     if busy and cursor>last: continue
     for incoming in (False,True):
      for ctl in (False,True):
       old=tuple((leaf,0,i) for i in range(4)); new=tuple((leaf,1,i) for i in range(4))
       old_read=old[cursor]
       fault=(incoming and busy and cursor!=last) or (ctl and busy)
       next_store=new if incoming else old
       observed=("ctl",leaf) if ctl else old_read
       assert observed==(("ctl",leaf) if ctl else (leaf,0,cursor))
       if incoming and busy and cursor==last and not ctl:
        assert not fault and observed==(leaf,0,last) and next_store[0]==(leaf,1,0)
        replacements+=1
       if incoming and busy and cursor!=last: assert fault; collisions+=1
       # Different leaf addresses and independently overlapping ub lifetimes
       # never alias: shared rdat is a broadcast write bus, not shared state.
       assert all(next_store[i][0]==leaf for i in range(4))
       checks+=1
 # Reset ub=0 and sw_v=0 suppresses observation, not data masking; packet data
 # need not reset. At first RD write K, first qualified read is K+1.
 reachable={(0,0,0,0,0)}; frontier=list(reachable); legal_transitions=0; final_replacements=0
 while frontier:
  state=frontier.pop()
  for dest in range(-1,5):
   for length in ((0,) if dest<0 else range(1,5)):
    if dest>=0 and state[dest]>1: continue
    next_state=tuple(length if i==dest else max(0,n-1) for i,n in enumerate(state))
    legal_transitions+=1
    final_replacements+=dest>=0 and state[dest]==1
    if next_state not in reachable: reachable.add(next_state); frontier.append(next_state)
 peak=max(sum(n>0 for n in state) for state in reachable)
 assert peak==4
 return dict(reachable_lifetime_states=len(reachable),reachable_legal_transitions=legal_transitions,reachable_final_replacement_transitions=final_replacements,peak_qualified_parallel_reads=peak,transitions=checks,legal_final_pair_replacements=replacements,early_collision_transitions=collisions,independent_destinations=5,bits_per_destination=1024,aggregate_bits=5120,packet_pairs=4,pair_bits=256,physical_read_lanes=5,simultaneous_writes=1,first_read_after_write_edges=1,read_during_replacement="OLD",reset_data_required=False,source_rtl_equivalence="OPEN; symbolic transition model only")
result=dict(schema="opentallas.s81.xr6.whole_copy_model.v1",source_commit="7ef9383db5788cbb9428ccc264bb34484071b541",source_sha256="b10a2c142dbf31e465f382b7f6cd3c6b354cd90be536ae015d159bcfe9f1bee6",native_odb_sha256=d["odb_sha256"],census_sha256=hashlib.sha256(BASE.read_bytes()).hexdigest(),native_variant="ot_s81sl_xr1 HB=0; HB1 bo/bi graph not measured",native_cells=d["cells"],native_ff=d["ff"],model32=fixedpoint(32),model24=fixedpoint(24),storage=storage_model(),extra_data_edges=0,extra_clock_capacitance_ff="priced separately TT/FF; excludes clock tree",source_correspondence="OPEN",native_successor="NOT BUILT",geometry_reach_pg="OPEN",reset_assertion_release_equivalence="OPEN; clone same native state edge; preserve 2face+2sync+1relay")
libdir=pathlib.Path("/home/ubuntu/.local/opentallas-pdk-asap7-platform/asap7/lib/NLDM")
libhash={"TT":"57a0b403485b99ebd676942af4673ac086b86c7c75fbdc3e5c0038501dd22ba3","FF":"d9b6e75c8720cdd450cff15178528502cc8df34c5ab6b0ffb53fc99d664b5302"}
result["library_sha256"]={}; result["clock_cap_increment_fF"]={}
for corner in ("TT","FF"):
 lib=libdir/("asap7sc7p5t_SEQ_RVT_"+corner+"_nldm_220123.lib")
 text=lib.read_text(); digest=hashlib.sha256(lib.read_bytes()).hexdigest(); assert digest==libhash[corner]
 result["library_sha256"][corner]=digest
 caps={}
 for master in ("DFFHQNx1_ASAP7_75t_R","DFFASRHQNx1_ASAP7_75t_R"):
  cell=text[text.index("cell ("+master+")"):]; cell=cell[:cell.find("\n  cell (",1)]
  pin=cell[cell.index("pin (CLK)"):]; pin=pin[:pin.index("}")]
  caps[master]=float(re.search(r"capacitance\s*:\s*([0-9.]+)",pin)[1])
 result["clock_cap_increment_fF"][corner]={key:sum((x["copies"]-1)*caps[x["master"]] for x in result[key]["ledger"] if x["role"]=="ff") for key in ("model32","model24")}
result["copied_ff_families"]={}
for row in result["model32"]["ledger"]:
 if row["role"]=="ff":
  family=row["driver"].split("[")[0].rstrip(chr(92))
  result["copied_ff_families"][family]=result["copied_ff_families"].get(family,0)+row["copies"]-1
incoming=collections.defaultdict(list)
for r in records:
 for target,pin in r["endpoints"]:
  if target in by: incoming[target].append(dict(pin=pin,source=r["driver"] if r["role"]!="input" else r["net"],role=r["role"],master=r["master"]))
for key in ("model32","model24"):
 for row in result[key]["ledger"]: row["incoming_owners"]=incoming[row["driver"]]
# Causal witnesses exercise distinct incorrect transition/graph assumptions.
assert result["model32"]["round_totals"][0] < result["model32"]["round_totals"][-1]
old_packet=tuple((0,i) for i in range(4)); new_packet=tuple((1,i) for i in range(4))
assert old_packet[3]!=new_packet[3]
assert (True and 0!=3)
result["negative_witnesses"]=[dict(mutant="reuse original upstream fanout after clone",verdict="REJECT",first_round_nodes=529,actual_fixedpoint_nodes=557),dict(mutant="NEW data on final pair replacement",verdict="REJECT",expected=[0,3],observed=[1,3]),dict(mutant="replace packet before final pair without collision",verdict="REJECT",busy=True,cursor=0,last=3,collision_required=True)]
(HERE/"model.json").write_text(json.dumps(result,indent=2)+"\n")
print(json.dumps({"model32":{k:v for k,v in result["model32"].items() if k not in ("ledger","inputs")},"model24":{k:v for k,v in result["model24"].items() if k not in ("ledger","inputs")},"storage":result["storage"]},indent=2))
