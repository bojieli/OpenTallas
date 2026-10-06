import collections,hashlib,json,pathlib,re
root=pathlib.Path(__file__).resolve().parent
out=root/'endpoint_diagnosis';out.mkdir(exist_ok=True)
num=r'(-?\d+\.\d+)'
def paths(p):
 lines=[]
 for line in p.open():
  if line.startswith('Startpoint:') and lines:
   yield ''.join(lines);lines=[]
  lines.append(line)
 if lines:yield ''.join(lines)
def parse(s):
 slack=re.findall(num+r'\s+slack',s)
 if not slack:return None
 start=s.splitlines()[0][12:];ep=re.search(r'^Endpoint: (.+)',s,re.M)[1]
 data=s.split('data arrival time',1)[0]
 # Last data pin, not report header's macro instance name.
 pins=re.findall(r'^\s*'+num+r'\s+'+num+r'\s+[\^v] (\S+) \(([^)]+)\)',data,re.M)
 endpoint=pins[-1][2] if pins else ep.split(' (')[0]
 family=re.sub(r'\[\d+\]','[]',endpoint)
 arrival=re.search(num+r'\s+data arrival time',s)
 clocks=re.findall(r'^\s*'+num+r'\s+'+num+r'\s+[\^v] (\S+/clk) \(',s,re.M)
 clk_edges=re.findall(r'^\s*'+num+r'\s+'+num+r'\s+clock core_clk \(rise edge\)',s,re.M)
 ext=re.findall(num+r'\s+'+num+r'\s+[\^v] input external delay',s)
 hold=re.findall(num+r'\s+'+num+r'\s+library (?:hold|setup) time',s)
 return dict(startpoint=start,endpoint=endpoint,family=family,slack_ps=float(slack[-1]),arrival_ps=float(arrival[1]) if arrival else None,capture_clock_pin_ps=float(clocks[-1][1]) if clocks else None,clock_edges_ps=[float(x[1]) for x in clk_edges],external_delay_ps=float(ext[0][0]) if ext else None,library_constraint_ps=float(hold[-1][0]) if hold else None,data_cells=[dict(pin=x[2],master=x[3],delay_ps=float(x[0]),time_ps=float(x[1])) for x in pins])
summary={}
for corner in ['WC','BC']:
 for mode in ['min','max']:
  p=root/f'cts_{corner}_{mode}_all.rpt';key=f'{corner}_{mode}';groups={};count=0;worst=None
  for block in paths(p):
   d=parse(block)
   if not d:continue
   f=d['family'];g=groups.setdefault(f,dict(count=0,worst=None));g['count']+=1;count+=1
   if g['worst'] is None or d['slack_ps']<g['worst']['slack_ps']:g['worst']=d
   if worst is None or d['slack_ps']<worst['slack_ps']:worst=d;(out/f'{key}_worst.rpt').write_text(block)
  summary[key]=dict(negative_endpoint_count=count,normalized_class_count=len(groups),families=groups,worst=worst,report_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),report_bytes=p.stat().st_size)
  print(key,count,len(groups),worst['slack_ps'] if worst else None,flush=True)
(out/'all_endpoint_classes.json').write_text(json.dumps(summary,indent=2)+'\n')
