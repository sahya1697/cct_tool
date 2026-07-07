#include "shared.h"

/* MISRA 2.1: Assembly language shall be encapsulated and isolated.
 * The inline assembly is isolated in its own dedicated function. */
static void nop_instruction(void)
{
    asm("NOP");
}

void reset_device(void)
{
    nop_instruction();
}
