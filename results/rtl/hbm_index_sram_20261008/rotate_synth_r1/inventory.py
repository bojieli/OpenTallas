from pathlib import Path
import re,json,sys
s=Path(sys.argv[1]).read_text();total={};mem=[];mux={}
for typ,body in re.findall(r'^  cell (\S+) [^\n]+\n(.*?)^  end$',s,re.M|re.S):
 params={}
 for line in body.splitlines():
  fields=line.split()
  if len(fields)==3 and fields[0]=='parameter' and fields[2].isdigit():params[fields[1].lstrip('\\')]=int(fields[2])
 if typ in ['$adff','$adffe','$dff','$dffe']:total[typ]=total.get(typ,0)+params.get('WIDTH',0)
 if typ=='$mem_v2':mem.append(params)
 if typ in ['$mux','$pmux','$shift','$shiftx']:mux[typ]=mux.get(typ,0)+params.get('WIDTH',params.get('Y_WIDTH',0))
print(json.dumps({'register_bits':total,'total_register_bits':sum(total.values()),'sidecar_memories':len(mem),'sidecar_bits':sum(m['WIDTH']*m['SIZE'] for m in mem),'selection_output_bits':mux},indent=2))
