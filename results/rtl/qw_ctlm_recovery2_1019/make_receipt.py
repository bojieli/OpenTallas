from pathlib import Path
import hashlib,json,re,shlex
root=Path('/srv/opentallas-scratch/claude/qw-ctlm-recovery2-1019')
old=Path('/srv/opentallas-scratch/claude/qw-ctlm-safe2-bench/src')
bench=Path('rtl/qwen_dv/lp/qfd_tt_ctlm_dv_lpf_lp_bench.sh')
sources=shlex.split(re.search(r'SRCS="([^"\n]+)"',(old/bench).read_text()).group(1))
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
for name in sources:
 if name.endswith('tb_qfd_tt_ctlm_dv_lpf_lp.sv'):continue
 a=digest(old/name);b=digest(root/'src'/name)
 checks.append(dict(path=name,original_sha256=a,observed_sha256=b,identical=a==b))
receipt=dict(source_commit='9ce75362f',baseline_snapshot='/srv/opentallas-scratch/claude/qw-ctlm-safe2-bench/src',dut_files=checks,dut_files_changed=sum(not x['identical'] for x in checks),
modified_benches={name:digest(root/name) for name in ['src/rtl/qwen_dv/lp/tb_qfd_tt_ctlm_dv_lpf_lp.sv','first_src/rtl/qwen_dv/lp/tb_qfd_tt_ctlm_dv_lpf_lp.sv','tb_ring_phase.sv']},
limitations=['same-source observation only; no RTL adoption','arbitrary-initial-state full-source startup assertion fails','no stopped-clock or native-clock qualification','single-source-clock component first-use schedule is not a full-token measurement'])
(root/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
