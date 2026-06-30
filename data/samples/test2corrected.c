#include <stdio.h>
int assign_bool(int x,int y){ if (x == y) return 1; return 0; }
int explicit_zero(int z){ if (z != 0) return 1; return 0; }
int eq_double(double a,double b){ double d = (a > b) ? (a - b) : (b - a); return d < 1e-9; }
int float_for(void){ int c = 0; for (int i = 0; i < 6; i++) c++; return c; }
int for_side(void){ int c = 0; for (int i = 0; i < 3; i++) { printf("t"); c++; } return c; }
int main(void){
    int r1 = assign_bool(0,1);
    int r2 = explicit_zero(5);
    int r3 = eq_double(0.1,0.1);
    int r4 = float_for();
    int r5 = for_side();
    printf("%d %d %d %d %d\n", r1, r2, r3, r4, r5);
    return 0;
}