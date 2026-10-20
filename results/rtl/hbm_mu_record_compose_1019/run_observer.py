from pathlib import Path
import subprocess
O=Path.cwd();A=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019/obj_arithmetic_clock');R=Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019');V=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
subprocess.run(['objcopy','--redefine-sym','main=baseline_main',str(O/'Vtb__ALL.a'),str(O/'observer.a')],check=True)
subprocess.run(['g++','-std=c++20','-O0','-DVL_TIME_CONTEXT','-I'+str(A),'-I'+str(V),'-I'+str(V/'vltstd'),'-pthread',str(O/'observe_requests.cpp'),str(O/'observer.a'),str(A/'verilated.o'),str(A/'verilated_threads.o'),str(A/'verilated_timing.o'),'-latomic','-o',str(O/'observe_requests')],check=True)
with (O/'observed_failure.log').open('w')as f:r=subprocess.run([str(O/'observe_requests'),f'+CFG={R}/production/cols/config.mem',f'+GOLD={R}/production/quarter.mem','+N=73','+W=70'],stdout=f,stderr=subprocess.STDOUT)
print('OBSERVED_REQUESTS',r.returncode)
