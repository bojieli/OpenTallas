# PG stream release-return CDC publication

Release kit uses READ_RETURN18/WRITE_RETURN15. The stream-local fault publication register resets with the stream leaf reset only. The serial bridge reset no longer enters its D cone; exact serial two-stage fault synchronization remains. The data bank calendar and windows do not change. Fault publication adds one stream edge, already priced by the prior kit.

Verilator5.050 on fleet ot-epyc7: legacy10/7, registeredrelease18/15, registered10/7 andQID0release18/15 pass. Mutants13(invertedsource),14(serialbridge reset wrongly clears streamfault),12(requestwindow),3(returnwindow),2(wrongrequestbank),8(wronginjectbank) allfail. Source hashes, build/runtime logs and exact receipts are alongside.

Functional evidence only; fresh current-tool CDC lint and CTS gate plus routed/nativeTTFF closure remain required. Prior failed gates and old10/7 witnesses remain historical.
