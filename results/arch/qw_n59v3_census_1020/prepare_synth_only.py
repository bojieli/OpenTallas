from pathlib import Path
import sys
w=Path(sys.argv[1]);p=w/'tools/run_abi3_physical.py';s=p.read_text()
key='    # Phase 2: floorplan through routing and metadata.'
assert s.count(key)==1
(w/'tools/run_abi3_n59_synth_only.py').write_text(s.replace(key,'    print("N59_SYNTH_ONLY_COMPLETE mapped=" + str(mapped), flush=True)\n    raise SystemExit(0)\n'+key))
p=w/'tools/ref_tile/ref_route.sh'
(w/'tools/ref_tile/n59_synth_only.sh').write_text(p.read_text().replace('python3 tools/run_abi3_physical.py','python3 tools/run_abi3_n59_synth_only.py'))
