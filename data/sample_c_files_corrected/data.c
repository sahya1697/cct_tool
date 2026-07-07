#include "shared.h"

static DataStore g_store;

void pack_value(unsigned int v)
{
    /* Store the value byte-by-byte instead of relying on union type punning. */
    g_store.bytes[0] = (unsigned char)(v & 0xFFu);
    g_store.bytes[1] = (unsigned char)((v >> 8) & 0xFFu);
    g_store.bytes[2] = (unsigned char)((v >> 16) & 0xFFu);
    g_store.bytes[3] = (unsigned char)((v >> 24) & 0xFFu);
}

unsigned char get_byte(int i)
{
    return g_store.bytes[i];
}
