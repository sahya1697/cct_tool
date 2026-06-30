#include "shared.h"

int check_limits(int x, int y) {
    if (x > 0 && y < 100 && x != y) { return 1; }
    return 0; }
