import sys,json,tempfile,pathlib,unittest,importlib.util
root=pathlib.Path(__file__).resolve().parents[1]
s=importlib.util.spec_from_file_location('context',root/'tools/hbrom/context_physical.py');m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class Test(unittest.TestCase):
 def test_exact_capture_scope(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);cells={};nets={};macros=[];bit=1
   for i in range(256):
    q=list(range(bit,bit+274));bit+=274;oq=list(range(bit,bit+274));bit+=274
    rn=f'g_rom[{i}].u_rom';cells[rn]={'type':'ot_rom_4096x274_m8','connections':{'rd_out':q},'port_directions':{'rd_out':'output'}}
    nets[f'feed.captured[{i}]']={'bits':oq}
    for j,(a,b) in enumerate(zip(q,oq)):
     cells[f'cap_{i}_{j}']={'type':'DFFHQNx1_ASAP7_75t_R','connections':{'D':[a],'Q':[b]},'port_directions':{'D':'input','Q':'output'}}
    macros.append({'instance':rn,'view':'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8','x':(i%16)*150,'y':(i//16)*80})
   n=p/'n.json';n.write_text(json.dumps({'modules':{'top':{'cells':cells,'netnames':nets}}}));l=p/'l.json';l.write_text(json.dumps({'macros':macros,'tiles':1,'die_um':[2500,1400],'scope':'test connectivity only'}))
   r=m.prepare(n,'top',l,p/'out');self.assertEqual(r['capture_count'],70144)
   sdc=(p/'out/capture.sdc').read_text();self.assertEqual(sdc.count('set_multicycle_path -setup 2 -through'),256);self.assertEqual(sdc.count('set_multicycle_path -hold 1 -through'),256)
   # Padding is outside the union of FP4/FP8/BF16 payload bits.
   for i in range(256):
    for j in (272,273):
     del cells[f'cap_{i}_{j}'];nets[f'feed.captured[{i}]']['bits'][j]='x'
   def save():n.write_text(json.dumps({'modules':{'top':{'cells':cells,'netnames':nets}}}))
   save();r=m.prepare(n,'top',l,p/'padding_removed')
   self.assertEqual(r['capture_count'],69632);self.assertEqual(r['meaningful_capture_count'],69632);self.assertEqual(r['padding_capture_count'],0)
   a=cells['cap_0_0']['connections']['D'];b=cells['cap_0_1']['connections']['D']
   cells['cap_0_0']['connections']['D']=b;save()
   with self.assertRaisesRegex(ValueError,'wrong ROM/bit origin'):m.prepare(n,'top',l,p/'wrong_bit')
   cells['cap_0_0']['connections']['D']=a
   old=nets['feed.captured[0]']['bits'][271];nets['feed.captured[0]']['bits'][271]='x';save()
   with self.assertRaisesRegex(ValueError,'Missing meaningful capture bit'):m.prepare(n,'top',l,p/'missing_payload')
   nets['feed.captured[0]']['bits'][271]=old
   cells['cap_0_0']['connections']['D']=[999999999];n.write_text(json.dumps({'modules':{'top':{'cells':cells,'netnames':nets}}}))
   with self.assertRaisesRegex(ValueError,'missing or multiple ROM'):m.prepare(n,'top',l,p/'bad')
if __name__=='__main__':unittest.main()
