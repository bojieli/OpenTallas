"""Stage every pinned byte before activation; never restart on an incomplete activation."""
import pathlib, subprocess, hashlib, json, datetime, os
revision='18b8c357d'
source=pathlib.Path('/home/ubuntu/wt/codex-root-takeover-1019')
target=pathlib.Path('/home/ubuntu/wt-claude-closure-daemon-1010')
paths=['physical/common_flow/'+x for x in ['clock_family.tcl','io_ref_routed.sdc','ot_pin_regs.tcl','ot_rst_copies.py']]+['tools/closure_loop/'+x for x in ['ck_insertion.py','helper_overlay.py']]+['tools/orfs_hold_mm.tcl','tools/qwen_kv_die/kv_fwd_lanes.py','tools/qwen_layerbench/netlist_relay_stages.py','tools/qwen_split/land_lag_sim.py']+['tools/ref_tile/'+x for x in ['clock_entry_constraints.py','layout_dump.tcl','lint_receipt.py','measured_band_fill.py','pre_route_gate.py','ref_tile.py','single_clock_contract.py','source_binding.py']]+['tools/textbook_lint.py']
def inactive():
    state=subprocess.run(['systemctl','--user','is-active','closure-loop.service'],capture_output=True,text=True).stdout.strip()
    if state!='inactive':raise SystemExit('refuse while service '+state)
inactive()
last=pathlib.Path('/home/ubuntu/.local/state/closure_loop/daemon.log').read_text()[-15000:]
if last.rfind('DRAINED')<last.rfind('closure-loop daemon up'):raise SystemExit('missing latest safe drain')
back=pathlib.Path('/home/ubuntu/.local/state/closure_loop/daemon_backups')/('root-codex-guarded-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
back.mkdir(parents=True)
rows=[]
for rel in paths:
    b=target/rel;old=b.read_bytes() if b.exists() else None
    new=subprocess.check_output(['git','-C',str(source),'show',revision+':'+rel])
    staged=back/'staged'/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(new)
    assert staged.read_bytes()==new
    if old is not None:
        q=back/'before'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(old)
    b.parent.mkdir(parents=True,exist_ok=True)
    rows.append(dict(path=rel,before=hashlib.sha256(old).hexdigest() if old else None,after=hashlib.sha256(new).hexdigest()))
manifest=dict(source_commit=subprocess.check_output(['git','-C',str(source),'rev-parse',revision],text=True).strip(),files=rows,status='staged',prior_partial_backup='root-codex-guarded-20261019-101600')
(back/'sync.json').write_text(json.dumps(manifest,indent=2)+'\n')
assert len(rows)==19 and len({r['path'] for r in rows})==19
for row in rows:
    staged=back/'staged'/row['path'];assert hashlib.sha256(staged.read_bytes()).hexdigest()==row['after']
    b=target/row['path'];tmp=b.with_name(b.name+'.codex-sync-tmp');tmp.write_bytes(staged.read_bytes())
    assert hashlib.sha256(tmp.read_bytes()).hexdigest()==row['after']
inactive()
for row in rows:
    b=target/row['path'];os.replace(b.with_name(b.name+'.codex-sync-tmp'),b)
for row in rows:
    assert hashlib.sha256((target/row['path']).read_bytes()).hexdigest()==row['after'],row['path']
inactive();manifest['status']='verified';(back/'sync.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(back)
