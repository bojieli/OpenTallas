"""Stage explicit, source-pinned optional recipe assets in a new runtime subtree."""
import hashlib
import re
from pathlib import Path, PurePosixPath


def _relative(value):
    if not isinstance(value,str) or not value or '\\'in value:
        raise ValueError('runtime asset path must be a relative POSIX path')
    p=PurePosixPath(value)
    if p.is_absolute()or any(x in ('','.','..')for x in value.split('/')):
        raise ValueError('runtime asset path traversal/absolute path refused')
    return p


def runtime_destination(value):
    p=_relative(value)
    if len(p.parts)<2 or p.parts[0]!='runtime':
        raise ValueError('runtime asset destination must be inside runtime/')
    # kit_hash deliberately excludes these basenames; never stage unhashed data.
    if p.name=='freeze.json'or p.name.startswith('run_'):
        raise ValueError('runtime asset destination excluded by normal kit hash')
    return p


def stage(kit,repo,entries=None):
    """Validate the complete optional readset before copying any new asset.

    Existing files, helper/config/RTL overwrites, path escape and stale source
    bytes are refused. Empty/default recipes retain their prior output bytes.
    """
    if entries is None:return []
    if not isinstance(entries,list):raise ValueError('runtime_files must be a list')
    kit,repo=Path(kit).resolve(),Path(repo).resolve();prepared=[];seen=set()
    for row in entries:
        if not isinstance(row,dict)or set(row)!={'source','sha256','destination'}:
            raise ValueError('runtime_files requires exact source/sha256/destination')
        src=_relative(row['source']);dst=runtime_destination(row['destination']);expected=row['sha256']
        if not isinstance(expected,str)or not re.fullmatch('[0-9a-f]{64}',expected):
            raise ValueError('runtime asset requires explicit SHA256')
        source=repo/src;resolved=source.resolve(strict=True)
        resolved.relative_to(repo)
        if not resolved.is_file():raise ValueError('runtime asset source is not a file')
        data=resolved.read_bytes()
        if hashlib.sha256(data).hexdigest()!=expected:raise ValueError('runtime asset source SHA256 differs')
        dest=kit/dst
        for part in [dest,*list(dest.parents)]:
            if part==kit:break
            if part.is_symlink():raise ValueError('runtime asset destination symlink refused')
            if part!=dest and part.exists()and not part.is_dir():
                raise ValueError('runtime asset destination ancestor is not a directory')
        dest.resolve().relative_to(kit)
        if dst in seen or dest.exists()or any(dst in q.parents or q in dst.parents for q in seen):
            raise ValueError('runtime asset destination collision/overwrite')
        seen.add(dst);prepared.append((dest,data,dict(source=src.as_posix(),sha256=expected,destination=dst.as_posix(),bytes=len(data))))
    for dest,data,row in prepared:
        dest.parent.mkdir(parents=True,exist_ok=True)
        with dest.open('xb')as f:f.write(data)
    return [row for _,_,row in prepared]
