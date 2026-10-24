"""BINDER2 10-23 (COORD R8): re-derive the Qwen compute collective calendar parameters from the BOUND lanes
(asbuilt.param_regen hook of tools/die_plan/bind.py).

The bound top dissolves qfd_collective_static_io_production: the SerDes legs (face phy_tx -> io_serdes_j tx_flit,
io_serdes_j rx_flit -> face phy_rx) and the core<->face relays (u_collective sx_j -> face tx_*, face rx_* ->
u_collective sr_j) become plan lanes of new depth, so the as-built LS / PHY / R parameters no longer match.  Rule
(tools/qwen_split/lane_groups.py collective_calendar, as STEWARD-TOKh tp8 used it on the bound top):
  TX_j = face[2+j].phy_tx -> io_serdes_j  depth,  RX_j = io_serdes_j -> face[2+j].phy_rx depth (flit == valid == up)
  RS_j = u_collective sx_j -> face[2+j] depth == face[2+j] rx -> u_collective sr_j depth (one relay depth per port)
  LX_j = TX(peer j) + RX_j,  LS = max_j KC + KW + 17 + PS + LX_j + RS_j + RS_peer(j)
Faces f=2..4: PHY = PS + LX_j, L = LS, R = RS_j, PEER_R = RS_peer(j); u_collective: LS.  UCIe faces 0/1 (RU) are
checked unchanged.  The ports used here are excluded from land_align (asbuilt.land_align_exclude): their timing is
carried by these parameters, not by as-built relative offsets."""
import sys
from pathlib import Path

C = "io_collective.u_io"
SER = ["io_serdes", "io_serdes_1", "io_serdes_2"]
PEER = {0: 2, 1: 1, 2: 0}


def _one(ctx, path, ports, what):
    v = set()
    for pn in ports:
        v |= set(ctx.depth(path, pn).values())
    if len(v) != 1:
        raise ValueError(f"{what}: {path} {ports} land at depths {sorted(v)} (one depth per leg required)")
    return v.pop()


def regen(ctx):
    tools = Path(sys.modules[type(ctx).__module__].__file__).resolve().parents[1]     # the binder's tools/
    sys.path.insert(0, str(tools / "qwen_split"))
    import lane_groups as LG
    face = lambda j: f"{C}.g_face[{2 + j}].u_face"
    TX = [_one(ctx, SER[j], ["tx_flit", "tx_v"], f"TX{j}") for j in range(3)]
    RX = [_one(ctx, face(j), ["phy_rx", "phy_rx_valid", "phy_up"], f"RX{j}") for j in range(3)]
    RS = []
    for j in range(3):
        t = _one(ctx, face(j), ["tx_data", "tx_valid", "tx_slot", "peer_slot"], f"RS{j} tx")
        r = _one(ctx, f"{C}.u_collective", [f"sr{j}_rec", f"sr{j}_valid"], f"RS{j} rx")
        if t != r:
            raise ValueError(f"RS{j}: core->face {t} vs face->core {r} stages (the face calendar takes one R per port)")
        RS.append(t)
    RU = [_one(ctx, f"{C}.g_face[0].u_face", ["tx_data", "tx_valid", "tx_slot", "peer_slot"], "RU0 tx"),
          _one(ctx, f"{C}.u_collective", ["dp_rec", "dp_valid"], "RU0 rx"),
          _one(ctx, f"{C}.g_face[1].u_face", ["tx_data", "tx_valid", "tx_slot", "peer_slot"], "RU1 tx"),
          _one(ctx, f"{C}.u_collective", ["dr_rec", "dr_valid"], "RU1 rx")]
    fp = {k: int(str(v).strip('"')) for k, v in ctx.F.cells[ctx.cell_index()[face(0)]].params.items()}
    if set(RU) != {fp["R"]}:
        raise ValueError(f"UCIe relay depths {RU} != as-built RU {fp['R']} (LU has no lane knob)")
    LX = [TX[PEER[j]] + RX[j] for j in range(3)]
    f2 = {k: int(str(v).strip('"')) for k, v in ctx.F.cells[ctx.cell_index()[face(0)]].params.items()}
    cal = LG.collective_calendar(LX, dict(RU=fp["R"], RS0=RS[0], RS1=RS[1], RS2=RS[2], PS=339), root=ctx.base)
    LS = cal["LS"]
    params = {f"{C}.u_collective": dict(LS=LS)}
    for j in range(3):
        params[face(j)] = dict(PHY=cal["PS"] + LX[j], L=LS, R=RS[j], PEER_R=RS[PEER[j]])
    return dict(params=params,
                record=dict(rule=__doc__.split("\n\n")[1], TX=TX, RX=RX, RS=RS, RU=fp["R"], LX=LX, LS=LS, calendar=cal,
                            bench_args=f"--relays {fp['R']} {RS[0]} {RS[1]} {RS[2]} --lanes {TX[0]} {TX[1]} {TX[2]} "
                                       f"{RX[0]} {RX[1]} {RX[2]} --lx {LX[0]} {LX[1]} {LX[2]}", ucie_face_params=f2))
