import argparse,json,re,subprocess
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--sources',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
def block(name):
 s=(a.sources/name).read_text();return s.split('// TOKEN_IDENTITY_POLICY_BEGIN',1)[1].split('// TOKEN_IDENTITY_POLICY_END',1)[0]
checks='''
  assert(kvh_service_epoch(0x0b0b,-1,false)==0x0b0b);
  assert(kvh_service_epoch(0x0b0b,0,true)==0); // explicit stale negative control remains possible
  assert(kvh_service_epoch(0x0b0b,0,false)==0x0b0b);
  assert(kvh_token_identity_valid(1,8191,1,4,0x0b0b));
  assert(!kvh_token_identity_valid(1,8191,1,0x0b0b,0x0b0b)); // token low bits differ from service
  assert(kvh_token_identity_valid(1,8191,1,0x0b08,0x0b0b));
  assert(!kvh_token_identity_valid(1,8191,4,4,0x0b0b));
  assert(!kvh_token_identity_valid(1,8191,-1,4,0x0b0b));
  assert(!kvh_token_identity_valid(151936,8191,1,4,0x0b0b));
  assert(!kvh_token_identity_valid(1,8192,1,4,0x0b0b));
  assert(!kvh_token_identity_valid(1,8191,1,4,-1));
  assert(!kvh_token_identity_valid(1,8191,1,65536,0x0b0b));
  assert(!kvh_token_identity_valid(1,8191,1,4,65536));
  bool observed_ready=true; unsigned observed_service=0x0b0b;
  assert(!(observed_ready && observed_service==0)); // actual old ready-wait counterexample
  assert(observed_ready && observed_service==kvh_service_epoch(0x0b0b,-1,false));
'''
results=[]
for i,n in enumerate(['main_kvfn3.cpp','main_kvfn4.cpp']):
 src=a.out/f'policy{i}.cpp';exe=a.out/f'policy{i}';src.write_text('#include <cassert>\n'+block(n)+'\nint main(){\n'+checks+'}\n')
 subprocess.run(['g++','-std=c++17','-O0',str(src),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True);results.append(dict(source=n,checks=15,status='PASS'))
sv=block('tb_kvslice_native.sv')
svchecks=checks.replace('assert(', 'check(').replace('true','1\'b1').replace('false','1\'b0').replace('0x0b0b',"16'h0b0b").replace('0x0b08',"16'h0b08")
svchecks=svchecks[:svchecks.index('  bool observed_ready')]+'''  check(!(1'b1 && 16'h0b0b==0));
  check(1'b1 && 16'h0b0b==kvh_service_epoch(16'h0b0b,-1,1'b0));
'''
tb=a.out/'policy.sv';tb.write_text('module tb;\n'+sv+'\ninteger count=0;task check(input bit ok);begin if(!ok)$fatal(1,"identity policy assertion");count++;end endtask\ninitial begin\n'+svchecks+'\n$display("IDENTITY_SV_PASS checks=%0d",count);$finish;end\nendmodule\n')
subprocess.run(['iverilog','-g2012','-s','tb','-o',str(a.out/'policy.vvp'),str(tb)],check=True)
r=subprocess.run(['vvp',str(a.out/'policy.vvp')],check=True,capture_output=True,text=True);(a.out/'sv.log').write_text(r.stdout)
results.append(dict(source='tb_kvslice_native.sv',checks=15,status='PASS'))
(a.out/'result.json').write_text(json.dumps(dict(scope='actual source identity-policy functions only; driver mismatch closure, not hardware witness/whole-native qualification',observed_programme_service_epoch='0b0b',observed_legacy_expected_service_epoch='0000',token_epoch_generation='independent job fields; default token epoch4 remains allowed for pos8191',results=results),indent=2)+'\n');print(r.stdout.strip());print('CPP_DRIVER_POLICY PASS 2x15')
