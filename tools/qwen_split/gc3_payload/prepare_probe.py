import json,subprocess,sys
from pathlib import Path
root=Path.cwd();sys.path.insert(0,str(root/'tools/qwen_split'));import sys_face_image as S
EVENTS='results/rtl/qwen_layer_tput_1018/compiled_L1/compute_programme/sys_face_events.json'
subprocess.run([sys.executable,'tools/qwen_split/gc3_payload/build.py','--ctlm','payload_complete2','--die-params','results/rtl/qw_gc3_payload_1020/actual_die_params.json','--events',EVENTS,'--fwd','results/rtl/qw_gc3_payload_1020/actual_fwd_lanes.json','--out','cfg_candidate'],check=True)
w=[int(x,16) for x in Path('cfg_candidate/program.memh').read_text().split()];w[1024]=0
rows,r=S.build(json.loads(Path(EVENTS).read_text()),w);o=Path('cfg_missing_base');o.mkdir(exist_ok=True)
(o/'sys_face_cfg.viamap.hex').write_text(S.viamap(rows));(o/'program.memh').write_text(''.join(f'{x:016x}\n' for x in w));(o/'program_metadata.svh').write_text(f"localparam [63:0] DIGEST=64'h{S.image_digest(w):016x};\n")
# Source-admission causal negative: a valid byte payload falsely claims an old R_HR.
wrong=Path('wrong_age_source');wrong.mkdir(exist_ok=True)
r=json.loads(Path('payload_complete2/ctlm_image.json').read_text());r['relay']['R_HR']-=1
(wrong/'ctlm_image.json').write_text(json.dumps(r))
(wrong/'program.memh').write_bytes(Path('payload_complete2/program.memh').read_bytes())
p=subprocess.run([sys.executable,'tools/qwen_split/gc3_payload/build.py','--ctlm',str(wrong),'--die-params','results/rtl/qw_gc3_payload_1020/actual_die_params.json','--events',EVENTS,'--fwd','results/rtl/qw_gc3_payload_1020/actual_fwd_lanes.json','--out','wrong_age_refused'],text=True,capture_output=True)
Path('source_wrong_age.log').write_text(p.stdout+p.stderr)
assert p.returncode!=0 and 'SOURCE_LANE_AGE_MISMATCH R_HR' in p.stdout+p.stderr
subprocess.run([sys.executable,'tools/qwen_split/gc3_payload/probe.py'],check=True)
