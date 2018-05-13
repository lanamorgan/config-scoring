#!/usr/bin/python

from utils.Helper import *
from utils.Classes import *
from utils.Route_Map import *
from utils.Write_Config import *
from utils.Write_Code import *
from utils.ktest_parser import *

def read_file(filename, directory=None, equiv=None):
    with open(filename, 'r') as data_file:    
        data = json.load(data_file)

    session_list_dict = {} # maps router (item) to list of sessions with neighbors
    route_map_dict = {}
    policy_dict = {} 
    community_list_dict = {} 
    as_path_list_dict = {} 
    route_filter_list_dict = {} 
    prefix_to_intf_dict = {}
    router_dict = {}

    if directory:
        create_directory(directory)
        config_dir = directory+'/configs/'
        create_directory(config_dir)
    
    config_file = None # init config_file; if directory not set, write_config_wrapper no-op
    topology_file = "topology.json" if directory else None

    for item in data['nodes']:
        if data['nodes'][item]['configurationFormat'].find('CISCO') == -1:
             print >> sys.stderr, "Warning:", data['nodes'][item]['name'], "does not use CISCO format"
             continue
        route_map_dict[item] = {} # dict of Route_Map_Clause name to list of clauses

        if directory:
            create_directory(config_dir + str(item))
            config_filename = config_dir + str(item) + '/Quagga.conf'
            config_file = open(config_filename, 'w')
            os.chmod(config_filename, 0o775)

        # Populate data structures
        community_list_dict[item] =     get_community_list(data, item)
        as_path_list_dict[item] =       get_as_path_list(data, item)
        route_filter_list_dict[item] =  get_route_filter(data, item)
        prefix_to_intf_dict[item] =     get_interfaces(data, item)
        policy_dict[item], bgp_tuple =  get_bgp_info(data, item, session_list_dict, \
                prefix_to_intf_dict[item])
        
        # NOTE: Modifies route_map_dict and policy_dict
        get_route_map_info(data, item, router_dict, route_map_dict[item], \
                policy_dict[item], community_list_dict[item], \
                as_path_list_dict[item], route_filter_list_dict[item])

        # Update policy attrs in session_list_dict; point to correct policy in route_map_dict
        update_session_list_dict(item, session_list_dict, route_map_dict, \
                policy_dict, prefix_to_intf_dict)

        # Update router_dict entries with static routes
        get_static_routes(data, item, router_dict[item])

        # Functions strictly to write to config in utils/Write_Config.py
        if config_file:
            write_config_file(config_file, data, item, bgp_tuple, session_list_dict, \
                    community_list_dict[item], as_path_list_dict[item], \
                    route_filter_list_dict[item], route_map_dict[item], policy_dict[item])

    if equiv:
        # Create neighbor mapping with router mapping tuples
        maps = router_neighbor_mappings(session_list_dict, equiv)
        write_equivalence_check(session_list_dict, directory, maps)
        write_code(session_list_dict, directory)
    else:
        if directory:
            write_code(session_list_dict, directory)

    topology = create_topology(prefix_to_intf_dict, directory, filename=topology_file)

    return session_list_dict, prefix_to_intf_dict, topology

# -----------------------------------------------------------------------------
# FUNCTIONS TO GET DATAMODEL INFORMATION
# -----------------------------------------------------------------------------
def get_route_filter(data, item):
    ipAccessList = set()
    routeFilterList = set()
    route_filter_list_dict = {}

    # get ip access-list first to compare with ip prefix-list
    if data['nodes'][item].get('ipAccessLists'):
        for entry in data['nodes'][item]['ipAccessLists']:
            ipAccessList.add(entry)

    if data['nodes'][item].get('routeFilterLists'):
        for entry in data['nodes'][item]['routeFilterLists']:
            routeFilterList.add(entry)
    # ip prefix-list (no seq info)
    # Takes care of extended ACLs used to configure BGP
    if data['nodes'][item].get('routeFilterLists'):
        for entry in data['nodes'][item]['routeFilterLists']:
            # if entry not in ipAccessList and entry.find('~') == -1:
            if entry.find('~') == -1:
                name = str(data['nodes'][item]['routeFilterLists'][entry]['name'])
                # NOTE: Currently keep track of seq according to standards 
                # Haven't found in batfish datamodel for routeFilterLists
                seq = 5
                if not route_filter_list_dict.get(name):
                    route_filter_list_dict[name] = []
                for line in data['nodes'][item]['routeFilterLists'][entry]['lines']:
                    prefix = str(line['prefix'])

                    # NOTE: Hack for routeFilterLists with 0 mask (lookup ipAccessLists instead)
                    if prefix.split('/')[1] == '0' and name in data['nodes'][item]['ipAccessLists']:
                        for ln in data['nodes'][item]['ipAccessLists'][name]['lines']:
                            # TODO: get information to populate Route_Filter_List
                            # prefix, lengthRange, seq
                            permit = True if ln['action'] == 'ACCEPT' else False
                            # prefix = str(ln['srcIps'][0]) # Compatible with old Batfish                          
                            prefix = str(ln['matchCondition']['headerSpace']['srcIps']["ipWildcard"]) # Compatible with new Batfish

                            # If no mask length, assume full host match
                            if len(prefix.split('/')) < 2:
                                prefix += '/32'
                            rng = prefix.split('/')[1]
                            rfl = Route_Filter_List(name, permit, prefix, rng, rng, seq)
                            route_filter_list_dict[name].append(rfl)
                            seq += 5
                        break

                    permit = True if line['action'] == 'ACCEPT' else False
                    rng = line['lengthRange'].split('-')
                    rfl = Route_Filter_List(name, permit, prefix, str(rng[0]), str(rng[1]), seq)
                    route_filter_list_dict[name].append(rfl)
                    seq += 5

    return route_filter_list_dict

def get_community_list(data, item):
    # ip community-list expanded
    community_list_dict = {}
    if data['nodes'][item].get('communityLists'):
        for community in data['nodes'][item]['communityLists']:
            communityName = str(data['nodes'][item]['communityLists'][community]['name'])
            for line in data['nodes'][item]['communityLists'][community]['lines']:
                if not community_list_dict.get(communityName):
                    community_list_dict[communityName] = []
                regex = str(line['regex'])
                permit = True if line['action'] == 'ACCEPT' else False
                cl = Community_List(communityName, permit, regex)
                community_list_dict[communityName].append(cl)
    return community_list_dict

def get_as_path_list(data, item):
    # ip as-path access-list
    as_path_list_dict = {}
    if data['nodes'][item].get('asPathAccessLists'):
        for as_path_list in data['nodes'][item]['asPathAccessLists']:
            as_path_list_name = str(data['nodes'][item]['asPathAccessLists'][as_path_list]['name'])
            for line in data['nodes'][item]['asPathAccessLists'][as_path_list]['lines']:
                if not as_path_list_dict.get(as_path_list_name):
                    as_path_list_dict[as_path_list_name] = []
                regex = str(line['regex'])
                permit = True if line['action'] == 'ACCEPT' else False
                aspl = AS_Path_List(as_path_list_name, permit, regex)
                as_path_list_dict[as_path_list_name].append(aspl)

    return as_path_list_dict

# -----------------------------------------------------------------------------
# FUNCTIONS GATHER INFORMATION FOR DATA STRUCTURES
# -----------------------------------------------------------------------------
def get_bgp_info(data, item, session_list_dict, prefix_to_intf_dict):
    policy_dict = {} # maps policies seen in vrfs to list of conjuncts of routingPolicies
    ReturnBGP = collections.namedtuple('ReturnBGP', ['localAs', 'router_id', 'bgpProcess', \
            'as_to_peer_group_dict', 'ngh_to_as_dict', 'ngh_list', 'prefix_to_intf_dict'])
    if data['nodes'][item]['vrfs']['default'].get('bgpProcess'):
        bgpProcess = data['nodes'][item]['vrfs']['default']['bgpProcess']
        localAs = -1 # Initialize default value in case bgpProcess has no neighbors
        router_id = bgpProcess['routerId']
        ngh_list = list()
        if bgpProcess.get('neighbors'):
            ngh_list = list(bgpProcess['neighbors'].keys())
            localAs = bgpProcess['neighbors'][ngh_list[0]]['localAs']
        as_to_peer_group_dict = {} # as number mapped to peer-group name
        ngh_to_as_dict = {} # neighbor ip matched to remote-as number (no group)
        ngh_policy = {} # contains importPolicy and exportPolicy for each neighbor
        for ngh in ngh_list:
            group = bgpProcess['neighbors'][ngh].get('group')
            remoteAs = bgpProcess['neighbors'][ngh]['remoteAs']
            # Either map remote as to peer-group or neighbor IP
            if group:
                as_to_peer_group_dict[str(remoteAs)] = str(group)
            '''
            else:
                ngh_to_as_dict[ngh.split('/')[0]] = str(remoteAs)
                '''
            ngh_to_as_dict[ngh.split('/')[0]] = str(remoteAs)

            ngh_policy[ngh] = {}
            ngh_policy[ngh]['exportPolicy'] = bgpProcess['neighbors'][ngh].get('exportPolicy')
            ngh_policy[ngh]['importPolicy'] = bgpProcess['neighbors'][ngh].get('importPolicy')

            policy_dict[ngh_policy[ngh]['exportPolicy']] = []
            if ngh_policy[ngh]['importPolicy']:
                policy_dict[ngh_policy[ngh]['importPolicy']] = []
                ses = Session(item, ngh, remoteAs, ngh_policy[ngh]['importPolicy'], \
                        ngh_policy[ngh]['exportPolicy'])
            else:
                ses = Session(item, ngh, remoteAs, "", ngh_policy[ngh]['exportPolicy'])
            if not session_list_dict.get(item):
                session_list_dict[item] = []
                # session_list_dict[item] = {}
            session_list_dict[item].append(ses)
            # session_list_dict[item][ngh] = ses
        '''
        if config_file:
            write_bgp(config_file, localAs, router_id, bgpProcess, as_to_peer_group_dict, \
                    ngh_to_as_dict, ngh_list, prefix_to_intf_dict)
                    '''
    else:
        return policy_dict, None

    bgp_tuple = ReturnBGP(localAs, router_id, bgpProcess, as_to_peer_group_dict, \
            ngh_to_as_dict, ngh_list, prefix_to_intf_dict)

    return policy_dict, bgp_tuple

def get_interfaces(data, item):
    prefix_to_intf = {}
    ip = None
    for intf in data['nodes'][item]['interfaces']:
        intf_obj = data['nodes'][item]['interfaces'][intf]
        # Replace original interface name with new encoding
        # Take care to have intf_name to be <= 15 characters
        # new_intf_name = item + '-' + get_ethernet_port_name(intf)
        new_intf_name = get_interface_name(item, intf)

        if data['nodes'][item]['interfaces'][intf].get('allPrefixes'):
            ip = str(data['nodes'][item]['interfaces'][intf].get('allPrefixes')[0])
            # Map prefix to interface name for item dictionary
            prefix_to_intf[ip] = new_intf_name

    return prefix_to_intf

def get_static_routes(data, item, router):
    if data['nodes'][item]['vrfs']['default'].get('staticRoutes'):
        for route in data['nodes'][item]['vrfs']['default']['staticRoutes']:
            network = str(route['network'])
            next_hop = str(route['nextHopIp'])
            if next_hop.find('NONE') != -1:
                next_hop = None
            cost = int(route['administrativeCost'])
            router.add_static_route(Route(network, next_hop, cost))

def read_router_file(router_file):
    routers = [] # list of equivalent router pairs
    if router_file and os.path.exists(router_file):
        with open(router_file, 'r') as f:
            for line in f:
                toks = line.rstrip().split(':')
                routers.append({toks[0]:toks[1]})
    return routers

if __name__ == '__main__':
    parser = argparse.ArgumentParser("Read Batfish Nodes file and directory")
    parser.add_argument("file", type=str, help="Batfish output topology JSON file.")
    parser.add_argument("dir", type=str, help="Target directory to store configs.")
    parser.add_argument("--nodes", type=str, help="Router(s)", nargs='*')
    parser.add_argument("--rf", type=str, help="File containing equivalent router pairs")
    args = parser.parse_args()
    filename = args.file
    directory = args.dir
    nodes = args.nodes
    # Router argument is a list of pairs, where fst is pair of routers and snd is map
    # routers = [(("rtr53f3e.cogen", "rtr54f3e.cogen"), {"169.232.13.210/32": "169.232.13.208/32"})]
    router_file = args.rf
    routers = read_router_file(router_file) # List of dictionary pairs for routers

    # Read the topology
    session_list_dict, prefix_to_intf_dict, topology = read_file(filename, directory, routers)
    '''
    # Create neighbor mapping with router mapping tuples
    with open('../exabgp_Trial/mapping.txt', 'r') as f:
        mapping = json.loads(f.read())
    test_announcements, test_map = generate_announcements(session_list_dict, directory, routers=nodes)
    '''
