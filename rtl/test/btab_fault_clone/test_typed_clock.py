from pathlib import Path
import importlib.util,json,tempfile
w=Path(__file__).resolve().parents[3]
p=w/'physical/die_plan/qwen_compute/cores/legacy/gen_core_kit_qc.py'
s=importlib.util.spec_from_file_location('qcgen',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class MS:
 @staticmethod
 def _clock_port(k,sl):return sl['core_clock_port']
 @staticmethod
 def slice_pins(sl,cp):return {cp:sl['islands'][0]['clock_pin']}
sl=dict(core_clock_port='ck',islands=[dict(clock_pin=dict(layer='M5',xy_um=[146.892,77.76]))])
for mode in ['typed','legacy','wrongXY','wrongLayer','wrongName']:
 with tempfile.TemporaryDirectory() as td:
  k=Path(td);row=dict(bus='ck',bit=None,face='C',layer='M5',x=146.892,y=77.76)
  if mode=='legacy':row['face']='S';row['y']=.042
  if mode=='wrongXY':row['x']=146.88
  if mode=='wrongLayer':row['layer']='M4'
  if mode=='wrongName':sl0=dict(sl,core_clock_port='other')
  else:sl0=sl
  if mode=='wrongName':
   try:m.interior_clock_pin(dict(name='ck',**{z:v for z,v in row.items() if z not in ['bus','bit']}),sl0,'ck')
   except SystemExit:print(mode,'REJECT');continue
   raise AssertionError('unknown clock accepted')
  (k/'master_slice.json').write_text(json.dumps(sl0));(k/'pins.json').write_text(json.dumps([row]))
  try:r=m.slice_clock_pins_out(k,MS,['ck'])
  except SystemExit:
   assert mode in ['wrongXY','wrongLayer'];print(mode,'REJECT');continue
  if mode=='typed':assert r==[] and json.load((k/'pins.json').open())==[row]
  elif mode=='legacy':assert r==['ck'] and json.load((k/'pins.json').open())==[]
  elif mode=='wrongName':assert r==[] # undeclared row is not granted clock exemption or moved by this function
  else:raise AssertionError('invalid typed clock accepted '+mode)
  print(mode,'PASS')
