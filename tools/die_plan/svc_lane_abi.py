"""Pin the native S81 R11 SVC lane order when preparing independently reused kits."""
import argparse
import hashlib
import json
from pathlib import Path
import re

SCHEMA = "opentallas.s81_svc_lane_abi.v1"
LANES = "L1 L14 L20 L22 L38 L39 L52 L53 L67 L78 L93".split()


def digest(value):
    return hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest()


def rows(bind_out):
    def load(name, key):
        table = json.loads((bind_out / name).read_text())[key]
        selected = [row for row in table if row["lane"] in LANES]
        if sorted(row["lane"] for row in selected) != sorted(LANES):
            raise ValueError(f"{name} missing or duplicating a scoped lane")
        return {row["lane"]: row for row in selected}

    return load("bind_latency.json", "buses"), load("bind_lane_asbuilt.json", "lanes")


def snapshot(bind_out, type_name=None):
    bind_out = Path(bind_out)
    lat, ages = rows(bind_out)
    rtl = bind_out / "rtl"
    top = (rtl / "s81_bound_top.sv").read_text()
    lanes = {}
    for lane in LANES:
        row, age = lat[lane], ages[lane]
        endpoint = dict(width=row["width"], delivered=age["delivered"],
                        source_bits_sha256=digest(row["source_bits"]))
        if (row["source_bit_order"] != "lsb_first" or len(row["source_bits"]) != row["width"] or
                age["verdict"] != "PASS" or age["delivered"] != row["plan_cycles"]):
            raise ValueError(f"{lane} has an invalid source bit order, width or age")
        for side, port_key, face in (("src", "bus_out", "bout"), ("dst", "bus_in", "bin")):
            tn, inst, port = age[side + "_type"], row[side], row[port_key]
            if type_name is not None and tn != type_name:
                continue
            if (age[side], age[port_key]) != (inst, port):
                raise ValueError(f"{lane} {side} timing endpoint differs from ordered source table")
            instance = re.search(r"^    (\w+) [^\n]*\b" + re.escape(inst) + r" \(\n(.*?)^    \);",
                                 top, re.M | re.S)
            if not instance:
                raise ValueError(f"{lane} missing top instance {inst}")
            attach = re.findall(r"^\s*\." + re.escape(port) + r"\(([^\n]+?)\)", instance[2], re.M)
            if len(attach) != 1:
                raise ValueError(f"{lane} missing or duplicate top port {inst}.{port}")
            wrapper = (rtl / (instance[1] + ".sv")).read_text()
            face_name = f"u_{face}_{port}"
            body = [line.split("//", 1)[0].strip() for line in wrapper.splitlines()]
            register = [line for line in body if re.search(r"\b" + re.escape(face_name) + r"\b", line)]
            if len(register) != 1:
                raise ValueError(f"{lane} missing or duplicate RTL register {face_name}")
            witness = dict(type=tn, instance=inst, port=port, module=instance[1], connection=attach[0],
                           face_sha256=digest(register[0]))
            if side == "dst":
                # Include exact lane-index use and the actual native ROM truth of local consumers.
                uses = [line for line in body if re.search(r"\b" + re.escape(port) + r"_q\b", line)]
                native_roms = {}
                used = "\n".join(uses)
                for line in body:
                    rom = re.fullmatch(r"(ot_bind_native_[0-9a-f]+) \w+ \((.*?)\.RD_DATA\((w_\w+)\)\);", line)
                    if rom and re.search(r"\b" + re.escape(rom[3]) + r"\b", used):
                        master = rtl / "native_glue" / (rom[1] + ".sv")
                        native_roms[rom[3]] = [line, hashlib.sha256(master.read_bytes()).hexdigest()]
                witness["consumers_sha256"] = digest([sorted(uses), native_roms])
            endpoint[side] = witness
        if "src" in endpoint or "dst" in endpoint:
            lanes[lane] = endpoint
    return dict(schema=SCHEMA, lanes=lanes)


def check_type(reference_path, bind_out, type_name, module=None, instance=None):
    reference = json.loads(Path(reference_path).read_text())
    if reference.get("schema") != SCHEMA or set(reference.get("lanes", {})) != set(LANES):
        raise ValueError("invalid SVC ordered ABI reference scope")
    expected = {}
    for lane, row in reference["lanes"].items():
        roles = {side: row[side] for side in ("src", "dst") if row[side]["type"] == type_name}
        for role in roles.values():
            if module is not None and role["module"] != module:
                raise ValueError(f"{lane} {type_name}: selected bound module {module} differs from {role['module']}")
            if instance is not None and role["instance"] != instance:
                raise ValueError(f"{lane} {type_name}: selected bound instance {instance} differs from {role['instance']}")
        if roles:
            expected[lane] = {k: v for k, v in row.items() if k not in ("src", "dst")} | roles
    if not expected:
        return []
    actual = snapshot(bind_out, type_name)["lanes"]
    mismatches = [lane for lane in LANES if expected.get(lane) != actual.get(lane)]
    if mismatches:
        raise ValueError(f"{type_name}: ordered ABI differs on {', '.join(mismatches)}")
    return sorted(expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bind_out", type=Path)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    args.write.write_text(json.dumps(snapshot(args.bind_out), indent=2) + "\n")


if __name__ == "__main__":
    main()
