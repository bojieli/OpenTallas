#!/usr/bin/env python3
"""Smallest native parent: protected owner + real SMH north front and op sink.
Arithmetic is outside this gate. Full NC8 X transport and actual op FIFO are in it.
"""
from pathlib import Path
import hashlib,json,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
B='rtl/hbm_accel/control_20261007/'
SOURCES=[B+'protected/ot_hbm_sm_serial_protected.sv',B+'protected/ot_hbm_sm_serial_protected_core.sv',B+'ot_hbm_sm_seq_ingress.sv','rtl/hbm_accel/sm/ot_hbm_accel_smh.sv','rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv','rtl/hbm_accel/epilogue/ot_hbm_accel_bulk_copy.sv']
FIXTURE='results/rtl/hbm_sm_command_20261007/stress_seq.hex'

def bench():
 s=(ROOT/(B+'tb_sm_serial_owner.sv')).read_text()
 s=s.replace('ot_hbm_sm_serial_owner #(.ENABLE(1))','ot_hbm_sm_serial_protected #(.ENABLE(1),.PROTECT(1))').replace('dut.state','dut.a.state')
 s=s.replace('reg start_ready;', 'wire start_ready;').replace('reg arrive;', 'wire arrive;')
 s=s.replace('start_ready=(cyc%4!=0);','').replace('start_ready=0;','').replace('arrive=0;','front_pbz=0;')
 s=s.replace('arrive<=~arrive','front_pbz[1]<=~front_pbz[1]')
 s=s.replace('if(start && start_ready)begin', 'if(front_m_valid && front_m_ready)begin')
 s=s.replace('if(op_rows!=words[ops*10]', 'if(front_m_data!=={13\'(words[ops*10]),16\'(words[ops*10+1]),8\'(words[ops*10+2]),1\'(words[ops*10+5]),2\'(words[ops*10+3]),7\'(words[ops*10+9])})$fatal(1,"actual native op FIFO changed record");\n   if(native_captures!=(words[ops*10+6]?words[ops*10+7]*13:0))$fatal(1,"native op precedes native X landing");\n   if(op_rows!=words[ops*10]')
 s=s.replace('captures=0;', 'captures=0;native_captures=0;',1) if False else s
 s=s.replace('   captures=0;','   captures=0;native_captures=0;')
 s=s.replace('total_captures!=expected_captures','total_captures!=expected_captures || native_total!=expected_captures')
 s=s.replace('PASS native stress records=', 'PASS actual north front + protected owner records=')
 extra='''
 wire front_v,front_ret,front_m_valid;
 wire[46:0]front_data,front_m_data;
 wire front_m_ready=(cyc%4!=0);
 reg[2:0]front_pbz=0;
 wire[2068:0]front_bout_l,front_bout_r,front_fx;
 integer native_captures=0,native_total=0;
 reg[2047:0]native_expected;
 ot_hbm_accel_smh_front_n front(
  .clk(clk),.rst_n(rst_n),.start(start),.start_ready(start_ready),.op_rows(op_rows),.op_c(op_c),.op_g(op_g),.op_gs(op_gs),.op_fmt(op_fmt),.op_xb(op_xb),
  .busy(),.xw_en(xw_en),.xw_addr(xw_addr),.xw_grp(xw_grp),.xw_data(xw_data),.arrive(arrive),.release_in(1'b0),.released(),
  .rout_l0(),.rout_r0(),.bout_l0(front_bout_l),.bout_r0(front_bout_r),.fs_v(front_v),.fs_d(front_data),.fs_ret(front_ret),.fx_b(front_fx),.fr_rl(),.fi_row0(818'd0),.fi_pbz(front_pbz));
 ot_hbm_accel_smh_csnk #(.W(47),.PK(1),.PRK(1),.DEPTH(10)) native_op_sink(
  .clk(clk),.rst_n(rst_n),.i_v(front_v),.i_d(front_data),.o_ret(front_ret),.m_valid(front_m_valid),.m_ready(front_m_ready),.m_data(front_m_data));
 always @(posedge clk)if(rst_n && front_bout_l[2068])begin
  native_expected=pattern(ops,native_captures/13,native_captures%13);
  if(native_captures%13==12)native_expected[2047:640]=0;
  if(front_bout_l!==front_bout_r || front_bout_l[2047:0]!==native_expected ||
     front_bout_l[2060:2048] !== (13'b1 << (native_captures%13)) ||
     front_bout_l[2067:2061] !== 7'((words[ops*10+9]+native_captures/13)%128))
    $fatal(1,"actual native full-shape X landing mismatch op=%0d beat=%0d",ops,native_captures);
  native_captures=native_captures+1;native_total=native_total+1;
 end
'''
 return s.replace('endmodule',extra+'\nendmodule')

def main():
 runs=[]
 with tempfile.TemporaryDirectory(prefix='sm-native-front-') as d:
  for mutation in [None,'drop_ring_base','drop_last_group']:
   tb=bench()
   if mutation=='drop_ring_base':tb=tb.replace('.op_xb(op_xb),','.op_xb(7\'d0),')
   if mutation=='drop_last_group':tb=tb.replace('.xw_en(xw_en),','.xw_en(xw_en && xw_grp!=12),')
   p=Path(d)/'tb.sv';p.write_text(tb);exe=Path(d)/'sim'
   subprocess.run(['iverilog','-g2012','-s','tb_sm_serial_owner','-o',str(exe),str(p),*[str(ROOT/x)for x in SOURCES]],check=True)
   r=subprocess.run(['vvp',str(exe),'+SEQ='+str(ROOT/FIXTURE)],capture_output=True,text=True)
   if (r.returncode==0)!=(mutation is None):raise RuntimeError(r.stdout)
   runs.append(dict(mutation=mutation,returncode=r.returncode,output=r.stdout.strip()))
 return dict(scope='protected native owner joined to actual full NC8 north-front X pipeline and real op sink; no arithmetic/weight backend/result owner simulation',
   runs=runs,sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [*SOURCES,B+'tb_sm_serial_owner.sv',FIXTURE,'tools/hbm_sm_native_front_gate.py']},passed=True,selected=False)
if __name__=='__main__':print(json.dumps(main(),indent=2))
