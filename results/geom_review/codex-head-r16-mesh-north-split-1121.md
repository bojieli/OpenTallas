# HEAD r16 mesh north pin access · 2026-11-21 16:16 PST

Viewed candidate `epyc9:/srv/opentallas-scratch3/claude/head-crossing-1119/mesh_n_access_1606/candidate/north_split_review.png`. This is the measured north M5/M7 cutout from the exact baseline placed ODB `ceef0df491bd` and corrected ODB `41595cc1c781`. The plan draft is `27bc1919c186`.

The original [362.880, 1224.990]–[392.634, 1226.610] µm reserved clock site created a blanket M1–M7 obstruction immediately beneath 27 residual BTerms. The frozen native tree `564220a7b28e` places the two covered stacks in the rectangle’s ends. Their union is the original bounding box. The revised site retains full placement and M1–M2 blockage. On M3–M7 it reserves the two actual stack windows, opening 25.434 µm in the center. Twenty-four affected BTerms have unobstructed direct x access through that gap. The other three remain adjacent to clock-stack ends and require actual GRT access evidence. The existing M8 keepout, south/center geometry, and west lane-B form are untouched by this one-row correction.

OpenROAD reread found all 27 BPin boxes identical. The prepared-plan generator retained the same placement blockages. Exact port evaluation preserved all 3,084 tracks across the three paired boundaries (`lk_EN0`, `lk_WS0`, `lk_ES0`), including bit order and M5/M7 assignment. The proof uses the same fixed placement and retains its existing PDN cut.

Verdict GRT-only candidate. Inspect actual north residuals, clock NDR, TT setup and FF hold before considering detail route.

The first two private continuations kept their failure records. Unit 2839410 used a copied pre-CTS reader that incorrectly propagated clocks. Unit 2893051 reached CTS after correcting that reader and hit the old kit’s missing `tb_cdirect` variable. The successor unit `oth-ubuntu-3170691-1795308248` uses the standard b7f3ee33e39f flow refresh, the same exact 41595cc1c781 placed ODB and the unchanged nominal gate. Its five ideal-clock setup check passed at TT +57.99 ps with TNS 0. The actual whole placed layout and density images under `active_ideal/hd_mesh/run/layout_review/place/` were also viewed. The north access geometry still needs GRT evidence.
