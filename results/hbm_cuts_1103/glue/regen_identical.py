"""DIE-HBM-61/CUTS: face_shell.emit_shell with in_stages unset re-emits the byte-identical shell of existing kits
(text rebuilt from each kit's face_shell.json and compared to its rtl/<module>__fshell.sv)."""
import glob, importlib.util, json, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('fs', sys.argv[1]); fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
kits = sorted(glob.glob(sys.argv[2]))
ok = bad = skip = 0
for jf in kits:
    kd = Path(jf).parent
    J = json.loads(Path(jf).read_text())
    sv = kd / 'rtl' / f"{J['module']}__fshell.sv"
    if not sv.is_file() or 'keep' not in J or J.get('mutant'):
        skip += 1; continue
    args = (J['module'], J['core'], J['params'], J['widths'], J['dirs'], J['keep'], set(J['passthrough']), J['clock'])
    kw = dict(mutant=None, scalars=set(J['scalars']), stages=J.get('out_extra_stages') or {},
              lockup=set((J.get('out_lockup') or {}).get('buses', [])), rst_relay=(J.get('reset_relay') or {}).get('resets', {}))
    t0 = fs.emit_shell(*args, **kw)
    t1 = fs.emit_shell(*args, **kw, in_stages=None)
    t2 = fs.emit_shell(*args, **kw, in_stages={})
    if t0 == t1 == t2 == sv.read_text():
        ok += 1
    else:
        bad += 1; print('DIFF', kd)
    if ok + bad >= int(sys.argv[3]):
        break
print(f"REGEN_IDENTICAL ok={ok} bad={bad} skipped={skip}")
sys.exit(1 if bad or ok == 0 else 0)
