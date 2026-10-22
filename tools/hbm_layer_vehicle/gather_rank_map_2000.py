"""Trace actual TP rank shards into the four native GSC aggregation runs.

This is programme/placement provenance only. It grants no commit, retention,
transport, physical-column or calendar epoch dates.
"""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/hbm_static'),str(ROOT/'tools/hgi_adapters')]
from hbm_layer_vehicle.layer_images import ds_dispatches_image
from su_program_inventory import decode
import su_bench as SB
from w19_hbm_tp96_isa import even


def main():
    inputs,layouts_path,out=map(Path,sys.argv[1:4])
    layouts=json.loads(layouts_path.read_text());layers={}
    for layer in ('L00','L02','L14'):
        path=inputs/layer/'programme.json';image=json.loads(path.read_text())
        tp=image['tp'];shards=even(384,tp)
        if tp!=96 or sorted(r['rank'] for r in image['ranks'])!=list(range(tp)):
            raise ValueError('actual source must contain all 96 TP rank programmes')
        layout=layouts['L'+str(int(layer[1:]))];rows=[]
        for rank in range(tp):
            recs=ds_dispatches_image(path,str(rank))
            act=[(r,d) for r,d,_ in recs if r.tag=='router_act']
            gsc=[r for r,_,_ in recs if r.tag=='router_gather.gsc']
            if len(act)!=1 or len(gsc)!=1:raise ValueError('actual router activation/GSC programme not unique')
            r,d=act[0];raw=SB.pack_rec(d);_,unit,sut,desc=decode(raw)
            lo,hi=shards[rank];base=gsc[0].desc['A'].base
            a,o=desc['A'],desc['O']
            if unit!=2 or a.base!=base+lo or o.base!=a.base or a.n!=hi-lo or o.n!=hi-lo:
                raise ValueError('actual activation descriptor differs from W.even rank ownership')
            run,offset=divmod(lo,96)
            if offset+(hi-lo)>96:raise ValueError('rank shard crosses aggregation run')
            rows.append(dict(rank=rank,logical_score_range=[lo,hi],logical_VM_first_word=a.base,
                word_count=hi-lo,activation_tag=r.tag,raw_dispatch=f'{raw:0550x}',
                logical_aggregation_run=run,word_offset_in_run=offset,
                existing_component_run_word=layout['segment_bases'][run]+offset,
                physical_column=None,producer_ready_edge=None,producer_release_edge=None,
                aggregation_commit_edge=None,aggregation_readable_edge=None))
        for run in range(4):
            owned=[r for r in rows if r['logical_aggregation_run']==run]
            if len(owned)!=24 or sum(r['word_count']for r in owned)!=96:
                raise ValueError('aggregation run must contain exactly24 real4word rank shards')
        layers[layer]=dict(tp=tp,programme_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            actual_rank_shards=rows,existing_component_layout=layout)
    result=dict(schema='opentallas.hbm.gather_rank_map.v1',scope='Actual TP96 programme provenance; no physical route or dates qualified',
        source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in (ROOT/'tools/hgi_sim/ds_native.py',ROOT/'tools/w19_hbm_tp96_isa.py',Path(__file__).resolve())},
        layers=layers,remaining=['Real four-word native activation commit/retention per rank',
            'Actual logical TP96 to selected-source TP192 rank/Col8 binding and aggregation programme; no identity mapping admitted',
            'Native all-rank aggregation arrival and retention for each96word run',
            'Selected CP launch and complete routed calendar epoch'])
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n')
    print('MAPPED 288 actual rank activation commands; each layer has four runs of24 ranks x4 words; all dates null')
if __name__=='__main__':main()
