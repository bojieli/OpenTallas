#!/usr/bin/env python3
"""Literal graded mesh graph from rectangles/vias; no inferred resistance model."""
import argparse,bisect,collections,json
from pathlib import Path

def build(g):
 rails=collections.defaultdict(list);anchors=collections.defaultdict(set)
 for seg in g["segments"]:
  layer=seg["layer"];x,y,xx,yy=seg["centre_um"];fixed=round(y if layer=="M8" else x,6)
  lo,hi=sorted((x,xx) if layer=="M8" else (y,yy));rails[(layer,fixed)].append((round(lo,6),round(hi,6),seg["width_um"]))
 for a in g.get("attachments",[]):
  x,y=a["xy_um"];layer=a["layer"];key=(layer,round(y if layer=="M8" else x,6));q=round(x if layer=="M8" else y,6)
  if not any(lo-1e-6<=q<=hi+1e-6 for lo,hi,w in rails.get(key,[])):raise ValueError("attachment is off the literal rail: "+str(a))
  anchors[key].add(q)
 nodes=[];lookup={};edges=[]
 def node(layer,x,y):
  key=(layer,round(x,6),round(y,6))
  if key not in lookup:lookup[key]=len(nodes);nodes.append(dict(layer=layer,xy_um=list(key[1:])))
  return lookup[key]
 for (layer,fixed),segs in rails.items():
  cuts=sorted(anchors[(layer,fixed)])
  for lo,hi,w in segs:
   points=[lo]+cuts[bisect.bisect_right(cuts,lo):bisect.bisect_left(cuts,hi)]+[hi]
   for a,b in zip(points,points[1:]):
    u=node(layer,a,fixed) if layer=="M8" else node(layer,fixed,a);v=node(layer,b,fixed) if layer=="M8" else node(layer,fixed,b)
    edges.append(dict(a=u,b=v,kind="wire",layer=layer,width_um=w,length_um=round(b-a,6)))
 for via in g["vias"]:
  x,y=via["x_um"],via["y_um"];a=node("M8",x,y);b=node("M9",x,y)
  edges.append(dict(a=a,b=b,kind="via",rows=via["rows"],cols=via["cols"],cut_um=via["cut_um"],pitch_um=via["pitch_um"],pad_um=via["pad_um"]))
 parent=list(range(len(nodes)))
 def find(a):
  while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
  return a
 for e in edges:
  a,b=find(e["a"]),find(e["b"])
  if a!=b:parent[a]=b
 components=len({find(i) for i in range(len(nodes))});cycles=len(edges)-len(nodes)+components
 attach=[]
 for a in g.get("attachments",[]):
  x,y=a["xy_um"];attach.append(dict(a,node=lookup[(a["layer"],round(x,6),round(y,6))],pin_metal_encoded=False))
 expected=(len(g["xs"])-1)*(len(g["ys"])-1)
 if components!=1 or cycles!=expected:raise ValueError(("literal mesh graph topology",components,cycles,expected))
 return dict(schema="opentallas.literal_graded_mesh_graph.v1",nodes=nodes,edges=edges,attachments=attach,summary=dict(nodes=len(nodes),edges=len(edges),components=components,cycles=cycles,expected_cycles=expected,via_edges=len(g["vias"]),native_extraction_qualified=False,driver_pin_metal_encoded=False,resistance_model=None))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("geometry");p.add_argument("out");a=p.parse_args();r=build(json.loads(Path(a.geometry).read_text()));Path(a.out).write_text(json.dumps(r,separators=(",",":"))+"\n");print(json.dumps(r["summary"],indent=2))
