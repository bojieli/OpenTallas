#!/usr/bin/env python3
"""closure-loop checkpoint resume (coordinator 2026-10-06): patch a job's SOURCE SNAPSHOT copy of
tools/run_abi3_physical.py so that a re-run with the same --keep-workdir resumes the ORFS flow from the last completed
stage instead of redoing it.  Behaviour change only when OT_CL_RESUME=1:
  * constraint.sdc / config.mk / io_constraints.tcl are rewritten only if their content differs (keeps mtimes, so
    make sees the stage files as up to date);
  * the post-synthesis netlist normalisation (in-place rewrite of 1_2_yosys.v) is skipped when 1_2_yosys.raw.v exists
    (it already ran in the original run; re-running it would bump the mtime and re-trigger every later stage).
The original file is kept as run_abi3_physical.py.pre_resume.   resume_patch.py <src snapshot dir>"""
import shutil, sys
from pathlib import Path

f = Path(sys.argv[1]) / "tools/run_abi3_physical.py"
s = f.read_text()
if "_cl_write_if_changed" in s:
    print("already patched"); sys.exit(0)
reps = [
    ('(case / "constraint.sdc").write_text(', '_cl_write_if_changed(case / "constraint.sdc", '),
    ('(case / "config.mk").write_text(', '_cl_write_if_changed(case / "config.mk", '),
    ('    shutil.copy2(mapped, raw_mapped)\n',
     '    _cl_resumed = os.environ.get("OT_CL_RESUME") == "1" and raw_mapped.is_file()\n'
     '    if not _cl_resumed:\n        shutil.copy2(mapped, raw_mapped)\n'),
    ('    signed_stripped = normalise_netlist(mapped, mapped)\n',
     '    signed_stripped = "skipped (closure-loop checkpoint resume)" if _cl_resumed else normalise_netlist(mapped, mapped)\n'),
]
for a, b in reps:
    if s.count(a) != 1:
        sys.exit(f"resume_patch: pattern not found exactly once: {a!r}")
    s = s.replace(a, b)
s = s.replace('(case / "io_constraints.tcl").write_text(', '_cl_write_if_changed(case / "io_constraints.tcl", ')
helper = '''

def _cl_write_if_changed(path, text, encoding="utf-8"):
    """closure-loop resume: keep the file (and its mtime) when the content is unchanged"""
    if os.environ.get("OT_CL_RESUME") == "1" and path.is_file() and path.read_text(encoding=encoding) == text:
        return len(text)
    return path.write_text(text, encoding=encoding)

'''
i = s.index("\ndef run_pnr(")
s = s[:i] + helper + s[i:]
if "\nimport os" not in s:
    sys.exit("resume_patch: module does not import os")
shutil.copy2(f, f.with_suffix(".py.pre_resume"))
f.write_text(s)
print("patched", f)
