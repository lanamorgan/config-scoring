#include "Announcement.h"

char * update_community(char *community, char *update_string, int additive){
    int result_len;
    char *result;

    // If additive, append update_string to community
    if(additive){
        result_len = strlen(community)+strlen(update_string)+2;
        result = (char *) malloc(result_len * sizeof(char));
        memset(result, '\0', result_len);
        strcpy(result, community);
        result[strlen(community)] = ' '; // Space between community tags
        // strcpy(&(result+strlen(community)+1), update_string);
        memcpy(&(result[strlen(community)+1]), update_string, strlen(update_string));
    }
    else{
        result_len = strlen(update_string)+1;
        result = (char *) malloc(result_len * sizeof(char));
        memset(result, '\0', result_len);
        strcpy(result, update_string);
    }
    free(community);
    return result;
}

// Checks if prefix_1 satisfies prefix_2 given ge/le constraints
int satisfy_prefix(char *prefix_1, char *prefix_2, int ge, int le){
    // Default mask length values of 32
    int mask_1_len=32, mask_2_len=32;
    unsigned int val_1, val_2;
    char *ip_1, *mask_1, *ip_2, *mask_2, *copy_1, *copy_2, *find_1, *find_2;

    // Create copies of ip and prefix before operating (i.e. tokenizing)
    copy_1 = (char *) malloc((strlen(prefix_1)+1) * sizeof(char));
    copy_2 = (char *) malloc((strlen(prefix_2)+1) * sizeof(char));
    strcpy(copy_1, prefix_1);
    strcpy(copy_2, prefix_2);

    // Check if prefix has slash; otherwise, assume 32 bit mask
    find_1 = strchr(copy_1, '/');
    find_2 = strchr(copy_2, '/');
    if(find_1 == NULL){
        ip_1 = copy_1;
    }
    else{
        ip_1 = strtok(copy_1, "/");
        mask_1 = strtok(NULL, "/");
        mask_1_len = atoi(mask_1);
    }
    if(mask_1_len < ge || mask_1_len > le){
        return 0;
    }
    if(find_2 == NULL){
        ip_2 = copy_2;
    }
    else{
        ip_2 = strtok(copy_2, "/");
        mask_2 = strtok(NULL, "/");
        mask_2_len = atoi(mask_2);
    }

    // Turn prefixes into integer value (using mask of prefix_2)
    val_1 = address_to_masked_value(ip_1, mask_2_len);
    val_2 = address_to_masked_value(ip_2, mask_2_len);

    if(val_1 == val_2){
        return 1;
    }
    return 0;
}

unsigned int address_to_masked_value(char *ip, int mask_len){
    unsigned int val = 0; 
    unsigned int mask_size = sizeof(mask_len) * 8; // Typically 32
    // unsigned int mask = mask_len < mask_size ? ( (1 << mask_len) - 1 ) : -1;
    unsigned int mask = BIT_MASK(unsigned int, mask_len);
    mask <<= mask_size - mask_len;

    char *tok = strtok(ip, ".");
    while(tok != NULL){
        val = (val << 8) + atoi(tok);
        tok = strtok(NULL, ".");
    }
    val &= mask;

    return val;
}


// Test functions
int main(int argc, char **argv){
    int ge = 16;
    int le = 32;
    char ip[] = "1.2.3.4";
    char prefix[] = "1.2.0.8/16";
    if(satisfy_prefix(ip, prefix, ge, le)){
        printf("%s satisfies prefix %s with range %d-%d\n", ip, prefix, ge, le);
    }
    else{
        printf("%s does not satisfy prefix %s with range %d-%d\n", ip, prefix, ge, le);
    }
    
    // Assume operating with dynamically allocated memory within announcement char *
    char *community = (char *) malloc(5 * sizeof(char));
    strcpy(community, "3:46");
    printf("Community: %s\n", community);

    char *result = update_community(community, "1:45", 1);
    printf("Result 1: %s\n", result);
    result = update_community(result, "2:3", 1);
    printf("Result 2: %s\n", result);

    return 0;
}
