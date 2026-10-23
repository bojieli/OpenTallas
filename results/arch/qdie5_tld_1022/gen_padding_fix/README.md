# TREQ bundle padding on the actual r51 command path

The first actual TREQ-on GEN fails before emission: dvw_treq_wi needs landingMCP7 > D-1=3. The existing command lane has a source-bound measured E_sta7 with positive TT/FF hold facts (h0TT4871.4/FF3589.1). Early frame_pads incorrectly treats that measured command as unproven, pads the command itself and raises group target19->23 after padding the new TREQ for19. The later equalizer already accepts the original command's measured hold window; the early padding stage must use the same facts.

The fix passes those existing TT/FF facts only for the new DV.treq.ctlm bundle. It keeps command E19 and E_sta7, adds10 registered stations to TREQ (n24->34, ownE18), and gives TREQ only one wait edge (E_sta3). No command cycle, ring depth, clock phase, uncertainty or exception changes. Every new/unmeasured lane keeps the D-1 limit. Insufficient hold or missing TT/FF facts fail. All other bundles and default-off behavior retain the existing calculation.

Four focused padding checks pass, including insufficient-hold, partial-corner and unproved-window negatives; the seven existing bundle tests and three TT-endpoint tests pass. Full actual GEN replay remains required; no GEN PASS is claimed from these component checks.
