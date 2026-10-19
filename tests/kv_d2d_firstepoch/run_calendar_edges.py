#!/usr/bin/env python3
"""Verification-only copies of the exact private calendar. Run on fleet only."""
import hashlib,json,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[2]
out=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/tmp/calendar_edges_results');out.mkdir(parents=True,exist_ok=True)
src=root/'rtl/qwen_sys/d2d_static_20261015/firstepoch_private/ot_qwen_d2d_cal_sf_fe.sv'
bench=root/'tests/kv_d2d_firstepoch/tb_calendar_edges.sv'
source=src.read_text()
mutations={
 'allow_w_plus_1': [(' && settled &&',' &&'),(' && !cfg_recent &&',' &&')],
 'emitted_valid_credit': [('if (cfg_we && !first_consumed && !bad_write) begin','if (cfg_valid && !first_consumed && !bad_write) begin'),('if (write_entry) seen[','if (!cfg_addr[AW]) seen['),('if (write_base) base_seen<=1;', 'if (cfg_addr[AW]) base_seen<=1;')],
 'emitted_credit': [('if (cfg_we && !first_consumed && !bad_write) begin','if (cfg_we) begin'),('if (write_entry) seen[','if (!cfg_addr[AW]) seen[')],
 'omit_data_compare':[('consumed_data == expected_data',"1'b1")],
 'omit_base_compare':[('cfg_base_c == EXPECTED_BOOT_BASE;',"1'b1;"),(' && (base_copies_ok === 1\'b1)','')],
 'reset_invalidation':[('seen<=0; base_seen<=0; installed_epoch<=0; epoch_valid<=0;', 'installed_epoch<=0;')],
 'clear_poison_on_upload':[('if (bad_write || pair_poison || fault || (any_start && !start_allowed)) poisoned<=1;', 'if (cfg_we && poisoned) poisoned<=0; else if (bad_write || pair_poison || fault || (any_start && !start_allowed)) poisoned<=1;')],
 'queued_retry':[
  ("(start_allowed ? start_c : 4'b0)","(start_allowed ? start_c : ((&seen) && base_seen && settled && poisoned ? 4'b1111 : 4'b0))"),
  ('(poisoned || fault || bad_write || pair_poison || reload || (any_start && !start_allowed))','(bad_write || pair_poison || reload || (any_start && !start_allowed))')],
 'output_only_mask':[('(start_allowed ? start_c : 4\'b0)', 'start_c'),('wire [3:0] effective_halt = halt_c | {4{ENABLE_FIRST_EPOCH_GUARD != 0 &&\n               (poisoned || fault || bad_write || pair_poison || reload || (any_start && !start_allowed))}};', 'wire [3:0] effective_halt = halt_c;')],
 'reload_invalidation':[('if (reload) begin seen<=0; base_seen<=0; epoch_valid<=0; settled<=0; first_consumed<=0; end','if (reload) begin end')],
}
manifest={'sources':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [src,bench,pathlib.Path(__file__)]},'mutations':mutations,'tool':'iverilog -g2012; vvp','scope':'4-state functional component; no native/physical qualification'}
(out/'precompile_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
results=[]
for name,edits in [('baseline',[])]+list(mutations.items()):
 text=source
 for before,after in edits:
  if text.count(before)!=1:raise RuntimeError(f'{name}: replacement count {text.count(before)}: {before}')
  text=text.replace(before,after)
 case=out/name;case.mkdir(exist_ok=True);copy=case/'calendar.sv';copy.write_text(text)
 build=subprocess.run(['iverilog','-g2012','-s','tb_calendar_edges','-o',str(case/'sim'),str(copy),str(bench)],capture_output=True,text=True)
 (case/'compile.log').write_text(build.stdout+build.stderr)
 if build.returncode:raise RuntimeError(f'{name} compile failed')
 run=subprocess.run(['vvp',str(case/'sim')],capture_output=True,text=True)
 (case/'run.log').write_text(run.stdout+run.stderr)
 verdict=run.returncode==0 and 'CALENDAR_EDGES_PASS' in run.stdout if name=='baseline' else run.returncode!=0 and 'ASSERT_FAIL ' in run.stdout
 results.append({'name':name,'rc':run.returncode,'expected_verdict':verdict,'source_sha256':hashlib.sha256(copy.read_bytes()).hexdigest(),'witness':[x for x in run.stdout.splitlines() if 'ASSERT_FAIL' in x or 'CALENDAR_EDGES_PASS' in x]})
 (out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
 print(json.dumps(results[-1]),flush=True)
 if name=='baseline' and not verdict:sys.exit(1)
sys.exit(0 if all(r['expected_verdict'] for r in results) else 1)
