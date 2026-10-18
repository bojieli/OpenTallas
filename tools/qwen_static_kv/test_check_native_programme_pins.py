import copy,json,os,shutil,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import check_native_programme_pins as cnp

ROOT=Path(__file__).resolve().parents[2]
RTL=ROOT/'rtl/qwen_sys/static_kv_20261014/qkd_kv_native_programme.sv'

def ff(kind,d,q,arst=None):
    conn=dict(CLK=[1],D=d,Q=q);dirs=dict(CLK='input',D='input',Q='output')
    if arst is not None:conn['ARST']=arst;dirs['ARST']='input'
    return dict(type=kind,connections=conn,port_directions=dirs)

def netlist(form):
    # ck=1 rst_n=2 x=3 -> x_q=4 (output y); internal state s=6 reset by the pin reset
    ports=dict(ck=dict(direction='input',bits=[1]),rst_n=dict(direction='input',bits=[2]),
               x=dict(direction='input',bits=[3]),y=dict(direction='output',bits=[4]))
    if form=='sync':
        cells=dict(rpin=ff('$dff',[2],[5]),xq=ff('$dff',[3],[4]),s=ff('$adff',[4],[6],arst=[5]))
    else:
        cells=dict(rpin=ff('$adff',['1'],[5],arst=[2]),xq=ff('$dff',[3],[4]),s=ff('$adff',[4],[6],arst=[5]))
    return dict(modules=dict(qkd_kv_native_programme=dict(ports=ports,cells=cells)))

class NativePinCheck(unittest.TestCase):
    def setUp(self):
        self.tmp=Path(tempfile.mkdtemp());self.saved=dict(cnp.LOGICAL_FF_BITS);cnp.LOGICAL_FF_BITS["sync"]=3
        cnp.LOGICAL_FF_BITS['async']=3
    def tearDown(self):
        cnp.LOGICAL_FF_BITS.clear();cnp.LOGICAL_FF_BITS.update(self.saved);shutil.rmtree(self.tmp)
    def run_check(self,j):
        p=self.tmp/'n.json';p.write_text(json.dumps(j));return cnp.check(p)
    def test_sync_reset_pin_accepted(self):
        r=self.run_check(netlist('sync'))
        self.assertEqual((r['external_reset_form'],r['reset_pin_assert_edges'],r['internal_arst_sinks_of_reset_pin_ff']),('sync',1,1))
    def test_async_reset_pin_still_accepted(self):
        self.assertEqual(self.run_check(netlist('async'))['external_reset_form'],'async')
    def test_sync_reset_pin_ff_feeding_logic_refused(self):
        j=netlist('sync');m=j['modules']['qkd_kv_native_programme']['cells'];m['lg']=dict(type='$and',connections=dict(A=[5],B=[3],Y=[7]),port_directions=dict(A='input',B='input',Y='output'))
        with self.assertRaises(AssertionError):self.run_check(j)
    def test_internal_arst_not_from_pin_ff_refused(self):
        j=netlist('sync');m=j['modules']['qkd_kv_native_programme']['cells'];m['t']=ff('$adff',[4],[8],arst=[3])
        with self.assertRaises(AssertionError):self.run_check(j)
    def test_second_rst_n_sink_refused(self):
        j=netlist('sync');m=j['modules']['qkd_kv_native_programme']['cells'];m['r2']=ff('$dff',[2],[9])
        with self.assertRaises(AssertionError):self.run_check(j)
    def test_rst_n_on_non_flop_refused(self):
        j=netlist('sync');m=j['modules']['qkd_kv_native_programme']['cells'];m['rpin']=dict(type='$not',connections=dict(A=[2],Y=[5]),port_directions=dict(A='input',Y='output'))
        with self.assertRaises(AssertionError):self.run_check(j)
    def test_input_bypassing_capture_still_refused(self):
        j=netlist('sync');m=j['modules']['qkd_kv_native_programme']['cells'];m['g']=dict(type='$not',connections=dict(A=[3],Y=[10]),port_directions=dict(A='input',Y='output'))
        with self.assertRaises(AssertionError):self.run_check(j)
    def test_ff_count_exact(self):
        cnp.LOGICAL_FF_BITS['sync']=4
        with self.assertRaises(AssertionError):self.run_check(netlist('sync'))

@unittest.skipUnless(shutil.which('yosys'),'yosys not installed')
class NativePinCheckRTL(unittest.TestCase):
    def test_current_rtl_passes_sync_form(self):
        with tempfile.TemporaryDirectory() as d:
            j=Path(d)/'pin.json'
            subprocess.run(['yosys','-Q','-T','-q','-p',f'read_verilog -sv {RTL}; hierarchy -top qkd_kv_native_programme -chparam VMAP 1; proc; memory_map; opt_clean; write_json {j}'],check=True,capture_output=True)
            r=cnp.check(j)
        self.assertEqual((r['external_reset_form'],r['total_logical_ff_bits'],r['internal_arst_sinks_of_reset_pin_ff']),('sync',6629,36))

if __name__=='__main__':unittest.main()
