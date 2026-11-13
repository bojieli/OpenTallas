#!/usr/bin/env python3
"""QC-S28-CTLCAP guarded kit_source_station_pricing inject (QC-BIND-IST-PAD, bind.py claude/qc-bind-ist-pad-1112).

bind.py reads kit_source_station_pricing from self.ab. With --asbuilt MANIFEST that is the manifest: load_plan replaces
the plan's own `asbuilt` section, so a plan-side key would be dropped silently (same as clock_merge / cm_inject.py).
The value comes from the sibling <plan stem>.kit_pricing.json (opentallas.qc_kit_source_pricing.v1:
{"kit_source_station_pricing": true | [types], "manifest_sha256": <sha256 of the manifest it was made for>}) or $KP_FILE.

  make   PLAN MANIFEST [VALUE_JSON]       write the sibling (default VALUE true) bound to MANIFEST's sha256
  inject PLAN MANIFEST OUT_MANIFEST       fail closed (exit 3): no sibling; manifest sha differs; OUT not beside MANIFEST
                                          (map_file paths resolve relative to the manifest folder); the manifest already
                                          carries a different value. Same value already present -> byte copy (idempotent).
  check  BIND_LOG                         exit 4 if the bind log reports any KIT_ISTATION_LATENCY
"""
import hashlib, json, os, re, sys
from pathlib import Path


def die(rc, msg):
    print("KP FAIL", msg)
    sys.exit(rc)


def sib(pl):
    return os.environ.get("KP_FILE") or re.sub(r"\.json$", ".kit_pricing.json", pl)


def main(a):
    if a[0] == "make":
        pl, man = a[1], a[2]
        val = json.loads(a[3]) if len(a) > 3 else True
        rec = dict(schema="opentallas.qc_kit_source_pricing.v1", kit_source_station_pricing=val,
                   manifest_sha256=hashlib.sha256(Path(man).read_bytes()).hexdigest(),
                   note="QC-BIND-IST-PAD: price kit-built source stations once; table refreshed by ctlcap_apply op 5")
        Path(sib(pl)).write_text(json.dumps(rec, indent=1) + "\n")
        print("KP MADE", sib(pl), rec["manifest_sha256"][:12])
    elif a[0] == "inject":
        pl, man, out = a[1], a[2], a[3]
        s = sib(pl)
        if not Path(s).exists():
            die(3, f"no sibling {s}")
        rec = json.loads(Path(s).read_text())
        mb = Path(man).read_bytes()
        if hashlib.sha256(mb).hexdigest() != rec.get("manifest_sha256"):
            die(3, f"manifest sha {hashlib.sha256(mb).hexdigest()[:12]} != sibling {str(rec.get('manifest_sha256'))[:12]}")
        if Path(out).resolve().parent != Path(man).resolve().parent:
            die(3, "OUT_MANIFEST must sit beside MANIFEST")
        m = json.loads(mb)
        cur = m.get("kit_source_station_pricing")
        if cur is not None and cur != rec["kit_source_station_pricing"]:
            die(3, f"manifest already has a different kit_source_station_pricing {cur!r}")
        m["kit_source_station_pricing"] = rec["kit_source_station_pricing"]
        Path(out).write_text(json.dumps(m, indent=1) + "\n")
        print("KP INJECT", out, hashlib.sha256(Path(out).read_bytes()).hexdigest()[:12])
    elif a[0] == "check":
        bad = [ln for ln in Path(a[1]).read_text().splitlines() if "KIT_ISTATION_LATENCY" in ln]
        print("KP CHECK", len(bad), "KIT_ISTATION_LATENCY")
        if bad:
            print("\n".join(bad[:20]))
            sys.exit(4)
    else:
        die(2, __doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
