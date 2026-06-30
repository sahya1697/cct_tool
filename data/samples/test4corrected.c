#include <stdio.h>
int bad_scope(int v) {
    int r = 0;
    switch (v) {
        case 0:
            r = 10;
            break;
        default:
            r = 1;
            break;
    }
    return r;
}
int missing_break(int v) {
    int r = 0;
    switch (v) {
        case 0:
            r = 1;
            break;         
        case 1:
            r = 2;
            break;
        default:
            r = 3;
            break;
    }
    return r;
}
int default_not_last(int v) {
    int r = 0;
    switch (v) {
        case 0:
            r = 1;
            break;
        default:
            r = 9;
            break;
    }
    return r;
}
int switch_bool(int v) {
    if (v > 0) {
        return 1;
    } else if (v < 0) {
        return 0;
    } else {
        return 2;
    }
}
int only_default(int v) {
    switch (v) {
        case 0:
            v++;
            break;
        default:
            v++;
            break;
    }
    return v;
}
int main(void) {
    (void)bad_scope(0);
    (void)missing_break(0);
    (void)default_not_last(0);
    (void)switch_bool(-3);
    (void)only_default(7);
    return 0;
}
