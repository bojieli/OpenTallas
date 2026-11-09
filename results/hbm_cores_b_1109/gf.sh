set -e
R=/srv/opentallas-scratch2/claude/kw35/repo
W=/srv/opentallas-scratch2/claude/kw36/wt_g
cd $R; git fetch -q origin 2>/dev/null || true
if [ ! -d $W ]; then
  git worktree add -q --no-checkout -b claude/kw-fix-36-gen-floor-1108 $W origin/main
  git -C $W sparse-checkout init --cone
  git -C $W sparse-checkout set tools physical/common_flow
  git -C $W checkout -q claude/kw-fix-36-gen-floor-1108
fi
cd $W/tools/autopilot
python3 -I - <<'PY'
p="kit_wave.py"
s=open(p).read()
# 1 record the hard floor per lane
old='''                lim = rfloor if len(f) == 4 and f[3] == "/" else floor
                for die in lanes[f[1]]:
                    free_map.setdefault(h, {})[die] = int(f[2])
'''
new='''                lim = rfloor if len(f) == 4 and f[3] == "/" else floor
                hard = int(cfg.get("root_floor_gb", 150)) if len(f) == 4 and f[3] == "/" else GEN_SCRATCH_HARD_FLOOR_GB
                for die in lanes[f[1]]:
                    free_map.setdefault(h, {})[die] = int(f[2])
                    cfg.setdefault("_workroot_hard", {}).setdefault(h, {})[die] = hard
'''
assert s.count(old)==1; s=s.replace(old,new)
# 2 fallback helper + load_hold
old='''def load_hold(cfg, die, *names):
'''
new='''# KW-FIX-36 11-08 (COORD 17:3x): gen_disk_min_gb is a preference.  When no gen host of a die clears it the die would stop
# although some host can still take a kit, so the fallback picks the host with the most free disk on the die's lane that
# clears the REAL floor (root_floor_gb for a lane on a root fs, ot-run's scratch floor otherwise) plus the gen need,
# at most gen_fallback_per_tick gens per host per tick.  Option gen_disk_fallback false turns it off.
GEN_SCRATCH_HARD_FLOOR_GB = 50      # ot-run refuses a scratch disk below this
GEN_NEED_GB = 20                    # gen + place of one kit: 1-3 GB measured on 8 HBM attempts, with margin
GEN_FALLBACK_PER_TICK = 2


def gen_fallback_host(cfg, die, hs):
    """the host for a gen when no host of hs clears the preference (see above), or None"""
    if cfg.get("gen_disk_fallback") is False:
        return None
    stt, hub = cfg.get("_otrun_status") or {}, cfg.get("_hub") or ""
    need, cap = int(cfg.get("gen_need_gb", GEN_NEED_GB)), int(cfg.get("gen_fallback_per_tick", GEN_FALLBACK_PER_TICK))
    taken, free, hard = cfg.get("_gen_fallback_taken") or {}, cfg.get("_workroot_free") or {}, cfg.get("_workroot_hard") or {}
    best = None
    for h in hs:
        v = stt.get("localhost" if h == hub else h)
        if not v or over_load_cap(v) or taken.get(h, 0) >= cap:
            continue
        f, floor = (free.get(h) or {}).get(die), (hard.get(h) or {}).get(die, GEN_SCRATCH_HARD_FLOOR_GB)
        f = int(v["scratch_gb"]) if f is None and v.get("scratch_gb") is not None else f
        if f is not None and int(f) >= floor + need and (best is None or int(f) > best[0]):
            best = (int(f), h)
    return best[1] if best else None


def load_hold(cfg, die, *names):
'''
assert s.count(old)==1; s=s.replace(old,new)
old='''    if any(host_room(v, die_disk_low(cfg, die, h, v)) and die not in low.get(h, {}) for h, v in rows):
        return ""
'''
new='''    if any(host_room(v, die_disk_low(cfg, die, h, v)) and die not in low.get(h, {}) for h, v in rows):
        return ""
    if gen_fallback_host(cfg, die, [h for h, _ in rows]):
        return ""
'''
assert s.count(old)==1; s=s.replace(old,new)
old='''    key = lambda h: stt.get("localhost" if h == hub else h)
    if len(hs) < 2:
        best = hs[0] if hs else cfg["dies"][die]["gen_host"]      # KW-FIX-30: the one host gen_hosts left
'''
new='''    key = lambda h: stt.get("localhost" if h == hub else h)
    if cfg.get("load_hold") is not False and hs and not any(
            host_room(key(h), die_disk_low(cfg, die, h, key(h))) and die not in (cfg.get("_workroot_low") or {}).get(h, {}) for h in hs):
        fb = gen_fallback_host(cfg, die, hs)                      # KW-FIX-36: no host clears the preference
        if fb:
            t = cfg.setdefault("_gen_fallback_taken", {})
            t[fb] = t.get(fb, 0) + 1
            return fb
    if len(hs) < 2:
        best = hs[0] if hs else cfg["dies"][die]["gen_host"]      # KW-FIX-30: the one host gen_hosts left
'''
assert s.count(old)==1; s=s.replace(old,new)
old='''    if nl and not AP.DRY:
        save_state(st, ap_dir)
    try:
        prov_resign_step(AP, cfg, st, notices, ap_dir, AP.HUB_NAME)
'''
new='''    if nl and not AP.DRY:
        save_state(st, ap_dir)
    if cfg.get("_gen_fallback_taken"):
        AP.log("KIT-WAVE GEN-DISK-FALLBACK no gen host over gen_disk_min_gb; gens on the most free host above the real floor: "
               + " ".join(f"{h}={n}" for h, n in sorted(cfg["_gen_fallback_taken"].items())))
    try:
        prov_resign_step(AP, cfg, st, notices, ap_dir, AP.HUB_NAME)
'''
assert s.count(old)==1; s=s.replace(old,new)
open(p,"w").write(s)
p="test_kit_wave_genhosts.py"
s=open(p).read()
s+='''

# ---- KW-FIX-36: gen disk fallback when no host clears the preference
def _fb_cfg(free, hard=None, **kw):
    c = dict(gen_disk_min_gb=100, _hub="intel2", dies={"s81": dict(gen_host="a", gen_hosts=["a", "b"], event="e")}, **kw)
    c["_otrun_status"] = {h: dict(admit=400, load=10, cores=128, scratch_gb=40) for h in free}
    c["_workroot_free"] = {h: {"s81": g} for h, g in free.items()}
    c["_workroot_low"] = {h: {"s81": g} for h, g in free.items()}
    c["_workroot_hard"] = {h: {"s81": (hard or {}).get(h, 50)} for h in free}
    return c


def test_fallback_picks_most_free_above_the_real_floor():
    c = _fb_cfg(dict(a=80, b=90))
    assert K.load_hold(c, "s81") == "" and K.pick_gen_host(c, "s81") == "b"


def test_fallback_keeps_the_root_floor():
    c = _fb_cfg(dict(a=165, b=70), hard=dict(a=150, b=50))         # a: 165 < 150 + 20; b: 70 clears 50 + 20
    assert K.pick_gen_host(c, "s81") == "b"
    c = _fb_cfg(dict(a=165, b=60), hard=dict(a=150, b=50))         # nobody clears floor + need: the hold stands
    assert K.load_hold(c, "s81").startswith("LOAD-HOLD") and K.gen_fallback_host(c, "s81", ["a", "b"]) is None


def test_fallback_is_capped_per_host_per_tick():
    c = _fb_cfg(dict(a=80, b=90))
    assert [K.pick_gen_host(c, "s81") for _ in range(4)] == ["b", "b", "a", "a"]
    assert K.load_hold(c, "s81").startswith("LOAD-HOLD")


def test_fallback_off_keeps_the_hold():
    c = _fb_cfg(dict(a=80, b=90), gen_disk_fallback=False)
    assert K.load_hold(c, "s81").startswith("LOAD-HOLD")


def test_fallback_not_used_while_a_host_has_room():
    c = _fb_cfg(dict(a=80, b=120))
    c["_workroot_low"] = {"a": {"s81": 80}}
    assert K.pick_gen_host(c, "s81") == "b" and not c.get("_gen_fallback_taken")
'''
open(p,"w").write(s)
PY
tar cf - kit_wave.py test_kit_wave_genhosts.py | ssh -o ControlPath=none epyc2 'mkdir -p /srv/opentallas-scratch3/claude/kw36/gtip && cd /srv/opentallas-scratch3/claude/kw36 && rm -rf gtip/tools && cp -al base/tools gtip/tools && rm -f gtip/tools/autopilot/kit_wave.py gtip/tools/autopilot/test_kit_wave_genhosts.py && [ -d gtip/physical ] || cp -al base/physical gtip/physical; tar xf - -C gtip/tools/autopilot'
