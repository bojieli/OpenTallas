"""Explicit, hash-pinned candidate library selection; captured bind stays immutable.

This selects source, not functional/physical qualification. Callers retain native
interface checks, exactness/model obligations and ordinary downstream gates.
"""
import copy
import hashlib
import json
from pathlib import Path
import re

SCHEMA = "opentallas.kit_library_profile.v1"
POLICY = "no edits; preserve exact original bound source/receipt"

def _path(value, base):
    if not isinstance(value, str) or not value:
        raise ValueError("library profile requires an explicit source path")
    p = Path(value)
    return p.resolve() if p.is_absolute() else (Path(base)/p).resolve()

def _modules(text):
    # Ignore comments and strings so diagnostics cannot masquerade as modules.
    text = re.sub(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"', ' ', text, flags=re.S)
    names = re.findall(r'\bmodule\s+(?:(?:automatic|static)\s+)?([A-Za-z_$][\w$]*)', text)
    if not names or len(names) != len(set(names)):
        raise ValueError("library profile needs unique literal module declarations")
    return sorted(names)

def apply(path, type_name, idx, prefer, defines, base):
    path = Path(path).resolve()
    raw = path.read_bytes()
    doc = json.loads(raw)
    if doc.get("schema") != SCHEMA or doc.get("type") != type_name:
        raise ValueError("library profile schema/type differs")
    if doc.get("bound_body_policy") != POLICY or not doc.get("proof") or not isinstance(doc.get("model"), dict):
        raise ValueError("library profile requires bound-body preservation, proof and model declaration")
    flags = doc.get("defines")
    if not isinstance(flags, list) or not flags or len(flags) != len(set(flags)) or any(
            not isinstance(x,str) or not re.fullmatch(r'[A-Za-z_]\w*(?:=\S+)?',x) for x in flags):
        raise ValueError("library profile requires unique explicit candidate defines")
    by_name = {}
    for flag in list(defines)+flags:
        name=flag.split("=",1)[0]
        if name in by_name and by_name[name] != flag:
            raise ValueError("library profile conflicts with captured define: "+name)
        by_name[name]=flag
    rows = doc.get("replacements")
    if not isinstance(rows,list) or not rows:
        raise ValueError("library profile requires explicit replacements")
    # Build everything in memory. Validation failures cannot partly alter a kit.
    out = {m:[str(_path(f,base)) for f in fs] for m,fs in idx.items()}
    preferred = [str(_path(f,base)) for f in prefer]
    originals, replacements, claimed = set(), set(), set()
    checked = []
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("library profile replacement must be an object")
        old = _path(row.get("original"),base)
        new = _path(row.get("replacement"),path.parent)
        if old == new or str(old) in originals or str(new) in replacements:
            raise ValueError("library profile aliases or duplicates a source file")
        original_names = row.get("original_modules")
        replacement_names = row.get("replacement_modules")
        for file, key, names in ((old,"original_sha256",original_names),(new,"replacement_sha256",replacement_names)):
            expected = row.get(key)
            if not isinstance(expected,str) or not re.fullmatch(r'[0-9a-f]{64}',expected):
                raise ValueError("library profile requires exact source SHA256")
            content = file.read_bytes()
            if hashlib.sha256(content).hexdigest() != expected:
                raise ValueError("library profile source SHA256 differs: "+str(file))
            if not isinstance(names,list) or any(not isinstance(x,str) for x in names) or sorted(names) != _modules(content.decode()):
                raise ValueError("library profile module inventory differs: "+str(file))
        if not set(original_names) <= set(replacement_names):
            raise ValueError("library profile cannot remove a captured module")
        if not any(str(old) in out.get(m,[]) for m in original_names):
            raise ValueError("library profile original is absent from captured library index")
        for name in original_names:
            if str(old) not in out.get(name,[]):
                raise ValueError("library profile original module/index differs: "+name)
        for name in replacement_names:
            if name in claimed or (name not in original_names and name in out):
                raise ValueError("library profile module addition collides: "+name)
            claimed.add(name)
        originals.add(str(old)); replacements.add(str(new))
        checked.append(dict(row,original=str(old),replacement=str(new)))
    if originals & replacements:
        raise ValueError("library profile replacement overlaps captured originals")
    for row in checked:
        old,new=row["original"],row["replacement"]
        for name in row["original_modules"]:
            out[name]=[f for f in out[name] if f != old]
        for name in row["replacement_modules"]:
            out.setdefault(name,[]).append(new)
        preferred=[f for f in preferred if f != old]
    preferred=[r["replacement"] for r in checked]+preferred
    receipt=copy.deepcopy(doc)
    receipt.update(profile=str(path),profile_sha256=hashlib.sha256(raw).hexdigest(),
        replacements=checked,defines=list(dict.fromkeys(list(defines)+flags)),
        scope="EXPLICIT_CANDIDATE_LIBRARY_ONLY_NOT_QUALIFIED",
        captured_bind_unchanged=True)
    return out,preferred,receipt
