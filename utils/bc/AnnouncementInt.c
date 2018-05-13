#include "AnnouncementInt.h"
#include <limits.h>
#include <stdint.h>

// Found online on stack overflow instead of using conditional for case where mask=32
#define BIT_MASK(__TYPE__, __ONE_COUNT__) \
    (((__TYPE__) (-((__ONE_COUNT__) != 0))) \
    & (((__TYPE__) -1) << ((sizeof(__TYPE__) * CHAR_BIT) - (__ONE_COUNT__ + ((__ONE_COUNT__) == 0)))))

int match_prefix(uint32_t prefix1, int32_t mask1, uint32_t prefix2, int32_t mask2, int32_t ge, int32_t le) {
    uint32_t val1, val2;
    val1 = prefix1 & BIT_MASK(uint32_t, mask1);
    val2 = prefix2 & BIT_MASK(uint32_t, mask2);

    return (val1 == val2) & (mask1 >= ge) & (mask1 <= le);
}

int match_community(uint32_t* communities, uint32_t len, uint32_t match)
{
    int result = 0;
    // Loop without branches on symbolic variables
    for(int i = 0; i < MAX_COMMUNITIES; i++)
    {
        result |= (i < len & communities[i] == match);
    }
    return result;
}

uint32_t update_community(uint32_t *communities, uint32_t len, uint32_t update, int32_t additive)
{
    if(additive) {
        communities[len] = update;
        return len;
    }
    communities[0] = update;
    return 0;
}


int ann_match_prefix(Announcement ann, uint32_t prefix, int32_t mask, int32_t ge, int32_t le)
{
    return match_prefix(ann.prefix, ann.mask, prefix, mask, ge, le);
}

int ann_match_community(Announcement ann, uint32_t match)
{
    return match_community(ann.communities, ann.community_len, match);
}

void ann_update_community(Announcement ann, uint32_t comm, int32_t additive)
{
    ann.community_len = update_community(ann.communities, ann.community_len, comm, additive);
}

void ann_set_communities(Announcement ann, uint32_t* comm_arr, uint32_t comm_len)
{
    ann.community_len = comm_len;
    for(int i = 0; i < MAX_COMMUNITIES; i++)
        ann.communities[i] = comm_arr[i];
}

int ann_communities_equal(Announcement ann1, Announcement ann2)
{
    int acc = ann1.community_len == ann2.community_len;

    // Loop without branches on symbolic variables
    for(int i = 0; i < MAX_COMMUNITIES; i++)
    {
        acc &= (i >= ann1.community_len | ann1.communities[i] == ann2.communities[i]);
    }

    return acc;
}
