from pathlib import Path
import subprocess,re,json,hashlib
repo=Path('/home/ubuntu/OpenTallas');job=Path('/srv/opentallas-scratch2/claude/codex-qc-su-const-0920');sha='7a1172e83012ec48fa6faf9359c3ca8924cf31d6'
files=Path('/srv/opentallas-scratch2/claude/codex-qc-bind-1027/provider/files.f').read_text().splitlines();tree=subprocess.check_output(['git','-C',str(repo),'ls-tree','-r','--name-only',sha]).decode().splitlines();seen={};pending=list(files)
while pending:
 p=pending.pop()
 if p in seen:continue
 s=subprocess.check_output(['git','-C',str(repo),'show',sha+':'+p]);q=job/'inputs'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(s);seen[p]=hashlib.sha256(s).hexdigest()
 for inc in re.findall(rb'`include\s+"([^"]+)"',s):
  inc=inc.decode();rel=str(Path(p).parent/inc)
  if rel not in tree:
   cand=[z for z in tree if z.endswith('/'+inc)]
   if len(cand)!=1:raise ValueError((p,inc,cand))
   rel=cand[0]
  pending.append(rel)
job.mkdir(parents=True,exist_ok=True);(job/'source_receipt.json').write_text(json.dumps(dict(source_commit=sha,files=seen,top='qfd_qc_su_lane_w_l0',original_rtl_unchanged=True),indent=2)+'\n')
(job/'files.f').write_text('\n'.join(files)+'\n')
incs=sorted({str(Path('/work/inputs')/Path(p).parent) for p in seen})
lines=['yosys read_verilog -sv -defer -DSYNTHESIS '+' '.join('-I'+d for d in incs)+' '+' '.join('/work/inputs/'+p for p in files), 'yosys hierarchy -check -top qfd_qc_su_lane_w_l0','yosys proc','yosys flatten','yosys opt_expr','set ::env(DESIGN_NAME) qfd_qc_su_lane_w_l0','set ::env(OT_KEEP_PIN_REGS) 1','set ::env(RESULTS_DIR) /work/front','source /work/tools/ot_keep_regs.tcl','yosys write_json /work/front/pre.json','yosys write_rtlil /work/front/pre.il','yosys stat']
(job/'front.tcl').write_text('\n'.join(lines)+'\n');(job/'front').mkdir(exist_ok=True)
print('CONST_ACTUAL_SOURCES',len(seen),sha)
