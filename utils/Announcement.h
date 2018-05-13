#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>     /* CHAR_BIT */

// Found online on stack overflow instead of using conditional for case where mask=32
#define BIT_MASK(__TYPE__, __ONE_COUNT__) \
    ((__TYPE__) (-((__ONE_COUNT__) != 0))) \
    & (((__TYPE__) -1) >> ((sizeof(__TYPE__) * CHAR_BIT) - (__ONE_COUNT__)))

typedef struct {
    char *community;
    char *prefix;
    char *as_path;
    int local_pref;
    int metric;
} Announcement;

// If prefix_1 satisfies prefix_2 given ge and le constraints
int satisfy_prefix(char *prefix_1, char *prefix_2, int ge, int le); 
unsigned int address_to_masked_value(char *ip, int mask_len);
char * update_community(char *community, char *update_string, int additive);
