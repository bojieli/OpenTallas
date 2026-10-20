import importlib.util,json,unittest
from pathlib import Path
p=Path(__file__).with_name('compare_ab_graphs.py');s=importlib.util.spec_from_file_location('g',p);g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
def fixture(hxk=13):
 return {'modules':{'top':{'parameter_default_values':{'HXK':f'{hxk:032b}','OTHER':'1'},'attributes':{'src':'actual/source.sv:1'},'ports':{'ck':{'direction':'input','bits':[2]},'rst':{'direction':'input','bits':[3]},'q':{'direction':'output','bits':[5]}},'netnames':{'ck':{'bits':[2]},'rst':{'bits':[3]},'bus':{'bits':[4,5],'offset':7,'upto':1},'alias':{'bits':[5]}},'cells':{'state':{'type':'$adff','parameters':{'CLK_POLARITY':'1','ARST_POLARITY':'0'},'port_directions':{'CLK':'input','ARST':'input','D':'input','Q':'output'},'connections':{'CLK':[2],'ARST':[3],'D':[4],'Q':[5]}},'actual_mem':{'type':'actual_sram','parameters':{'DEPTH':'128'},'port_directions':{'CLK':'input','WD':'input','Q':'output'},'connections':{'CLK':[2],'WD':[4,4],'Q':[6]}}}}}}
def other():return fixture(15)
def same(a,b):return g.canonical(a,'top',13)==g.canonical(b,'top',15)
class Graph(unittest.TestCase):
 def test_only_profile_and_net_alpha_allowed(self):
  a=fixture();b=other()
  for m in b['modules'].values():
   for v in m['ports'].values():v['bits']=[x+100 for x in v['bits']]
   for v in m['netnames'].values():v['bits']=[x+100 for x in v['bits']]
   for c in m['cells'].values():
    for k,v in c['connections'].items():c['connections'][k]=[x+100 for x in v]
  self.assertTrue(same(a,b))
 def test_every_clock_reset_connection(self):
  b=other();c=b['modules']['top']['cells']['state']['connections'];c['CLK'],c['ARST']=c['ARST'],c['CLK'];self.assertFalse(same(fixture(),b))
 def test_alias_not_elided(self):
  b=other();del b['modules']['top']['netnames']['alias'];self.assertFalse(same(fixture(),b))
 def test_net_multiplicity_preserved(self):
  b=other();b['modules']['top']['cells']['actual_mem']['connections']['WD']=[4,6];self.assertFalse(same(fixture(),b))
 def test_storage_master_and_parameter(self):
  for field,value in [('type','different_sram'),('parameters',{'DEPTH':'256'})]:
   b=other();b['modules']['top']['cells']['actual_mem'][field]=value;self.assertFalse(same(fixture(),b))
 def test_port_direction_offset_and_literals(self):
  b=other();b['modules']['top']['ports']['rst']['direction']='output';self.assertFalse(same(fixture(),b))
  b=other();b['modules']['top']['netnames']['bus']['offset']=6;self.assertFalse(same(fixture(),b))
  b=other();b['modules']['top']['cells']['state']['connections']['D']=['0'];self.assertFalse(same(fixture(),b))
 def test_hierarchy_and_instance_names_not_elided(self):
  b=other();b['modules']['top']['cells']['renamed']=b['modules']['top']['cells'].pop('state');self.assertFalse(same(fixture(),b))
if __name__=='__main__':unittest.main()
