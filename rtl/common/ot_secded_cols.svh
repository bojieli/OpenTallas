// ot_secded columns (included inside the modules): column i = the i-th R-bit value of odd weight >= 3, increasing;
// all K columns are one elaboration-time constant (COLS[16 i +: 16]).
function automatic [256*16-1:0] cols_all(input integer kk, input integer rr);
  integer v, n, w, b;
  begin
    cols_all = 0; n = 0;
    for (v = 1; v < (1 << rr); v = v + 1) begin
      w = 0; for (b = 0; b < rr; b = b + 1) w = w + ((v >> b) & 1);
      if ((w & 1) && w >= 3 && n < kk) begin cols_all[16*n +: 16] = v[15:0]; n = n + 1; end
    end
  end
endfunction
