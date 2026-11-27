"""Exact placement review requests for the private kit controller."""

import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import socket
import subprocess
from tempfile import NamedTemporaryFile
import time

ACTIVE_DIES = {"s81", "s81_head", "qwen_compute", "qwen_kvsys"}
ROUTING_GOALS = {"auto", "grt", "route", "finish"}
REQUEST_SCHEMA = "placement-visual-request.v1"
REVIEW_SCHEMA = "placement-visual-review.v1"
IDENTITY = ("die", "item", "attempt", "kit", "stage_fingerprint", "odb_sha256")
REQUEST = "visual_request.json"
REVIEW = "visual_review.json"
PLACE_GEOMETRY = "place_auto_geom.json"

# Read on the placement host. Require one actual detailed placement, not GP or a stale alternate base.
CHECKPOINT = """
import hashlib,json,sys
from pathlib import Path
kit=Path(sys.argv[1])
paths=list(kit.glob('run/results/asap7/*/base/3_place.odb'))
odb=Path(sys.argv[2])
if paths != [odb] or not odb.is_file() or not odb.stat().st_size:
    raise ValueError('expected the single nonempty 3_place.odb of the exact kit')
before=odb.stat()
with odb.open('rb') as f:
    digest=hashlib.file_digest(f,'sha256').hexdigest()
after=odb.stat()
if (before.st_ino,before.st_size,before.st_mtime_ns) != (after.st_ino,after.st_size,after.st_mtime_ns):
    raise ValueError('placement changed while recording review request')
print('KW_VISUAL_CHECKPOINT '+json.dumps({'odb':str(odb.relative_to(kit)),'odb_sha256':digest,
      'size':after.st_size,'mtime_ns':after.st_mtime_ns,'inode':after.st_ino}))
"""

# Run on the placement host. Serialize the actual geometry check even if the
# controller disconnected after admission and is recovering the same checkpoint.
GEOMETRY_ONCE = r"""
import fcntl,json,os,subprocess,sys,tempfile
from pathlib import Path
directory,checker,checkpoint=map(Path,sys.argv[1:4])
identity=json.loads(sys.argv[4])
def unchanged():
    st=checkpoint.stat()
    return [st.st_ino,st.st_size,st.st_mtime_ns]==identity
with (directory/'.place-geometry.lock').open('a') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX)
    if not unchanged():
        sys.exit('AP_AUTO_GEOM_ERROR exact placement changed before check')
    completed=directory/'place-geometry.log'
    report=directory/'auto_geom.json'
    if completed.is_file() and report.is_file():
        print(completed.read_text(errors='replace'),end='')
        sys.exit(0)
    with tempfile.TemporaryFile() as output:
        run=subprocess.run(['bash',str(checker),str(directory)],stdout=output,stderr=subprocess.STDOUT,
                           env=dict(os.environ,OT_KIT_GOAL='place'))
        output.seek(0)
        text=output.read().decode(errors='replace')
    if not unchanged():
        sys.exit('AP_AUTO_GEOM_ERROR exact placement changed during check')
    print(text,end='')
    try:
        record=json.loads(report.read_text())
        line=record['line']
        verdict=record['verdict']
    except (OSError,KeyError,TypeError,ValueError):
        sys.exit('AP_AUTO_GEOM_ERROR no readable placement geometry report')
    if (verdict not in ('PASS','FAIL') or not isinstance(line,str) or not line.startswith('AUTO-GEOM '+verdict+' ') or
            'AP_AUTO_GEOM '+line not in text.splitlines() or run.returncode not in (0,1)):
        sys.exit('AP_AUTO_GEOM_ERROR placement report and checker disagree')
    receipt='KW_EXACT_PLACE_GEOM '+line+'\n'
    temp=completed.with_suffix('.new')
    temp.write_text(receipt)
    os.replace(temp,completed)
    print(receipt,end='')
"""

def applies(spec):
    return bool(spec.get("private") and (spec.get("kind") or "type") == "type" and spec.get("die") in ACTIVE_DIES)


def load(path):
    try:
        value = json.loads(path.read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def write(path, value):
    with NamedTemporaryFile("w", dir=path.parent, prefix=f".{path.name}.", delete=False) as f:
        tmp = f.name
        json.dump(value, f, indent=1)
        f.write("\n")
    try:
        os.replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def sha256(value):
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def place_geometry(out, result, checkpoint, observe):
    """Record one rule observation per placed checkpoint under the private controller lease."""
    fp = (result.get("stage_fp") or {}).get("place")
    odb = checkpoint.get("odb_sha256")
    stamp = [checkpoint.get(k) for k in ("inode", "size", "mtime_ns")]
    if not sha256(fp) or not sha256(odb) or not all(type(k) is int and k > 0 for k in stamp):
        return {"verdict": "ERROR", "reason": "exact placement identity unavailable"}
    key = hashlib.sha256(json.dumps([result["kit"], fp, odb]).encode()).hexdigest()
    destination = out / PLACE_GEOMETRY
    prior = load(destination)
    if prior.get("key") == key:
        return prior
    receipt = dict(observe(key, stamp), key=key, stage_fingerprint=fp, odb_sha256=odb)
    write(destination, receipt)
    return receipt


# Canonical requests are immutable. stdout is a single JSON document on a successful read.
INDEX = """
import json,os,re,sys,tempfile
from pathlib import Path
operation,ident=sys.argv[1:3]
if not re.fullmatch('[0-9a-f]{64}',ident):
    raise ValueError('invalid review request identity')
directory=Path.home()/'coord/autopilot/private_visual_requests'/ident
if operation == 'write':
    doc=json.loads(sys.argv[3])
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/'visual_request.json'
    with tempfile.NamedTemporaryFile('w',dir=directory,delete=False) as fp:
        temp=Path(fp.name)
        json.dump(doc,fp,indent=1)
    try:
        try:
            os.link(temp,path)
        except FileExistsError:
            pass
    finally:
        temp.unlink(missing_ok=True)
    stored=json.loads(path.read_text())
    if {k:v for k,v in stored.items() if k != 'ready_at'} != {k:v for k,v in doc.items() if k != 'ready_at'}:
        raise ValueError('immutable request identity collision')
    print(json.dumps(stored))
elif operation == 'read':
    path=directory/'visual_review.json'
    print(path.read_text() if path.is_file() else '{}')
else:
    raise ValueError('invalid index operation')
"""


def central(hub, operation, ident, doc=None):
    if not isinstance(hub, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", hub) or not sha256(ident):
        return {}
    argv = ["python3", "-I", "-c", INDEX, operation, ident]
    if doc is not None:
        argv.append(json.dumps(doc, sort_keys=True))
    if hub != "localhost":
        argv = ["ssh", "-n", "-o", "BatchMode=yes", "-o", "ControlPath=none", "-o", "ConnectTimeout=5",
                hub, shlex.join(argv)]
    try:
        result = subprocess.run(argv, capture_output=True, text=True, check=True, timeout=15)
        value = json.loads(result.stdout)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError, subprocess.SubprocessError):
        return {}


def request(out, res, spec_sha256, checkpoint, hub="", spec_path=None):
    host, _, kit = str(res.get("kit") or "").partition(":")
    fp = (res.get("stage_fp") or {}).get("place")
    if not host or not kit.startswith("/") or not sha256(fp) or not sha256(checkpoint.get("odb_sha256")):
        return {}
    geom = res.get("geom_dir")
    doc = {"schema": REQUEST_SCHEMA, "die": res["die"], "item": res["item"], "attempt": out.name,
           "kit": res["kit"], "stage_fingerprint": fp, "spec_sha256": spec_sha256,
           **{k: v for k, v in checkpoint.items() if k != "inode"},
           "render_dir": f"{res['kit']}/run/layout_review", "auto_geom": f"{geom}/auto_geom.png" if geom else ""}
    doc.update(request_dir=str(out), spec_path=str(Path(spec_path or out / "spec.json").absolute()),
               controller=socket.gethostname(), review_hub=hub)
    # Ignore mtime during identity selection: exact byte copies can retain the review.
    ident = {k: v for k, v in doc.items() if k != "mtime_ns"}
    doc["request_id"] = hashlib.sha256(json.dumps(ident, sort_keys=True).encode()).hexdigest()
    old = load(out / REQUEST)
    if old.get("request_id") == doc["request_id"]:
        doc = old
    else:
        doc["ready_at"] = time.time()
    if hub:
        stored = central(hub, "write", doc["request_id"], doc)
        if not stored:
            print(f"KW_PRIVATE_VISUAL index unavailable for {doc['request_id']}; local request retained", flush=True)
        else:
            doc = stored
    if doc != old:
        write(out / REQUEST, doc)
    return doc


def verdict(out, req):
    if req.get("schema") != REQUEST_SCHEMA or not all(req.get(k) for k in IDENTITY):
        return ""
    review = central(req["review_hub"], "read", req.get("request_id")) if req.get("review_hub") else load(out / REVIEW)
    if review.get("schema") != REVIEW_SCHEMA or any(review.get(k) != req[k] for k in IDENTITY):
        return ""
    value = review.get("verdict")
    if value in ("BAD", "ISSUES"):
        return value
    images = review.get("image_sha256")
    if value == "GOOD" and isinstance(images, dict) and images and all(sha256(sha) for sha in images.values()):
        return "GOOD"
    return ""


def wait(out, res, goal, reason="", decision="", blocked=False):
    res.update(stage="visual_review", goal=goal,
               verdict="WAIT-FORM" if blocked or decision in ("BAD", "ISSUES") else "WAIT-VISUAL",
               evidence=res.get("kit", ""), review_hold=reason or "awaiting exact viewed placement")
    write(out / "result.json", res)
    print(f"KW_PRIVATE_VISUAL {res['verdict']} {res['die']}/{res['item']} {res['review_hold']}", flush=True)
    return 0
