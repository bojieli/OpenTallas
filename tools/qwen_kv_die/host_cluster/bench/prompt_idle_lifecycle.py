#!/usr/bin/env python3
"""Actual four-context idle lifecycle; source variants stay local to the bench."""
from pathlib import Path
import subprocess
import sys

out = Path(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else 'exact'
assert mode in ('exact', 'old_idle', 'omit_boundary', 'omit_context', 'omit_event')
out.mkdir(parents=True, exist_ok=True)
root = Path('rtl/qwen_sys/host_cluster_20261017')
source = root / 'prompt_safe3'
pb = (source / 'ot_host_if_pb2_observed_ps3.sv').read_text()
wrapper = (source / 'qkd_host_if_pins_observed_ps3.sv').read_text()
if mode == 'old_idle':
    pb = pb.replace('host_idle<=idle_quiescent;', 'host_idle<=!inflight&&i_st==I_IDLE&&d_st==D_IDLE&&ev_n==0&&!m_arvalid&&!m_rready&&!m_awvalid&&!m_wvalid&&!m_bready&&sq_head==sq_tail;')
elif mode == 'omit_boundary':
    wrapper = wrapper.replace('core_idle && !(|channel_busy)', 'core_idle')
elif mode == 'omit_event':
    pb = pb.replace('ev_n==0 && !ep_v', "1'b1 && !ep_v")
elif mode == 'omit_context':
    pb = pb.replace('!(|idle_context_busy) && !inflight', "1'b1 && !inflight")
(out / 'pb2.sv').write_text(pb)
(out / 'wrapper.sv').write_text(wrapper)
files = Path('rtl/test/mu_qwen_1018/lists/tb_qkd_host_mu_out.f').read_text()
files = files.replace('rtl/test/mu_qwen_1018/tb_qkd_host_mu_out.sv', 'rtl/test/qwen_host/tb_hkv_mu4_idle.sv')
files = files.replace('rtl/qwen_sys/host_integrated_20261014/qkd_host_fullcontrol_observed.sv', str(source / 'qkd_host_fullcontrol_observed_ps3_rr.sv'))
files = files.replace('rtl/qwen_sys/host_integrated_20261014/qkd_host_if_pins_observed.sv', str(out / 'wrapper.sv') + '\n' + str(source / 'qkd_host_if_pins_observed_ps3_rr.sv'))
files = files.replace('rtl/qwen_sys/host_integrated_20261014/ot_host_if_pb2_observed.sv', str(out / 'pb2.sv'))
files += '\n' + '\n'.join(map(str, [source / 'qkd_host_pin_channel_ps3.sv', root / 'prompt_safe/ot_hkv_prompt_mem.sv', root / 'prompt_pd/ot_hkv_cnt_la.sv', Path('physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v')])) + '\n'
files += '\n'.join(map(str, [Path('rtl/lib/ot_rst_relay.sv'), root / 'prompt_rr/qkd_host_ctl_service_pins_rr.sv', root / 'prompt_rr/qkd_host_csr_service_pins_rr.sv'])) + '\n'
(out / 'sources.f').write_text(files)
with (out / 'build.log').open('w') as f:
    subprocess.run(['verilator', '--binary', '--timing', '-j', '4', '-Wno-fatal', '-Wno-lint', '-Wno-style', '--top-module', 'tb_hkv_mu4_idle', '-Mdir', str(out / 'obj'), '-f', str(out / 'sources.f')], stdout=f, stderr=subprocess.STDOUT, check=True)
with (out / 'run.log').open('w') as f:
    run = subprocess.run([str(out / 'obj/Vtb_hkv_mu4_idle')], stdout=f, stderr=subprocess.STDOUT)
log = (out / 'run.log').read_text()
print(log, flush=True)
assert (run.returncode == 0 and 'IDLE_LIFECYCLE PASS' in log) if mode == 'exact' else (run.returncode != 0 and 'IDLE_FAIL' in log)
