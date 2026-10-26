# Required native-pair leaf relay receipt

Gold2 unit `oth-ubuntu-2772044-1792605839` completed with exit 0. This bounded
run was launched before the coordinator's no-new-tests instruction and was
collected without a retry or additional launch. It extends the existing
RDPAIR/XRT/RSTOPT/VP component mechanism with the production slice's actual
`ot_s81sl_rly` W594 down and W667 up records, both at DL4. Each case transfers
one native 256-bit pair from actual VP SRAM, through the actual transport
blocks and relays, into actual destination SRAM. Extension readback checks all
256 bits. Both source and destination use leaf 0.

The three required paths pass with zero component faults and one destination
SRAM commit each. A typed-V input payload-bit corruption reaches SRAM but fails
readback (`bad=1`), so the scoreboard is sensitive to corrupted data. The
generated model passes the installed NBA guard with no findings or missing
source files; the full scan record is preserved.

| Point, relative to RDOUT CTL pin | Local | Typed V | Adjacent horizontal |
| --- | ---: | ---: | ---: |
| Raw XRT command output / VP input after DL4 | 5 / 9 | 5 / 9 | 5 / 9 |
| Raw VP pair output / XRT input after DL4 | 14 / 18 | 14 / 18 | 14 / 18 |
| Raw XRT CI output | 22 | 21 | 22 |
| RSTOP outward packet | internal | 23 | 24 |
| Raw receiving XRT write output | 25 | 29 | 30 |
| VP write input after DL4 | 29 | 33 | 34 |
| SRAM write commit | 30 | 34 | 35 |

All observers sample at posedge before NBA updates. The SRAM commit point is
the real bank-0 macro's asserted write-enable pin at its clock edge, rather
than the earlier XRT write output. A native pair writes both SRAM banks. The
benchmark statically places send-config CTL nine pin edges before RDOUT CTL;
it does not wait on an acknowledgement or completion to issue the transfer.
Readback occurs at a fixed later age. The local case uses the actual body-bit44
local-copy mode; typed V uses the real partner-only kind-4 V format; horizontal
uses a direct adjacent same-tier E link with zero test-wire age. No landed
wire or physical link latency is asserted.

`component_profile.json` preserves raw timestamps and the relative edge
measurements. These measurements support the component prices needed by the
existing 29-leg/58-CTL plan. They do not supply its producer-completion dates,
absolute CTL calendar, interrank exchange, link physical qualification or full
layer/token evidence. In particular, a longer route must separately price
its real links and intervening stops; its total is not this adjacent result.

`source_reconciliation.json` compares publication `c8bb7cf5e` with candidate
`286841a838132f393f3b387f2ecce0e20111c73b`. XRT, RSTOPT and VP match at the
whole-file level. The candidate's containing slice file differs because of
other integration changes, while the exact `ot_s81sl_rly` module text matches.
This component directly instantiates those modules. It does not establish
that main's normal slice selects XRT or adopts the candidate KV binding.

Source and runner are in `tools/s81_dv/rdpair_leaf4_1021`. The immutable fleet
root is `gold2:/srv/opentallas-scratch/claude/codex-s81-kv-vp-1021`; output is
`native_r1`. Existing KV binaries could not be reused for a different active
hierarchy with added relays and RSTOP/XRT, so this necessary component used a
new generated model; no progressing job or source was replaced.
