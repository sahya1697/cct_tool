#include <stdint.h>
#include <stddef.h>

static int demo12_5(int a, int b, int c)
{
    if ((a && b) || c) {
        return 1;
    }
    return 0;
}

static void demo13_1_and_13_4_fixed(void)
{
    int x = 0, y = 2, z = 0;
    x = y;
    z = x;
    (void)z;
}

static void demo14_2_fixed(void)
{
    int i;
    for (i = 0; i < 3; i++) {
        printf("Iteration %d\n", i);
    }
}

static int structured_flow_no_goto(int x)
{
    int r;
    if (x == 0) {
        r = 1;
    } else if (x == 1) {
        r = 1;
    } else if (x == 2) {
        r = 2;
    } else {
        r = -1;
    }
    return r;
}

static int single_exit_15_5(int n)
{
    int result = 1;
    if (n < 0) {
        result = -1;
    } else if (n == 0) {
        result = 0;
    }
    return result;
}

int main(void)
{
    (void)demo12_5(1, 0, 1);
    demo13_1_and_13_4_fixed();
    demo14_2_fixed();
    (void)structured_flow_no_goto(0);
    (void)single_exit_15_5(0);
    return 0;
}