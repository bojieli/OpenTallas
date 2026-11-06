import sys,json,re,copy
from pathlib import Path
import argparse
parser=argparse.ArgumentParser();parser.add_argument('--work-dir',type=Path,required=True);parser.add_argument('--tool-dir',type=Path,default=Path(__file__).resolve().parents[4]/'tools/die_plan');args=parser.parse_args()
sys.path.insert(0,str(args.tool_dir))
import station_hierarchy_split as S
from station_native_clock_capture import root_bit
b=args.work_dir
source=json.load(open(b/'captured.json'));split=json.load(open(b/'split.json'));event=json.load(open(b/'selection.json'));clocks=json.load(open(b/'clock_capture.json'));old=source['modules'][event['module']];parent=split['modules'][event['module']]
root_bits={root_bit(old,r):r for r in clocks['roots']}
maps={};stats={}
for child,names in event['children'].items():
 cm=split['modules'][event['child_modules'][child]];inst=parent['cells'][event['child_instances'][child]];mapping=S._bits_to_original(cm,old)
 new_ports={};new_connections={};new_dirs={};pm={};serial=0
 for port,v in sorted(cm['ports'].items()):
  originals=S._mapped(v['bits'],mapping)
  is_clock=any(bit in root_bits for bit in originals)
  if is_clock:
   if len(originals)!=1 or originals[0] not in root_bits or v['direction']!='input':raise ValueError('mixed/noninput clock port')
   clean=port if re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',port) else 'clock_'+str(serial)
   serial+=1
   if clean in new_ports:raise ValueError('clock ABI collision')
   new_ports[clean]=v;new_connections[clean]=inst['connections'][port];new_dirs[clean]=v['direction'];pm[clean]={'old_port':port,'width':1,'kind':'clock','source_root':root_bits[originals[0]]}
   if clean!=port:cm['netnames'][clean]={'hide_name':0,'bits':v['bits'],'attributes':{}}
  else:
   for index,bit in enumerate(v['bits']):
    clean='p'+str(serial).zfill(5);serial+=1
    while clean in cm['netnames'] or clean in new_ports:clean='p'+str(serial).zfill(5);serial+=1
    new_ports[clean]={'direction':v['direction'],'bits':[bit]};new_connections[clean]=[inst['connections'][port][index]];new_dirs[clean]=v['direction']
    cm['netnames'][clean]={'hide_name':0,'bits':[bit],'attributes':{}}
    pm[clean]={'old_port':port,'old_bit_position':index,'kind':'signal'}
 cm['ports']=new_ports;inst['connections']=new_connections;inst['port_directions']=new_dirs;maps[child]=pm
 stats[child]={'clock_ports':sum(v['kind']=='clock' for v in pm.values()),'scalar_signal_ports':sum(v['kind']=='signal' for v in pm.values())}
receipt=S.check(source,split,event)
(b/'split_clean.json').write_text(json.dumps(split)+chr(10));(b/'abi_map.json').write_text(json.dumps({'status':'PORT_REPRESENTATION_ONLY; whole-stage ownership unchanged; timing frames still owed','children':maps,'counts':stats},indent=1));(b/'conservation_clean.json').write_text(json.dumps(receipt,indent=1));print('CLEAN_ABI',stats);print('CONSERVATION',receipt)
