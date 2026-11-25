#!/usr/bin/env python3
"""stage_seat.py -- STAGE-SEAT (S81-STAGE-SEAT 11-25, COORD; FP-CONVERGE-S81 finding, 0 cycles added).

Of 354 S81 dsdv_slice groups whose placed hops exceed 405 um, 311 are pipeline stages the kit never seats: relay_mid.tcl
(PRE_GLOBAL_PLACE, FIRM stations at j/(n+1) on the source -> sink line, FIT + POLY = obstacle-aware path) only knows the
flops that match OT_RELAY_MID_RE, and the S81 default names the u_y_* relays only.  The bind's own stage chains
(u_bin_* ot_dp_st input stages, u_lpad_* / u_d<D>_* ot_dp_dly + ot_dp_rrelay pads, xf / xg / reset legs) were left to GPL.

This module is the generic, die-agnostic part: it reads the BOUND RTL of the kit, finds every instance of a stage module
(register-only, no logic), and widens the relay regex with one alternative per instance stem (digit runs -> [0-9]+).  A chain
whose ends are fixed points (hard-core pins, ports, FIRM flops) is then seated by relay_mid.tcl exactly like a u_y_ relay; a
group with a soft end stays with GPL (relay_mid.tcl rule, unchanged).

Knob OT_STAGE_SEAT (GEN env / kit item_env): 1 = on, 0 = off, unset = STAGE_SEAT_DEFAULT_DIES (S81: on once proven, see
DEFAULT_ON).  plan budgets.stage_seat (true/false) and budgets.stage_seat_types (types or unsplit base names) also switch it.
On: OT_RELAY_MID_RE widened, and OT_RELAY_MID_FIT = 1, OT_RELAY_MID_FIT_CHAIN = 1, OT_RELAY_POLY = 1 exported.
OT_STAGE_SEAT_RE_EXTRA = regex alternative(s) (first capture inside the group) for stage registers the bound RTL does not
name as an instance (generate-block registers).  Off = byte-identical kits.
"""
import os
import re

CHECK = "STAGE-SEAT"
# S81 kits take the knob on by default once the place probes are proven; flip together with the probe verdict.
DEFAULT_ON = False
DEFAULT_DIES = ("s81",)
# register-only stage modules a bind instantiates; u_y_* (ot_s81_rly) is covered by the base regex
STAGE_MODULES = ("ot_dp_st", "ot_dp_dly", "ot_dp_rrelay", "ot_dp_relay", "ot_dp_rly")
DLY_MODULES = ("ot_dp_dly",)
MAX_STEMS = 400          # config.mk line length: beyond it the stems collapse to their leading word run

_INST = re.compile(r"\b(" + "|".join(STAGE_MODULES) + r")\s*(?:#\s*\((?:[^()]|\([^()]*\))*\))?\s*(\\?[A-Za-z_][\w$]*)\s*\(", re.S)


def enabled(budgets=None, tn=None, die=None, env=None):
    """OT_STAGE_SEAT env wins, then plan budgets (stage_seat, stage_seat_types), then the per-die default."""
    env = os.environ if env is None else env
    e = env.get("OT_STAGE_SEAT")
    if e in ("0", "1"):
        return e == "1"
    b = budgets or {}
    if b.get("stage_seat") is not None:
        return bool(b["stage_seat"])
    per = list(b.get("stage_seat_types") or [])
    if tn is not None and (tn in per or tn.split("__")[0] in per):
        return True
    return bool(DEFAULT_ON and die in DEFAULT_DIES)


def _strip(text):
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)


def stage_instances(text):
    """[(module, instance)] of every stage-module instance in a bound RTL text (comments stripped)."""
    return [(m.group(1), m.group(2).lstrip("\\")) for m in _INST.finditer(_strip(text))]


def stem(name):
    """instance name -> regex stem: digit runs generalised, so u_lpad_leafup_i0..i4 is one alternative"""
    return re.sub(r"[0-9]+", "\x00", re.escape(name)).replace("\x00", "[0-9]+")


def stems(texts):
    """-> (pad stems, flat stems): ot_dp_dly ranks are r[k] / q, every other stage module is one register rank (.q)"""
    pad, flat = set(), set()
    for text in texts:
        for mod, inst in stage_instances(text):
            (pad if mod in DLY_MODULES else flat).add(stem(inst))
    if len(pad) + len(flat) > MAX_STEMS:      # keep the line short: collapse to the leading u_<word> run
        def lead(s):
            m = re.match(r"(u_[A-Za-z]+)", s.replace("\\", ""))
            return (m.group(1) + "_[A-Za-z0-9_]*") if m else s
        pad, flat = {lead(s) for s in pad}, {lead(s) for s in flat}
    return sorted(pad), sorted(flat)


def alternatives(texts, extra=None):
    pad, flat = stems(texts)
    alts = []
    if pad:
        alts.append(r"(?:.*[._])?(?:" + "|".join(pad) + r")[.](?:r\[[0-9]+\]|q)(?![A-Za-z0-9_])")
    if flat:
        alts.append(r"(?:.*[._])?(?:" + "|".join(flat) + r")(?=[.])")
    if extra:
        alts.append(extra)
    return alts


def widen(base_re, texts, extra=None):
    """base relay regex (first capture = group, trailing [.] outside) + stage alternatives -> one regex, same capture"""
    alts = alternatives(texts, extra)
    if not alts:
        return base_re
    m = re.match(r"^\^\((.*)\)\[\.\]$", base_re)
    if m:
        core = m.group(1) + r"(?=[.])"
    else:
        m2 = re.match(r"^\^\((.*)\)$", base_re)
        if not m2:
            return base_re        # a base form this module cannot extend safely: unchanged
        core = m2.group(1)
    return "^(" + "|".join([core] + alts) + ")"


def exports(on):
    """config.mk export lines that turn the seats FIT + chain-measured + obstacle-aware (core_place --obstacle-aware sense)"""
    if not on:
        return []
    return ["export OT_RELAY_MID_FIT = 1", "export OT_RELAY_MID_FIT_CHAIN = 1", "export OT_RELAY_POLY = 1"]
