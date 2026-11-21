# QC V1 retained ST placement review, 2026-11-21

Viewed actual run/layout_review/place/layout.png for the five obsolete pre-CTS stop attempts. All place checkpoints are retained. The exact job IDs and original paths are also in autopilot/state.json.

| Job | Item and source | Placement observations |
| --- | --- | --- |
| 1c9b150b59df | slw_st_a_v1__clfc5867a6__pvdf8e5ca4 a2, epyc8 | Four separated core rows. East/lower landing strips and three memory macros are close. Broad west aisle. |
| 1abde1f9b66b | slw_st_a_v1__clfc5867a6__pvf82a6c28 a3, epyc9 | Same separated core form. Different north-facing pin distribution. Landing strip constricts the southeast approach. |
| 9b067d713a24 | slw_st_a_v2__clf4365a62 a3, epyc8 | Four separated central cores. East memory bank beside the landing strip and a south edge companion. |
| d8b78b1b1596 | sle_st_a_v1__cl67389ecd a3, epyc8 | East landing strip extends to the south boundary. Fourth memory macro bridges the middle to the east set. |
| 95a3876c5b24 | sle_st_a_v2__pv30dda31f__pv88773f93 a4, epyc9 | East stack and landing strip leave a tight lower approach. Central tap cluster and open space between core rows. |

PASS for a read-only corrected ideal-clock TT measurement on each exact existing 3_place checkpoint. Existing routed signal, clock insertion and PDN continuity are outside what these placement images establish. Use corrected TT values and path attribution before a CTS or route decision. No baseline evidence is overwritten.
