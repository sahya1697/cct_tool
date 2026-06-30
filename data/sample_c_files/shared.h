#ifndef SHARED_H
#define SHARED_H

union DataStore { unsigned int raw; unsigned char bytes[4]; };
int check_limits(int x, int y);
void reset_device(void);
#endif
