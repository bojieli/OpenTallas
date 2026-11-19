"""KV-TYPES-5 11-08 (COORD 10:0x kv3_phy@7R): opt-in partition_types[].reset.port_relays for a DELIVERED-reset wrapper.

A native hard wrapper takes the delivered reset (bind.py `wire rst_n = arst_n;`): every flop of the wrapper has its
reset pin on the arst_n port net, so a face register far from the reset port is timed (recovery) over the whole hop
(kv3_phy: arst_n at the die spine tap (842.4, 760.32) -> u_bin_i_host_hbm_rst_n at the N face, about 1.09 mm of
buffered wire, recovery TT -64 ps).  A row

    {"name": "hrst", "depth": 2, "sinks": ["u_bin_i_host_hbm_rst_n"]}

emits `depth` synchronous reset relays (ot_dp_rrelay u_prl_<name>_<j>, the cell the landing reset copies already use)
from rst_n and moves only the named ot_dp_st sinks' rst_n pins onto the last relay.  Those sinks then assert and release
`depth` clocks later than the rest of the wrapper; nothing else changes (no port, clock, data path or lane cycle).  The
plan places the relays with relay_sites keys u_prl_<name>_<j>/q (kit_istations FIRM sites).  Use it only where the
later release is not observable at the wrapper outputs.  kv3_phy: the sink is the host-reset face register; its data q
has no reset and its epoch eq is read by nothing (u_lpad eq -> i_host_hbm_rst_n_eq, unused), so only that unread epoch
moves (up to `depth` cycles at each reset edge); the bench
(physical/die_plan/qwen_kvsys/plan_of_record/phy_pi_1108/bench) proves every wrapper output cycle-identical and shows
a relay on an OBSERVED epoch (u_bout, depth 6) is caught.
Fail closed: the wrapper must carry the delivered-reset alias, every sink must be one emitted ot_dp_st whose rst_n is
connected to rst_n, names must be new and unique.
CBC-RULES-1119 (COORD r713 rule 4, reset relay tree <= 32 per leaf): depth up to MAX_DEPTH (16; a 4.3-mm hard wrapper such as
S81 phy__t1 needs 11 hops of <= 405 um from its reset tap), and ot_dp_ste banks are sinks like ot_dp_st.  bank_reset_delta.py
writes the rows (one equal-depth chain per bank group) and raises the hard type's reset.depth by the same D.
apply_bank_taps(): reset.bank_taps for a type WITH a generated reset tree (`wire rst_n = rst_n_t<k>;`): each row
{"tap": i, "sinks": [ot_dp_st/ste insts]} re-points those banks' rst_n pins from the leaf tap to the tree tap rst_n_t<i>
nearest them.  reset_tree pads every tap to the same depth K, so the release cycle is unchanged: 0 cycles, 0 flops; only
the far banks stop hanging off one leaf (S81 serdes__t12: 17 banks over 2.9 mm on rst_n_t11).
"""
import re

import reset_consumers as RC


class PortRelayError(ValueError):
    pass


_ID = re.compile(r"^[A-Za-z_][A-Za-z_0-9]*$")
DELIVERED = re.compile(r"(?m)^[ \t]*wire[ \t]+rst_n[ \t]*=[ \t]*arst_n[ \t]*;")
LEAF = re.compile(r"(?m)^[ \t]*wire[ \t]+rst_n[ \t]*=[ \t]*rst_n_t(\d+)[ \t]*;")
MAX_DEPTH = 16
BANKS = ("ot_dp_st", "ot_dp_ste")


def relay_names(row):
    """flop instance names of a row, launch side first"""
    return [f"u_prl_{row['name']}_{j}" for j in range(int(row["depth"]))]


def apply(text, rows):
    """(RTL, receipts); an empty list leaves the bytes untouched"""
    if not rows:
        return text, []
    if not isinstance(rows, list):
        raise PortRelayError("port_relays must be a list")
    if len(DELIVERED.findall(text)) != 1:
        raise PortRelayError("port_relays needs exactly one delivered-reset alias `wire rst_n = arst_n;`")
    calls = RC._calls(text)
    names, sinks_seen, receipts, patches, add = set(), set(), [], [], []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"name", "depth", "sinks"}:
            raise PortRelayError(f"row needs exactly name, depth, sinks: {row}")
        name, depth, sinks = row["name"], row["depth"], row["sinks"]
        if not isinstance(name, str) or not _ID.fullmatch(name) or name in names:
            raise PortRelayError(f"bad or duplicate relay name {name!r}")
        names.add(name)
        if isinstance(depth, bool) or not isinstance(depth, int) or not 1 <= depth <= MAX_DEPTH:
            raise PortRelayError(f"{name}: depth must be an integer 1..{MAX_DEPTH}")
        if not isinstance(sinks, list) or not sinks:
            raise PortRelayError(f"{name}: sinks must be a non-empty list")
        insts = relay_names(row)
        for i in insts + [f"prl_{name}_{j}" for j in range(depth)]:
            if re.search(rf"\b{re.escape(i)}\b", text):
                raise PortRelayError(f"{name}: identifier {i} already exists in the emitted RTL")
        q_last = f"prl_{name}_{depth - 1}"
        for s in sinks:
            if not isinstance(s, str) or s in sinks_seen:
                raise PortRelayError(f"{name}: bad or duplicate sink {s!r}")
            sinks_seen.add(s)
            c = calls.get(s)
            if c is None or c["module"] not in BANKS:
                raise PortRelayError(f"{name}: sink {s} is not an emitted ot_dp_st")
            net, lo, hi = c["ports"].get("rst_n", (None, 0, 0))
            if net != "rst_n":
                raise PortRelayError(f"{name}: sink {s}.rst_n is {net!r}, not the delivered rst_n")
            patches.append((lo, hi, q_last))
        prev = "rst_n"
        for j, i in enumerate(insts):
            q = f"prl_{name}_{j}"
            add.append(f"    wire {q};")
            add.append(f"    (* keep = \"true\" *) ot_dp_rrelay {i} (.clk(clk), .d({prev}), .q({q}));  "
                       f"// reset.port_relays {name}: synchronous reset relay {j + 1}/{depth}")
            prev = q
        receipts.append(dict(name=name, depth=depth, relays=insts, sinks=list(sinks), reset=q_last))
    for lo, hi, q in sorted(patches, reverse=True):
        text = text[:lo] + text[lo:hi].replace("rst_n", q) + text[hi:]
    m = DELIVERED.search(text)
    text = text[:m.end()] + "\n" + "\n".join(add) + text[m.end():]
    return text, receipts


def apply_bank_taps(text, rows):
    """reset.bank_taps -> (RTL, receipts): bank rst_n pins re-pointed from the leaf tap to an equal-depth tree tap.
    Fail closed: one generated-tree leaf alias, every tap net declared, every sink an emitted bank on rst_n, no sink twice."""
    if not rows:
        return text, []
    if not isinstance(rows, list):
        raise PortRelayError("bank_taps must be a list")
    leaf = LEAF.findall(text)
    if len(leaf) != 1:
        raise PortRelayError("bank_taps needs exactly one generated reset-tree leaf alias `wire rst_n = rst_n_t<k>;`")
    calls = RC._calls(text)
    seen, patches, receipts = set(), [], []
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"tap", "sinks"}:
            raise PortRelayError(f"bank_taps row needs exactly tap, sinks: {row}")
        tap, sinks = row["tap"], row["sinks"]
        if isinstance(tap, bool) or not isinstance(tap, int) or tap < 0:
            raise PortRelayError(f"bank_taps: bad tap {tap!r}")
        net = f"rst_n_t{tap}"
        if not re.search(rf"\bwire\s+{net}\s*;", text):
            raise PortRelayError(f"bank_taps: reset tap net {net} is not declared in the emitted RTL")
        if not isinstance(sinks, list) or not sinks:
            raise PortRelayError(f"bank_taps tap {tap}: sinks must be a non-empty list")
        for s in sinks:
            if not isinstance(s, str) or s in seen:
                raise PortRelayError(f"bank_taps: bad or duplicate sink {s!r}")
            seen.add(s)
            c = calls.get(s)
            if c is None or c["module"] not in BANKS:
                raise PortRelayError(f"bank_taps: sink {s} is not an emitted ot_dp_st")
            pn, lo, hi = c["ports"].get("rst_n", (None, 0, 0))
            if pn != "rst_n":
                raise PortRelayError(f"bank_taps: sink {s}.rst_n is {pn!r}, not the leaf rst_n")
            if int(leaf[0]) != tap:
                patches.append((lo, hi, net))
        receipts.append(dict(tap=tap, reset=net, sinks=list(sinks), leaf=f"rst_n_t{leaf[0]}"))
    for lo, hi, net in sorted(patches, reverse=True):
        text = text[:lo] + text[lo:hi].replace("rst_n", net) + text[hi:]
    return text, receipts
