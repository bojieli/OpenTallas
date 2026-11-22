# S81 J7 placed review

Event `18a2688b741`. All three exact placement images were opened and reviewed. The dispositions apply only to the named producer kits.

| Item and attempt | Block | Verdict | Placed evidence |
| --- | --- | --- | --- |
| eng__t1 a2 | `97982ca70843` | BAD | `epyc9:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/items/eng__t1/attempt_2/gen/eng__t1/run/layout_review/place/layout.png` |
| serdes__t2 a1 | `97902619fe47` | BAD | `intel1:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/items/serdes__t2/gen/serdes__t2/run/layout_review/place/layout.png` |
| serdes__t1__clfe1f0815 a1 | `7cd6d6b377ed` | BAD | `epyc7:/srv/opentallas-scratch2/claude/kw43-wave-1109n/runs/s81/kit-wave/s81/18a2688b741/items/serdes__t1__clfe1f0815/gen/serdes__t1__clfe1f0815/run/layout_review/place/layout.png` |

- ENG retains the MX U_E shelf beside the lower macros. H and V cut demand are 2.01 and 2.854. The 571 long register captures reach 959.85 µm. The two XTIER input rings each have 243 of 276 over-reach captures on the ring-to-bin leg. The private U_E R0 alternative addresses the separate hard-core pin delivery and shelf geometry.
- t2 retains the long north PMA span and narrow south SRAM shelf. The exact x0[516] to x_q[516] capture spans 1,134.65 µm. There are 2,036 over-reach captures and 73 collapsed relay groups.
- clfe t1 retains the same north PMA wall, opposed E and W pin bands, and a crowded southern channel. The recovered transport to AM pre-stage reaches 1,288.01 µm. There are 1,284 over-reach captures and 376 collapsed relay groups. The x0 to x_q bank also has 247 of 544 over 405 µm.

Earlier admitted work remains available for diagnosis. Future identical-route decisions use these exact verdicts.

