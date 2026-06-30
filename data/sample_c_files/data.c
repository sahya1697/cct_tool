#include "shared.h"

union DataStore g_store;
void pack_value(unsigned int v) { g_store.raw = v; }
unsigned char get_byte(int i) { return g_store.bytes[i]; }
