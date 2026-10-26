from pathlib import Path
import subprocess,sys,json,argparse,hashlib
r=Path(__file__).resolve().parents[3];ap=argparse.ArgumentParser();ap.add_argument('out',type=Path);out=ap.parse_args().out.resolve();out.mkdir(parents=True,exist_ok=True)
def blob(p):return subprocess.check_output(['git','-C',str(r),'show','HEAD:'+p])
paths=['rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_cal_seq.sv','rtl/qwen_split/qfd_sys_face_ovl.sv','rtl/qwen_split/qfd_sys_face_record_port.sv','rtl/qwen_split/mu/qfd_mu_head_context_tx.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_static.sv','rtl/qwen_sys/d2d_static_20261015/qfd_d2d_cal_seq_ovl_rope.sv','rtl/qwen_sys/d2d_static_20261015/ot_qwen_d2d_ovl_seq.sv','rtl/qwen_sys/context_transport_20261014/qkd_context_records.sv','rtl/qwen_sys/program_receiver_20261014/qkd_program_commit.sv','physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v']
svh=subprocess.check_output(['git','-C',str(r),'ls-tree','-r','--name-only','HEAD','rtl/qwen_sys/d2d_static_20261015'],text=True).splitlines()
for p in paths+[p for p in svh if p.endswith('.svh')]:
 f=out/p;f.parent.mkdir(parents=True,exist_ok=True);b=blob(p)
 if p==paths[-1]:b=b.replace(b'parameter string ',b'parameter ')
 f.write_bytes(b)
p='rtl/qwen_split/qfd_sys_face_ovl_fault1.sv';(out/p).write_bytes((r/p).read_bytes())
sys.path.insert(0,str(r/'tools'))
from qwen_split.source_pin_plan import rtl_ports
ports=rtl_ports(r/p,'qfd_sys_face_ovl_fault1')
lines=['`timescale 1ns/1ps','module tb;reg clk=0;always #0.5 clk=~clk;integer ticks=0,checks=0;reg expected=0;']
for name,(w,d) in ports.items():
 rg=f'[{w-1}:0]'if w>1 else''
 if d=='input':lines.append(f'reg {rg} {name}=0;')
 else:lines.append(f'wire {rg} n_{name},b_{name};')
lines.append('always @* ck=clk;')
for mod,inst,pfx in [('qfd_sys_face_ovl_fault1','dut','n_'),('qfd_sys_face_ovl','base','b_')]:
 conn=', '.join(f'.{p}({p if d=="input"else pfx+p})'for p,(w,d)in ports.items()if inst=='dut'or p!='obs_fault')
 lines.append(f'{mod} #(.MU(1),.MU_HEAD(1),.ROPE(0)) {inst}({conn});')
 # Isolate the existing fault fold. No alternate fault, boot programme or token execution is being qualified here.
 for signal in ['boot_fault','prog_fault','cal_fault','emb_fault','prov_fault_q','rp_fault','head_tx_fault','head_mux_fault','armed_fault','go_fault','mu_hc_fault']:
  lines.append(f'initial force {inst}.{signal}=0;')
 for signal in ['boot_done','rp_program_ready','ev_res']:
  lines.append(f'initial force {inst}.{signal}=1;')
lines.append('''task tick;reg oldexp,active;begin @(negedge clk);oldexp=expected;active=dut.rst_obs;
if(!active)expected=0;else if(obs_fault)expected=1;
@(posedge clk);#0.01;ticks=ticks+1;
if(n_fault!==expected)$fatal(1,"actual sticky root capture edge");
if(dut.rst_obs!==dut.rst_emb)$fatal(1,"parallel regional reset age");
if(active)begin
 if(n_tt_fab!==oldexp || n_result_cause[0]!==oldexp || n_admit_ready!==!oldexp)$fatal(1,"real face-fault consumers");
 if(b_fault!==0||b_tt_fab!==0||b_result_cause[0]!==0||b_admit_ready!==1)$fatal(1,"baseline consumer cut");
 checks=checks+1;
end
end endtask
initial begin
rst_n=0;seq_dc[50]=1;repeat(4)tick();rst_n=1;repeat(6)tick();
obs_fault=1;tick();obs_fault=0;repeat(4)tick();
// Link/host calendar epoch events do not clear the fault state.
fwd_epoch=1;tick();fwd_epoch=0;repeat(4)tick();
if(n_fault!==1)$fatal(1,"epoch event must not clear sticky root");
rst_n=0;#0.01;expected=0;if(n_fault!==0)$fatal(1,"regional asynchronous reset clears root");repeat(4)tick();
obs_fault=1;repeat(2)tick();obs_fault=0;rst_n=1;repeat(6)tick();
if(n_fault!==0)$fatal(1,"fault during reset ignored");obs_fault=1;tick();obs_fault=0;repeat(3)tick();
$display("FAULT_FACE_SOURCE_CUT_PASS ticks=%0d checks=%0d capture1/resetonly/realconsumers; otherfault+boot/eventsources explicitly cut",ticks,checks);$finish;end
endmodule
''')
(out/'tb.sv').write_text('\n'.join(lines))
s=(out/p).read_text();assert s.count('else if (obs_fault) obs_fault_q')==1
(out/'wrong_omit_capture.sv').write_text(s.replace('else if (obs_fault) obs_fault_q','else if (1\'b0) obs_fault_q'))
(out/'common.f').write_text('\n'.join(paths)+'\n')
# Exact historical compiler fixture, never current coherent73 programme evidence.
fixture_commit='e18e3d597ec09e6841b2e859bfd8800761d4e193'
for p in ('rtl/qwen_sys/d2d_static_20261015/ovl_release_rope/ovl_release_img.svh',
          'rtl/qwen_sys/d2d_static_20261015/d2d_cal_image_mu_ew1627_r16_rope.svh'):
 f=out/p;f.parent.mkdir(parents=True,exist_ok=True)
 f.write_bytes(subprocess.check_output(['git','-C',str(r),'show',fixture_commit+':'+p]))
(out/'FIXTURE_SCOPE.json').write_text(json.dumps(dict(legacy_parse_fixture=fixture_commit,
 scope='ISOLATED FAULT CAPTURE ONLY; forced otherfault+boot/events; no calendar/GEN/transport/sole73 qualification'),indent=2)+'\n')
(out/'source_manifest.json').write_text(json.dumps({str(p.relative_to(out)):hashlib.sha256(p.read_bytes()).hexdigest() for p in out.rglob('*')if p.is_file() and p.suffix in ('.sv','.v','.svh','.f')},indent=2)+'\n')
