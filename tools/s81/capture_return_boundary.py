#!/usr/bin/env python3
"""Preserve the exact failed return-station invocation without changing search."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import sys
import types


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source', type=Path, required=True)
    ap.add_argument('--recipe', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--chain', default='crE2_W0_hub')
    args = ap.parse_args()
    source, out = args.source.resolve(), args.out.resolve()
    os.chdir(source)
    sys.path.insert(0, str(source / 'tools'))
    import cloudpickle
    import dsrom_s81_fulldie as G
    original = G.Chains.run
    def run(self, name, lanes, path, allowed, src, *positional, **keywords):
        try:
            return original(self, name, lanes, path, allowed, src, *positional, **keywords)
        except RuntimeError as error:
            if name != args.chain:
                raise
            frame = error.__traceback__
            local = None
            while frame:
                if frame.tb_frame.f_code is original.__code__:
                    local = dict(frame.tb_frame.f_locals)
                    break
                frame = frame.tb_next
            out.mkdir(parents=True, exist_ok=True)
            keys = ('L','pos','cur','target','t_','cx','cy','d','horiz','w','h','step','reach','must','forced','force_horiz')
            selected = {key: local[key] for key in keys if local is not None and key in local}
            cx,cy = selected.get('cx',src[0]),selected.get('cy',src[1])
            obstacles = [item.d() for item in self.m['insts']
                         if item.x < cx+800 and item.x+item.w > cx-800
                         and item.y < cy+800 and item.y+item.h > cy-800]
            state = {key:value for key,value in vars(G).items() if key.isupper()
                     and not key.startswith('_NEAR_') and not isinstance(value,types.ModuleType) and not callable(value)}
            receipt = dict(scope='EXACT_FAILED_INVOCATION_DIAGNOSTIC_NO_ROUTE_NO_STA',
                 source_commit=(source/'SOURCE_SHA').read_text().strip(),
                 generator_sha256=hashlib.sha256((source/'tools/dsrom_s81_fulldie.py').read_bytes()).hexdigest(),
                 recipe_sha256=hashlib.sha256((source/args.recipe).read_bytes()).hexdigest(),
                 chain=name,lanes=list(lanes),path=path,allowed=allowed,source=src,
                 positional=positional,keywords=keywords,failure=str(error),local=selected,
                 native_outline_along={str(horizontal):G.stn_dims(lanes,horizontal) for horizontal in (False,True)},
                 native_outline_across={str(horizontal):G.stn70_across(lanes,horizontal) for horizontal in (False,True)},
                 nearby_obstacles=obstacles,
                 reserved_sites=[r for r in G.RSV_RECTS if r[0]<cx+800 and r[2]>cx-800 and r[1]<cy+800 and r[3]>cy-800],
                 physical_scope='Actual source placement occupancy. Real PG/CTS/reset blockage and native pin proof remain separate obligations.')
            (out/'failure.json').write_text(json.dumps(receipt,indent=2,default=str)+'\n')
            with (out/'partial_model.pickle').open('wb') as stream:
                cloudpickle.dump(dict(model=self.m,state=state,occupancy=self.P.occ,
                                      receipt=receipt),stream,protocol=5)
            print('OT_RETURN_BOUNDARY_CAPTURE '+json.dumps(dict(chain=name,lanes=lanes,local=selected,out=str(out))),flush=True)
            raise
    G.Chains.run = run
    return G.main(['real',*shlex.split((source/args.recipe).read_text()),'--cfifo-colck','--work',str(out/'unemitted_real')])


if __name__ == '__main__':
    raise SystemExit(main())
