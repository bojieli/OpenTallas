"""Opt-in, read-only diagnostics of the actual Q595 late fault/reset geometry.

No placement algorithm or gate changes. The caller must use the returned module
via selected(), because die_top_lint.load_qwen() reimports and discards wrappers.
"""
from pathlib import Path
import hashlib
import importlib.util
import inspect
import json
import os
import pickle
import sys

SOURCE_SHA256 = 'c5655b8dec117f2525c093b56348287a5f68577e0a74c9102122caed81e0fdd8'
LATE_ANCHOR = "            m.setdefault('fault_emit', {})['late_unrepaired'] = _late_bad"
SITE_ANCHOR = '        return None if best is None else (best[1], best[2])'


class SnapshotComplete(Exception):
    """The diagnostic completed reset construction; stop before further GEN."""


class ActualSnapshot:
    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.files = []

    def save(self, name, value):
        path = self.output / name
        assert not path.exists(), ('snapshot would overwrite evidence', path)
        with path.open('wb') as out:
            pickle.dump(value, out, protocol=pickle.HIGHEST_PROTOCOL)
        self.files.append(dict(name=name, sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
        (self.output / 'manifest.json').write_text(json.dumps(dict(source_sha256=SOURCE_SHA256, files=self.files), indent=2))
        print('ACTUAL_SNAPSHOT', name, path.stat().st_size, flush=True)

    @staticmethod
    def rects(grid):
        return sorted({tuple(r) for values in grid.values() for r in values})

    @staticmethod
    def model(m):
        return dict(die=m['die'], insts=[{k: getattr(i, k, None) for k in ('name', 'master', 'x', 'y', 'w', 'h', 'orient', 'kind', 'region', 'domain')} for i in m['insts']],
                    buses=m['buses'], fault_emit=m.get('fault_emit'), fault_source_bit_contract=m.get('fault_source_bit_contract'))

    def late(self, m, plans, grid, grid0, site_cache, unrep, pt_face, pt_ext):
        self.save('late_graph.pkl', dict(model=self.model(m), plans=plans, occupied=self.rects(grid), static_occupied=self.rects(grid0),
                                        sites={key: value[0] for key, value in site_cache.items()}, unrepaired=dict(unrep),
                                        pt_face=pt_face, pt_ext=pt_ext))

    def site_failure(self, state):
        # Called only after the unchanged actual search reports no candidate.
        # Keep the actual heap/pops/seen state, rather than guessing why it failed.
        frame = inspect.currentframe().f_back
        while frame is not None:
            if frame.f_code.co_name == 'new' and frame.f_back is not None and frame.f_back.f_code.co_name == 'chain':
                caller = frame.f_back
                parent = caller.f_back
                occ = state['self']
                self.save('reset_pad_failure.pkl', dict(
                    site_parameters={k: state[k] for k in ('tx', 'ty', 'box', 'lim', 'w', 'h', 'gap')},
                    search={k: state[k] for k in ('pops', 'heap', 'seen', 'best', 'd', 'cx', 'cy', 'x0', 'y0', 'r', 'q') if k in state},
                    occupied=self.rects(occ.g), W=occ.W, H=occ.H, gx=occ.gx, gy=occ.gy,
                    context={k: caller.f_locals[k] for k in ('k', 'lv', 'mst', 'head', 'prev', 'N', 'ht', 'bid') if k in caller.f_locals},
                    parent_context={k: parent.f_locals[k] for k in ('p', 'root', 'hdom', 'ht', 'net') if parent is not None and k in parent.f_locals},
                    new_context={k: frame.f_locals[k] for k in ('tx', 'ty', 'box', '_bid') if k in frame.f_locals}))
                break
            frame = frame.f_back

    def load_generator(self, source):
        source = Path(source).resolve()
        data = source.read_bytes()
        assert hashlib.sha256(data).hexdigest() == SOURCE_SHA256, 'actual generator source changed'
        text = data.decode()
        assert text.count(LATE_ANCHOR) == 1
        text = text.replace(LATE_ANCHOR, LATE_ANCHOR + '\n            _actual_snapshot.late(m, plans, grid, grid0, site_cache, unrep, PT_FACE, PT_EXT)')
        assert text.count(SITE_ANCHOR) == 1
        text = text.replace(SITE_ANCHOR, '        if best is None: _actual_snapshot.site_failure(locals())\n' + SITE_ANCHOR)
        spec = importlib.util.spec_from_file_location('qwen_rom_fulldie_b3r2', source)
        G = importlib.util.module_from_spec(spec)
        G._actual_snapshot = self
        sys.modules[spec.name] = G
        exec(compile(text, str(source), 'exec'), G.__dict__)
        self.wrap(G)
        return G

    def wrap(self, G):
        original_reset = G._reset_tree
        original_build = G._rst_tree_build
        snapshot = self

        def build(nets, rects, W, H, gx, gy, *args, **kwargs):
            snapshot.save('reset_inputs.pkl', dict(nets=nets, rects=rects, W=W, H=H, gx=gx, gy=gy,
                                                   args=args, kwargs=kwargs,
                                                   constants={n: getattr(G, n) for n in ('RST_W', 'RST_H', 'RST_GAP_UM', 'RST_NET_UM', 'RST_OK_UM', 'RST_PITCH_UM', 'RST_PAD_LV')}))
            try:
                result = original_build(nets, rects, W, H, gx, gy, *args, **kwargs)
            except BaseException as error:
                snapshot.save('reset_exception.pkl', dict(type=type(error).__name__, message=str(error)))
                raise
            snapshot.save('reset_result.pkl', result)
            return result

        def reset(v, m):
            snapshot.save('before_reset_model.pkl', snapshot.model(m))
            result = original_reset(v, m)
            snapshot.save('after_reset_model.pkl', snapshot.model(m))
            raise SnapshotComplete('actual diagnostic stopped after reset construction, before further GEN')

        G._rst_tree_build = build
        G._reset_tree = reset
        G._actual_snapshot_wrapped = True


def enabled_snapshot():
    """Default OFF: absent environment yields no directory, mutation, or hooks."""
    path = os.environ.get('OT_Q_ACTUAL_SNAPSHOT')
    return ActualSnapshot(path) if path else None
