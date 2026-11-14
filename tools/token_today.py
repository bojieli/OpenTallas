#!/usr/bin/env python3
"""Today's plans of record for the token-path export (TOKEN-EXPORT-1, 2026-11-14).

tools/token_path_export.py replays the October inputs (cycle records, reprice, composition, HGI programs).  This layer
does not change a cycle.  It re-points what the Token view shows ABOUT those cycles at today's design:

  * geometry   the die plans of record (plan_now.json rows: plan path + commit on origin/main), drawn by
               tools/fleet_viz/plan_now.py plan_geometry, written as geo_<design>.json and named in record["geometry"]
               (the October die snapshot stays in record["geometry"]["october"]);
  * classes    each operator class is joined to the types / hard cores of those plans by the reviewed regex rules of
               tools/fleet_viz/token_design_rules.json (one rule per class and die, graded named / inferred; no committed
               bind manifest carries a token class, so there is nothing stronger to join on yet); a class with no
               rule keeps no hardware and says so;
  * currency   for every stage the input records, their last commit date and whether that is as new as the plan of
               record ("current") or older ("October record" - the cycles are not a measurement on today's die);
               plus today's token-pass lines of the release tree and the newest results/token_pass records;
  * export     generated time, repo head and the plan-state stamp, so a reader does not need git to date the file.

    python3 tools/token_path_export.py --viz-dir DIR --today <state>/plan_now.json
"""
from __future__ import annotations

import datetime
import gzip
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools/fleet_viz"))

DESIGN_DIES = {"ds_rom": ["s81", "s81_head"], "qwen_rom": ["qwen_compute", "qwen_kvsys"],
               "hbm_gen_qwen": ["hbm"], "hbm_gen_ds": ["hbm"],
               "qwen_kvdie": ["qwen_compute", "qwen_kvsys"], "qwen_hbm": ["hbm"]}
RULE_KEY = {"hbm_gen_qwen": "hbm_gen", "hbm_gen_ds": "hbm_gen", "qwen_kvdie": "qwen_rom", "qwen_hbm": "hbm_gen"}
# release-tree TOK lines and token_pass directory keywords that speak for a design
TOK_PREFIX = {"ds_rom": ("TOK.DS",), "qwen_rom": ("TOK.QW", "KV.FN"), "hbm_gen_qwen": ("TOK.HBM",), "hbm_gen_ds": ("TOK.HBM",),
              "qwen_kvdie": ("TOK.QW", "KV.FN"), "qwen_hbm": ("TOK.HBM",)}
TOK_DIR = {"ds_rom": re.compile(r"(^|_)(s81|ds|head|svc|xtier|lep)(_|\d|$)"), "qwen_rom": re.compile(r"(^|_)(qw|qwen|qc|kv|bc4)(_|\d|$)"),
           "hbm_gen_qwen": re.compile(r"(^|_)hbm(_|\d|$)"), "hbm_gen_ds": re.compile(r"(^|_)hbm(_|\d|$)"),
           "qwen_kvdie": re.compile(r"(^|_)(qw|qwen|qc|kv|bc4)(_|\d|$)"), "qwen_hbm": re.compile(r"(^|_)hbm(_|\d|$)")}
ALL_TOK = ("TOK.PROGRAM", "TOK.E2E")

# stage -> input records of token_path_export.py (repo paths; a directory counts as its newest file)
INPUTS = {
    "qwen_rom": [
        ("operation cycles (STREAM4 P8191 full token, L0 op trace)", ["results/rtl/qwen_plain_ar_stream4_P8191_20261005/terminal.json",
            "results/rtl/qwen_rom_kv_fullbw_20261004/dspark_step_stream4.json", "results/rtl/qwen_rom_kv_fullbw_20261004/model.json"]),
        ("composition lines + re-price", ["results/arch/unified_composition_20261007/ledger.json", "results/arch/reprice_20261008/reprice.json"]),
        ("relays, collective, embedding", ["results/rtl/qwen_rom_die_r17_20261005/relays_r21/relay_token_cost.json",
            "results/arch/qwen_coll_native_20261009/coll_cost.json", "results/arch/emb_hbm_20261008/token_path_inputs.json"]),
        ("KV die leg", ["results/arch/qwen_kv_die_20261009/reprice.json"]),
    ],
    "ds_rom": [
        ("field phases + all-measured composition", ["tools/s81/field_phases_1792.py", "tools/dsrom_1m_allmeasured.py"]),
        ("re-price items", ["results/arch/reprice_20261008/reprice.json", "results/arch/unified_composition_20261007/ledger.json"]),
        ("MTP step charges + DSpark binding", ["results/arch/mtp_step_20261009", "results/uarch/dsrom_s81_mtp_binding_20261010/verdict.json"]),
        ("engram table", ["results/arch/engram_20261008/design.json"]),
        ("draft / wavefront / wfc records", ["results/rtl/dsrom_recovery_20261004", "results/rtl/dsrom_wfc_split_20261006/closure.json"]),
    ],
    "hbm_gen": [
        ("compiled HGI-1 programs + simulator schedule", ["results/arch/hgi_programs_20261010", "results/arch/hgi_sim_20261009/e2e_calibration.json"]),
    ],
}


def _git(*a, binary=False):
    p = subprocess.run(["git", *a], cwd=ROOT, capture_output=True, timeout=300)
    return p.stdout if binary else p.stdout.decode(errors="replace").strip()


def _iso(ts):
    return datetime.datetime.fromtimestamp(ts, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _dt(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def last_date(path):
    """commit date (ISO) of the newest commit touching a repo path (a directory counts as its newest file)"""
    return _git("log", "-1", "--format=%cI", "origin/main", "--", path) or None


def label(iso, plan_iso):
    """'current' when the record is at least as new as the plan of record, else '<Month> record'"""
    if not iso:
        return "unknown"
    if plan_iso and _dt(iso) >= _dt(plan_iso):
        return "current"
    return _dt(iso).strftime("%B") + " record"


class Today:
    def __init__(self, state_file, rules_file=None):
        self.S = json.loads(Path(state_file).read_text())
        self.rules = json.loads(Path(rules_file or ROOT / "tools/fleet_viz/token_design_rules.json").read_text())
        self.dies = {r["die"]: r for r in self.S["dies"]}
        self.now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self._geo, self._cn = {}, {}
        import plan_now as PN
        self.PN = PN

    # ------------------------------------------------------------------ geometry
    def die_geo(self, die):
        if die not in self._geo:
            r = self.dies[die]
            raw = _git("show", "origin/main:" + r["plan_path"], binary=True)
            d = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
            g = self.PN.plan_geometry(die, r["plan_path"], r["plan_commit"], d)
            I, M, K = g["inst"], g["masters"], g["kinds"]
            inst = [[I["name"][i], K[I["k"][i]], I["x"][i], I["y"][i], I["w"][i], I["h"][i], M[I["m"][i]]["name"]] for i in range(len(I["name"]))]
            self._geo[die] = dict(die=die, label=r["label"], plan=r["plan_path"], commit=r["plan_commit"], date=r["plan_date"],
                                  subject=r.get("plan_subject"), w=g["W"], h=g["H"], instances=inst)
        return self._geo[die]

    def geo_file(self, design):
        dies = [self.die_geo(d) for d in DESIGN_DIES[design]]
        p = dies[0]
        return dict(schema="opentallas.token_path.geometry.v2", source="plan of record: " + ", ".join(f"{d['plan']}@{d['commit'][:9]}" for d in dies),
                    w=p["w"], h=p["h"], instances=p["instances"], dies=dies)

    # ------------------------------------------------------------------ class -> plan nodes
    def rules_of(self, design):
        rd = self.rules["designs"].get(RULE_KEY.get(design, design)) or {}
        return self.rules["designs"].get(rd["same_as"]) if rd.get("same_as") else rd

    def class_nodes(self, design):
        """{cls: {instances: [names], masters: [names], confidence, why}} over the geometry of today's plans"""
        if design in self._cn:
            return self._cn[design]
        rd, out = self.rules_of(design), {}
        for cid, rule in (rd.get("classes") or {}).items():
            names, masters = [], set()
            for die, rx in rule.get("rules") or []:
                if die not in DESIGN_DIES[design]:
                    continue
                pat = re.compile(rx)
                for n, kind, x, y, w, h, m in self.die_geo(die)["instances"]:
                    if pat.match(m):
                        names.append(n)
                        masters.add(m)
            out[cid] = dict(instances=names, masters=sorted(masters), confidence=rule.get("confidence"), why=rule.get("why"))
        self._cn[design] = out
        return out

    # ------------------------------------------------------------------ record
    def stages(self, design):
        plan_iso = max((self.dies[d]["plan_date"] for d in DESIGN_DIES[design]), key=_dt)
        rows = []
        for stage, paths in INPUTS[RULE_KEY.get(design, design)]:
            ds = [(p, last_date(p)) for p in paths]
            newest = max((d for _, d in ds if d), key=_dt, default=None)
            rows.append(dict(stage=stage, records=[dict(path=p, last_commit=d) for p, d in ds], newest=newest, status=label(newest, plan_iso)))
        return rows, plan_iso

    def today_tokens(self, design):
        T = self.S.get("token") or {}
        pre = TOK_PREFIX[design] + ALL_TOK
        lines = [ln for ln in T.get("release_lines") or [] if ln.lstrip("[ ]x").lstrip().startswith(pre)]
        dirs = [d for d in T.get("token_pass") or [] if TOK_DIR[design].search(Path(d["dir"]).name)]
        return dict(release_tree=lines, release_tree_mtime=_iso(T["release_mtime"]) if T.get("release_mtime") else None,
                    newest_token_pass_records=dirs[:8],
                    note="component and functional token-pass records of today's dies; none of them is a whole-token cycle count, so the cycles are not re-priced from them")

    def apply(self, rec, design):
        stages, plan_iso = self.stages(design)
        cn = self.class_nodes(design)
        dies = [self.die_geo(d) for d in DESIGN_DIES[design]]
        old_geo = rec.get("geometry")
        for c in rec.get("classes") or []:
            m = cn.get(c["id"])
            c["october_elements"], c["october_instances"] = c.get("elements"), c.get("instances")
            if m and m["instances"]:
                c["elements"], c["instances"] = m["masters"], m["instances"]
                c["mapping"] = dict(grade=m["confidence"], why=m["why"], rules="tools/fleet_viz/token_design_rules.json")
            else:
                c["elements"], c["instances"] = [], []
                c["mapping"] = dict(grade="none", why=(m or {}).get("why") or "no rule maps this class onto the current plans")
        old = sum(s["status"] != "current" for s in stages)
        pl = [dict(die=d["die"], plan=d["plan"], commit=d["commit"], date=d["date"]) for d in dies]
        rec["geometry"] = dict(source="; ".join(f"{d['plan']}@{d['commit'][:9]}" for d in dies), key="plan:" + "+".join(DESIGN_DIES[design]),
                               die=" + ".join(f"{d['label']} (plan of record {d['commit'][:9]}, {d['date'][:10]})" for d in dies), dies=pl, october=old_geo)
        gen = self.S.get("generated")
        rec["currency"] = dict(generated=self.now, plan_state_generated=_iso(gen) if isinstance(gen, (int, float)) else gen, plans=pl, stages=stages,
                               stages_older_than_plan=old, stages_total=len(stages),
                               cycles="October record" if old == len(stages) else ("mixed" if old else "current"),
                               summary=(f"{old} of {len(stages)} input stages are older than the plan of record ({plan_iso[:10]}): their cycles are the "
                                        "recorded 2026-10 numbers, not a measurement on today's die" if old else "all input stages are at least as new as the plan of record"),
                               token_pass_today=self.today_tokens(design))
        rec["export"] = dict(generated=self.now, tool="tools/token_path_export.py --today", mode="today-plans", repo_head=rec.get("repo_head"))
        return rec
