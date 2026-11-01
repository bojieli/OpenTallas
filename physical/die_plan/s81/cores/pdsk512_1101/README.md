PDSK512 opt-in physical candidates

The recipes in this directory create separate trial kits; the production recipes and default RTL parameters stay unchanged. Run the canonical generator from the repository root, for example:

```sh
python3 physical/die_plan/s81/cores/legacy/gen_core_kit_legacy.py \
  --module ot_s81sl_xrt1_pdsk512_m70 \
  --recipes physical/die_plan/s81/cores/pdsk512_1101/recipes.json \
  --out "$CANDIDATE_KITS" --trial --suffix pdsk512_m70
```

Use a current Yosys frontend when generating XRT3: its canonical `rtl_dirs: true` obtains directions from RTL while retaining the actual plan pin table. The old declared LEF carries different layers and is not the current pin contract. Outlines and face positions come from the current die plan, not the historical reference spec outline. These profiles are preparation only; a frozen source-bound plan slice and matching signed views are required for adoption. `--trial` is explicit and does not create a release kit.

Each master has setup-repair margins70/110ps as two physical variants, with two-mode TT setup/FF hold and identical functional parameters PDSK512, FACE_LAND1, FOREG0, QDELAYS0. The candidate changes returning partial delays by[-4,-3,-2,0,0] and removes297 logical FF per XRT. Matching the external output anchor requires current compiler programme alignment; the component equation is not a global zero-cycle claim. External ports and widths stay unchanged.

Exactness prerequisite: f6db9345e, results/token_pass/norm_leaf_calendar_1101/{impact.md,pdsk_lockstep.json,pdsk_lockstep.log}:3220 edge checks,640 total words,0errors, wrong-depth576 mutant caught in both masters. That proof covers aligned returning interfaces; full issuer/calendar/token qualification remains outstanding.

Review the pin plan before placement; stop fresh flow at `place`, render and personally inspect3_place geometry, then record a short verdict before CTS/GRT/route. Preserve old and failed evidence. Do not adopt or merge these profiles automatically.
