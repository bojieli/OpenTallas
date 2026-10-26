"""Validate the typed, source-bound core-publisher local-age receipt.

This contract is distinct from the legacy LP compiler record. Source tuples,
publisher stages and measured component logs are checked against exact bytes.
"""
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "opentallas.qwen.tt_source_local.v1"

def source_local_edges(root, master, receipt):
    root = Path(root).resolve()
    receipt = Path(receipt)
    row = json.loads(receipt.read_text())
    if (row.get("schema") != SCHEMA or row.get("status") != "QUALIFIED_SOURCE_LOCAL_EDGES"
            or row.get("master") != master or row.get("calendar_sample_edges") != 1
            or row.get("producer_instance") != "u_gi" or row.get("clock_domain") != "ck_core"):
        raise ValueError("typed TT source receipt identity/sample/clock mismatch")

    def bound(path, sha):
        p = (root / path).resolve()
        if not p.is_relative_to(root) or hashlib.sha256(p.read_bytes()).hexdigest() != sha:
            raise ValueError("typed TT source receipt hash/path mismatch: " + path)
        return p

    rtl = bound(row["rtl"], row["rtl_sha256"])
    source = bound(row["source_record"], row["source_record_sha256"])
    bench = bound(row["bench_receipt"], row["bench_receipt_sha256"])
    record, measured = json.loads(source.read_text()), json.loads(bench.read_text())
    if record.get("schema") != "opentallas.hp13.core_publisher_local_edges.v2":
        raise ValueError("typed TT source record schema mismatch")
    variant = str(row["variant"])
    v = record["variants"][variant]
    if (v["master"] != master or v["rtl"] != row["rtl"] or v["rtl_sha256"] != row["rtl_sha256"]
            or v["producer_instance"] != "u_gi"):
        raise ValueError("typed TT selected publisher variant mismatch")
    text = rtl.read_text()
    if not re.search(r"\bmodule\s+" + re.escape(master) + r"\b", text):
        raise ValueError("typed TT RTL does not define selected master")
    pub = v["publisher_statement"]
    stages = re.search(r"qfd_hp13_corepub39 #\(\.STAGES\((\d+)\)\)", pub)
    if (not stages or text.count(pub) != 1 or ".ck(ck_core)" not in pub
            or ".o({emb_user,emb_position,emb_token,emb_start})" not in pub):
        raise ValueError("typed TT publisher source/clock mismatch")
    stages = int(stages.group(1))
    if stages not in (1, 2) or int(variant) != stages:
        raise ValueError("typed TT publisher stage mismatch")
    bits = v["source_bits"]
    if len(bits) != 39 or {b["bit"] for b in bits} != set(range(39)):
        raise ValueError("typed TT source tuple is incomplete")
    expected_ports = [("emb_start", 0)] + [("emb_token", i) for i in range(18)] + [("emb_position", i) for i in range(18)] + [("emb_user", i) for i in range(2)]
    if [(b["port"], b["port_bit"]) for b in bits] != expected_ports:
        raise ValueError("typed TT source tuple field identity mismatch")
    nets = []
    for b in bits:
        stmt = b["source_statement"]
        q = re.search(r"\.Q\((n_\d+)\)", stmt)
        if (text.count(stmt) != 1 or ".C(n_3159)" not in stmt
                or not re.match(r"qfd_bmath_dff_", stmt) or q is None):
            raise ValueError("typed TT source capture is not the exact core FF")
        nets.append(q.group(1))
    actual = re.search(r"\.i\(\{([^}]+)\}\)", pub)
    if not actual or actual.group(1).split(",") != list(reversed(nets)) or len(set(nets)) != 39:
        raise ValueError("typed TT publisher tuple source/order mismatch")
    if "assign n_3159 = ck_core;" not in text:
        raise ValueError("typed TT source FF clock is not the core root")
    for key, expected in (("producer_offset_edges", 0), ("output_offset_edges", stages),
                          ("source_to_output_edges", stages), ("total_source_local_edges", 1 + stages)):
        if type(v.get(key)) is not int or v[key] != expected:
            raise ValueError("typed TT source record age mismatch: " + key)
    if (measured.get("schema") != "opentallas.hp13.publisher_component_measurement.v1"
            or measured.get("status") != "PASS"):
        raise ValueError("typed TT actual component measurement missing")
    mv = measured["variants"][variant]
    if mv["rtl_sha256"] != row["rtl_sha256"] or mv["source_to_output_edges"] != stages:
        raise ValueError("typed TT measured source/age mismatch")
    for artifact in measured["sources"]:
        bound(artifact["path"], artifact["sha256"])
    for run in mv["runs"]:
        log = bound(run["path"], run["sha256"]).read_text()
        marker = "PUB_PASS stages=" + str(stages) if run["mutant"] == 0 else "PUB_FAIL"
        if marker not in log:
            raise ValueError("typed TT component witness missing")
    if len(mv["runs"]) != 3 or {run["mutant"] for run in mv["runs"]} != {0, 1, 2}:
        raise ValueError("typed TT component causal witnesses incomplete")
    for key, expected in (("producer_offset_edges", 0), ("output_offset_edges", stages),
                          ("source_to_output_edges", stages), ("source_local_edges", 1 + stages)):
        if type(row.get(key)) is not int or row[key] != expected:
            raise ValueError("typed TT receipt age mismatch: " + key)
    return 1 + stages, dict(status=row["status"], schema=SCHEMA, master=master,
        calendar_sample_edges=1, producer_instance="u_gi", producer_offset_edges=0,
        output_offset_edges=stages, source_to_output_edges=stages,
        receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest(),
        rtl_sha256=row["rtl_sha256"], source_record_sha256=row["source_record_sha256"],
        bench_receipt_sha256=row["bench_receipt_sha256"])
