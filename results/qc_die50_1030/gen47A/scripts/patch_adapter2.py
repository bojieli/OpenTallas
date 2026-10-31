"""DIE-QC-50/gen47A patch 2 (diagnostic only, env OT_G47A_E1DIAG=1): die_clock_128.fixed_wires keeps its no_clock_track
rows but RETURNS the wires (failing nets keep their attempted geometry) so the E1-style fixed_wires.json exists for the
range-window backbone planner (dqc37_backbone.py needs E1 router tracks). Status is relabelled; never a qualification."""
import sys
p=sys.argv[1];s=open(p).read()
if '_G47A_E1DIAG' in s: print('already'); sys.exit(0)
anchor="import die_infra as DI\n"
add='''import die_infra as DI
import os as _os0
_G47A_E1DIAG_ERRS = []
if _os0.environ.get('OT_G47A_E1DIAG') == '1':
    _src = Path(C128.__file__).read_text()
    _old = "    if errs:\\n        raise PlanError(errs)\\n    if port_on_trunk:"
    assert _src.count(_old) == 1, 'die_clock_128 pin-stack PlanError anchor changed'
    _src = _src.replace(_old, "    if errs:\\n        _G47A_E1DIAG_SINK.extend(errs)\\n    if port_on_trunk:")
    C128.__dict__['_G47A_E1DIAG_SINK'] = _G47A_E1DIAG_ERRS
    exec(compile(_src, C128.__file__, 'exec'), C128.__dict__)
    print('G47A_E1DIAG active: no_clock_track rows recorded, wires returned', flush=True)
'''
assert s.count(anchor)==1; s=s.replace(anchor,add)
old="    (out/'fixed_wires.json').write_text(json.dumps(wires)+'\\n')"
assert s.count(old)>=1
s=s.replace(old,old+"\n    if _G47A_E1DIAG_ERRS:(out/'e1diag_errors.json').write_text(json.dumps(_G47A_E1DIAG_ERRS)+'\\n');print('G47A_E1DIAG errors',len(_G47A_E1DIAG_ERRS),flush=True)",1)
open(p,'w').write(s);print('patched2')
