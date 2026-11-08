"""Bounded real-cell proof of the control-only reset pipeline and negative controls."""
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
import control_reset_pipeline as C
import gen_rtl
import reset_consumers as RC

TREE=dict(type='kv3_phy_v1',entry='relayed',sync_stages=2,depth=2,root=[400,750],reach_um=450,
          taps=[[850,750]],relays=[dict(name='u_cr_mid',q='cr_mid',d='rst_root_n',depth=1,xy=[625,750],kind='relay',tap=0),
                                  dict(name='u_cr_tap',q='rst_n_t0',d='cr_mid',depth=2,xy=[850,750],kind='tap',tap=0)])
DECL=dict(tree=TREE,delivered_reset_net='arst_n',cycle_contract=dict(extra_reset_cycles=3,steady_data_cycles=0,
          start_guard_cycles=272,source_witness='phy_EN_1_start_reset_witness: START>=356; reset delivery84'),
          consumers={'u_epoch':'rst_n_t0'},consumer_sites={'u_epoch':[855,750]})
TEXT='''module dut(input clk, arst_n, d, ea, output q, eq, native_reset);
wire rst_n = arst_n; // delivered native hard reset
assign native_reset = arst_n;
ot_dp_st #(.W(1)) u_epoch (.clk(clk), .rst_n(rst_n), .d(d), .ea(ea), .q(q), .eq(eq));
endmodule
'''
def apply(text=TEXT,decl=None,**kw):
    return C.apply(text,DECL if decl is None else decl,type_name='kv3_phy_v1',hard=True,outline=[864,1520.64],**kw)

class Guards(unittest.TestCase):
    def test_default_identical(self):self.assertEqual(apply(decl={}), (TEXT,None,None))
    def test_preserve_ports(self):
        out,tree,rec=apply();before=RC._calls(TEXT)['u_epoch']['ports'];after=RC._calls(out)['u_epoch']['ports']
        self.assertEqual({k:v[0] for k,v in before.items() if k!='rst_n'}, {k:v[0] for k,v in after.items() if k!='rst_n'})
        self.assertIn('assign native_reset = arst_n;',out);self.assertEqual(rec['extra_reset_cycles'],3)
    def test_bound_receipt_and_placement_roundtrip(self):
        import bound_reset_contract as BRC
        out,tree,_=apply()
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'kv3_phy_v1_part.sv';p.write_text(out)
            rec=BRC.emitted(p,'kv3_phy_v1',tree)
            BRC.validate(json.loads(p.with_suffix('.reset_tree.json').read_text()),'kv3_phy_v1')
            tcl=p.with_suffix('.reset_tree.tcl').read_text()
            self.assertIn('u_cr_tap',tcl)
            self.assertNotIn('OT_RESET_CORE_KEPT',tcl)
            self.assertEqual(rec['tree']['max_hop_um'],225)
    def test_bad_contract(self):
        for key,value in [('extra_reset_cycles',2),('steady_data_cycles',1),('start_guard_cycles',3),('source_witness','')]:
            d=copy.deepcopy(DECL);d['cycle_contract'][key]=value
            with self.assertRaises(C.ControlResetError):apply(decl=d)
    def test_native_reset_rejected(self):
        with self.assertRaises(C.ControlResetError):apply(TEXT.replace('ot_dp_st #(.W(1))','hard_phy'))
    def test_bad_topology(self):
        for d in [copy.deepcopy(DECL) for _ in range(3)]:
            if not hasattr(self,'case'):self.case=0
            self.case+=1
            if self.case==1:d['tree']['relays'][0]['d']='rst_n_t0'
            elif self.case==2:d['tree']['relays'][1]['depth']=1
            else:d['tree']['relays'][0]['xy']=[860,750]
            with self.assertRaises(C.ControlResetError):apply(decl=d)
    def test_macro_overlap(self):
        with self.assertRaises(C.ControlResetError):apply(blocked_boxes=[[390,740,410,760]])
    def test_actual_native_calls_unchanged(self):
        p=Path('/srv/opentallas-scratch2/claude/kw23/bind_kv_q/rtl/kv3_phy_v1_part.sv')
        if not p.exists():self.skipTest('actual binding not mounted')
        text=p.read_text();d=copy.deepcopy(DECL);calls=RC._calls(text)
        d['consumers']={k:'rst_n_t0' for k,v in calls.items() if v['module']=='ot_dp_st'}
        d['consumer_sites']={k:[855,750] for k in d['consumers']}
        out,_,_=apply(text,d);after=RC._calls(out)
        for name,row in calls.items():
            old={k:v[0] for k,v in row['ports'].items()};new={k:v[0] for k,v in after[name]['ports'].items()}
            if name in d['consumers']:
                self.assertEqual(new.pop('rst_n'),'rst_n_t0');old.pop('rst_n')
            self.assertEqual(old,new,name)
        print('ACTUAL_PHY_NATIVE_DATA_START_PORTS_UNCHANGED',len(calls),'selected_epoch_controls',len(d['consumers']))

TB='''module tb;
reg clk=0, arst_n=0,d=0,ea=1; wire q,eq,native_reset; dut u(.*);
reg [2:0] model=0; reg old_data=0; integer cycle=0;
always #5 clk=~clk;
always @(posedge clk) begin
 model <= {model[1:0],arst_n};
 old_data <= d;
 #1;
 if(cycle>5 && q!==old_data) $fatal(1,"DATA_LATENCY_CHANGED");
 if(native_reset!==arst_n) $fatal(1,"NATIVE_RESET_CHANGED");
 cycle=cycle+1;
end
reg prev_tap=0;
always @(posedge clk) begin
 prev_tap = model[2];
 #2;
 if(cycle>5 && eq !== ((prev_tap && model[2]) ? ea : 1'b0)) $fatal(1,"CONTROL_RESET_EDGE_MISMATCH");
end
integer i;
initial begin
 for(i=0;i<700;i=i+1) begin
  @(negedge clk); d=~d;
  if(i==24 || i==350 || i==500) arst_n=1;
  if(i==320 || i==470) arst_n=0;
  if(i==298 || i==620) ea=0;
  if(i==305 || i==630) ea=1;
 end
 $display("CONTROL_RESET_700_EDGES_PASS reset+3 data+0 native_unchanged");$finish;
end
endmodule
'''
def cells():
    return '\n'.join(re.search(r'\bmodule\s+'+n+r'\b.*?\bendmodule\b',gen_rtl.CELLS,re.S)[0] for n in ('ot_dp_st','ot_dp_rrelay'))
def simulation():
    out,_,_=apply();results={}
    with tempfile.TemporaryDirectory() as td:
        p=Path(td)
        forms={'good':out,'bypass':out.replace('.rst_n(rst_n_t0)','.rst_n(rst_n)'),
               'wrong_depth':out.replace('.rst_n(rst_n_t0)','.rst_n(cr_mid)')}
        for name,txt in forms.items():
            (p/'all.sv').write_text(cells()+'\n'+txt+TB)
            subprocess.run(['iverilog','-g2012','-s','tb','-o',str(p/'sim'),str(p/'all.sv')],check=True)
            r=subprocess.run(['vvp',str(p/'sim')],capture_output=True,text=True)
            results[name]={'exit':r.returncode,'stdout':r.stdout.strip()}
        assert results['good']['exit']==0, results
        assert all(results[n]['exit']!=0 for n in ('bypass','wrong_depth')),results
    print(json.dumps(results,indent=2))
if __name__=='__main__':
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(Guards)
    r=unittest.TextTestRunner(verbosity=2).run(suite)
    if not r.wasSuccessful():sys.exit(1)
    simulation()
