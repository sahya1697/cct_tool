#include <stdio.h>
int process(int x);
int sw_case(int a);
int eq_double(double a, double b);
int float_loop(int n);
int main(void)
{
    int v = process(-1);
    int s = sw_case(0);
    int loops = float_loop(5);
    int eq = eq_double((0.1 + 0.2), 0.3);
    (void)printf("%d %d %d %d\n", v, s, loops, eq);
    return 0;
}