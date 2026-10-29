Fresh KV core kits with --master-slice were not self-contained: gen_core_kit_kv
loaded the original plan pin table, recorded its hashes in freeze.json and
placed the pins, but did not copy that table into the kit. The standalone
kit_contract.pins_canonical gate requires that exact table to judge the
slice's placements. It could work accidentally where an old recipe manually
copied the pin basename, then fail on a clean fresh kit.

Measured counterexample: PHY pad d243d1cfeca8bf5e, autopilot4f1fb8c68d90,
source0fb27d2292. Admission stopped before the physical runner:
  KIT_PREFLIGHT FAIL issues1
  pins_canonical: slice kit: plan pin file (freeze pins_file) not reachable
No timing/geometry failure, no timing rule changed.

Fix: copy the exact input pin file as KIT/plan_pins.json immediately after
loading it and before generating freeze/hash/provenance. Existing contract
logic already discovers that filename and verifies whole-file SHA and
canonical placement after the slice.

Actual repaired successor: original pin table SHA256
9a8a33e72a55cea5b5efe47fbccbc39002ca276f0ed39557edd8e37569b71c4f
matches freeze.pins_sha256. Same RTL/clocks/pins/3_place placement/LEC,
only the missing documentary snapshot bundled. Using the exact autopilot
admission kit_preflight from ea11636aef37d37a7f66, --contract:
  KIT_PREFLIGHT PASS issues0
  ot-run unit oth-ubuntu-2306886-1793259341 exit0.
No broad tests or physical reruns for this packaging fix. Prior failed
admission log retained in the old autopilot job directory. Successor route
kit is intel2:.../codex-kv-phy-pad-1028/routekit/qkd_hr_phy_pad__86.4x95.04.
