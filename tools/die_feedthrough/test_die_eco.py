"""die_eco.py: drop / insert / reconnect on a synthetic lane, bit order under mirrored blocks (reversed-bus catch)."""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import die_eco  # noqa: E402
import geom  # noqa: E402

NB = 4


def relay_masters():
    inv = {}
    for d in ("WE", "EW", "NS", "SN"):
        for w in (4, 2, 1):
            inv[f"tst_rly_{w}_{d}"] = {"i": w, "o": w, "ck": 1, "ck_o": 1, "rs": 1}
    inv["__outputs__"] = {m: {"o", "ck_o"} for m in inv}
    return inv


def spec(block, orient, x0):
    W, H = 1000.0, 200.0
    ports = [dict(name="ft0_i", path=0, dir="input", face="W", lo=80.0, hi=120.0, layer="M8", bits=NB),
             dict(name="ft0_o", path=0, dir="output", face="E", lo=80.0, hi=120.0, layer="M8", bits=NB)]
    if orient == "MX":     # master y flipped: plan.py wrote the master-frame band (inv_xform) = same die band
        for p in ports:
            p["lo"], p["hi"] = H - 120.0, H - 80.0
    return dict(schema=die_eco.SPEC_SCHEMA, block=block, master="tst_frame", variant="tst_frame__ft", outline=[W, H],
                orient=orient, die_bbox=[x0, 0.0, W, H], clock="forwarded",
                ports=ports, paths=[dict(path=0, lane="L0", **{"in": "ft0_i", "out": "ft0_o"}, bits=NB, stages=2)],
                _x0=x0)


def case(tmp_path):
    specs = [spec("u_b1", "R0", 1000.0), spec("u_b2", "MX", 2200.0)]
    sd = tmp_path / "ftspec"
    sd.mkdir()
    for s in specs:
        (sd / f"{s['block']}.json").write_text(json.dumps(s))
    lane = dict(id="L0", src="u_src", src_bus="x", dst="u_dst", dst_bus="x", bits=NB, keep_channel=False,
                pts=[[0.0, 100.0], [4000.0, 100.0]],
                segments=[dict(kind="block", block="u_b1", t_in=1000.0, t_out=2000.0),
                          dict(kind="block", block="u_b2", t_in=2200.0, t_out=3200.0)],
                channel_regs_t=[500.0, 3600.0])
    dropped = ["r0", "r1", "r2"]
    bits = [dict(src_bit=f"x[{k}]", a_pin=f"u_src/x[{k}]", a_net=f"src_x{k}", b_pin=f"u_dst/x[{k}]",
                 b_old_net=f"old{k}", in_pin=f"i[{k}]", out_pin=f"o[{k}]") for k in (2, 0, 3, 1)]   # unsorted on purpose
    chains = dict(lanes=[dict(lane="L0", status="ok", subchains=[dict(
        dropped=dropped, masters={r: "tst_rly_4_WE" for r in dropped}, width=NB, bits=bits,
        chained=[dict(out_pin="ck_o", in_pin="ck", kind="fclk", head_net="fclk_head", tail_sinks=["u_dst/ck_f"])],
        static={r: dict(xy=[1000.0 * i, 100.0], master="tst_rly_4_WE", pins={"rs": f"rst_{i}"})
                for i, r in enumerate(dropped)})])], dropped_all=dropped)
    plan = dict(lanes=[lane])
    return sd, plan, chains, specs


def netlist(tcl):
    """ft_conn net inst pin -> {(inst, pin): net}; ft_inst name master -> {name: master}."""
    conn, inst = {}, {}
    for ln in tcl.splitlines():
        m = re.match(r"ft_conn \{(.*?)\} \{(.*?)\} \{(.*?)\}$", ln)
        if m:
            conn[(m.group(2), m.group(3))] = m.group(1)
        m = re.match(r"ft_inst \{(.*?)\} (\S+) ", ln)
        if m:
            inst[m.group(1)] = m.group(2)
    return conn, inst


def trace(conn, inst, net):
    """follow net through new relays (i[k]->o[k]) and blocks (ft0_i[k]->ft0_o[k]) to a non-ECO sink pin."""
    hops = []
    for _ in range(50):
        sinks = [(i, p) for (i, p), n in conn.items() if n == net and not re.match(r"^(o|ft0_o|ck_o)(\[|$)", p)]
        assert len(sinks) == 1, (net, sinks)
        i, p = sinks[0]
        m = re.match(r"^(i|ft0_i)\[(\d+)\]$", p)
        if not m:
            return (i, p), hops
        hops.append((i, m.group(1), int(m.group(2))))
        net = conn[(i, ("o" if m.group(1) == "i" else "ft0_o") + f"[{m.group(2)}]")]
    raise AssertionError("loop")


def die_pos(s, port, k):
    q = next(p for p in s["ports"] if p["name"] == port)
    W, H = s["outline"]
    y = q["lo"] + (q["hi"] - q["lo"]) * k / (q["bits"] - 1)
    x = 0.0 if q["face"] == "W" else W
    return geom.xform(x, y, W, H, s["orient"], s["_x0"], 0.0)


def test_drop_insert_reconnect(tmp_path):
    sd, plan, chains, _ = case(tmp_path)
    js, tcl = die_eco.gen(sd, plan, chains, relay_masters())
    assert js["relays_dropped"] == 3 and js["relays_new"] == 2, js
    assert js["lanes_with_problems"] == 0, js["lanes"]
    conn, inst = netlist(tcl)
    assert set(inst.values()) == {"tst_rly_4_WE"}               # exact cover, direction from the route
    for name in inst:                                          # no open input on a new relay
        for pin in ("i[0]", "i[1]", "i[2]", "i[3]", "ck", "rs"):
            assert (name, pin) in conn, (name, pin)
    assert "{r0} {r1} {r2}" in tcl and "dbInst_destroy" in tcl
    for k in range(NB):                                        # end to end: src bit k -> dst bit k
        end, hops = trace(conn, inst, f"src_x{k}")
        assert end == ("u_dst", f"x[{k}]"), (k, end)
        assert [h[0] for h in hops][:1] == ["ft_L0_0_0_r0"] and len(hops) == 4
    assert conn[("u_dst", "ck_f")].startswith("ft_L0_0_3")     # forwarded clock chained through to the tail


def test_mirrored_block_keeps_die_track_order(tmp_path):
    """a reversed bus (lane bit order flipped across the MX block) puts bit k on the opposite die track: caught."""
    sd, plan, chains, specs = case(tmp_path)
    js, tcl = die_eco.gen(sd, plan, chains, relay_masters())
    conn, inst = netlist(tcl)
    by = {s["block"]: s for s in specs}
    for k in range(NB):
        _, hops = trace(conn, inst, f"src_x{k}")
        blk = [(i, b) for i, kind, b in hops if kind == "ft0_i"]
        (b1, i1), (b2, i2) = blk
        y_out1 = die_pos(by[b1], "ft0_o", i1)[1]
        y_in2 = die_pos(by[b2], "ft0_i", i2)[1]
        assert abs(y_out1 - y_in2) < 1e-6, (k, y_out1, y_in2)     # same die track on both sides of the gap
    assert die_eco.port_flipped(by["u_b2"], "ft0_i") and not die_eco.port_flipped(by["u_b1"], "ft0_i")


def test_reversed_bus_is_detected(tmp_path, monkeypatch):
    """negative control: with the orientation mapping disabled the same check fails (the bus crosses itself)."""
    sd, plan, chains, specs = case(tmp_path)
    monkeypatch.setattr(die_eco, "port_flipped", lambda spec, name: False)
    js, tcl = die_eco.gen(sd, plan, chains, relay_masters())
    conn, inst = netlist(tcl)
    by = {s["block"]: s for s in specs}
    bad = 0
    for k in range(NB):
        _, hops = trace(conn, inst, f"src_x{k}")
        (b1, i1), (b2, i2) = [(i, b) for i, kind, b in hops if kind == "ft0_i"]
        bad += abs(die_pos(by[b1], "ft0_o", i1)[1] - die_pos(by[b2], "ft0_i", i2)[1]) > 1e-6
    assert bad == NB


def test_exact_cover_no_tieoff(tmp_path):
    sd, plan, chains, _ = case(tmp_path)
    inv = relay_masters()
    pick = die_eco.Inventory(inv).pick("tst_rly_4_WE", 7, "NS")
    assert sorted(w for _, w, _ in pick) == [1, 2, 4] and all(m.endswith("_NS") and not n for m, _, n in pick)
    inv.pop("tst_rly_1_NS")      # 7 bits NS without a 1-bit NS relay: a 7-bit kit is requested, never a wider relay
    pick = die_eco.Inventory(inv).pick("tst_rly_4_WE", 7, "NS")
    assert pick == [("tst_rly_7_NS", 7, True)]
    assert die_eco.direction([(0, 0), (0, -10)], 5) == "NS" and die_eco.direction([(0, 0), (-9, 0)], 1) == "EW"


def test_missing_spec_path_reported(tmp_path):
    sd, plan, chains, _ = case(tmp_path)
    (sd / "u_b2.json").unlink()
    js, _ = die_eco.gen(sd, plan, chains, relay_masters())
    assert any("u_b2" in p for p in js["lanes"][0]["problems"])
    js, tcl = die_eco.gen(sd, plan, chains, relay_masters(), blocks_as_wire=True)
    assert js["lanes_with_problems"] == 0 and "ft0_i" not in tcl


def test_station_local_reset_register_recreated(tmp_path):
    """S81 stations carry a reset flop on the forwarded clock (rfw_* DFFHQN -> INV -> rs): every new stage gets its own,
    clocked by the clock arriving at that stage, D from the die reset net; the old ones are listed for deletion."""
    sd, plan, chains, _ = case(tmp_path)
    sc = chains["lanes"][0]["subchains"][0]
    for i, r in enumerate(sc["dropped"]):
        sc["static"][r]["pins"].pop("rs")
        sc["static"][r]["local_regs"] = {"rs": dict(flop=f"rfw_{i}", flop_master="DFFHQNx1_ASAP7_75t_R", flop_out="QN",
                                                    d_net="die_rst", ck_net=f"fck{i}", path=[f"rfwi_{i}"], n_inv=1)}
    chains["dropped_cells"] = [f"rfw_{i}" for i in range(3)] + [f"rfwi_{i}" for i in range(3)]
    js, tcl = die_eco.gen(sd, plan, chains, relay_masters())
    assert js["local_regs_new"] == 2 and js["lanes_with_problems"] == 0, js
    conn, inst = netlist(tcl)
    st0 = "ft_L0_0_0_r0"
    assert conn[(f"{st0}_lr_rs", "CLK")] == "fclk_head" and conn[(f"{st0}_lr_rs", "D")] == "die_rst"
    assert conn[(st0, "rs")] == conn[(f"{st0}_lr_rs_inv", "Y")]
    st3 = "ft_L0_0_3_r0"                               # after both blocks: clocked by u_b2's forwarded clock out
    assert conn[(f"{st3}_lr_rs", "CLK")] == "u_b2_ft0_ck_o"
    assert "{rfw_0} {rfw_1} {rfw_2}" in tcl


def test_reset_pipeline_rechained(tmp_path):
    """S81 reset pipeline: rfw_k.D = rs of station k-1.  The new stages chain the same way and the kept element after
    the run takes the last new stage's rs."""
    sd, plan, chains, _ = case(tmp_path)
    sc = chains["lanes"][0]["subchains"][0]
    for i, r in enumerate(sc["dropped"]):
        sc["static"][r]["pins"]["rs"] = f"rs_{i}"
        sc["static"][r]["local_regs"] = {"rs": dict(flop=f"rfw_{i}", flop_master="DFFHQNx1_ASAP7_75t_R", flop_out="QN",
                                                    d_net="rst_in" if i == 0 else f"rs_{i - 1}", path=[f"rfwi_{i}"],
                                                    n_inv=1)}
    sc["reset_chain"] = {"rs": dict(head="rst_in", tails=["u_dst/rfw_D"])}
    js, tcl = die_eco.gen(sd, plan, chains, relay_masters())
    conn, _ = netlist(tcl)
    s0, s3 = "ft_L0_0_0_r0", "ft_L0_0_3_r0"
    assert conn[(f"{s0}_lr_rs", "D")] == "rst_in"
    assert conn[(f"{s3}_lr_rs", "D")] == conn[(s0, "rs")]          # pipelined: stage 3 resets from stage 0
    assert conn[("u_dst", "rfw_D")] == conn[(s3, "rs")]
