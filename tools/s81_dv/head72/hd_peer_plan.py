#!/usr/bin/env python3
"""H2 same-region CTL glue + exact CLOSED MTP peer, inside the H1 reserve."""
import copy,json,sys
from pathlib import Path
def build(src,out):
 p=json.loads(Path(src).read_text());B=p['blocks'];ci=next(i for i,b in enumerate(B) if b['name']=='ctl');c=B[ci];old=copy.deepcopy(c)
 c.update(master='ot_s81hd_ctl_glue',w=1036.8,h=1036.8,y=round(old['y']+(old['h']-1036.8)/2,4))
 # Every old CTL face endpoint keeps its fractional face position on the actual glue rectangle.
 for link in p['links']:
  for k,e in enumerate(link['e']):
   if e[0]!=ci:continue
   face=link['endpoint_faces'][k]
   if face in ('N','S'):
    t=(e[2]-old['x'])/old['w'];e[2]=round(c['x']+t*c['w'],4);e[3]=round(c['y']+(c['h'] if face=='N' else 0),4)
   else:
    t=(e[3]-old['y'])/old['h'];e[2]=round(c['x']+(c['w'] if face=='E' else 0),4);e[3]=round(c['y']+t*c['h'],4)
 seq=dict(name='mtp_seq',master='dsfd_mtp_seq',kind='ctl_peer',group='clctl',x=round(c['x']+c['w']+108,4),y=round(c['y']+c['h']/2-75.6,4),w=151.2,h=151.2,reg=False,orient='R0')
 assert seq['x']+seq['w']<=old['x']+old['w'] and seq['y']>=old['y'] and seq['y']+seq['h']<=old['y']+old['h']
 si=len(B);B.append(seq);cy=round(c['y']+c['h']/2,4);sy=round(seq['y']+seq['h']/2,4)
 for name,width,a,ap,b,bp,faces in [('seq_t',605,ci,'seq_t',si,'ctl_i',['E','W']),('seq_r',686,si,'ctl_o',ci,'seq_r',['W','E'])]:
  e=[[a,ap,round(c['x']+c['w'],4) if a==ci else seq['x'],cy if a==ci else sy,'box'],[b,bp,round(c['x']+c['w'],4) if b==ci else seq['x'],cy if b==ci else sy,'box']]
  assert abs(e[0][2]-e[1][2])+abs(e[0][3]-e[1][3])<=405
  p['links'].append(dict(i=name,c='unit',b=width,d=1,e=e,n='Direct registered CTL/seq peer, same clctl clock region, zero added cycles',endpoint_faces=faces,payload_b=width))
 p['facts']['ctl_peer']={'reserve':old,'glue':c,'sequencer':seq,'source':'b4f571642 unchanged CTL factored by split_ctl_peer.py','same_region':'clctl','added_cycles':0,'peer_seed_reach_um':108,'max_peer_face_manhattan_um':334.8,'physical_view':'physical/ref_tile/s81hd_mtp_peer/views/dsfd_mtp_seq','original_closed_job':'mtp-mtp_seq-c-c67a71fe5-tc'}
 p['facts']['physical72']['design']='S81 HEAD H2 (direct CTL/seq peers)';p['facts']['instance_orientations']['mtp_seq']='R0'
 Path(out).parent.mkdir(parents=True,exist_ok=True);Path(out).write_text(json.dumps(p,indent=1)+'\n')
if __name__=='__main__':build(*sys.argv[1:3])
