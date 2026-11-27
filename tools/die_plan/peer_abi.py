#!/usr/bin/env python3
"""peer_abi: cross-die interface ABI guard ([P-PEER-ABI], R3-PEERABI 11-27).

Every cross-die interface pair of the live plans must agree on the interface ABI of its two ends.  A die is built and signed
alone, so nothing else notices that one end changed (or never changed) its wrapper: KV sys_c kept OBS1_COMPAT=0 while the live
QC C9 d2d master emits STATUS-v1 (qfd_d2d_static_ovl_sf7_obs1); the KV status receiver then faults on the first status frame
(rx_sf legacy validator: bad_extension = |d[511:156]).  Neither die's PRE/G0/bind sees it.

Pair table (declared by the rack connection tables results/arch/release_rack_1021/connections_*.csv, ABI by the bound RTL):

  QC-KV:status    QC u_d2d_rom (qfd_d2d_static_*) status TX codec  ->  KV u_d2d_kv (qkd_d2d_static_*) status RX accept set
                  tx 'v1' needs the RX to accept v1: OBS1_COMPAT=1 (or an *_obs1 receiver).  tx 'legacy' is accepted by all.
                  The status flows QC -> KV (rx_sf lives in the KV end), so the KV end is the one that changes.
  S81-HEAD:link   ot_pdie_serdes header (parameters + port widths), ot_s81_kp4_common / enc / dec contract text: the KP4
                  RS(544,514) codeword + 512-b beat + pma lane widths both dies' serdes link masters must share.

Descriptors are read from a die's BOUND RTL (kit_rtl.bind_out/rtl, else <tree>/physical/die_plan/<die>/bind_of_record/rtl) and
tree (rtl/dsrom_sys/s81_link).  A pair is MATCH, MISMATCH (blocks), or UNKNOWN (an end's files unreadable on this host:
recorded, never blocks, because the guard must not stop a cut over a host it cannot read).

    peer_abi.py census --kv TREE[:BIND_OUT] --qc TREE[:BIND_OUT] --s81 ... --head ... [--json]
    peer_abi.py gate --die DIE --tree T [--bind-out B] --peer DIE=TREE[:BIND_OUT] ...   (exit 1 on MISMATCH)
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA_ID = "opentallas.peer_abi.v1"
DIE_ROLE = {"qwen_compute": "qc", "qwen_kvsys": "kv", "s81": "s81", "s81_head": "head"}
ROLE_DIE = {v: k for k, v in DIE_ROLE.items()}
LINK_DIR = "rtl/dsrom_sys/s81_link"
INST = {"qc": ("qfd_d2d_static", "u_d2d_rom"), "kv": ("qkd_d2d_static", "u_d2d_kv")}
# module parameters whose default is not 0 when the instance leaves them out (none of the status params today)
OBS1_COMPAT_DEFAULT = 0


# ----------------------------------------------------------------------------------------------- parsing
def _match_paren(text, i):
    """index of the ')' that closes the '(' at text[i]"""
    depth = 0
    for j in range(i, len(text)):
        c = text[j]
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return j
    return -1


def _named_params(body):
    """'.A(1), .B(32'h3)' -> {'A': '1', 'B': "32'h3"} (top-level named parameters only)"""
    out, i = {}, 0
    while True:
        m = re.compile(r"\.\s*([A-Za-z_]\w*)\s*\(").search(body, i)
        if not m:
            return out
        j = _match_paren(body, m.end() - 1)
        if j < 0:
            return out
        out[m.group(1)] = " ".join(body[m.end():j].split())
        i = j + 1


def find_instances(text, module_prefix, inst_name):
    """-> [{module, inst, params}] for every `module_prefix*  #( .. ) inst_name (` in text"""
    res = []
    for m in re.finditer(r"\b(%s\w*)\s*#\s*\(" % re.escape(module_prefix), text):
        j = _match_paren(text, m.end() - 1)
        if j < 0:
            continue
        t = re.match(r"\s*(\\?[\w.\[\]\\$]+)\s*\(", text[j + 1:])
        if t and t.group(1) == inst_name:
            res.append({"module": m.group(1), "inst": inst_name, "params": _named_params(text[m.end():j])})
    # a parameterless instance `module inst (` is the all-defaults instance
    for m in re.finditer(r"\b(%s\w*)\s+(%s)\s*\(" % (re.escape(module_prefix), re.escape(inst_name)), text):
        res.append({"module": m.group(1), "inst": inst_name, "params": {}})
    return res


def _int(v, default=None):
    if v is None:
        return default
    m = re.fullmatch(r"(?:\d+'[sS]?[dD])?(\d+)", v.strip())
    if m:
        return int(m.group(1))
    m = re.fullmatch(r"\d+'[hH]([0-9a-fA-F_]+)", v.strip())
    return int(m.group(1).replace("_", ""), 16) if m else None


def _rtl_dirs(tree, bind_out, die):
    ds = []
    if bind_out:
        ds.append(Path(bind_out) / "rtl")
    if tree:
        ds.append(Path(tree) / "physical" / "die_plan" / die / "bind_of_record" / "rtl")
    return [d for d in ds if d.is_dir()]


def _d2d_instance(role, tree, bind_out):
    prefix, inst = INST[role]
    dirs = _rtl_dirs(tree, bind_out, ROLE_DIE[role])
    if not dirs:
        return None, "no bound rtl dir (bind_out/rtl or bind_of_record/rtl) readable"
    for d in dirs:
        for f in sorted(d.glob("*.sv")):
            try:
                text = f.read_text(errors="replace")
            except OSError:
                continue
            if inst not in text:
                continue
            found = find_instances(text, prefix, inst)
            if found:
                return dict(found[0], file=f.name, rtl_dir=str(d)), ""
    return None, f"no {prefix}* instance {inst} in {[str(d) for d in dirs]}"


# ----------------------------------------------------------------------------------------------- descriptors
def describe_status_end(role, tree, bind_out):
    """QC: status TX codec of u_d2d_rom.  KV: status RX accept set of u_d2d_kv."""
    inst, why = _d2d_instance(role, tree, bind_out)
    if inst is None:
        return {"role": role, "known": False, "why": why}
    mod, params = inst["module"], inst["params"]
    d = {"role": role, "known": True, "module": mod, "file": inst["file"], "params": params}
    if role == "qc":
        d["status_tx"] = "v1" if mod.endswith("_obs1") else "legacy"
    else:
        c = _int(params.get("OBS1_COMPAT"), OBS1_COMPAT_DEFAULT)
        d["OBS1_COMPAT"] = c
        d["status_rx_accepts"] = ["legacy", "v1"] if (c or mod.endswith("_obs1")) else ["legacy"]
    return d


def _module_header(text, module):
    m = re.search(r"\bmodule\s+%s\b" % re.escape(module), text)
    if not m:
        return None
    i = m.end()
    # header = parameter list + port list up to the first ');'
    j = text.find(");", i)
    return " ".join(re.sub(r"//[^\n]*", "", text[m.start():j + 2]).split()) if j > 0 else None


def describe_link(role, tree):
    """S81 / HEAD serdes + KP4 wire contract from the tree's s81_link sources"""
    d = Path(tree or "/nonexistent") / LINK_DIR
    if not (d / "ot_pdie_serdes.sv").is_file():
        return {"role": role, "known": False, "why": f"{d}/ot_pdie_serdes.sv not readable"}
    out = {"role": role, "known": True, "link_dir": str(d)}
    for f, mods in (("ot_pdie_serdes.sv", ["ot_pdie_serdes"]), ("ot_s81_kp4_enc.sv", ["ot_s81_kp4_enc"]),
                    ("ot_s81_kp4_dec.sv", ["ot_s81_kp4_dec"])):
        p = d / f
        text = p.read_text(errors="replace") if p.is_file() else ""
        for mod in mods:
            h = _module_header(text, mod)
            out["hdr_" + mod] = hashlib.sha256(h.encode()).hexdigest()[:12] if h else None
            if mod == "ot_pdie_serdes":
                out["serdes_header"] = h
    p = d / "ot_s81_kp4_common.sv"
    out["kp4_common"] = hashlib.sha256(p.read_bytes()).hexdigest()[:12] if p.is_file() else None
    return out


# ----------------------------------------------------------------------------------------------- pairs
LINK_KEYS = ("hdr_ot_pdie_serdes", "hdr_ot_s81_kp4_enc", "hdr_ot_s81_kp4_dec", "kp4_common")


def check_pairs(desc):
    """desc = {role: descriptor}.  -> [{pair, state, detail, fix_side}] ; state MATCH | MISMATCH | UNKNOWN"""
    rows = []
    qc, kv = desc.get("qc"), desc.get("kv")
    if not (qc and kv):
        rows.append({"pair": "QC-KV:status", "state": "UNKNOWN", "detail": "an end was not supplied", "fix_side": ""})
    elif not (qc.get("known") and kv.get("known")):
        rows.append({"pair": "QC-KV:status", "state": "UNKNOWN",
                     "detail": "; ".join(f"{d['role']}: {d.get('why')}" for d in (qc, kv) if not d.get("known")), "fix_side": ""})
    else:
        tx, acc = qc["status_tx"], kv["status_rx_accepts"]
        ok = tx in acc
        rows.append({"pair": "QC-KV:status", "state": "MATCH" if ok else "MISMATCH",
                     "detail": f"QC {qc['module']} status_tx={tx}; KV {kv['module']} OBS1_COMPAT={kv['OBS1_COMPAT']} accepts={acc}"
                               + ("" if ok else f" -> KV receiver faults on the first {tx} status frame"),
                     "fix_side": "" if ok else "KV (set OBS1_COMPAT=1 on u_d2d_kv; QC is the live STATUS-v1 producer)"})
    h, s = desc.get("head"), desc.get("s81")
    if not (h and s):
        rows.append({"pair": "S81-HEAD:link", "state": "UNKNOWN", "detail": "an end was not supplied", "fix_side": ""})
    elif not (h.get("known") and s.get("known")):
        rows.append({"pair": "S81-HEAD:link", "state": "UNKNOWN",
                     "detail": "; ".join(f"{d['role']}: {d.get('why')}" for d in (h, s) if not d.get("known")), "fix_side": ""})
    else:
        bad = [k for k in LINK_KEYS if h.get(k) != s.get(k)]
        rows.append({"pair": "S81-HEAD:link", "state": "MISMATCH" if bad else "MATCH",
                     "detail": ("differs: " + ", ".join(f"{k} head={h.get(k)} s81={s.get(k)}" for k in bad)) if bad
                     else "serdes header, KP4 enc/dec headers and kp4_common identical",
                     "fix_side": "the older-main die (re-cut from current main)" if bad else ""})
    return rows


def describe(role, tree, bind_out=None):
    return describe_status_end(role, tree, bind_out) if role in ("qc", "kv") else describe_link(role, tree)


def verdict(rows):
    return "FAIL" if any(r["state"] == "MISMATCH" for r in rows) else "PASS"


def gate(die, tree, bind_out, peers):
    """candidate die + peer live trees {die_name: (tree, bind_out)} -> check record for publish_gate"""
    role = DIE_ROLE.get(die)
    if role is None:
        return {"verdict": "PASS", "n": 0, "pairs": [], "why": f"die {die} has no peer ABI pair"}
    desc = {role: describe(role, tree, bind_out)}
    for pd, (pt, pb) in (peers or {}).items():
        pr = DIE_ROLE.get(pd)
        if pr and pr != role:
            desc[pr] = describe(pr, pt, pb)
    mine = {"qc": ("QC-KV:status",), "kv": ("QC-KV:status",), "s81": ("S81-HEAD:link",), "head": ("S81-HEAD:link",)}[role]
    rows = [r for r in check_pairs(desc) if r["pair"] in mine]
    return {"verdict": verdict(rows), "n": len(rows), "pairs": rows, "descriptors": desc}


# ----------------------------------------------------------------------------------------------- cli
def _split(v):
    t, _, b = v.partition(":")
    return t, (b or None)


def main(argv=None):
    P = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = P.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("census")
    for r in ("kv", "qc", "s81", "head"):
        c.add_argument("--" + r, metavar="TREE[:BIND_OUT]")
    c.add_argument("--json", action="store_true")
    g = sub.add_parser("gate")
    g.add_argument("--die", required=True)
    g.add_argument("--tree", required=True)
    g.add_argument("--bind-out")
    g.add_argument("--peer", action="append", default=[], metavar="DIE=TREE[:BIND_OUT]")
    a = P.parse_args(argv)
    if a.cmd == "census":
        desc = {}
        for r in ("kv", "qc", "s81", "head"):
            if getattr(a, r):
                t, b = _split(getattr(a, r))
                desc[r] = describe(r, t, b)
        rows = check_pairs(desc)
        if a.json:
            print(json.dumps({"schema": SCHEMA_ID, "pairs": rows, "descriptors": desc}, indent=1))
        else:
            for r in rows:
                print(f"{r['pair']:16s} {r['state']:9s} {r['detail']}" + (f"  FIX: {r['fix_side']}" if r["fix_side"] else ""))
        return 1 if verdict(rows) == "FAIL" else 0
    peers = {}
    for p in a.peer:
        d, _, v = p.partition("=")
        peers[d] = _split(v)
    rec = gate(a.die, a.tree, a.bind_out, peers)
    print(json.dumps(rec, indent=1))
    return 0 if rec["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
