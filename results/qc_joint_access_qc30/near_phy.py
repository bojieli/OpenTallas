import json,sys
g=json.load(open(sys.argv[1]));d=g['dbu']
pins={'io_serdes':(777.632,15171.768),'io_serdes_1':(777.632,3481.952),'io_serdes_2':(777.632,1157.792),'ucie_kv':(388.768,9633.568)}
W=3.0
out={k:dict(obs=[],sig=[],sup=[]) for k in pins}
for key,rows in (('obs',g['obstructions']),('sig',g['signal_shapes']),('sup',g['existing_supplies'])):
  for r in rows:
    lay=r[-5]
    if lay not in ('M6','M7','M8'):continue
    x0,y0,x1,y1=[v/d for v in r[-4:]]
    for k,(x,y) in pins.items():
      if x0<=x+W and x1>=x-W and y0<=y+W and y1>=y-W:
        out[k][key].append([*r[:-4],round(x0,4),round(y0,4),round(x1,4),round(y1,4)])
for k in out:
  print(k,{a:len(b) for a,b in out[k].items()})
  for a in out[k]:
    for r in out[k][a][:40]:print(' ',a,r)
json.dump(out,open(sys.argv[2],'w'),indent=0)
