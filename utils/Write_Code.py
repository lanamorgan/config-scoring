from utils.Helper import *
import re, sys


def write_equivalence_check(sld, directory, router_list):
    for pair, mapping in router_list:
        r1 = sld[pair[0]]
        r2 = sld[pair[1]]
        equivalence(directory, r1, r2,  mapping)
'''
    neighbor_map should be of the form r1Neighbor:r2Neighbor
    and only neighbors in the dictionary will be checked
    if no map is provided, will checkf or an exact 1:1 match.
'''
def equivalence(directory, r1_sess, r2_sess, neighbor_map = None):
    r1_name = r1_sess[0].router_name
    r2_name = r2_sess[0].router_name
    r1_neighbors = {s.neighbor: s for s in r1_sess}
    r2_neighbors = {s.neighbor: s for s in r2_sess}

    r1_ips = r1_neighbors.keys()
    r2_ips  = r2_neighbors.keys()

    if not neighbor_map:
        # if no map provided, check r1 neighbors == r2 neighbors
        if not len(r1_ips) == len(r2_ips) or not all([ip in r1_ips for ip in r2_ips]):
            print >> sys.stderr, "Missing neighbors"
            return -1
        else:
            # if all neighbors are the same, make a map
            neighbor_map = {s.neighbor: s for s in r2_sess}
    else:
        # if there is a map, check that all neighborss exist
        for key in neighbor_map:
            # if neighbor not present, raise error
            if key not in r1_ips or neighbor_map[key] not in r2_ips:
                print >> sys.stderr, "Missing neighbors"
                return -1
            else:
                # if neighbor is present, set to the associated session for r2
                neighbor_map[key] = r2_neighbors[neighbor_map[key]]

    # neighbor_map now of the form r1_ip : r2_sess
    r1_name = str(r1_sess[0].router_name)
    r2_name = str(r2_sess[0].router_name)
    file_name = r1_name + "_to_" + r2_name
    f = open(directory + '/' + file_name + '.c', 'w')
    # f = open(directory + '/' + str(r1) + str(r2) + '.c', 'w')

    f.write("#include <stdio.h>\n#include <stdlib.h>\n")
    # f.write("#include <klee/klee.h>\n#include \"AnnouncementInt.h\"\n")
    f.write("#include \"AnnouncementInt.h\"\n")
    f.write("#include <assert.h>\n\n")

    for neighbor in neighbor_map:
        r1_sess = r1_neighbors[neighbor]
        r2_sess = neighbor_map[neighbor]

        r1_ngh_val = str(str_to_ip(r1_sess.neighbor.split('/')[0]))
        if r1_sess.import_policy:
            write_policy(f, r1_sess.import_policy, "1_" + r1_ngh_val)
        if r1_sess.export_policy:
            write_policy(f, r1_sess.export_policy, "1_" + r1_ngh_val)

        r2_ngh_val = str(str_to_ip(r2_sess.neighbor.split('/')[0]))
        if r2_sess.import_policy:
            write_policy(f, r2_sess.import_policy, "2_" + r2_ngh_val)
        if r1_sess.export_policy:
            write_policy(f, r2_sess.export_policy, "2_" + r2_ngh_val)
        f.write("\n\n")

    # Write main method
    f.write("int main(int argc, char **argv){\n")
    f.write("\tint test_num;\n")
    f.write("\tklee_make_symbolic(&test_num, sizeof(test_num),\"test_num\");\n")

    # Symbolic first announcement
    f.write("\t// Create first announcement\n")
    f.write("\tint m1, lp1, comm_len1, prefix1, mask1, nexthop1;\n")
    f.write("\tunsigned int comm_arr1[MAX_COMMUNITIES];\n")
    f.write("\tAnnouncement ann1;\n")
    f.write("\tklee_make_symbolic(&lp1, sizeof(lp1), \"loc_pref1\");\n")
    f.write("\tklee_make_symbolic(&m1, sizeof(m1), \"metric1\");\n")
    f.write("\tklee_make_symbolic(&comm_arr1, sizeof(comm_arr1), \"comm_arr1\");\n")
    f.write("\tklee_make_symbolic(&comm_len1, sizeof(comm_len1), \"comm_len1\");\n")
    f.write("\tklee_make_symbolic(&prefix1, sizeof(prefix1), \"pfx1\");\n")
    f.write("\tklee_make_symbolic(&mask1, sizeof(mask1), \"mask1\");\n")
    f.write("\tklee_make_symbolic(&nexthop1, sizeof(nexthop1), \"nexthop1\");\n")
    f.write("\tklee_assume(mask1 <= 32);\n")
    f.write("\tklee_assume(mask1 >= 0);\n")
    f.write("\tklee_assume(comm_len1 >= 0);\n")
    f.write("\tklee_assume(comm_len1 <= 32);\n")
    f.write("\tann1.is_dropped = 0;\n\n")

    #Symbolic second announcement
    f.write("\t// Create second announcement\n")
    f.write("\tint m2, lp2, comm_len2, prefix2, mask2, nexthop2;\n")
    f.write("\tunsigned int comm_arr2[MAX_COMMUNITIES];\n")
    f.write("\tAnnouncement ann2;\n")
    f.write("\tklee_make_symbolic(&lp2, sizeof(lp2), \"loc_pref2\");\n")
    f.write("\tklee_make_symbolic(&m2, sizeof(m2), \"metric2\");\n")
    f.write("\tklee_make_symbolic(&comm_arr2, sizeof(comm_arr2), \"comm_arr2\");\n")
    f.write("\tklee_make_symbolic(&comm_len2, sizeof(comm_len2), \"comm_len2\");\n")
    f.write("\tklee_make_symbolic(&prefix2, sizeof(prefix2), \"pfx2\");\n")
    f.write("\tklee_make_symbolic(&mask2, sizeof(mask2), \"mask2\");\n")
    f.write("\tklee_make_symbolic(&nexthop2, sizeof(nexthop2), \"nexthop2\");\n")
    f.write("\tklee_assume(mask2 <= 32);\n")
    f.write("\tklee_assume(mask2 >= 0);\n")
    f.write("\tklee_assume(comm_len2 >= 0);\n")
    f.write("\tklee_assume(comm_len2 <= 32);\n")
    f.write("\tann2.is_dropped = 0;\n\n")

    # Set both announcements equal to each other
    f.write("\t// Set inputs equal\n")
    f.write("\tklee_assume(m1 == m2);\n")
    f.write("\tklee_assume(lp1 == lp2);\n")
    f.write("\tklee_assume(prefix1 == prefix2);\n")
    f.write("\tklee_assume(mask1 == mask2);\n")
    f.write("\tklee_assume(nexthop1 == nexthop2);\n")
    f.write("\tann1.local_pref = lp1;\n\tann1.metric = m1;\n")
    f.write("\tann_set_communities(ann1, comm_arr1, comm_len1);\n")
    f.write("\tann1.prefix = prefix1;\n\tann1.mask = mask1;\n")
    f.write("\tann1.next_hop = nexthop1;\n\tann2.next_hop = nexthop2;\n")
    f.write("\tann2.local_pref = lp2;\n\tann2.metric = m2;\n")
    f.write("\tann_set_communities(ann2, comm_arr1, comm_len1);\n")
    f.write("\tann2.prefix = prefix2;\n\tann2.mask = mask2;\n")
    f.write("\tklee_assume(ann_communities_equal(ann1, ann2));\n")
    path = 0

    for neighbor in neighbor_map:
        r1_sess = r1_neighbors[neighbor]
        r2_sess = neighbor_map[neighbor]

        #TODO: move all of this into write_check, clean up
        if r1_sess.import_policy and r2_sess.import_policy:
            write_check(f, r1_sess, r2_sess, r1_sess.import_policy, r2_sess.import_policy, path)
            path += 1
        elif r1_sess.import_policy or r2_sess.import_policy:
            print >> sys.stderr, "Missing %s:%s import policy" % \
                    (neighbor.split('/')[0], r2_sess.neighbor.split('/')[0])
        if r1_sess.export_policy and r2_sess.export_policy:
            write_check(f, r1_sess, r2_sess, r1_sess.export_policy, r2_sess.export_policy, path)
            path += 1
        elif r1_sess.export_policy or r2_sess.export_policy:
            print >> sys.stderr, "Missing %s:%s export policy" % \
                    (neighbor.split('/')[0], r2_sess.neighbor.split('/')[0])
    f.write("\n\treturn 0;\n}\n\n")
    f.close()

def write_check(f, session1, session2, policy1, policy2, path):
    # Function name for neighbor X to r1
    r1_ngh_val = str_to_ip(session1.neighbor.split('/')[0])
    r1_func_name = fix_policy_name(policy1[0].name + "_1_" + str(r1_ngh_val))
    # Function name for neighobr X to r2
    r2_ngh_val = str_to_ip(session2.neighbor.split('/')[0])
    r2_func_name = fix_policy_name(policy2[0].name + "_2_" + str(r2_ngh_val))

    f.write("\tif (test_num == {n}){{\n".format(n=str(path)))
    f.write("\t\tAnnouncement r1 = {func}(ann1);\n".format(func=r1_func_name))
    f.write("\t\tAnnouncement r2 = {func}(ann2);\n".format(func=r2_func_name))
    f.write("\t\tassert(r1.is_dropped == r2.is_dropped);\n")
    f.write("\t\tif(!r1.is_dropped && !r2.is_dropped){\n")
    f.write("\t\t\tassert(r1.local_pref == r2.local_pref);\n")
    f.write("\t\t\tassert(r1.metric == r2.metric);\n")
    f.write("\t\t\tassert(ann_communities_equal(r1,r2));\n")
    f.write("\t\t\tassert(r1.mask == r2.mask);\n")
    f.write("\t\t\tassert(r1.prefix == r2.prefix);\n")
    f.write("\t\t\tassert(r1.next_hop == r2.next_hop);\n")
    f.write("\t\t}\n")
    f.write("\t}\n")

def write_code(session_list_dict, directory):
    dir_code = directory + '/code/'
    dir_pseudo = directory + '/pseudocode/'
    dir_map = directory + '/map/'
    create_directory(dir_code)
    create_directory(dir_pseudo)
    create_directory(dir_map)
    for router_name in session_list_dict:
        code_file = open(dir_code + str(router_name)+'.c', 'w')
        pseudocode_file = open(dir_pseudo + str(router_name)+'.c', 'w')
        test_map_file = open(dir_map + str(router_name) + "_map", 'w')
        code_file.write("#include <stdio.h>\n#include <stdlib.h>\n")
        # code_file.write("#include <klee/klee.h>\n")
        code_file.write("#include \"AnnouncementInt.h\"\n\n")
        for session in session_list_dict[router_name]:
            code_file.write("// Policies for Neighbor: " + session.neighbor + "\n")
            if session.import_policy:
                code_file.write("// Import Policies:\n")
                ngh_val = str_to_ip(session.neighbor.split('/')[0])
                write_policy(code_file, session.import_policy, ngh_val)
                write_pseudocode_policy(pseudocode_file, session.import_policy)
            if session.export_policy:
                code_file.write("// Export Policies:\n")
                ngh_val = str_to_ip(session.neighbor.split('/')[0])
                write_policy(code_file, session.export_policy, ngh_val)
                write_pseudocode_policy(pseudocode_file, session.export_policy)
            code_file.write("\n\n")
        write_identity_function(code_file)
        write_main(code_file, session_list_dict[router_name], test_map_file)

def write_identity_function(f):
    f.write("Announcement identity(Announcement a){\n")
    f.write("\treturn a;\n")
    f.write("}\n\n")

def write_main(f, rs, tmap):
    f.write("int main(int argc, char **argv){\n")
    f.write("\tint test_num;\n")
    f.write("\tklee_make_symbolic(&test_num, sizeof(test_num),\"test_num\");\n")
    f.write("\tint m, lp, comm_len, prefix, mask;\n")
    f.write("\tunsigned int comm_arr[MAX_COMMUNITIES];\n")
    f.write("\tAnnouncement ann;\n")
    f.write("\tklee_make_symbolic(&lp, sizeof(lp), \"loc_pref\");\n")
    f.write("\tklee_make_symbolic(&m, sizeof(m), \"metric\");\n")
    f.write("\tklee_make_symbolic(&comm_arr, sizeof(comm_arr), \"comm_arr\");\n")
    f.write("\tklee_make_symbolic(&comm_len, sizeof(comm_len), \"comm_len\");\n")
    f.write("\tklee_make_symbolic(&prefix, sizeof(prefix), \"pfx\");\n")
    f.write("\tklee_make_symbolic(&mask, sizeof(mask), \"mask\");\n")
    f.write("\tklee_assume(mask <= 32);\n")
    f.write("\tklee_assume(mask >= 0);\n")
    f.write("\tklee_assume(comm_len >= 0);\n")
    f.write("\tklee_assume(comm_len <= 32);\n")
    f.write("\tann.local_pref = lp;\n\tann.metric = m;\n")
    f.write("\tann_set_communities(ann, comm_arr, comm_len);\n")
    f.write("\tann.prefix = prefix;\n\tann.mask = mask;\n")
    f.write("\tann.is_dropped = 0;\n")
    path = 0

    policies_map = {}
    for i_session in rs: 
        if i_session.import_policy:
            i_ngh_val = str_to_ip(i_session.neighbor.split('/')[0])
            ip = fix_policy_name(i_session.import_policy[0].name + "_" + str(i_ngh_val))
        else:
            ip = "identity"
        if policies_map.get(ip):
            continue
        ep_list = []
        ep_id = False
        for e_session in rs: 
            if e_session.neighbor == i_session.neighbor and ip != "identity":
                continue
            if e_session.export_policy:
                e_ngh_val = str_to_ip(e_session.neighbor.split('/')[0])
                ep = fix_policy_name(e_session.export_policy[0].name + "_" + str(e_ngh_val))
                ep_list += [(ep, i_session.neighbor, e_session.neighbor)]
            else:
                ep = "identity"
                # Only have identity output once, and exclude if ip was identity
                if not ep_id and ip != "identity":
                    ep_list += [(ep, i_session.neighbor, e_session.neighbor)]
                    ep_id = True
        policies_map[ip] = ep_list
    for import_path in policies_map:
        neighbors = policies_map[import_path]
        if neighbors:
            f.write("\tif (test_num == {n}){{\n".format(n=str(path)))
        for export in range(len(neighbors)):
            neighbor = neighbors[export]
            ep = neighbor[0]
            i_ngh = neighbor[1]
            e_ngh = neighbor[2]
            f.write("\t\tAnnouncement r{i}={func}(ann);\n".format(i=str(export), func=import_path))
            f.write("\t\tif (!r{i}.is_dropped){{\n".format(i=str(export)))
            f.write("\t\t\t{func}(r{i});\n".format(i=str(export), func=ep))
            f.write("\t\t}\n")
            tmap.write(str(path) + "|" +  import_path + '|' + ep + '|')
            tmap.write(i_ngh + '|' + e_ngh + '\n')
        path += 1
        if neighbors:
            f.write("\t}\n")

    f.write("\n\treturn 0;\n}\n\n")

# Replace C operators with '_'
def fix_policy_name(name):
    name = name.replace('&', '_')
    name = name.replace('-', '_')
    return name

# Write pseudocode for policies
def write_policy(code_file, policies, tag):
    if not policies:
        return
    name = fix_policy_name(policies[0].name)
    code_file.write("Announcement " + name + "_" + str(tag) + "(Announcement a){\n")
    first_flag = True
    for policy in policies:
        if first_flag:
            code_file.write("\tif ( (")
            first_flag = False
        else:
            code_file.write("\telse if ( (")
        cond = False # keep track of setting an earlier condition for this policy
        if policy.community_list:
            for i, cl in enumerate(policy.community_list):
                if cond:
                    code_file.write("& (")
                m = re.match("\^(\d+):(\d+)\$$", cl.regex)
                if m:
                    comm = (int(m.group(1)) << 16) + int(m.group(2))
                else:
                    comm = re.sub("[^0-9:]", "", cl.regex)
                    comm = comm_to_int(comm)
                if not cl.permit:
                    code_file.write("!")
                code_file.write("ann_match_community(a, %s)" % (str(comm)))

                if i+1 < len(policy.community_list):
                    code_file.write(" | ")
                else:
                    code_file.write(" ) ")
                    cond = True

        if policy.route_filter_list:
            for i, rfl in enumerate(policy.route_filter_list):
                if cond:
                    code_file.write("& (")
                    cond = False
                ip, mask = rfl.prefix.split("/")
                ip = str(str_to_ip(ip))
                if not rfl.permit:
                    code_file.write("!")
                code_file.write("ann_match_prefix(a, %s, %s, %s, %s)" \
                        % (ip, mask, rfl.mask_lower, rfl.mask_upper))
                # code_file.write("( a->prefix == \"" + rfl.prefix + "\" )")
                if i+1 < len(policy.route_filter_list):
                    code_file.write("|")
                else:
                    code_file.write(") ")
                    cond = True

        # Leaving as_path_list commented out as there's no way to test
        # currently
        '''
        if policy.as_path_list:
            for i, aspl in enumerate(policy.as_path_list):
                if cond:
                    code_file.write("& ( ")
                    cond = False
                if not aspl.permit:
                    code_file.write("!")
                # code_file.write("( a.as_path_list == \"" + aspl.regex + "\"
                # )")
                code_file.write("( match(\"" +aspl.regex + "\", a.as_path_list)
)")
                if i+1 < len(policy.as_path_list):
                    code_file.write(" | ")
                 else:
                    code_file.write(" ) ")
                    cond = True
                    '''
        # No guards for this route-map
        if not cond:
            code_file.write("1 ) ")
        code_file.write(") {\n")

        for action in policy.actions:
            # TODO: append to community string (or create char ** for each
            # community added)
            # Same probably applies to as_path
            if action.field is "community": 
                action.value = comm_to_int(action.value)
                code_file.write("\t\tann_update_community(a, " + str(action.value) + ", " + str(int(action.additive)) + ");\n")
            else:
		code_file.write("\t\ta." + action.field + " = " + str(action.value) + ";\n")
            '''
            if action.additive:
                code_file.write("\t\ta." + action.field + " += " + str(action.value) + ";\n")
            else:
                code_file.write("\t\ta." + action.field + " = " +str(action.value) + ";\n")
                '''
        code_file.write("\t\treturn a;\n")
        code_file.write("\t}\n")
    # Write implicit "else drop" condition
    code_file.write("\telse {\n")
    code_file.write("\t\ta.is_dropped = 1;\n")
    code_file.write("\t\treturn a;\n\t}\n}\n")
    code_file.write("\n")

def str_to_ip(s):
    nums = [int(c) for c in s.split('.')]
    return (nums[0] << 24) + (nums[1] << 16) + (nums[2] << 8) + nums[3]

def comm_to_int(s):
    s = str(s)
    if len(s) is 0:
        return -1
    nums = s.split(':')
    if nums != 2:
        if s[-1] == ':':
            one = s[0]
            two = 0
        # if a single integer, just return it as is
        else:
            one = 0
            two = s[0]
    else:
        one = s[0]
        two = s[1]

    comm = int(one) << 16 | int(two)
    return comm


def int_to_comm(i):
    one = (comm & 0xFFFF0000) >> 16
    two = comm & 0x0000FFFF
    return str(one) + ":" + str(two)


# Write pseudocode for policies
def write_pseudocode_policy(code_file, policies):
    code_file.write("def " + policies[0].name + ":\n")
    for i, policy in enumerate(policies):
        if i == 0:
            code_file.write("\tif ( ( ")
        else:
            code_file.write("\telse if ( ( ")
        cond = False # keep track of setting an earlier condition for this policy
        if policy.community_list:
            for i, cl in enumerate(policy.community_list):
                if cond:
                    code_file.write(" && ( ")
                    cond = False
                op = '=='
                if not cl.permit:
                    op = '!='
                code_file.write("( community %s \"%s\" )" % (op, cl.regex[cl.regex.find(')')+1:]))
                if i+1 < len(policy.community_list):
                    code_file.write(" || ")
                else:
                    code_file.write(" ) ")
                    cond = True

        if policy.route_filter_list:
            for i, rfl in enumerate(policy.route_filter_list):
                if cond:
                    code_file.write(" && ( ")
                    cond = False
                op = '=='
                if not rfl.permit:
                    op = '!='
                code_file.write("( prefix %s \"%s\" )" % (op, rfl.prefix))
                if i+1 < len(policy.route_filter_list):
                    code_file.write(" || ")
                else:
                    code_file.write(" ) ")
                    cond = True
        if policy.as_path_list:
            for i, aspl in enumerate(policy.as_path_list):
                if cond:
                    code_file.write(" && ( ")
                op = '=='
                if not aspl.permit:
                    op = '!='
                code_file.write("( as_path_list %s \"%s\" )" % (op, aspl.prefix))
                if i+1 < len(policy.as_path_list):
                    code_file.write(" || ")
                else:
                    code_file.write(" ) ")
                    cond = True
        if not cond:
            code_file.write(" True ) ")
        code_file.write(") ")
        code_file.write("{\n")

        for action in policy.actions:
            value = str(action.value)
            op = '='
            if action.additive:
                op = '+='
            else:
                if action.field == 'next_hop':
                    value = int_to_ip(int(value))
            code_file.write("\t\t%s %s %s\n" % (action.field, op, value))
        code_file.write("\t}\n")
    code_file.write("\n")
