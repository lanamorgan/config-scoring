#!/usr/bin/python
from parse import *
from utils.Write_Code import *
from os.path import isfile, join
import os
from munkres import Munkres
from Levenshtein import distance
from scoring import get_neighbor_pair_score
import time

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def rank(in_path, out_path, routers):
    pair_score = []
    for i in range(len(routers)):
        for j in range(i+1, len(routers)):
            pair = (routers[i], routers[j])
            pair_score.append(mapping_from_JSON(in_path,pair))

    log_file = open("bgp"+str(time.time())+".txt", 'w')  
    pair_score = sorted(pair_score, key = lambda p: p.m_score + p.edit_d)
    router_map = {}
    for pair in pair_score:
        if pair.r1 not in router_map:
            router_map[pair.r1] = pair
        if pair.r2 not in router_map:
            router_map[pair.r2] = pair
    for p1 in router_map:
        p = router_map[p1]
        p2 = p.r2 if p1 == p.r1 else p.r1       
        log_line = bcolors.WARNING + "Router1: "+ p1 + "\nRouter2: "+ p2 +\
         "\nNgh_Ip_Score: " +  str(p.m_score) + "\nEdit_score: "  + str(p.edit_d) + bcolors.ENDC +  "\n"
        
        for key,value in p.n_map.iteritems():
            # pdb.set_trace()
            r1_desc = p.r1_bgp_nghs[key] if p.r1_bgp_nghs[key]!=None else "" 
            r2_desc = p.r2_bgp_nghs[value] if p.r2_bgp_nghs[value]!=None else "" 
            log_line = log_line +"R1:   (" +key + " , "+ r1_desc +\
                       ")\nR2:   (" + value + " , " + r2_desc  +") \n"        
        log_line = log_line + "\n\n"
        log_file.write(log_line)

    log_file = open("intf"+str(time.time())+".txt", 'w')
    pair_score = sorted(pair_score, key = lambda p: p.intf_score + p.edit_d)
    router_map = {}
    for pair in pair_score:
        if pair.r1 not in router_map:
            router_map[pair.r1] = pair
        if pair.r2 not in router_map:
            router_map[pair.r2] = pair
    for p1 in router_map:
        p = router_map[p1]
        p2 = p.r2 if p1 == p.r1 else p.r1
        log_line = bcolors.WARNING + "Router1: "+ p1 + "\nRouter2: "+ p2 +\
         "\nIntf_Score: " +  str(p.intf_score) + "\nEdit_score: "  + str(p.edit_d) + bcolors.ENDC +  "\n"
        for key,value in p.intf_map.iteritems():
            log_line = log_line +"R1:   (" +key + " , "+ p.r1_intf[key][0] + " , "+ p.r1_intf[key][1] +\
                       ")\nR2:   (" + value + " , " + p.r2_intf[value][0] + " , "+ p.r2_intf[value][1] +") \n"        
        log_line = log_line + "\n\n"
        log_file.write(log_line) 

    return router_map


'''
"HundredGigabitEthernet0/2/0/3": {
                    "declaredNames": [
                        "HundredGigE0/2/0/3"
                    ], 
                    "prefix": "169.232.4.12/31",      
                    "description": "bd11f2.csb1.ucla.net:ns:et-0/0/0 CID#310-200-3410", 
                    "allPrefixes": [
                        "169.232.4.12/31"
                    ], 
                    "name": "HundredGigabitEthernet0/2/0/3", 
                    "bandwidth": 1000000000000.0, 
                    "mtu": 9192, 
                }, 
Made an assumption that declaredNames and allprefixes are just of unit size.
'''

def interface_name_mapping(data, item):
    prefix_to_intf = {}
    ip = None
    for intf in data['nodes'][item]['interfaces']:
        intf_obj = data['nodes'][item]['interfaces'][intf]
        if intf_obj.get('allPrefixes'):
            ip = str(intf_obj.get('allPrefixes')[0])
            intf_name = str(intf_obj.get('declaredNames')[0])
            description = str(intf_obj.get('description'))
            prefix_to_intf[ip] = (intf_name,description)
    return prefix_to_intf

def get_bgp_neighbors(data, item):
    ngh_desription = {}
    if data['nodes'][item]['vrfs']['default'].get('bgpProcess'):
        bgpProcess = data['nodes'][item]['vrfs']['default']['bgpProcess']
        if bgpProcess.get('neighbors'):
            ngh_list = list(bgpProcess['neighbors'].keys())
            for ngh in ngh_list:
                ngh_desription[ngh] = bgpProcess['neighbors'][ngh].get('description')
            return ngh_desription
        else:
            return ngh_desription

def mapping_from_JSON(path,pair):
    (r1, r2) = pair
    r1_file = path + r1 + ".json"
    r2_file = path + r2 + ".json"
    with open(r1_file, 'r') as data_file:    
        data = json.load(data_file)
    r1_intf_dict = interface_name_mapping(data,[y for y in data['nodes']][0])
    r1_bgp_nghs = get_bgp_neighbors(data,[y for y in data['nodes']][0])
    with open(r2_file, 'r') as data_file:    
        data = json.load(data_file)
    r2_intf_dict = interface_name_mapping(data,[y for y in data['nodes']][0])
    r2_bgp_nghs = get_bgp_neighbors(data,[y for y in data['nodes']][0])
    (n_map, n_score) = get_neighbor_pair_score(r1_bgp_nghs.keys(), r2_bgp_nghs.keys())
    (intf_map, intf_score) = get_neighbor_pair_score(r1_intf_dict.keys(),r2_intf_dict.keys())
    return Pair(r1, r2, r1_intf_dict, r2_intf_dict, r1_bgp_nghs, r2_bgp_nghs, \
                n_map, n_score, intf_map, intf_score, distance(r1,r2))

class Pair:
    def __init__(self, r1, r2, r1_intf, r2_intf, r1_bgp_nghs, r2_bgp_nghs, n_map, map_score, intf_map, intf_score, edit_distance):
        self.r1 = r1
        self.r2 = r2
        self.r1_intf = r1_intf
        self.r2_intf = r2_intf
        self.r1_bgp_nghs = r1_bgp_nghs
        self.r2_bgp_nghs = r2_bgp_nghs
        self.m_score = map_score
        self.n_map = n_map
        self.intf_map = intf_map
        self.intf_score = intf_score
        self.edit_d = edit_distance

def main():
    path = sys.argv[1]
    directory = "utils/bc/"
    routers = [f[:-5] for f in os.listdir(path)]
    rank(path, directory, routers)

if __name__ == "__main__":
    main()