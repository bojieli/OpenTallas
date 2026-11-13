#!/usr/bin/env python3
"""QC-REGION-1 COUNT FRAME (DIE-QC-100 11-13): the one count frame of a regional (link-fed) die clock.

Under a die-wide balanced tree every region's leaves sit the same whole number of cycles after the root, so the count
frame of count_align_plan / count_align_bind (origins counted in each region's OWN clock edges, "edge-index frame") and
the wall clock agree.  Under clock.spine.topology link_htree the regional leaves of region v arrive f_v whole cycles
after the root (feed frame_offset, 1..19 on QC s29), and the edge-index schedule latency of a crossing u -> v,
lat = K + 1 + n_v - n_u, loses f_v - f_u cycles (it can reach 0 or below although the word takes several cycles).

WALL-ALIGNED FRAME (clock.spine.feed.frame "wall_aligned"): node x carries N'_x = N_x + f_x, so
    sched_lat = K + 1 + N'_dst - N'_src = lat_edge + f_dst - f_src
while the RTL K, the origins' physical steps (PAD + 2 + J) and the lag L = (K + N_dst - N_src) T + d are unchanged:
the frame is a relabelling of the count, it moves whole cycles out of d into the schedule.  A start-tree edge's step
and a relay edge's stages take the same shift, so every fundamental loop still sums to zero.

f is read from the plan: clock.spine.feed {path, sha256, frame} + clock.spine.region_map {path, sha256}; a partition
takes its map region's offset, a region name its own, a virtual start-tree node (st:...) 0.  A plan WITHOUT
clock.spine.feed has no frame: load() returns None and every reader is unchanged.

Readers (all take the frame from here): count_align_plan --sta-proof / --frame-plan (lat_cycles), count_align_bind
(identity, loops, relay K), clock_landings.Landings (sidecar count_aligned.frame == plan feed, bind_clock_landings
count_frame), lane_asbuilt_latency (bind_clock_landings count_frame == plan feed), region_form apply (sidecar K).
"""
import hashlib
import json
from pathlib import Path

FRAMES = ("wall_aligned",)
SCHEMA = "opentallas.count_frame.v1"


class FrameError(ValueError):
    pass


def _sha(b):
    return hashlib.sha256(b).hexdigest()


def _resolve(rel, plan_path, base=None):
    """a plan-relative path (plan_of_record/x.json is relative to the die dir = plan file's dir or its parent)"""
    p = Path(rel)
    if p.is_absolute():
        return p if p.is_file() else None
    cands = []
    for b in (base, None if plan_path is None else Path(plan_path).resolve().parent):
        if b is None:
            continue
        b = Path(b)
        cands += [b / p, b.parent / p, b / p.name]
    cands.append(Path.cwd() / p)
    return next((c for c in cands if c.is_file()), None)


class Frame:
    def __init__(self, name, offsets, part_region, feed_path, feed_sha, map_sha):
        self.name, self.offsets, self.part_region = name, dict(offsets), dict(part_region)
        self.feed_path, self.feed_sha, self.map_sha = feed_path, feed_sha, map_sha

    def f(self, node):
        if node in self.part_region:
            return int(self.offsets[self.part_region[node]])
        if node in self.offsets:
            return int(self.offsets[node])
        if str(node).startswith("st:"):
            return 0        # virtual start-tree node (clock-tree stage): frame 0, bookkeeping only
        raise FrameError(f"count frame: node {node!r} is neither a partition, a region nor a virtual start node")

    def shift(self, src, dst):
        return self.f(dst) - self.f(src)

    def meta(self, offsets=False):
        m = dict(schema=SCHEMA, frame=self.name, feed=self.feed_path, feed_sha256=self.feed_sha[:16],
                 region_map_sha256=self.map_sha[:16])
        if offsets:
            m["offsets"] = dict(sorted(self.offsets.items()))
            m["part_region"] = dict(sorted(self.part_region.items()))
        return m


def spine_feed(plan):
    return ((plan or {}).get("clock") or {}).get("spine", {}).get("feed")


def load(plan, plan_path=None, base=None):
    """Frame of a die plan dict, or None (no clock.spine.feed: legacy edge-index = wall frame, every reader no-op)."""
    sp = (plan.get("clock") or {}).get("spine") or {}
    fd = sp.get("feed")
    if not fd:
        return None
    name = fd.get("frame")
    if name not in FRAMES:
        raise FrameError(f"clock.spine.feed.frame {name!r} not in {FRAMES}")
    rm = sp.get("region_map")
    if not rm:
        raise FrameError("clock.spine.feed without clock.spine.region_map")
    fp, mp = _resolve(fd["path"], plan_path, base), _resolve(rm["path"], plan_path, base)
    if fp is None or mp is None:
        raise FrameError(f"count frame files not found: feed {fd['path']} -> {fp}, region map {rm['path']} -> {mp}")
    fb, mb = fp.read_bytes(), mp.read_bytes()
    fs, ms = _sha(fb), _sha(mb)
    if not fs.startswith(fd["sha256"]) or not ms.startswith(rm["sha256"]):
        raise FrameError(f"count frame sha mismatch: feed {fs[:16]} vs plan {fd['sha256']}, "
                         f"region map {ms[:16]} vs plan {rm['sha256']}")
    feed, rmap = json.loads(fb), json.loads(mb)
    if feed.get("frame") != name or "frame_offset" not in feed:
        raise FrameError(f"feed {fd['path']}: frame {feed.get('frame')!r} / frame_offset missing (plan says {name})")
    return Frame(name, feed["frame_offset"], rmap["part_region"], fd["path"], fs, ms)


def load_path(plan_path):
    """explicit frame plan (--frame-plan): a missing / unreadable file is an error"""
    return None if plan_path is None else load(json.loads(Path(plan_path).read_bytes()), plan_path)


def load_optional(plan_path):
    """implicit frame source (--sta-plan / --plan-die): None when not given or not a readable file, so a run without a
    die plan on disk keeps the legacy (no-frame) behaviour byte-identical; a plan WITH clock.spine.feed still loads
    (and fails closed on a bad feed / map)"""
    if not plan_path or not Path(plan_path).is_file():
        return None
    try:
        raw = json.loads(Path(plan_path).read_bytes())
    except (OSError, ValueError):
        return None
    return load(raw, plan_path) if isinstance(raw, dict) else None


def from_meta(m):
    """Frame rebuilt from a meta(offsets=True) record (count_align_plan summary.frame -> count_align_bind)"""
    if not m:
        return None
    if "offsets" not in m:
        raise FrameError("count frame record without offsets")
    return Frame(m["frame"], m["offsets"], m.get("part_region", {}), m.get("feed"), m.get("feed_sha256", ""),
                 m.get("region_map_sha256", ""))


def same(m, frame):
    """record m (a sidecar / bind output count frame) names the plan's frame (both None = legacy)"""
    if frame is None:
        return not m
    return bool(m) and m.get("frame") == frame.name and m.get("feed_sha256", "")[:16] == frame.feed_sha[:16]


def check_same(m, frame, what):
    if not same(m, frame):
        got = None if not m else (m.get("frame"), m.get("feed_sha256"))
        want = None if frame is None else (frame.name, frame.feed_sha[:16])
        raise FrameError(f"{what}: count frame {got} != plan clock.spine.feed {want} (re-derive it in the plan's frame)")


def wall_lat(lat_edge, frame, src, dst):
    return lat_edge if frame is None else lat_edge + frame.shift(src, dst)


def edge_lat(sched, frame, src, dst):
    return sched if frame is None else sched - frame.shift(src, dst)
