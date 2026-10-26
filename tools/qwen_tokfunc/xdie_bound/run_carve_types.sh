#!/bin/bash
# TOK-DS 10-26: per-type Verilator lint of a bound_carve_build.py WORK dir (run inside WORK, e.g. via ot-run --dir WORK).
#   run_carve_types.sh LIST P TAG    LIST = file of type names (one per line), P = parallel lints, TAG = result name
# Each type: verilator -f types/<T>.f under /usr/bin/time -v -> lint/<T>.{log,time,rc}; then lint_<TAG>.json with
# rc / %Error lines / warning count / peak RSS (GB) per type.  Exit 0 only if every type has rc 0 and no %Error.
set -u
LIST=$1; P=${2:-8}; TAG=${3:-lint}
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
mkdir -p lint
"$VL" --version > lint/verilator.version
one() {
  /usr/bin/time -v -o "lint/$1.time" "$VL" -f "types/$1.f" > "lint/$1.log" 2>&1
  echo $? > "lint/$1.rc"
}
export -f one; export VL
echo "start $(date) $(wc -l < "$LIST") types P=$P"
xargs -a "$LIST" -P "$P" -I{} bash -c 'one {}'
echo "done $(date)"
python3 - "$LIST" "$TAG" <<'EOF'
import json, re, sys
from pathlib import Path
res, bad = {}, 0
for t in Path(sys.argv[1]).read_text().split():
    log = Path(f"lint/{t}.log").read_text(errors="replace").splitlines()
    tm = Path(f"lint/{t}.time").read_text(errors="replace") if Path(f"lint/{t}.time").exists() else ""
    m = re.search(r"Maximum resident set size \(kbytes\): (\d+)", tm)
    w = re.search(r"Elapsed \(wall clock\) time.*: (\S+)", tm)
    errs = [l for l in log if l.startswith("%Error") and not l.startswith("%Error: Exiting")]
    rc = int(Path(f"lint/{t}.rc").read_text().strip() or 99)
    res[t] = dict(rc=rc, errors=len(errs), first_errors=errs[:10], warnings=sum(l.startswith("%Warning") for l in log),
                  peak_gb=round(int(m.group(1)) / 1048576, 2) if m else None, wall=w.group(1) if w else None)
    bad += bool(rc or errs)
Path(f"lint_{sys.argv[2]}.json").write_text(json.dumps(dict(schema="opentallas.tok_ds.carve_type_lint.v1",
    verilator=Path("lint/verilator.version").read_text().strip(), types=len(res), failing=bad, per_type=res), indent=1) + "\n")
print(f"types {len(res)} failing {bad} max_peak_gb {max((r['peak_gb'] or 0) for r in res.values())}")
sys.exit(1 if bad else 0)
EOF
