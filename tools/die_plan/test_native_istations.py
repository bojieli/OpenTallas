import copy,json,os,subprocess,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
import bind,native_istations

class NativeStations(unittest.TestCase):
 def fixture(self):
  typ={'module':'vehicle','buses':[{'name':'o','dir':'out','width':8}], 'internal_stations':[{'conn':'bus:o','regs_um':[[i,0] for i in range(8)]}], 'contents':[]}
  L={'lane':'L0','oname':'o','cycles':22,'ft':[],'width':8}
  b=SimpleNamespace(ab={'internal_stations_types':['sys']},types={'sys':typ},parts={'p':{'type':'sys'}},by_type={'sys':['p']},out_bus={'p':[L]},plan={'lanes':[{'id':'L0','fixed_cycles':8}]})
  return b,L
 def test_pricing_and_guards(self):
  b,L=self.fixture();native_istations.annotate(b);self.assertEqual(bind.lane_pad(L),12);self.assertEqual(2+bind.lane_pad(L)+L['internal_source_cycles'],22)
  b,L=self.fixture();b.plan['lanes'][0]['fixed_cycles']=7
  with self.assertRaises(ValueError):native_istations.annotate(b)
  b,L=self.fixture();L['cycles']=9
  with self.assertRaises(ValueError):native_istations.annotate(b)
 def test_signed_clock_landing_budget(self):
  # Reset landing removes both generic boundary stages; the real source stations remain.
  b,L=self.fixture();L.update(cycles=8,clock_landing_cycles=-2)
  native_istations.annotate(b)
  self.assertEqual(bind.lane_pad(L),0)
  self.assertEqual(2+L['internal_source_cycles']+L['clock_landing_cycles'],8)
  b,L=self.fixture();L.update(cycles=7,clock_landing_cycles=-2)
  with self.assertRaisesRegex(ValueError,'priced lane depth'):native_istations.annotate(b)
  # A positive CA landing consumes its own budget and cannot be reused for source stations.
  b,L=self.fixture();L.update(cycles=12,clock_landing_cycles=3)
  with self.assertRaisesRegex(ValueError,'priced lane depth'):native_istations.annotate(b)
  L['cycles']=13;native_istations.annotate(b)
  self.assertEqual(bind.lane_pad(L),0)
 def test_mixed_and_duplicate_metadata(self):
  b,L=self.fixture();t=b.types['sys'];e=t['internal_stations'][0]
  t['internal_stations'].append(copy.deepcopy(e));t['internal_stations'][-1]['note']='same geometry, another reference'
  t['buses'].append(dict(name='i',dir='in',width=8));t['internal_stations'].append(dict(conn='bus:i',regs_um=[[99,99]]))
  t['internal_stations'].append(dict(conn='core:a|core:b',regs_um=[[9,9]]))
  native_istations.annotate(b);self.assertEqual(L['internal_source_cycles'],8);self.assertEqual(len(native_istations.source_entries(t)),1)
  t['internal_stations'][1]['regs_um'][0]=[1,999]
  with self.assertRaisesRegex(ValueError,'conflicting OUT'):native_istations.annotate(b)

 def test_bus_scope_skips_unselected_out_buses(self):
  # HBM-PLAN-1: a relay type realises only its relay OUT buses; per-core OUT rows of other buses stay KIT
  b,L=self.fixture();t=b.types['sys']
  t['buses'].append(dict(name='m',dir='out',width=4))
  t['internal_stations']+= [dict(conn='bus:m',regs_um=[[0,0]]),dict(conn='bus:m',regs_um=[[5,5],[6,6]])]
  with self.assertRaisesRegex(ValueError,'conflicting OUT'):native_istations.annotate(b)
  b.ab['internal_stations_buses']={'sys':['o']}
  native_istations.annotate(b);self.assertEqual(L['internal_source_cycles'],8)
  self.assertEqual([e['conn'] for e in native_istations.source_entries(t,native_istations.selected_buses(b.ab,'sys'))],['bus:o'])
  self.assertIsNone(native_istations.selected_buses(b.ab,'other'))
  with self.assertRaisesRegex(ValueError,'unknown OUT buses'):native_istations.source_entries(t,{'zz'})

 def test_output_geometry_follows_signal_order(self):
  b,L=self.fixture();e=b.types['sys']['internal_stations'][0]
  e.update(launch='u_t00.n_y',capture='face flop',from_um=[0,0],to_um=[8,0])
  result=native_istations.source_entries(b.types['sys'])[0]
  self.assertEqual(result['regs_um'],list(reversed(e['regs_um'])))
  self.assertEqual(result['from_um'],e['to_um'])
  self.assertEqual(e['regs_um'][0],[0,0])

 def test_output_geometry_core_first_is_kept(self):
  # STATION-FIX-HBM 11-11: a plan entry already written core -> face (to_um on the outline) is source ordered;
  # face-first and core-first forms of the same stations give identical native entries (bind receipt unchanged)
  b,L=self.fixture();t=b.types['sys'];t['outline_um']=[100.0,50.0];e=t['internal_stations'][0]
  e.update(launch='u_t00.n_y',capture='face flop',from_um=[0.0,10.0],to_um=[60.0,10.0],regs_um=[[7,10],[30,10],[52,10]])
  old=native_istations.source_entries(t)[0]
  self.assertEqual(old['regs_um'],[[52,10],[30,10],[7,10]]);self.assertEqual(old['from_um'],[60.0,10.0])
  e['from_um'],e['to_um'],e['regs_um']=e['to_um'],e['from_um'],list(reversed(e['regs_um']))
  self.assertEqual(native_istations.source_entries(t)[0],old)
  # neither end on the outline: the face-first reading stays
  e.update(from_um=[5.0,10.0],to_um=[60.0,10.0])
  self.assertEqual(native_istations.source_entries(t)[0]['from_um'],[60.0,10.0])

 def test_source_and_destination_station_budget_is_not_double_charged(self):
  b,L=self.fixture();b.types['sys']['internal_stations'][0]['regs_um']=[[0,0],[1,0]]
  b.types['receiver']={'buses':[{'name':'i','dir':'in','width':8}],'internal_stations':[{'conn':'bus:i','regs_um':[[i,1] for i in range(7)]}]}
  b.parts['q']={'type':'receiver'};b.out_bus['q']=[];L.update(dst='q',iname='i');b.plan['lanes'][0]['fixed_cycles']=9
  native_istations.annotate(b);self.assertEqual(L['internal_source_cycles'],2);self.assertEqual(2+bind.lane_pad(L)+2,22)
  b.plan['lanes'][0]['fixed_cycles']=8
  with self.assertRaisesRegex(ValueError,r'source 2 \+ destination 7'):native_istations.annotate(b)
 def test_narrow_payload_and_relative_path(self):
  b,L=self.fixture();L['width']=3
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);f=root/'rtl/vehicle.sv';f.parent.mkdir()
   f.write_text('module vehicle(input clk,input arst_n,input [2:0] d,output [3:0] o);\nwire rst_n=arst_n;\n ot_dp_st #(.W(3)) u_bout_o (.clk(clk), .rst_n(rst_n), .d(d), .ea(rst_n), .q(o[2:0]), .eq(o[3]));\nendmodule\n')
   previous=Path.cwd()
   try:
    os.chdir(root);native_istations.materialize(b,'sys',Path('rtl/vehicle.sv'))
   finally:os.chdir(previous)
   text=f.read_text();self.assertIn('ot_dp_st #(.W(3)) u_ist_o_0',text)
   self.assertEqual(b.types['sys']['buses'][0]['width'],8)
   self.assertEqual(text.count('FIRM plan station'),8)
 def test_mixed_bound_widths_fail_closed(self):
  b,L=self.fixture();b.by_type['sys'].append('q');b.out_bus['q']=[dict(L,width=7)]
  with self.assertRaisesRegex(ValueError,'unique bound payload width'):
   native_istations.materialize(b,'sys',Path('/tmp/never_native_width.sv'))

 def test_cycle_and_mutants(self):
  b,L=self.fixture();b.types['sys']['buses'].append(dict(name='i',dir='in',width=8));b.types['sys']['internal_stations'].append(dict(conn='bus:i',regs_um=[[99,99]]));native_istations.annotate(b)
  with tempfile.TemporaryDirectory() as tmp:
   d=Path(tmp);f=d/'rtl/vehicle.sv';f.parent.mkdir()
   f.write_text('module vehicle(input clk,input arst_n,input [7:0] d,output [8:0] o);\nwire rst_n=arst_n;\n ot_dp_st #(.W(8)) u_bout_o (.clk(clk), .rst_n(rst_n), .d(d), .ea(rst_n), .q(o[7:0]), .eq(o[8]));\nendmodule\n')
   before=Path.cwd()
   try:
    os.chdir(d);native_istations.materialize(b,'sys',Path('rtl/vehicle.sv'))
   finally:os.chdir(before)
   text=f.read_text();self.assertEqual(text.count('FIRM plan station'),8)
   native_istations.materialize(b,'sys',f);self.assertEqual(f.read_text(),text)
   tb='''module tb;reg clk=0;always #5 clk=~clk;reg rst_n=0;reg[7:0]d=1;wire[8:0]o;vehicle u(clk,rst_n,d,o);reg[7:0] gold[0:21];integer i,cyc=0;wire[7:0]q,land;ot_dp_st #(.W(8)) rx(.clk(clk),.rst_n(rst_n),.d(o[7:0]),.ea(o[8]),.q(land),.eq());ot_dp_dly #(.W(8),.D(PAD)) pad(.clk(clk),.d(land),.q(q));always@(posedge clk)begin gold[0]<=d;for(i=1;i<22;i=i+1)gold[i]<=gold[i-1];end always@(negedge clk)begin cyc=cyc+1;if(cyc>40 && q!==gold[21])$fatal(1,"EDGE_MISMATCH %d",cyc);d={d[6:0],d[7]^d[5]^d[4]^d[3]};rst_n=1;if(cyc==120)begin $display("CYCLE22_PASS");$finish;end end endmodule'''
   for name,source,pad,want in [('nominal',text,12,0),('missing',text.replace('.d(o_is7_q)', '.d(d)'),12,1),('double',text,20,1)]:
    if name=='missing':self.assertNotEqual(source,text)
    src=d/(name+'.sv');src.write_text(bind.CELLS+'\n'+source+'\n'+tb.replace('PAD',str(pad)))
    binary=d/name;cp=subprocess.run(['iverilog','-g2012','-s','tb','-o',str(binary),str(src)],capture_output=True,text=True);self.assertEqual(cp.returncode,0,cp.stderr)
    run=subprocess.run(['vvp',str(binary)],capture_output=True,text=True);print(name,run.returncode,run.stdout.strip());self.assertEqual(bool(run.returncode),bool(want))
class KitSourceStations(unittest.TestCase):
 """QC-BIND-IST-PAD 11-12: kit-built (non-native) OUT stations are priced at the source, not padded at the receiver."""
 def fixture(self,cycles=12,regs=4,fixed=4,native=()):
  src={'module':'s','buses':[{'name':'o','dir':'out','width':8}],'internal_stations':[{'conn':'bus:o','regs_um':[[i,0] for i in range(regs)],'bit_route':'per_bit'}] if regs else []}
  rx={'module':'r','buses':[{'name':'i','dir':'in','width':8}]}
  L={'lane':'L0','oname':'o','iname':'i','dst':'q','cycles':cycles,'ft':[],'width':8}
  b=SimpleNamespace(ab={'internal_stations_types':list(native),'kit_source_station_pricing':True},types={'src':src,'rx':rx},parts={'p':{'type':'src'},'q':{'type':'rx'}},
                    by_type={'src':['p'],'rx':['q']},out_bus={'p':[L],'q':[]},plan={'lanes':[{'id':'L0','fixed_cycles':fixed}]},errors=[])
  return b,L
 def test_table_counts_kit_stations(self):
  # table 12 = 2 boundary + 4 kit source stations + 6 pad: the receiver pads 6, not 10; bound stages = table
  b,L=self.fixture();native_istations.annotate(b);native_istations.annotate_kit(b)
  self.assertEqual(L['internal_kit_source_cycles'],4);self.assertEqual(bind.lane_pad(L),6);self.assertEqual(b.errors,[])
  self.assertEqual(2+bind.lane_pad(L)+L['internal_kit_source_cycles'],12)
 def test_lane_without_stations_unchanged(self):
  b,L=self.fixture(regs=0,fixed=0);native_istations.annotate(b);native_istations.annotate_kit(b)
  self.assertNotIn('internal_kit_source_cycles',L);self.assertEqual(bind.lane_pad(L),10)
 def test_native_type_not_double_subtracted(self):
  b,L=self.fixture(native=('src',));b.types['src']['internal_stations'][0].pop('bit_route')
  native_istations.annotate(b);native_istations.annotate_kit(b)
  self.assertEqual(L['internal_source_cycles'],4);self.assertNotIn('internal_kit_source_cycles',L);self.assertEqual(bind.lane_pad(L),6)
 def test_e5_fixed_cycles_case_keeps_receivers_identical(self):
  # sl_E5_fw carries 2 kit OUT stations (lane fixed 2, table +2), sl_E0_fw none: both sle_ctl receivers get the same pad,
  # so the 6 cl503337ff instances keep one ibus signature (no TYPE_SPLIT)
  b5,L5=self.fixture(cycles=22,regs=2,fixed=2);b0,L0=self.fixture(cycles=20,regs=0,fixed=0)
  for b in (b5,b0):native_istations.annotate(b);native_istations.annotate_kit(b)
  self.assertEqual(bind.lane_pad(L5),bind.lane_pad(L0));self.assertEqual(bind.lane_pad(L0),18)
 def test_stale_table_fails_closed(self):
  # table not refreshed for the stations (cl67434795 since 11-09): the bind reports it instead of building n long
  b,L=self.fixture(cycles=4);native_istations.annotate(b);native_istations.annotate_kit(b)
  self.assertNotIn('internal_kit_source_cycles',L);self.assertEqual(len(b.errors),1);self.assertIn('KIT_ISTATION_LATENCY L0',b.errors[0])
 def test_unpriced_stations_keep_old_pad(self):
  # HEAD hd_spn form: OUT stations not priced in fixed_cycles -> pad unchanged, no error (no cross-die change)
  b,L=self.fixture(cycles=5,regs=2,fixed=0);native_istations.annotate_kit(b)
  self.assertNotIn('internal_kit_source_cycles',L);self.assertEqual(b.errors,[]);self.assertEqual(bind.lane_pad(L),3)
 def test_default_off_is_unchanged(self):
  # COMPAT: without asbuilt kit_source_station_pricing the bind prices exactly as before (no cross-die change)
  b,L=self.fixture();del b.ab['kit_source_station_pricing'];native_istations.annotate_kit(b)
  self.assertNotIn('internal_kit_source_cycles',L);self.assertEqual(bind.lane_pad(L),10);self.assertEqual(b.errors,[])
 def test_type_list_scope(self):
  b,L=self.fixture();b.ab['kit_source_station_pricing']=['other'];native_istations.annotate_kit(b)
  self.assertNotIn('internal_kit_source_cycles',L)
  b,L=self.fixture();b.ab['kit_source_station_pricing']=['base'];b.types['src']['split_of']='base';native_istations.annotate_kit(b)
  self.assertEqual(L['internal_kit_source_cycles'],4)
 def test_deepest_row_is_the_chain(self):
  b,L=self.fixture();b.types['src']['internal_stations'].append({'conn':'bus:o','regs_um':[[0,1],[1,1]],'bit_route':'per_bit'})
  native_istations.annotate_kit(b);self.assertEqual(L['internal_kit_source_cycles'],4)

if __name__=='__main__':unittest.main()
