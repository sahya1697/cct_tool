int eq_double(double a, double b) {
    return a == b;
}

int float_loop(int n) {
    int count = 0;
    for (float i = 0.0f; i < (float)n; i += 0.5f) {
        count++;
    }
    return count;
}