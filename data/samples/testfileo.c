#include <stdint.h>
#include <stddef.h>

static int demo12_5(int a, int b, int c)
{
    if (a && b || c) {
        return 1;
    }
    return 0;
}

static void demo13_4_and_13_1(void)
{
    int x = 0, y = 2, z = 0;
    z = (x = y);
    (void)z;
}

static void demo14_2(void)
{
    int i = 0;
    for (; i < 3; i++) {
    }
}

static int multi_exit(int n)
{
    if (n < 0) { return -1; }
    if (n == 0) { return 0; }
    return 1;
}

int main(void)
{
    (void)demo12_5(1, 0, 1);
    demo13_4_and_13_1();
    demo14_2();
    (void)multi_exit(0);
    return 0;
}