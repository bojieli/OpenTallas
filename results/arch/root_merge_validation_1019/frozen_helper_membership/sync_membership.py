"""Stage every pinned byte before activation; never restart on an incomplete activation."""
import pathlib, subprocess, hashlib, json, datetime, os
revision='6213f9e9e'
source=pathlib.Path('/home/ubuntu/wt/codex-root-takeover-1019')
target=pathlib.Path('/home/ubuntu/wt-claude-closure-daemon-1010')
paths=['physical/common_flow/clock_family.tcl', 'physical/common_flow/io_ref_routed.sdc', 'physical/common_flow/ot_pin_regs.tcl', 'physical/common_flow/ot_rst_copies.py', 'tools/closure_loop/ck_insertion.py', 'tools/closure_loop/closure_loop.py', 'tools/closure_loop/helper_overlay.py', 'tools/die_bind_unread_manifest.py', 'tools/die_port_bind.py', 'tools/orfs_hold_mm.tcl', 'tools/qwen_kv_die/kv_fwd_lanes.py', 'tools/qwen_layerbench/netlist_relay_stages.py', 'tools/qwen_split/land_lag_sim.py', 'tools/ref_tile/clock_entry_constraints.py', 'tools/ref_tile/layout_dump.tcl', 'tools/ref_tile/lint_receipt.py', 'tools/ref_tile/measured_band_fill.py', 'tools/ref_tile/pre_route_gate.py', 'tools/ref_tile/ref_tile.py', 'tools/ref_tile/single_clock_contract.py', 'tools/ref_tile/source_binding.py', 'tools/textbook_lint.py']
def inactive():
    state=subprocess.run(['systemctl','--user','is-active','closure-loop.service'],capture_output=True,text=True).stdout.strip()
    if state!='inactive':raise SystemExit('refuse while service '+state)
inactive()
last=pathlib.Path('/home/ubuntu/.local/state/closure_loop/daemon.log').read_text()[-15000:]
if last.rfind('DRAINED')<last.rfind('closure-loop daemon up'):raise SystemExit('missing latest safe drain')
back=pathlib.Path('/home/ubuntu/.local/state/closure_loop/daemon_backups')/('root-codex-membership-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
back.mkdir(parents=True)
rows=[]
for rel in paths:
    b=target/rel;old=b.read_bytes() if b.exists() else None
    new=subprocess.check_output(['git','-C',str(source),'show',revision+':'+rel])
    mode=int(subprocess.check_output(['git','-C',str(source),'ls-tree',revision,'--',rel],text=True).split()[0],8)&0o777
    staged=back/'staged'/rel;staged.parent.mkdir(parents=True,exist_ok=True);staged.write_bytes(new);staged.chmod(mode)
    assert staged.read_bytes()==new
    if old is not None:
        q=back/'before'/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(old)
    b.parent.mkdir(parents=True,exist_ok=True)
    rows.append(dict(path=rel,mode=mode,before=hashlib.sha256(old).hexdigest() if old else None,after=hashlib.sha256(new).hexdigest()))
manifest=dict(source_commit=subprocess.check_output(['git','-C',str(source),'rev-parse',revision],text=True).strip(),files=rows,status='staged',prior_runtime_sync='root-codex-guarded-20261019-101721')
(back/'sync.json').write_text(json.dumps(manifest,indent=2)+'\n')
assert len(rows)==22 and len({r['path'] for r in rows})==22
for row in rows:
    staged=back/'staged'/row['path'];assert hashlib.sha256(staged.read_bytes()).hexdigest()==row['after']
    b=target/row['path'];tmp=b.with_name(b.name+'.codex-sync-tmp');tmp.write_bytes(staged.read_bytes());tmp.chmod(row['mode'])
    assert hashlib.sha256(tmp.read_bytes()).hexdigest()==row['after'] and (tmp.stat().st_mode&0o777)==row['mode']
inactive()
for row in rows:
    b=target/row['path'];os.replace(b.with_name(b.name+'.codex-sync-tmp'),b)
for row in rows:
    assert hashlib.sha256((target/row['path']).read_bytes()).hexdigest()==row['after'] and ((target/row['path']).stat().st_mode&0o777)==row['mode'],row['path']
inactive();manifest['status']='verified';(back/'sync.json').write_text(json.dumps(manifest,indent=2)+'\n')
print(back)
