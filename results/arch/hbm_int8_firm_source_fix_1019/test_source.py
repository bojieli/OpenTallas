"""Resource-free causal geometry and exact native implementation checks."""
import pathlib, sys, tempfile, runpy, contextlib, io, json
p = pathlib.Path(__file__).parent
out = pathlib.Path(tempfile.gettempdir())/'int8-firm-source-test.json'
sys.argv = [str(p/'finite_feasibility.py'), '/home/ubuntu/artifacts/hbm-int8-clone-eco-kit-1019/kit', str(out)]
with contextlib.redirect_stdout(io.StringIO()): ns = runpy.run_path(str(p/'finite_feasibility.py'))
overlap = ns['overlap_pairs']
assert overlap({'a':[0,0,162,270], 'b':[162,0,324,270]}) == []
assert len(overlap({'a':[0,0,432,270], 'b':[162,0,324,270]})) == 1
assert overlap({'a':[0,0,432,270], 'b':[162,270,324,540]}) == []
src = (p/'vendor/dbInst.cpp').read_text()
ori = src[src.index('void dbInst::setOrient('):src.index('dbPlacementStatus dbInst::getPlacementStatus')]
assert ori.index('if (orient == getOrient())') < ori.index('if (getPlacementStatus().isFixed())')
swap = src[src.index('bool dbInst::swapMaster('):src.index('void dbInst::setPinAccessIdx')]
assert '_dbInst::setInstBBox(inst);' in swap
assert 'setOrient(' not in swap and 'setOrigin(' not in swap and 'setPlacementStatus(' not in swap
r = json.loads(out.read_text())
assert r['baseline_overlap_pairs'] == 0 and r['preserved_origin_orientation_growth_overlap_pairs'] == 265
out.unlink()
print('SOURCE_CHECKS_PASS: native same-orient no-op precedes FIRM refusal; swap keeps transform/status; adjacency clean; growth causal overlap; separate row clean; full frozen growth 265 refusals')
