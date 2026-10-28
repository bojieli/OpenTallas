import sys, json
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-head-9-face/tools/die_plan")
import face_guard as F
K = "/srv/opentallas-scratch2/claude/codex-head-die-1028-0405/kits_countsites_fullpin/hd_tile"
net = open(K + "/run/results/asap7/dp_hd_tile/base/1_2_yosys.v").read()
pins = json.load(open(K + "/pins.json"))
ck = F.sdc_clock_ports(open(K + "/constraint.sdc").read())
land = F.kit_land("land_slots_hd_tile.json")
ft1 = F.read_ft1(K + "/ft_stations.txt")
sl = F.kit_strap_list(K)
bl = F.kit_bump_list(K)
def run(t):
    g = F.guard(t, None, pins=pins, ft1=ft1, straps=sl, bumps=bl, clocks=ck, land=land)
    return dict(verdict=g["verdict"], land_mux_bits=g.get("land_mux_bits"), fails=g["fail_counts"], why={k: v[:3] for k, v in g["fails"].items() if k == "land_slot"})
a = "  AND3x1_ASAP7_75t_R _12808_ (\n    .A(_06161_),\n    .B(d[5]),\n    .C(_06159_),"
b = "  AND3x1_ASAP7_75t_R _11492_ (\n    .A(_07679_),\n    .B(d[5]),\n    .C(_05411_),"
assert net.count(a) == 1 and net.count(b) == 1
muts = {"real": net,
        "M1_nonexclusive_enable": net.replace(a, a.replace("_06161_", "_07679_").replace("_06159_", "_05411_")),
        "M2_load_moved_d5_to_d6": net.replace(b, b.replace("d[5]", "d[6]")),
        "M3_enable_tied_high": net.replace(b, b.replace(".A(_07679_)", ".A(1'b1)").replace(".C(_05411_)", ".C(1'b1)"))}
out = {k: run(v) for k, v in muts.items()}
json.dump(out, open("real_mutants.json", "w"), indent=1)
for k, v in out.items(): print(k, json.dumps(v)[:500])
