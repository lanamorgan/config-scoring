from utils.Helper import *

def write_config_file(config_file, data, item, bgp_tuple, session_list_dict, \
        community_list_dict, as_path_list_dict, route_filter_list_dict, \
        route_map_dict, policy_dict):
    # write_cisco(config_file, data, item)
    write_debug(config_file)
    write_interfaces(config_file, data, item)
    write_ospf(config_file, data, item)
    write_bgp(config_file, bgp_tuple)
    write_address_family(config_file, data, item, session_list_dict)
    write_community_list(config_file, community_list_dict)
    write_as_path_list(config_file, as_path_list_dict)
    write_route_filter(config_file, route_filter_list_dict)
    write_route_map(config_file, route_map_dict, policy_dict)

def write_route_map(config_file, route_map_dict, policy_dict):
    for route_map in route_map_dict:
        for clause in route_map_dict[route_map]:
            write_file_wrapper(config_file, 'route-map ' + clause.name + ' permit ' + \
                    clause.seq + '\n')
            # Write match (guard) statements (just need one st
            if clause.community_list:
                name = clause.community_list[0].name
                write_file_wrapper(config_file, ' match community ' + name + '\n')
            if clause.route_filter_list:
                name = clause.route_filter_list[0].name
                write_file_wrapper(config_file, ' match ip address prefix-list ' + \
                        name + '\n')
            if clause.as_path_list:
                name = clause.as_path_list[0].name
                write_file_wrapper(config_file, ' match as-path ' + name + '\n')
            # Write set (action) statements
            if clause.actions:
                for action in clause.actions:
                    additive = " additive" if action.additive else ""
                    value = action.value
                    # Action names defined by setting action.field in set_route_map()
                    if action.field.find('local_pref') != -1:
                        set_string = ' set local-preference '
                    elif action.field.find('metric') != -1:
                        set_string = ' set metric '
                    elif action.field.find('community') != -1:
                        set_string = ' set community '
                    elif action.field.find('next_hop') != -1:
                        value = int_to_ip(int(action.value))
                        set_string = ' set ip next-hop '
                    else:
                        raise Exception("Undefined action.field")
                    write_file_wrapper(config_file, set_string + value + additive + '\n')

def write_community_list(config_file, community_list_dict):
    for community_list in community_list_dict:
        for entry in community_list_dict[community_list]:
            action = ' permit ' if entry.permit else ' deny '
            write_file_wrapper(config_file, 'ip community-list expanded ' + entry.name + \
                    action + entry.regex + '\n') 

def write_as_path_list(config_file, as_path_list_dict):
    for as_path_list in as_path_list_dict:
        for entry in as_path_list_dict[as_path_list]:
            action = ' permit ' if entry.permit else ' deny '
            write_file_wrapper(config_file, 'ip as-path access-list ' + entry.name + \
                    action + entry.regex + '\n') 

def write_route_filter(config_file, route_filter_list_dict):
    for route_filter_list in route_filter_list_dict:
        for entry in route_filter_list_dict[route_filter_list]:
            action = ' permit ' if entry.permit else ' deny '
            write_file_wrapper(config_file, 'ip prefix-list ' + entry.name + \
                    " seq " + str(entry.seq) + action + entry.prefix)
            prefix_length = entry.prefix.split('/')[1]

            # If len = ge = le, do not print ge or le
            # If len < ge <= le, print both ge and le
            # if ge <= len < le, print le (no ge)

            # Write le if mask length < le
            if int(prefix_length) < int(entry.mask_upper):
                # Write ge if mask length < ge
                if prefix_length < entry.mask_lower:
                    write_file_wrapper(config_file, ' ge ' + entry.mask_lower)
                write_file_wrapper(config_file, ' le ' + entry.mask_upper)
            elif int(prefix_length) > int(entry.mask_upper):
                raise Exception("Prefix length longer than max of route filter range.")
            write_file_wrapper(config_file, '\n')


# TODO:
# aggregate-address <A.B.C.D/M> summary-only
# neighbor <as_> send-community (in vrfs, but not all encompassing)
# neighbor <as_> route-map <routingPolicy> in|out
# neighbor <as_> route-reflector-client (in vrfs)
# neighbor as2 advertise additional-paths all
# neighbor <ip> activate (only cisco)
def write_address_family(config_file, data, item, session_list_dict):
    agg_str = None
    # Assume always unicast
    write_file_wrapper(config_file, ' address-family ipv4 unicast\n')
    if data['nodes'][item]['vrfs']['default'].get('aggregateRoutes'):
        ip = data['nodes'][item]['vrfs']['default']['aggregateRoutes'][0]['network']
        agg_str = '  aggregate-address ' + ip
    if data['nodes'][item].get('routingPolicies'):
        for policy in data['nodes'][item]['routingPolicies']:
            if policy.find('BGP_COMMON_EXPORT_POLICY') != -1:
                # NOTE: Most have only have one statement, but some cases with multiple (i.e. next-hop-self)
                for statement in data['nodes'][item]['routingPolicies'][policy]['statements']:
                # statement = data['nodes'][item]['routingPolicies'][policy]['statements'][0]
                    if not statement.get('guard'):
                        continue
                    if statement['guard'].get('disjuncts'):
                        for classes in statement['guard']['disjuncts']:
                            if classes.get('conjuncts'):
                                if classes['conjuncts'][0].get('prefixSet'):
                                    ip = classes['conjuncts'][0]['prefixSet']['prefixSpace'][0]
                                    write_file_wrapper(config_file, '  network ' + ip + '\n')
                                # elif classes['comment'].find('Redistribute connected routes'):
                    elif statement.get('prefixSet'):
                        if agg_str and statement['prefixSet']['name'].find('SUMMARY_ONLY') != -1:
                            agg_str += ' summary-only'
                    elif statement['class'].find('SetNextHop') != -1 and statement['expr']['class'].find('SelfNextHop') != -1:
                        ip = policy.split(':')[2][:-1]
                        write_file_wrapper(config_file, '  neighbor ' + ip + ' next-hop-self\n')


    # Write route-map information
    if session_list_dict.get(item):
        for session in session_list_dict[item]:
            neighbor = session.neighbor.split('/')[0]
            if session.import_policy_name:
                write_file_wrapper(config_file, '  neighbor ' + neighbor + \
                        ' route-map ' + session.import_policy_name + ' in\n')
            if session.export_policy_name:
                write_file_wrapper(config_file, '  neighbor ' + neighbor + \
                        ' route-map ' + session.export_policy_name + ' out\n')

    if agg_str:
        write_file_wrapper(config_file, agg_str + '\n')

    if data['nodes'][item]['vrfs']['default'].get('bgpProcess'):
        bgpProcess = data['nodes'][item]['vrfs']['default']['bgpProcess']
        # router_id = data['nodes'][item]['vrfs']['default']['bgpProcess']['routerId']
        if bgpProcess.get('neighbors'):
            for ngh in bgpProcess['neighbors']:
                if bgpProcess['neighbors'][ngh]['sendCommunity']:
                    write_file_wrapper(config_file, '  neighbor ' + ngh.split('/')[0] + \
                            ' send-community\n')

    write_file_wrapper(config_file, ' exit-address-family\n')

def write_ospf(config_file, data, item):
    if data['nodes'][item]['vrfs']['default'].get('ospfProcess'):
        ospfProcess = data['nodes'][item]['vrfs']['default']['ospfProcess']
        for area in ospfProcess['areas']:
            # area_name = data['nodes'][item]['vrfs']['default']['ospfProcess']['areas'][area]
            # write_file_wrapper(config_file, 'router ospf ' + str(area_name) + '\n')
            router_id = ospfProcess['routerId']
            write_file_wrapper(config_file, 'router ospf \n')
            write_file_wrapper(config_file, ' router-id ' + str(router_id) + '\n')
            # NOTE: Hack to infer network ip for ospf from first byte of router_id 
            # with mask 0.255.255.255 or /8 (Does not work for as2dist2)
            ip = str( router_id.split('.')[0] )
            ip += '.0.0.0'
            # mask = '0.255.255.255'
            mask = '/8'
            write_file_wrapper(config_file, ' network ' + ip + mask + ' area ' + \
                    str(area) + '\n')

            # Write "redistribute connected subnets" by looking up OSPF_EXPORT_POLICY
            ospf_export_policy_name = ospfProcess['exportPolicy']
            if data['nodes'][item].get('routingPolicies'):
                ospf_export_policy = data['nodes'][item]['routingPolicies'][ospf_export_policy_name]
                if ospf_export_policy.get('statements'):
                    for statement in ospf_export_policy['statements']:
                        if statement['class'].find('routing_policy.statement.If') != -1:
                            if statement['guard']['class'].find('MatchProtocol') != -1:
                                if statement['guard']['protocol'].find('connected') != -1:
                                    write_file_wrapper(config_file, \
                                            ' redistribute connected \n')
                                elif statement['guard']['protocol'].find('static') != -1:
                                    write_file_wrapper(config_file, \
                                            ' redistribute static \n')

            # Write passive-interface if necessary
            for interface in ospfProcess['areas'][area]['interfaces']:
                intf_obj = data['nodes'][item]['interfaces'][interface]
                if intf_obj['ospfPassive']:
                    # CHANGE to always be lo (since set loopback in mininext)
                    write_file_wrapper(config_file, ' passive-interface lo \n')
                    '''
                    write_file_wrapper(config_file, ' passive-interface ' + \
                            get_ethernet_port_name(interface) + '\n')
                            '''


'''
def write_bgp(config_file, localAs, router_id, bgpProcess, as_to_peer_group_dict, \
        ngh_to_as_dict, ngh_list, prefix_to_intf_dict):
        '''
def write_bgp(config_file, bgp_tuple):
    if not bgp_tuple:
        return

    localAs = bgp_tuple.localAs
    router_id = bgp_tuple.router_id
    bgpProcess = bgp_tuple.bgpProcess
    as_to_peer_group_dict = bgp_tuple.as_to_peer_group_dict
    ngh_to_as_dict = bgp_tuple.ngh_to_as_dict
    ngh_list = bgp_tuple.ngh_list
    prefix_to_intf_dict = bgp_tuple.prefix_to_intf_dict

    loopback_address = None
    loopback_name = None
    write_file_wrapper(config_file, 'router bgp ' + str(localAs) + '\n')
    write_file_wrapper(config_file, ' bgp router-id ' + str(router_id) + '\n')
    
    # Get loopback information
    for intf in prefix_to_intf_dict.keys():
        if prefix_to_intf_dict[intf].lower().find('lo') != -1:
            loopback_address = intf.split('/')[0]
            loopback_name = prefix_to_intf_dict[intf]
    # Comment out writing of peer-groups
    '''
    for remoteAs, group in as_to_peer_group_dict.items():
        write_file_wrapper(config_file, ' neighbor ' + group + ' peer-group\n')
        write_file_wrapper(config_file, ' neighbor ' + group + ' remote-as ' + remoteAs + '\n')
        '''
    for ngh, remoteAs in ngh_to_as_dict.items():
        write_file_wrapper(config_file, ' neighbor ' + ngh + ' remote-as ' + remoteAs + '\n')

    # neighbor <address> update-source lo0
    if loopback_address:
        for ngh in ngh_list:
            if bgpProcess['neighbors'][ngh].get('localIp'):
                localIp = bgpProcess['neighbors'][ngh].get('localIp')
                if localIp == loopback_address:
                    # CHANGE to always be lo (since set loopback in mininext)
                    write_file_wrapper(config_file, ' neighbor ' + ngh.split('/')[0] + \
                            ' update-source lo' + '\n')
                    '''
                    write_file_wrapper(config_file, ' neighbor ' + ngh.split('/')[0] + \
                            ' update-source ' + loopback_name + '\n')
                            '''
    '''
    for ngh in ngh_list:
        group = bgpProcess['neighbors'][ngh].get('group')
        if group:
            # Add neighbor to peer-group if it belongs to group
            address = bgpProcess['neighbors'][ngh]['address']
            write_file_wrapper(config_file, ' neighbor ' + address + ' peer-group ' + \
                    group + '\n')
                    '''

# NOTE: ip access-group (interface incomingFilter, outgoingFilter) refers to data plane ACLS
# No media-type gbic, duplex full, negotiation auto (ignore bc not important)
# def write_interface(config_file, intf_obj, intf_name, ip):
def write_interfaces(config_file, data, item):
    for intf in data['nodes'][item]['interfaces']:
        ip = None
        if data['nodes'][item]['interfaces'][intf].get('allPrefixes'):
            ip = str(data['nodes'][item]['interfaces'][intf].get('allPrefixes')[0])
        intf_obj = data['nodes'][item]['interfaces'][intf]
        # new_intf_name = item + '-' + get_ethernet_port_name(intf)
        new_intf_name = get_interface_name(item, intf)

        write_file_wrapper(config_file, 'interface ' + new_intf_name + '\n')
        if ip:
            write_file_wrapper(config_file, ' ip address ' + ip + '\n')
        else:
            write_file_wrapper(config_file, ' no ip address\n')
        if not intf_obj['active']:
            write_file_wrapper(config_file, ' shutdown\n')
        if intf_obj['type'] == 'PHYSICAL':
            speed = int( intf_obj['bandwidth'] / 1.0E6 )
            write_file_wrapper(config_file, ' speed ' + str(speed) + '\n')

def write_cisco(config_file, data, item):
    timestamps = None
    for vendor in data['nodes'][item]['vendorFamily']:
        if data['nodes'][item]['vendorFamily'][vendor]['services']['timestamps']['enabled']:
            timestamps = True
        for subservice in data['nodes'][item]['vendorFamily'][vendor]['services']['timestamps']['subservices']:
            if timestamps:
                string = 'service timestamps'
            if subservice == 'debug' and data['nodes'][item]['vendorFamily'][vendor]['services']['timestamps']['subservices'][subservice]['subservices']['datetime']['enabled'] and data['nodes'][item]['vendorFamily'][vendor]['services']['timestamps']['subservices'][subservice]['subservices']['datetime']['subservices']['msec']['enabled']:
                string += ' debug datetime msec'
            elif subservice == 'log' and data['nodes'][item]['vendorFamily'][vendor]['services']['timestamps']['subservices'][subservice]['subservices']['datetime']['enabled'] and data['nodes'][item]['vendorFamily'][vendor]['services']['timestamps']['subservices'][subservice]['subservices']['datetime']['subservices']['msec']['enabled']:
                string += ' log datetime msec'
            write_file_wrapper(config_file, string + '\n')
        write_file_wrapper(config_file, 'hostname ' + str(item) + '\n')
        if data['nodes'][item]['vendorFamily'][vendor]['aaa']['newModel']:
            write_file_wrapper(config_file, 'aaa new-model\n')
        else:
            write_file_wrapper(config_file, 'no aaa new-model\n')

def write_debug(config_file):
    write_file_wrapper(config_file, 'dump bgp all /var/log/quagga/all.mrt\n')
    write_file_wrapper(config_file, 'log file /var/log/quagga/bgpd.log\n')
    write_file_wrapper(config_file, 'debug bgp updates\n')
    write_file_wrapper(config_file, 'debug ip routing\n')

