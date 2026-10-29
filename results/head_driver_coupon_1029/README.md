HEAD START branch driver prebuild coupon

NativeOpenSTA TT+FF using pinnedASAP7 INVBUF_RVT_{TT,FF}_nldm_220122 libraries. Requested100psinputtransition; INVx1load15fF andBUFx8load34.7049fF. Same833psvirtualclock60/25policy; thisisstandard-cell characterization, notphysicalsignoff.

TT INVx1rise/falldelay98.820587/85.669052ps andslew143.686600/114.197929ps; FF74.572639/65.930832delay,105.084297/90.020569slew. TT BUFx8delay64.547539/68.911728ps,slew48.189510/40.489437ps; FF47.939728/52.494926delay,34.997482/30.979097slew. No maxcap/slewviolatorsforrequestedlumpedloads. TheseareYpinnumbers, notfarendwire.

Extraonehopπmodel uses185.166um,R4919.5643544ohm,C34.704922716fF,halfCeachend,plus0.852fFdownstreambufferinput. WireCisSPEFonly; outputset_loadis0.852only, nodoublecount. Elmorefirstmoment85.366550358ps; nativeDMP50%delaydiffers. TTfarendtotaldelay123.213882/127.815811ps,slew214.192352/211.393921ps; FF107.406616/112.042557delay,208.015182/207.046082slew. Thisonehopmodel staysbelow320psslew. No physicalRC/phase/FFhold/clockpairclaim. Inputtransitionfixed100ps, nottheINV143psoutputcomposedwithbufferinput.

InitialπreadoutfailedbecausePortobjectshavenoarrivalproperty; convertedtosameport'sPinusingsta::get_port_pin,andkeptoldfailedlog. Jobs2633666/2672542 bothot-run4GB1threadexit0onintel1;2672542correctsfailed2658970harness. Inputs/scripts/readoutsstoredhere; librarybinariesremainhostinputs.

The sameπ-hop at incoming320ps alsoPASSes bothcorners: TTfarendslew215.873795/214.138184ps,totaldelay151.930634/164.099289ps; FF209.114777/208.893799slew,125.584915/139.602554delay. Maximumfarendslew215.873795ps leaves104.126205ps versus320. With the unchangedonehopR/C/downstream.852fF andlibrarymodel, this maps incoming≤320 tofarend<320 and supports chainedrepeaters as a prebuildestimate. INVx1 at15fF/incoming320 givesTTslew200.187439/166.224960ps andFF157.325302/136.618927ps. These remain standard-cell/analyticwire estimates, notroutedclock timing or proof forotherloads. Unit2713260-1793271776 ot-run4GB1threadexit0.
