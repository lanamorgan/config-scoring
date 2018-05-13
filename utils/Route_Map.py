from utils.Classes import *
from utils.Helper import address_to_masked_value
import pdb

# Helper functions to interpret route_map information (follow all the indirection)
def get_route_map_info(data, item, router_dict, route_map_dict, policy_dict, cld, apld, rfld):
    router = Router(item)
    if data['nodes'][item].get('routingPolicies'):
        for policy in data['nodes'][item]['routingPolicies']:
            if not data['nodes'][item]['routingPolicies'][policy].get('statements'):
                continue

            # NOTE: Batfish data model routingPolicies seem to have statements of length 1
            route_map = data['nodes'][item]['routingPolicies'][policy]['statements'][0]
            route_map_dict[policy] = [] # list of clauses matching route_map_name

            order = 1
            # Write these policies to quagga config file (ignore routingPolicies with '~')
            if policy.find('EXPORT_POLICY') == -1 and policy.find('~') == -1:
                name = str(data['nodes'][item]['routingPolicies'][policy]['name'])
                # Get nested route-maps inside falseStatements
                if route_map.get('comment'):
                    while route_map.get('comment'):
                        rmc = process_route_map(route_map, name, \
                                 policy_dict, cld, apld, rfld, str(order))
                        if rmc:
                            route_map_dict[name].append(rmc)
                        route_map = route_map['falseStatements'][0]
                        order += 1
                    # NOTE: Haven't tested this code, but should theoretically handle 
                    # route-map where last clause has no match statement
                    if route_map.get('statements'):
                        rmc = Route_Map_Clause(name, seq=str(order), permit=True)
                        set_route_map(route_map, rmc, "statements")
                        route_map_dict[name].append(rmc)
                else:
                    # Handles route-map with no match statement
                    rmc = Route_Map_Clause(name, seq=str(order), permit=True)
                    route_map = data['nodes'][item]['routingPolicies'][policy]
                    set_route_map(route_map, rmc, "statements")
                    route_map_dict[name].append(rmc)

            elif policy.find('BGP_COMMON_EXPORT_POLICY') != -1:
                process_common_export_policy(data['nodes'][item]['routingPolicies'][policy]['statements'], router)

            elif policy.find('OSPF') == -1 and policy.find('.') != -1 \
                    and policy.find('AGGREGATE_ROUTE_GEN') == -1: 
                # NOTE: currently ignoring ~OSPF_EXPORT_POLICY:default~, 
                # ~AGGREGATE_ROUTE_GEN:default:<prefix>~,
                # ~BGP_PEER_EXPORT_POLICY:default:<IPv6>~
                name = str(data['nodes'][item]['routingPolicies'][policy]['name'])
                # NOTE: Found cases where len(statements) > 1, so loop through
                for route_map_statement in data['nodes'][item]['routingPolicies'][policy]['statements']:
                    rmc = process_route_map(route_map_statement, name, policy_dict, \
                            cld, apld, rfld, str(order))
                if rmc:
                    route_map_dict[name].append(rmc)

            # Hack to delete policies with tilda in policy name (internal to batfish)
            if policy in route_map_dict.keys() and policy.find("~") != -1:
                del route_map_dict[policy]
            # If policy remains, sort list of Route_Map_Clause based on seq num (low to high)
            if policy in route_map_dict.keys():
                route_map_dict[policy].sort(key=lambda x: x.seq)
    router_dict[item] = router

def process_route_map(route_map, policy_name, policy_dict, cld, apld, rfld, seq):
    rmc = None
    if not route_map.get('comment'):
        # Ignore section in Batfish JSON
        return None
    toks = route_map['comment'].split('~')

    for i in range(len(toks)):
        if toks[i] == policy_name:
            seq = str(toks[i+1])
            break
    if route_map.get('guard'):
        # Guard: start with 'org.batfish.datamodel.routing_policy.expr.'
        rmc = Route_Map_Clause(policy_name, seq, permit=True)
        cls = route_map['guard']['class']
        if cls.find('Conjunction') != -1:
            for entry in route_map['guard']['conjuncts']:
                cls = entry['class'] # Update cls variable so it's not '*.Conjunction'
                match_route_map(entry, cls, policy_name, rmc, policy_dict, \
                        cld, apld, rfld)
        else:
            entry = route_map['guard']
            match_route_map(entry, cls, policy_name, rmc, policy_dict, \
                    cld, apld, rfld)
    else:
        raise Exception("route map has no guard")
    set_route_map(route_map, rmc, "trueStatements")

    return rmc

def process_common_export_policy(statements, router):
    for route_map_statement in statements:
        if route_map_statement.get('guard'):
            if route_map_statement['guard'].get('disjuncts'):
                for clause in route_map_statement['guard']['disjuncts']:
                    if clause.get('comment') and clause['comment'].find('Redistribute') != -1:
                        connected = False
                        static = False
                        rm = None
                        for entry in clause['conjuncts']:
                            if entry.get('protocol'):
                                if entry['protocol'] == 'static':
                                    static = True
                                elif entry['protocol'] == 'connected':
                                    connected = True
                            elif entry.get('expr'):
                                if entry['expr'].get('calledPolicyName'):
                                    rm = entry['expr']['calledPolicyName']
                        if static:
                            router.set_static(rm)
                        elif connected:
                            router.set_connected(rm)
                    elif clause.get('conjuncts'):
                        for entry in clause['conjuncts']:
                            if entry['class'].find('MatchPrefixSet') != -1:
                                router.add_network(str(entry['prefixSet']['prefixSpace'][0]))

def match_route_map(entry, cls, policy_name, rmc, policy_dict, cld, apld, rfld):
    cl = None
    rfl = None
    apl = None
    if cls.find('MatchCommunitySet') != -1:
        community = str(entry['expr']['name'])
        if cld.get(community):
            cl = cld.get(community)
            rmc.update_community_list(cl)
    elif cls.find('MatchPrefixSet') != -1:
        ip = str(entry['prefixSet']['name'])
        if rfld.get(ip):
            rfl = rfld.get(ip)
            rmc.update_route_filter_list(rfl)
    # TODO: Probably will need another condition for match on as path list in future

    # Redirects export policy to actual route-map name
    elif cls.find('CallExpr') != -1:
        if policy_name in policy_dict:
            # List of policies that make up policy_name
            policy_dict[policy_name].append(entry['calledPolicyName'])
        else:
            # Exception to see what goes down this path
            raise Exception("policy_name not in policy_dict")

def set_route_map(route_map, rmc, statements_str):
    local_pref = None
    metric = None
    community = None

    med = None
    as_path = None

    for statement in route_map[statements_str]:
        if statement['class'].find('SetMetric') != -1:
            metric = str(statement['metric']['value'])
            rmc.update_action("metric", metric)
        elif statement['class'].find('SetLocalPreference') != -1:
            local_pref = str(statement['localPreference']['value'])
            rmc.update_action("local_pref", local_pref)
        elif statement['class'].find('AddCommunity') != -1:
            prefix = str(statement['expr']['communities'][0]['prefix']['value'])
            suffix = str(statement['expr']['communities'][0]['suffix']['value'])
            community = prefix + ":" + suffix
            rmc.update_action("community", community, True)
        elif statement['class'].find('SetNextHop') != -1:
            if statement['expr']['class'].find('IpNextHop') != -1:
                next_hop = str(address_to_masked_value(str(statement['expr']['ips'][0]), 32))
                rmc.update_action("next_hop", next_hop)
        '''
        elif statement['class'].find('StaticStatement') != -1:
            # Not sure what to do (occurs for route-map with set ipv6 next-hop statement)
            continue
            '''
