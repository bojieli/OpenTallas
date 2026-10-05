#!/usr/bin/env python3
"""Portable read-only strict terminal replay; no live ROOT or runtime admission.

The immutable raw archive is presented in a temporary symlink view containing
its locked released index. This never edits raw files or overwrites verdicts.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile

VALIDATOR_SHA256='740e828dd6be2990839883b477c7aedbcabc8110afe857bc2e6013ea2686bf7d'


def replay(archive, repo, index, qualified, validator):
    archive=Path(archive).resolve();repo=Path(repo).resolve();index=Path(index).resolve()
    qualified=Path(qualified).resolve();validator=Path(validator).resolve()
    if hashlib.sha256(validator.read_bytes()).hexdigest()!=VALIDATOR_SHA256:
        raise ValueError('immutable930d5ff16 validator source pin')
    spec=importlib.util.spec_from_file_location('strict_terminal_coverage',validator)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    with tempfile.TemporaryDirectory(prefix='qwen-terminal-replay-') as tmp:
        view=Path(tmp)
        for path in archive.iterdir():
            if path.name!='checkpoint_index.json':(view/path.name).symlink_to(path)
        (view/'checkpoint_index.json').symlink_to(index)
        result=module.verify(view,repo,qualified)
    result['replay_scope']='read-only archival replay; runtime ROOT/admission guards unchanged'
    result['validator_sha256']=VALIDATOR_SHA256
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--archive',type=Path,required=True)
    parser.add_argument('--repo',type=Path,required=True)
    parser.add_argument('--index',type=Path,required=True)
    parser.add_argument('--qualified-images',type=Path,required=True)
    parser.add_argument('--validator',type=Path,default=Path(__file__).resolve().parent/'qwen_native_terminal_coverage.py')
    args=parser.parse_args()
    print(json.dumps(replay(args.archive,args.repo,args.index,args.qualified_images,args.validator),indent=2))
