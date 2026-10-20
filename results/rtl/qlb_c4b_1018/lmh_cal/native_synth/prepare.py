from pathlib import Path
s=Path('tools/run_abi3_physical.py').read_text()
needle='    shutil.copy2(mapped, raw_mapped)'
assert s.count(needle)==1
s=s.replace(needle,needle+'\n    print("SEGCAL_SYNTH_ONLY_MAPPED", mapped, flush=True)\n    raise SystemExit(0) # audit-only: stop before any floorplan or layout step')
Path('tools/run_abi3_segcal_synth.py').write_text(s)
