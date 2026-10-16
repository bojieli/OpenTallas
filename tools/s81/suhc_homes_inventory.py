#!/usr/bin/env python3
"""Reproducible source/view inventory for the owner-requested SU/HC floorplan study.
No historical child is asserted instantiated by the current flat SU die wrapper.
"""
import argparse, collections, gzip, hashlib, json, re, subprocess
from pathlib import Path
R=Path(__file__).resolve().parents[2]
def git(*args):return subprocess.check_output(['git','-C',str(R),*args])
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 a=argparse.ArgumentParser();a.add_argument('--model',required=True);a.add_argument('--out',required=True);args=a.parse_args()
 modelraw=Path(args.model).read_bytes();m=json.loads(gzip.decompress(modelraw));out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
 commit=git('rev-parse','HEAD').decode().strip();paths=git('ls-tree','-r','--name-only','HEAD','physical/ref_tile').decode().splitlines()
 # These are the native hierarchical production arithmetic counts, excluding RX and physical relays/glue.
 groups={'io':{'pin':4,'ctl':1},'qn':{'qnt':2,'qne':32,'qnh':2,'qnr':1,'qnq':8},'kv':{'kvt':4,'kve':56,'kvp':8,'qnh':4,'kvr':1,'kvq':16},'qb':{'qbtl':1,'swth':1,'qbe':8},'sw':{'swtl':1,'swth':1,'qbe':8,'swe':128},'sm':{'smt':8,'sml':256,'smc':16,'smr':16,'smd':128}}
 catalog=[]
 for p in paths:
  if not p.endswith('/insertion.json'):continue
  cell=p.split('/')[-2]
  if not (cell.startswith('dsfd_su_t_') or cell.startswith('ot_s81_hc_')):continue
  raw=git('show','HEAD:'+p);ins=json.loads(raw);lp=p.rsplit('/',1)[0]+'/'+cell+'.lef'
  if lp not in paths:continue
  lefraw=git('show','HEAD:'+lp);lef=lefraw.decode();sz=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef)
  w,h=map(float,sz.groups());pins=[];faces=collections.Counter();clocks=[]
  for pm in re.finditer(r'\n  PIN (\S+)\n(.*?)(?=\n  END )',lef,re.S):
   name,body=pm.groups();rect=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',body)
   if not rect:continue
   x0,y0,x1,y1=map(float,rect.groups());x,y=(x0+x1)/2,(y0+y1)/2;face=min({'W':x,'E':w-x,'S':y,'N':h-y},key=lambda k:{'W':x,'E':w-x,'S':y,'N':h-y}[k]);faces[face]+=1
   rec={'pin':name,'face':face,'xy_um':[x,y],'layer':re.search(r'LAYER (\S+)',body).group(1),'direction':re.search(r'DIRECTION (\S+)',body).group(1)};pins.append(rec)
   if re.search(r'(^|_)(ck|clk)(_|\[|$)',name):clocks.append(rec)
  corner={c:ins.get(c,{}).get('boundary') for c in ('tt','ff','ss')}
  record=dict(cell=cell,view=lp.rsplit('/',1)[0],outline_um=[w,h],area_um2=w*h,lef_sha256=sha(lefraw),insertion_sha256=sha(raw),boundary_clocks=clocks,face_pin_count=dict(faces),insertion=corner,scope='historical real view; not automatically selected or qualified for new shape')
  catalog.append(record);(out/(p.split('/')[2]+'__'+cell+'_pins.json')).write_text(json.dumps(pins,separators=(',',':'))+'\n')
 targets={'sp_su_s','sp_hc_s','sp_hc_t'};incident=[]
 for bus in m['buses']:
  if any(e[0] in targets for e in bus[3]):incident.append(dict(name=bus[0],kind=bus[1],bits=bus[2],endpoints=bus[3]))
 conpath='results/arch/hier_contract_1011/s81_v23_hc_budget.json';conraw=(R/conpath).read_bytes();con=json.loads(conraw)
 slots=[s for s in con['slots'] if any(s['name']==t or s['name'].startswith(t+'/') for t in targets)]
 src={p:sha((R/p).read_bytes()) for p in ['rtl/dsrom_sys/s81_suhc/dsfd_sp_su_c.sv','rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_su_h.sv','rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv']}
 report=dict(schema='opentallas.s81.suhc-homes-inventory.v1',source_commit=commit,model=dict(path=args.model,sha256=sha(modelraw),source_commit=m.get('source_commit')),source_pins=src,contract=dict(path=conpath,sha256=sha(conraw)),current_die_macros=[i for i in m['insts'] if i[0] in targets],current_die_incident_buses=incident,historical_contract_slots=slots,hierarchical_arithmetic_counts=groups,hierarchical_arithmetic_count=sum(sum(g.values()) for g in groups.values()),historical_real_views=catalog,cth_row_inventory=con['sub_layouts']['ot_s81_hc_cth'],open=['Current SU wrapper instantiates flat dsfd_sp_su, not dsfd_sp_su_h. Hierarchical counts are a constructive design input, not proof of die elaboration.','RX current hard children, source-current flattened instance graph, relay/glue placement and per-root ownership remain required.','Contract SU slots contain obsolete qn0/qn1 and aggregate reservations; cannot use as complete physical placement.','HC cth slot heights 758.16 disagree with sublayout790.56 and literal newer NT835.92; do not silently inherit or scale.','Every moved facing pin/leaf requires actual incident-cut routing <=0.60, realviews, phi-R per root, full native trial, TT setup/FF hold/DRC0 and exact calendar before adoption.'])
 (out/'inventory.json').write_text(json.dumps(report,indent=1)+'\n');print(json.dumps({'views':len(catalog),'incident_buses':len(incident),'arithmetic_children_excluding_rx_relays_glue':report['hierarchical_arithmetic_count'],'out':str(out)}))
if __name__=='__main__':main()
