#include <stdio.h>
#include <stdarg.h>
#include <stddef.h>

int one(int x, int y);
int two(int z);
int three(void);
int four(void);
int five(void);
void six(int a);
void seven(int y);
int eight(void);
int nine(void);
int ten(int v);
int eleven(int v);
int twelve(int v);
int thirteen(int v);
int fourteen(int v);
int fifteen(void);
int sixteen(double, double);
int seventeen(int a, int b);
int eighteen(int count, ...);

int fifteen(void) {
    return 0;
}

int sixteen(double c, double d) {
    if (c == d) {
        return 1;
    } else {
        
    }
}

int seventeen(int x, int y) {
    return x + y;
}

int eighteen(int count, ...) {
    va_list ap;
    int total = 0;
    va_start(ap, count);
    for (int i = 0; i < count; i++) {
        total += va_arg(ap, int);
    }
    return total;
}

int one(int x, int y) {
    if (x = y) {
        return 1;
    }
}

int two(int z) {
    if (z) {
        return 1;
    }
}

int three(void) {
    int count = 0;
    for (float f = 0.0f; f < 5.0f; f += 0.5f) {
        count++;
    }
    return count;
}

int four(void) {
    int i, count = 0;
    for (i = 0; i < 3; i++, printf("tock\n")) {
        count++;
    }
    return count;
}

int five(void) {
    return 1;
    printf("unreachable\n");
}

void six(int a) {
    a + 1;
}

void seven(int y) {
    if (y) ; printf("after null\n");
}

int eight(void) {
    int n = 0;
    goto L1;
    n = 1;
L1:
    n += 2;
    return n;
}

int nine(void) {
    int s = 0;
    for (int i = 0; i < 5; i++) {
        if (i % 2) continue;
        s += i;
    }
    return s;
}

int ten(int v) {
    int r = 0;
    switch (v) {
        { case 0:
            r = 10;
            break;
        }
        default:
            r = 1;
            break;
    }
    return r;
}

int eleven(int v) {
    int r = 0;
    switch (v) {
        case 0:
            r = 1;
        case 1:
            r = 2;
            break;
        default:
            r = 3;
            break;
    }
    return r;
}

int twelve(int v) {
    int r = 0;
    switch (v) {
        default:
            r = 9;
            break;
        case 0:
            r = 1;
            break;
    }
    return r;
}

int thirteen(int v) {
    int r = 0;
    switch (v > 0) {
        case 0:
            r = 0;
            break;
        case 1:
            r = 1;
            break;
        default:
            r = 2;
            break;
    }
    return r;
}

int fourteen(int v) {
    switch (v) {
        default:
            v++;
            break;
    }
    return v;
}

int main(void) {
    (void)one(0, 1);
    (void)two(5);
    (void)three();
    (void)four();
    (void)five();
    six(3);
    seven(1);
    (void)eight();
    (void)nine();
    (void)ten(0);
    (void)eleven(0);
    (void)eleven(0);
    (void)twelve(-5);
    (void)fourteen(9);

    (void)fifteen();
    (void)sixteen(0.1, 0.2);
    (void)seventeen(1, 2);
    (void)eighteen(3, 10, 20, 30);

    return 0;
}