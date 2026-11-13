"""Frozen-payload routing tests on the production lane-path algorithm."""
from collections import defaultdict
import copy
import heapq
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bind import Binder
from split_bind_routes import SCHEMA, SplitRouteError, cell_fingerprint, payload_sha256, prefill


def cell(path):
    return SimpleNamespace(path=path,module="source",params={"D":2},ports={"q":[10,11]},
                           dirs={"q":"output"},kind="leaf",ytype=None,yparams={})


def lane(lid,src,dst,n):
    return dict(id=lid,src=src,dst=dst,cap=n,left=n,items=[],carried={},cycles=2)


class Toy:
    _route=Binder._route
    def __init__(self,swapped=False,dependency=False):
        self.F=SimpleNamespace(cells=[cell("b"),cell("a")] if swapped else [cell("a"),cell("b")])
        self.by_path={c.path:i for i,c in enumerate(self.F.cells)}
        self.cpart={self.by_path["a"]:"A0",self.by_path["b"]:"A1"}
        self.parts={p:{} for p in ["A0","A1","B0","B1","C"]}
        self.plan=dict(partitions=[dict(name=p) for p in self.parts])
        self.lanes=[lane("L0","A1","B0",2),lane("L1","A1","B1",2),
                    lane("cut_A","A0","A1",2),lane("cut_B01","B0","B1",2),
                    lane("cut_B10","B1","B0",2)]
        if dependency:self.lanes.append(lane("L2","B1","C",4))
        self.byid={x["id"]:x for x in self.lanes}
        self.out=defaultdict(list)
        for L in sorted(self.lanes,key=lambda x:x["id"]):self.out[L["src"]].append(L)
        self.recv={};self.holders=defaultdict(set);self.put_count=0
    def key(self,path,bit):return self.by_path[path],"q",bit
    def put(self,L,key,_unused):
        if key in L["carried"]:return L["carried"][key]
        assert L["left"]>0
        if L["src"]==self.cpart[key[0]]:item=("leaf",)+key
        else:
            prev,idx,_cyc=self.recv[(L["src"],)+key];item=("fwd",prev["id"],idx)
        index=len(L["items"]);L["items"].append(item);L["carried"][key]=index;L["left"]-=1
        self.recv.setdefault((L["dst"],)+key,(L,index,2));self.holders[key].add(L["dst"])
        self.put_count+=1
        return index
    def deliver(self,key,dst):
        srcs={self.cpart[key[0]]}|set(self.holders[key])
        if dst in srcs:return True
        path=self._route(srcs,dst,[key],self.out,heapq)
        if path is None:return False
        for L in path:self.put(L,key,None)
        return True
    def reference(self,dependency=False):
        rows=[dict(id="L0",src="A",dst="B",drivers=[["a","q",i]for i in range(2)]),
              dict(id="L1",src="A",dst="B",drivers=[["b","q",i]for i in range(2)])]
        if dependency:rows.insert(0,dict(id="L2",src="B",dst="C",drivers=[[p,"q",i]for p in ["a","b"]for i in range(2)]))
        return dict(schema=SCHEMA,payload_sha256=payload_sha256(rows),part_groups={"A":["A0","A1"],"B":["B0","B1"],"C":["C"]},
                    cells={c.path:dict(fingerprint=cell_fingerprint(c),part="A")for c in self.F.cells},lanes=rows)
    def prefill(self,ref):return prefill(self,ref,self.lanes,self.put,self.recv,self.holders,self.out,heapq)


def test_reference_preserves_two_streams_where_greedy_multicast_exhausts_capacity():
    greedy=Toy()
    # The greedy direct phase fills both old windows with b before a reaches A1.
    for lid in ["L0","L1"]:
        for bit in range(2):greedy.put(greedy.byid[lid],greedy.key("b",bit),None)
    assert all(greedy.deliver(greedy.key("a",bit),"A1")for bit in range(2))
    assert not greedy.deliver(greedy.key("a",0),"B0")
    fixed=Toy();receipt=fixed.prefill(fixed.reference())
    assert receipt["original_bits"]==4 and receipt["cut_puts"]==2
    assert list(fixed.byid["L0"]["carried"])==[fixed.key("a",i)for i in range(2)]
    assert list(fixed.byid["L1"]["carried"])==[fixed.key("b",i)for i in range(2)]
    # Remaining multicast traverses the new cut windows, without duplicating old payloads.
    for name in ["a","b"]:
        for bit in range(2):
            for dst in ["B0","B1"]:assert fixed.deliver(fixed.key(name,bit),dst)
    assert fixed.byid["L0"]["left"]==fixed.byid["L1"]["left"]==0


def test_symbolic_paths_survive_changed_raw_cell_indices_and_old_lane_dependencies():
    b=Toy(swapped=True,dependency=True)
    result=b.prefill(b.reference(dependency=True))
    assert result["passes"]==2
    assert list(b.byid["L2"]["carried"])==[b.key(p,i)for p in ["a","b"]for i in range(2)]
    assert all(("C",)+b.key(p,i) in b.recv for p in ["a","b"]for i in range(2))


@pytest.mark.parametrize("mutation,match",[
    ("bit","out of range"),("module","fingerprint changed"),
    ("parameter","fingerprint changed"),("part","outside declared"),
    ("duplicate","duplicate payload"),("capacity","exceeds cap")])
def test_invalid_source_and_contract_mutants_fail_before_any_put(mutation,match):
    b=Toy();ref=b.reference()
    if mutation=="bit":ref["lanes"][0]["drivers"][0][2]=2
    if mutation=="module":b.F.cells[b.by_path["a"]].module="mutated_source"
    if mutation=="parameter":b.F.cells[b.by_path["a"]].params["D"]=3
    if mutation=="part":b.cpart[b.by_path["a"]]="B0"
    if mutation=="duplicate":ref["lanes"][0]["drivers"][1]=ref["lanes"][0]["drivers"][0][:]
    if mutation=="capacity":b.byid["L0"]["cap"]=1
    if mutation in ("bit","duplicate"):ref["payload_sha256"]=payload_sha256(ref["lanes"])
    with pytest.raises(SplitRouteError,match=match):b.prefill(ref)
    assert b.put_count==0


def test_prefill_cannot_use_an_unfrozen_cross_group_shortcut():
    b=Toy();ref=b.reference()
    # Misdeclared A input never appears: the extra new crossing cannot replace a frozen old transport.
    b.cpart[b.by_path["a"]]="B0";ref["cells"]["a"]["part"]="B"
    new=lane("new_cross_group","B0","A1",2);b.lanes.append(new);b.out["B0"].append(new)
    with pytest.raises(SplitRouteError,match="awaiting"):b.prefill(ref)
    assert new["left"]==2


def test_failed_cut_dry_run_does_not_consume_partial_capacity():
    b=Toy();b.byid["cut_A"]["left"]=1
    with pytest.raises(SplitRouteError,match="no cut-only path"):b.prefill(b.reference())
    assert b.byid["cut_A"]["left"]==1 and not b.byid["cut_A"]["carried"]


def test_absent_optin_is_an_exact_noop():
    b=Toy();before=copy.deepcopy(b.lanes)
    assert b.prefill(None)["enabled"] is False
    assert b.lanes==before and not b.recv and b.put_count==0


def test_fingerprint_excludes_raw_net_ids_but_keeps_pin_shape():
    c=cell("a");before=cell_fingerprint(c)
    c.ports["q"]=[200,300]
    assert cell_fingerprint(c)==before
    c.ports["q"].append(400)
    assert cell_fingerprint(c)!=before


def test_valid_wrong_source_bit_mutant_is_rejected_by_frozen_payload_receipt():
    b=Toy();ref=b.reference()
    ref["lanes"][0]["drivers"][0]=["b","q",0]  # legal range, unique, wrong source
    with pytest.raises(SplitRouteError,match="payload_sha256"):b.prefill(ref)
    assert b.put_count==0


def production_toy(monkeypatch, enabled):
    import native_istations, reset_carriers, split_source_guard
    for name in ("annotate", "annotate_kit", "annotate_kit_dest"):
        monkeypatch.setattr(native_istations,name,lambda b:None)
    monkeypatch.setattr(reset_carriers,"register",lambda b:None)
    monkeypatch.setattr(split_source_guard,"validate_guard",lambda ref,b:{"test_guard":True})
    t=Toy(); b=Binder.__new__(Binder)
    b.F=t.F; b.cpart=t.cpart; b.parts={p:{"type":"T"}for p in t.parts}
    b.plan={"lanes":[1]}; b.pc=None; b.ab={}; b.base="."
    if enabled:b.ab["split_lane_reference"]=t.reference()
    b.plan_lanes=lambda:dict(((x["src"],x["dst"]),[x])for x in t.lanes)
    for x in t.lanes:x.update(oname="o_generic",iname="i_generic",sleaf="",dleaf="",ft=[])
    b.cross=defaultdict(dict); b.cross_sinks={}; b.cross_stages={}
    for ci,c in enumerate(t.F.cells):
        for dst in ["B0","B1"]:
            key=(b.cpart[ci],dst,ci,"q")
            b.cross[key[:2]][key[2:]]={0,1}; b.cross_sinks[key]={("sink","d")}; b.cross_stages[key]={0}
    b.rel_of=lambda ci:t.F.cells[ci].path
    b.die_port_name={}; b.cross_sink_alias={}; b.errors=[]
    b.members={p:[0]for p in b.parts}; b.root={}
    b.build_buses()
    return b


def test_production_build_buses_optin_preserves_payload_then_multicasts(monkeypatch):
    default=production_toy(monkeypatch,False)
    assert sum(default.unplanned.values())==4
    fixed=production_toy(monkeypatch,True)
    assert not fixed.unplanned and not fixed.errors
    assert len(fixed.bitpos)==8
    assert fixed.split_route_prefill["original_bits"]==4
    original={x["id"]:x for x in fixed.links if x["id"]in {"L0","L1"}}
    assert [(fixed.F.cells[ci].path,pn,bit)for ci,pn,bit in original["L0"]["carried"]]==[("a","q",i)for i in range(2)]
    assert [(fixed.F.cells[ci].path,pn,bit)for ci,pn,bit in original["L1"]["carried"]]==[("b","q",i)for i in range(2)]
