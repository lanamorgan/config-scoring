import sys, os, math, re, json, argparse, pdb, collections, subprocess, shutil
from ktest_parser import *

# Helper function to update data structure
def update_session_list_dict(router_name, session_list_dict, route_map_dict, policy_dict, prefix_to_intf_dict):
    if session_list_dict.get(router_name):
        for session in session_list_dict[router_name]:
            if session.import_policy_name:
                session.import_policy = route_map_dict[router_name][session.import_policy_name]
            if session.export_policy_name in policy_dict[router_name]:
                policies = policy_dict[router_name][session.export_policy_name]
                for policy in policies:
                    if policy.find('BGP_COMMON_EXPORT_POLICY') == -1:
                        # Currently assume only one other policy that isn't COMMON_EXPORT_POLICY
                        # Update export_policy_name to route_map name
                        session.export_policy = route_map_dict[router_name][policy]
                        session.export_policy_name = policy
                if not session.export_policy:
                    # Clear export_policy_name if no export_policy object added to session
                    session.export_policy_name = ""

            # Iterate through prefixes and check if any prefix matches session.neighbor
            # If so, update the interface name in that session object
            for prefix in prefix_to_intf_dict[router_name].keys():
                if host_matches_prefix(session.neighbor, prefix):
                    session.interface = prefix_to_intf_dict[router_name][prefix]

# Generate topology json object and file, so don't need to get it from Batfish
def create_topology(prefix_to_intf_dict, directory1=None, filename=None):
    topology = []
    for router_1 in prefix_to_intf_dict.keys():
        for router_2 in prefix_to_intf_dict.keys():
            # Ignore case where router has 2 interfaces on same subnet
            if router_1 == router_2:
                continue
            for prefix_1 in prefix_to_intf_dict[router_1].keys():
                for prefix_2 in prefix_to_intf_dict[router_2].keys():
                    if prefix_matches_prefix(prefix_1, prefix_2):
                        if prefix_to_intf_dict[router_1][prefix_1].find('lo') != -1 \
                            or prefix_to_intf_dict[router_2][prefix_2].find('lo') != -1:
                            continue
                        obj = {}
                        obj['node1'] = router_1
                        obj['node1interface'] = prefix_to_intf_dict[router_1][prefix_1]
                        obj['node2'] = router_2
                        obj['node2interface'] = prefix_to_intf_dict[router_2][prefix_2]
                        topology.append(obj)
    if filename and directory1:
        with open(directory1+'/'+filename, 'w') as out_file:
            json.dump(topology, out_file, indent=4)

    return topology

# Generate topology json object and file, so don't need to get it from Batfish
# This topology generator is used when we are provided with only one config file i.e. 
# if the above topology generator returns empty list then this function is invoked
def create_singleNode_topology(tested_node,session_list_dict,prefix_to_intf_dict, directory1=None, filename=None):
    co = 0
    dummy = 0
    for sessions in session_list_dict[tested_node]:
        co = co + 1
        sessions.neighbor_name = tested_node + '_N' + str(co) # Update neighbor name
        if sessions.interface:
            ip_mask = prefix_to_intf_dict[tested_node].keys()\
                        [\
                        prefix_to_intf_dict[tested_node].values().index(sessions.interface)\
                        ].split('/')[1]
            prefix_to_intf = {}
            prefix_to_intf[sessions.neighbor.split('/')[0] + '/'+ip_mask] = 'intf_N' + str(co)
            prefix_to_intf_dict[sessions.neighbor_name] = prefix_to_intf
        else:
            dummy = dummy +1
            #Check this logic on how to assign private range to dummy interfaces
            private_range = '192.168.'
            prefix_to_intf = {}
            prefix_to_intf[sessions.neighbor] = 'lo_N' + str(co) 
            prefix_to_intf[private_range+str(dummy)+'.1/24'] =  'intf_d'+ str(dummy) + '_N' + str(co)
            prefix_to_intf_dict[sessions.neighbor_name] = prefix_to_intf

            prefix_to_intf =  prefix_to_intf_dict[tested_node]
            prefix_to_intf[private_range+str(dummy)+'.2/24'] = 'N' +str(co)+ '_d'+ str(dummy) 
            prefix_to_intf_dict[tested_node] = prefix_to_intf
    return create_topology(prefix_to_intf_dict,directory1 = directory1,filename=filename)
    
# -----------------------------------------------------------------------------
# RANDOM HELPER FUNCTIONS
# -----------------------------------------------------------------------------
# TODO: Need to have some sort of convention for interface name transformation
# Or, have mapping from original interface name to new intf (or vice versa)
def get_intf_name(name, tok):
    string = 'eth'
    if tok[0].find('Loopback') != -1:
        string = 'lo'
    elif tok[0].find('GigabitEthernet') != -1:
        string = 'geth'
    if len(tok) > 1:
        return string + tok[0][-1] + tok[1]
    else:
        return string + tok[0][-1]

# Max length = 15 and eliminate '.' from interface name
def get_interface_name(router, intf):
    new_intf = get_ethernet_port_name(intf)
    return "%s%s" % (re.sub('[\.]', '', router)[:(15-len(new_intf))], new_intf)

# Modified from HSA Code
# Replacement for get_intf_name
# Max length = 5 (Assuming remainder length <= 3
def get_ethernet_port_name(port):
    result = ""
    remainder = ""
    if port.lower().startswith("tengigabitethernet"):
        result = "te"
        remainder = port[len("tengigabitethernet"):]
    elif port.lower().startswith("gigabitethernet"):
        result = "gi"
        remainder = port[len("gigabitethernet"):]
    elif port.lower().startswith("fastethernet"):
        result = "fa"
        remainder = port[len("fastethernet"):]
    elif port.lower().startswith("ethernet"):
        result = "et"
        remainder = port[len("ethernet"):]
    elif port.lower().startswith("loopback"):
        result = "lo"
        remainder = port[len("loopback"):]
    elif port.lower().startswith("vlan"):
        result = "vl"
        remainder = port[len("vlan"):]
    else:
        result = port[:5]
    if remainder:
        remainder = re.sub('[/]', '', remainder)
    return "%s%s" % (result, remainder) # Max length = 5

def prefix_matches_prefix(prefix_1, prefix_2):
    p1, mask1 = prefix_1.split('/')
    p2, mask2 = prefix_2.split('/')

    p1_val = address_to_masked_value(p1, int(mask1))
    p2_val = address_to_masked_value(p2, int(mask2))
    if p1_val == p2_val:
        return True
    return False

def host_matches_prefix(host, prefix):
    mask_len = int(prefix.split('/')[1])
    host_val = address_to_masked_value(host.split('/')[0], mask_len)
    prefix_val = address_to_masked_value(prefix.split('/')[0], mask_len)
    if host_val == prefix_val:
        return True
    return False

def address_to_masked_value(ip, mask_len):
    val = 0
    for tok in ip.split('.'):
        val = (val << 8) + int(tok)
    mask = int( math.pow(2, int(mask_len)) - 1 ) << (32 - int(mask_len))
    val &= mask
    return val

def int_to_ip(val):
    ip = ""
    for i in range(3, -1, -1):
        ip += "%d." % (val >> (i*8) & 0xFF)
    return ip[:-1]

def str_to_ip_mask(ip_mask_str):
    ip = ''
    toks = ip_mask_str.split('.')
    for i in range(len(toks)-1):
        ip += toks[i] + '.'
    last = toks[3].split('/')
    ip += last[0]
    mask = count_to_mask( int(last[1]) )
    # return (ip + ' ' + mask)
    return str(ip), str(mask)

def validate_ip(s):
    a = s.split('.')
    if len(a) != 4:
        return False
    for x in a:
        if not x.isdigit():
            return False
        i = int(x)
        if i < 0 or i > 255:
            return False
    return True

def count_to_mask(count):
    string = ''
    val = ( (1 << 24) - 1 ) << (32 - count)
    for i in range(4):
        temp = val >> ( (3-i) * 8 ) & 0xFF
        string += str(temp) + '.'
    return string[:-1]

def mask_to_count(s):
    count = 0
    a = s.split('.')
    for x in a:
        i = int(x)
        count += bin(i).count('1')
    return str(count)

def create_directory(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

# Wrapper for filename.write(string); doesn't write if filename provided is None
def write_file_wrapper(filename, string):
    if filename:
        filename.write(string)

def generate_announcements(session_list_dict, directory, routers=None, mapping=None):
    test_announcements = {}
    test_map = None
    code_path = directory + '/code/'
    shutil.copy2(os.path.dirname(os.path.realpath(__file__)) + '/bc/AnnouncementInt.h', \
        code_path + 'AnnouncementInt.h')
    shutil.copy2(os.path.dirname(os.path.realpath(__file__)) + '/bc/AnnouncementInt.c', \
        code_path + 'AnnouncementInt.c')

    if routers:
        if type(routers) is list:
            # Should be list of length 2
            for router in routers:
                test_announcements[router] = run_klee(router, directory)
            reverse_mapping = [(b,a) for (a,b) in mapping]
            add_announcements(test_announcements, reverse_mapping, routers[1], routers[0])
            add_announcements(test_announcements, mapping, routers[0], routers[1])
            test_map = get_test_map(test_announcements, mapping)
        else:
            test_announcements[routers] = run_klee(routers, directory)
    else:
        for router in session_list_dict:
            test_announcements[router] = run_klee(router, directory)

    return test_announcements, test_map

def run_klee(router, directory):
    print("-" * 100)
    print(router)
    code_path = directory + '/code/'
    file_path = code_path + router
    if not os.path.exists(file_path + '.c'):
        return None
    subprocess.call(['clang-3.4', '-I ../../include', '-emit-llvm', '-c', '-g', \
        file_path + '.c', '-o', file_path + '.bc'])
    subprocess.call(['clang-3.4', '-I ../../include', '-emit-llvm', '-c', '-g', \
        code_path + 'AnnouncementInt.c', '-o', code_path + 'AnnouncementInt.bc'])
    subprocess.call(['/usr/bin/llvm-link-3.4', code_path + 'AnnouncementInt.bc', \
        file_path + '.bc', '-o', file_path + '_link.bc'])
    subprocess.call(['klee', '--libc=uclibc', '--write-kqueries', '--posix-runtime',  file_path + '_link.bc'])

    map_file = directory + '/map/' + router + '_map'
    test_map = [ line.split('|') for line in open(map_file) ]
    results = code_path + 'klee-last'
    ann = generate_all_tests(router, test_map, results)
    return ann

# Add announcements from rtr1 to rtr2
def add_announcements(announcements, mapping, rtr1, rtr2):
    for ann1 in announcements[rtr1]:
        match = False
        # print("ann1:\n%s" % ann1)
        # Get neighbor mapping
        ngh = get_neighbor(mapping, ann1.neighbor)
        '''
        for pair in mapping:
            if ann1.neighbor == str(pair[0]):
                ngh = str(pair[1])
                break
                '''
        for ann2 in announcements[rtr2]:
            # print("ann2:\n%s" % ann2)
            if ngh == ann2.neighbor and ann1.announcement == ann2.announcement:
                match = True
                break
        # If match is False, ann1 needs to be added to rtr2
        if not match:
            ann = Announcement(rtr2, ngh, ann1.announcement)
            announcements[rtr2].append(ann)

def get_neighbor(mapping, ngh):
    for pair in mapping:
        if ngh == str(pair[0]):
            return str(pair[1])

def get_test_map(announcements, mapping):
    test_map = []
    routers = announcements.keys()
    for i, ann1 in enumerate(announcements[routers[0]]):
        ngh = get_neighbor(mapping, ann1.neighbor)
        for j, ann2 in enumerate(announcements[routers[1]]):
            if ngh == ann2.neighbor and ann1.announcement == ann2.announcement:
                test_map.append((i,j))
                break
    return test_map

def get_neighbor_pair(ngh_list1, ngh_list2):
    if(len(ngh_list1)!= len(ngh_list2)):
        print("Length of two lists differ")
        print(ngh_list1)
        print(ngh_list2)
        return []
    ngh_list1_int = [address_to_masked_value(ngh.split('/')[0],'32') for ngh in ngh_list1 ]
    ngh_list2_int = [address_to_masked_value(ngh.split('/')[0],'32') for ngh in ngh_list2 ]
    # x = 0
    # neighbor_map = []
    neighbor_dict = {}
    for x, int_ip in enumerate(ngh_list1_int):
        mod_sub = min( (abs(val - int_ip), idx) for (idx,val) in enumerate(ngh_list2_int))
        if ngh_list2[mod_sub[1]] in neighbor_dict.values():
            print("Multiple Neighbors are getting mapped to Single Neighbor")
            return {}
        neighbor_dict[ngh_list1[x]] = ngh_list2[mod_sub[1]]
        '''
        if pair_map[1] in [nghs[1] for nghs in neighbor_map]:
            print("Multiple Neighbors are getting mapped to Single Neighbor")
            return []
        neighbor_map.append(pair_map)
        x = x + 1
        '''
    return neighbor_dict

def router_neighbor_mappings(sld, routers):
    res = []
    for router_pair in routers:
        r1, r2 = router_pair.items()[0]
        # Skip router pairs in routers if not in Batfish JSON file, so never added to sld
        if not sld.get(r1) or not sld.get(r2):
            continue
        r1_sess = sld[r1]
        r2_sess = sld[r2]
        r1_neighbors = {s.neighbor: s for s in r1_sess}
        r2_neighbors = {s.neighbor: s for s in r2_sess}
        r1_ips = r1_neighbors.keys()
        r2_ips  = r2_neighbors.keys()
        neighbor_map = get_neighbor_pair(r1_ips, r2_ips)
        res.append(((r1, r2), neighbor_map))
        if not neighbor_map:
            print(r1, r2)
        # res.append((router_pair, neighbor_map))
    return res

