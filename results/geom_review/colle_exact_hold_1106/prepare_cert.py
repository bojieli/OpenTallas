from pathlib import Path
import sys,shutil,json,hashlib,importlib.util
r=Path('/srv/opentallas-scratch2/claude/codex-colle-exact-hold-1106');t=Path('/srv/opentallas-scratch2/claude/codex-bank128-wface/release_bh/tools/die_plan')
spec=importlib.util.spec_from_file_location('coll_form',t/'compact_coll_form.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
for side in sys.argv[1:]:
 assert side in ('e','w')
 s=r/side/'repair1';d=r/side/'cert_input1'
 clock_log=s/'exact_four_clock_check.log'
 assert clock_log.exists() and 'CLK_GEOM_DIFF PASS' in clock_log.read_text(), 'fresh exact-repair clock check incomplete'
 clock=json.load(open(s/'clk_geom_diff.json'));assert clock['verdict']=='PASS',clock
 final_odb=next((s/'run/results/asap7').glob('*/base/6_final.odb'))
 assert (s/'clk_geom_diff.json').stat().st_mtime>=final_odb.stat().st_mtime, 'stale copied clock receipt'
 assert hashlib.sha256((s/'ck0_pin.tcl').read_bytes()).hexdigest()==mod.CLOCK_PIN_SHA256
 d.mkdir()
 for p in s.iterdir():
  if p.is_file():shutil.copy2(p,d/p.name)
  elif p.name in ('rtl','macros','reset_contract'):shutil.copytree(p,d/p.name)
 for name in ('results','logs','reports'):
  for p in (s/'run'/name).rglob('*'):
   if not p.is_file():continue
   keep=(name=='results' and (p.name.startswith('6_final') or p.name=='1_synth.v')) or (name=='logs' and p.suffix=='.json') or (name=='reports' and any(x in p.name.lower() for x in ('drc','antenna')))
   if keep:
    q=d/p.relative_to(s);q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q)
 # Restore the exact original context after FF-only diagnostic initialization.
 original_base=next((r/side/"kit/run/results/asap7").glob("*/base"))
 cert_base=next((d/"run/results/asap7").glob("*/base"))
 shutil.copy2(original_base/"6_final.sdc",cert_base/"6_final.sdc")
 assert (cert_base/"6_final.sdc").read_bytes()==(original_base/"6_final.sdc").read_bytes()
 mod.declare_clock_pin(d)
 for name in ('pin_audit.py','native_pin_contract.py'):shutil.copy2(t/name,d/name)
 (d/'native_clock_contract_receipt.json').write_text(json.dumps({'authority':'released bh compact_coll_form.declare_clock_pin, DIE-S81-62','source':str(s),'clock_wire_or_pin_geometry_changed':False,'logical_plan_anchor_changed':False,'ck0_hook_sha256':mod.CLOCK_PIN_SHA256,'preserves_own_context':side},indent=2)+'\n')
 print('COLLE_CERT_PREPARED',side,d)
