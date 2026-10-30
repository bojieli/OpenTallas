module tb;wire a,b,c;probe0 p(a);probe1 q(b);probe2 r(c);always @(a or b or c)if(a&&b&&c)$finish;initial begin #30000;$fatal(1,"timeout");end endmodule
