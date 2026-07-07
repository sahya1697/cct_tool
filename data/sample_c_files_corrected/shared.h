#ifndef SHARED_H
#define SHARED_H

/* MISRA 18.4: Unions shall not be used. Replaced with a struct that stores
 * the value as individual bytes, avoiding type punning via a union. */
typedef struct {
    unsigned char bytes[4];
} DataStore;

int check_limits(int x, int y);
void reset_device(void);
void pack_value(unsigned int v);
unsigned char get_byte(int i);

#endif
