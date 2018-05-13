
#include <stdlib.h>
#include <stdint.h>
#define MAX_COMMUNITIES 16
#define MAX_AS_PATH 16

typedef struct {
    uint32_t community;
    uint32_t communities[MAX_COMMUNITIES];
    uint32_t as_path[MAX_AS_PATH];
    uint32_t community_len;
    uint32_t as_path_len;

    uint32_t prefix;
    int32_t mask;
    int32_t local_pref;
    int32_t metric;
    int32_t is_dropped;
    uint32_t next_hop;
} Announcement;

int match_prefix(uint32_t prefix1, int32_t mask1, uint32_t prefix2, int32_t mask2, int32_t ge, int32_t le);

int match_community(uint32_t* communities, uint32_t len, uint32_t match);

uint32_t update_community(uint32_t *communities, uint32_t len, uint32_t update, int32_t additive);

int ann_match_prefix(Announcement ann, uint32_t prefix, int32_t mask, int32_t ge, int32_t le);

int ann_match_community(Announcement ann, uint32_t match);

void ann_update_community(Announcement ann, uint32_t comm, int32_t additive);

void ann_set_communities(Announcement ann, uint32_t* comm_arr, uint32_t comm_len);

int ann_communities_equal(Announcement ann1, Announcement ann2);
