from pathlib import Path
import re,hashlib,json,subprocess,shutil
D=Path('/srv/opentallas-scratch/claude/hbm-native-record23-clock-1019');A=D/'obj_arithmetic_clock';O=Path.cwd();R=Path('/srv/opentallas-scratch/claude/hbm-record23-repair-1019')
src=(A/'Vtb___024root__0.cpp').read_text()
# Change only the testbench final acceptance coroutine. Keep its first assertions.
finish='    VL_FINISH_MT("native_record23_tb.sv", 112, "");'
assert src.count(finish)==1
wait=lambda c: f'''    while ({c}) {{
        Vtb___024root____VbeforeTrig_ha8f1a4ce__0(vlSelf, "@(negedge tb.stream)");
        co_await vlSelfRef.__VtrigSched_ha8f1a4ce__0.trigger(0U, nullptr, "@(negedge tb.stream)", "mu_record_tb.sv", 1);
    }}\n'''
waitq=lambda c:f'''    while ({c}) {{
        Vtb___024root____VbeforeTrig_hadc8cf6d__0(vlSelf, "@(negedge tb.clk)");
        co_await vlSelfRef.__VtrigSched_hadc8cf6d__0.trigger(0U, nullptr, "@(negedge tb.clk)", "mu_record_tb.sv", 1);
    }}\n'''
p='''    VL_WRITEF_NX("REQUEST0_ACCEPT stream3800 original32words unchanged\\n",0);
    vlSelfRef.tb__DOT__n=0; vlSelfRef.tb__DOT__first=0xffffffffU;
    vlSelfRef.tb__DOT__fills=0; vlSelfRef.tb__DOT__checked=0;
'''
for b in range(2):
 pref=f'vlSelfRef.tb__DOT__B__BRA__{b}__KET____DOT__'
 p+=f'    {pref}seen=0;\n    {{ auto tmp={pref}expected[0]; {pref}expected[0]={pref}expected[1]; {pref}expected[1]=tmp; }}\n'
# R1 data: exact existing record23 operands, permute the two input sectors
# within each bank. Drive host producer pins only; no internal memory writes.
payloads=[['3ea0e35f3e8f2d283e0b309c3e1874323e087e3c3dcdb42f3e22152f3e471b6a','3df69e453e3068863dd706293d91d4593ec18c363f0f5f843e659ae23ec05ff4'],['3de8c4703eb80cb23e76cd7e3dc445983ea82b4c3e0454cf3e42ae3e3e2caef6','3d85f0423e1c163b3e07d37a3ddb711a3e8a28463e8c8e853dfab5ef3e4f398a']]
def hostwrites(k,clear=False):
 out=''
 for b in range(2):
  word=0 if clear else (1<<280)|((264+b+8*k)<<264)|(int(payloads[b][1-k],16)<<8)|255
  for w in range(9):out+=f'    vlSelfRef.tb__DOT__B__BRA__{b}__KET____DOT__hostw[{w}]=0x{(word>>(32*w))&0xffffffff:08x}U;\n'
 return out
p+=wait('vlSelfRef.tb__DOT__st < 3805')+hostwrites(0)+wait('vlSelfRef.tb__DOT__st < 3806')+hostwrites(0,True)
p+=wait('vlSelfRef.tb__DOT__st < 3818')+hostwrites(1)+wait('vlSelfRef.tb__DOT__st < 3819')+hostwrites(0,True)
p+=wait('vlSelfRef.tb__DOT__st < 3900')+'    vlSelfRef.tb__DOT__lv=1;\n'+wait('vlSelfRef.tb__DOT__st < 3901')+'    vlSelfRef.tb__DOT__lv=0;\n'
p+=waitq('vlSelfRef.tb__DOT__qt < 2965')+'    vlSelfRef.tb__DOT__start=1;\n'+waitq('vlSelfRef.tb__DOT__qt < 2966')+'    vlSelfRef.tb__DOT__start=0;\n'
for k,edge in enumerate([4150,4170]):
 p+=wait(f'vlSelfRef.tb__DOT__st < {edge}')
 for b in range(2):p+=f'    vlSelfRef.tb__DOT__B__BRA__{b}__KET____DOT__hostr={65536+280+b+8*k}U;\n'
 p+=wait(f'vlSelfRef.tb__DOT__st < {edge+1}')
 for b in range(2):p+=f'    vlSelfRef.tb__DOT__B__BRA__{b}__KET____DOT__hostr=0;\n'
p+=wait('vlSelfRef.tb__DOT__st < 4200')
# Reuse the identical final correctness/fault checks, with fresh counters.
check=src[src.index('    VL_WRITEF_NX("RESULT commands='):src.index('    VL_WRITEF_NX("NATIVE_RECORD23 PASS')]
p+=check+'    VL_WRITEF_NX("SERIAL_REQUESTS2 PASS contexts=1 requests=2 start_offset_serial=300 acceptance_stream=3800,4200\\n",0);\n'+finish
src=src.replace(finish,p)
assert src.count('tb__DOT__unnamedblk1_1__DOT____Vrepeat0 = 0x00000fa0U;')==1
src=src.replace('tb__DOT__unnamedblk1_1__DOT____Vrepeat0 = 0x00000fa0U;','tb__DOT__unnamedblk1_1__DOT____Vrepeat0 = 4400U;').replace('incomplete after4000 stream edges','incomplete after4400 stream edges')
(O/'Vtb___024root__0.cpp').write_text(src)
src26=(A/'Vtb___024root__26.cpp').read_text()
a='VL_GTS_III(32, 0x000000c8U, vlSelfRef.tb__DOT__st)';b='VL_LTES_III(32, 0x00000e9cU, vlSelfRef.tb__DOT__st)'
assert src26.count(a)==1 and src26.count(b)==1
src26=src26.replace(a,'(vlSelfRef.tb__DOT__st < 200 || (vlSelfRef.tb__DOT__st >= 3800 && vlSelfRef.tb__DOT__st < 3900))').replace(b,'((vlSelfRef.tb__DOT__st >= 3740 && vlSelfRef.tb__DOT__st < 3800) || vlSelfRef.tb__DOT__st >= 4140)')
(O/'Vtb___024root__26.cpp').write_text(src26)
vr=Path('/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator/include')
cmd=['g++','-std=c++20','-O0','-DVL_TIME_CONTEXT','-I'+str(A),'-I'+str(vr),'-I'+str(vr/'vltstd'),'-pthread']
# Preserve aggregate membership; only two generated testbench source includes differ.
for group,changed in [(0,'Vtb___024root__0.cpp'),(1,'Vtb___024root__26.cpp')]:
 name=f'Vtb_vm_classes_{group}'
 original=(A/(name+'.cpp')).read_text()
 assert original.count('"'+changed+'"')==1
 (O/(name+'.cpp')).write_text(original.replace('"'+changed+'"','"'+str(O/changed)+'"'))
 subprocess.run(cmd+['-c',str(O/(name+'.cpp')),'-o',str(O/(name+'.o'))],check=True)
shutil.copy2(A/'Vtb__ALL.a',O/'Vtb__ALL.a')
subprocess.run(['ar','r',str(O/'Vtb__ALL.a'),str(O/'Vtb_vm_classes_0.o'),str(O/'Vtb_vm_classes_1.o')],check=True)
subprocess.run(cmd+[str(O/'Vtb__ALL.a'),str(A/'verilated.o'),str(A/'verilated_threads.o'),str(A/'verilated_timing.o'),'-latomic','-o',str(O/'two_requests')],check=True)
shutil.copy2(R/'calendar.mem',O/'calendar.mem')
with (O/'positive.log').open('w') as f:r=subprocess.run([str(O/'two_requests'),f'+CFG={R}/production/cols/config.mem',f'+GOLD={R}/production/quarter.mem','+N=73','+W=70'],stdout=f,stderr=subprocess.STDOUT)
(O/'exit.txt').write_text(str(r.returncode));print('TWO_REQUEST_REPLAY',r.returncode,flush=True)
files=[A/'Vtb__ALL.a',D/'native_record23_tb.sv',O/'Vtb___024root__0.cpp',O/'Vtb___024root__26.cpp',O/'Vtb__ALL.a',O/'two_requests',O/'positive.log']
(O/'hashes.json').write_text(json.dumps({str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files},indent=2))
raise SystemExit(r.returncode)
