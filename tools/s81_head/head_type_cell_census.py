#!/usr/bin/env python3
"""HEAD RE-FORM (l48rf) real synthesized std-cell census per partition type (DH58-RFRTL 11-03).

Reads ORFS synth results of generated kits (run/logs/asap7/*/base/1_synth.json + synth_stat.txt + config.mk +
gen_lint.json): std-cell count/area (hard cores and memory macros are macros, not std cells), macro area, the kit's
SYNTH_MEMORY_MAX_BITS / SYNTH_MOCK_LARGE_MEMORIES, and the gen-lint memory_bits verdict.  Picks, per type, the newest
kit (by 1_synth.json mtime) among the given kit dirs.  Verdict vs the RE-FORM bound (<= 150k std cells per block).

  head_type_cell_census.py --kits LIST.txt --out census.json [--tsv census.tsv]
  LIST.txt: one kit dir per line (the gen/<type> dir holding config.mk)
"""
import argparse, glob, json, os, re, sys
from pathlib import Path

BOUND = 150_000


def cfg(kd):
    out = {}
    try:
        txt = (kd / "config.mk").read_text().replace("\\\n", " ")
    except OSError:
        return out
    for m in re.finditer(r"^\s*export\s+(\w+)\s*[:?]?=\s*(.*)$", txt, re.M):
        out.setdefault(m.group(1), []).append(m.group(2).strip())
    return out


def one(kd):
    js = sorted(glob.glob(str(kd / "run/logs/asap7/*/base/1_synth.json")), key=os.path.getmtime)
    if not js:
        return None
    j = json.load(open(js[-1]))
    c = cfg(kd)
    stat = sorted(glob.glob(str(kd / "run/reports/asap7/*/base/synth_stat.txt")))
    macros = {}
    if stat:
        # top-level macro instances: rows "<n> <area> <n_local> <area_local> <cell>" for non-ASAP7 cells
        for ln in Path(stat[-1]).read_text(errors="replace").splitlines():
            m = re.match(r"\s*(\d+)\s+\S+\s+(\d+|-)\s+\S+\s+(\S+)\s*$", ln)
            if m and re.match(r"(ot_sram_1r|ot_rom_|.*_cv$|.*lep_pair$|.*kp4_dchn$)", m.group(3)):
                macros[m.group(3)] = max(macros.get(m.group(3), 0), int(m.group(1)))
    gl = {}
    try:
        gl = json.load(open(kd / "gen_lint.json")).get("checks", {}).get("memory_bits", {})
    except (OSError, ValueError):
        pass
    mems = []
    for mj in sorted(glob.glob(str(kd / "run/results/asap7/*/base/mem.json"))):
        try:
            for mod, md in json.load(open(mj)).get("modules", {}).items():
                for cn, cd in (md.get("cells") or {}).items():
                    if cd.get("type") == "$mem_v2":
                        pr = cd.get("parameters", {})
                        w, sz = int(pr.get("WIDTH", "0"), 2), int(pr.get("SIZE", "0"), 2)
                        mems.append(dict(module=mod, cell=cn, width=w, size=sz, bits=w * sz))
        except (OSError, ValueError):
            mems = None
    n = int(j.get("synth__design__instance__count__stdcell", 0))
    return dict(type=kd.name, kit=str(kd), synth_json=js[-1], synth_mtime=os.path.getmtime(js[-1]),
                design=(c.get("DESIGN_NAME") or [""])[-1],
                stdcells=n, stdcell_area_um2=float(j.get("synth__design__instance__area__stdcell", 0)),
                macro_area_um2=float(j.get("synth__design__instance__area__macros", 0)), macros=macros,
                synth_memory_max_bits=int((c.get("SYNTH_MEMORY_MAX_BITS") or ["4096"])[-1]),
                mock_large_memories=(c.get("SYNTH_MOCK_LARGE_MEMORIES") or ["0"])[-1] == "1",
                gen_lint_memory_bits=gl.get("verdict", "NOT_RUN"), gen_lint_memory_errors=gl.get("errors", []),
                memories=mems, memories_over_4096=None if mems is None else [m for m in mems if m["bits"] > 4096],
                over_bound=n > BOUND)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--kits", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tsv", type=Path)
    a = ap.parse_args(argv)
    best = {}
    for ln in a.kits.read_text().split():
        r = one(Path(ln))
        if r and (r["type"] not in best or r["synth_mtime"] > best[r["type"]]["synth_mtime"]):
            best[r["type"]] = r
    rows = [best[k] for k in sorted(best)]
    a.out.write_text(json.dumps(dict(schema="opentallas.head_type_cell_census.v1", bound=BOUND, types=rows), indent=1))
    if a.tsv:
        with open(a.tsv, "w") as f:
            f.write("type\tstdcells\tstdcell_area_um2\tmacro_area_um2\tmem_max_bits\tmems/over4096\tmem_lint\tover150k\tmacros\tkit\n")
            for r in rows:
                f.write(f"{r['type']}\t{r['stdcells']}\t{r['stdcell_area_um2']:.1f}\t{r['macro_area_um2']:.0f}\t"
                        f"{r['synth_memory_max_bits']}\t{'NA' if r['memories'] is None else len(r['memories'])}/{'NA' if r['memories_over_4096'] is None else len(r['memories_over_4096'])}\t{r['gen_lint_memory_bits']}\t{int(r['over_bound'])}\t"
                        f"{','.join(f'{k}x{v}' for k, v in r['macros'].items())}\t{r['kit']}\n")
    print(f"{len(rows)} types, over {BOUND}: {[r['type'] for r in rows if r['over_bound']]}")


if __name__ == "__main__":
    sys.exit(main())
