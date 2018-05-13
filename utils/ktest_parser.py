import sys
import string
import os
import subprocess

class Announcement:
    def __init__(self, router, neighbor_ip, ann):
        self.router = router
        self.neighbor = neighbor_ip
        self.announcement = ann
    def __str__(self):
        ann_str = "Router:\t\t%s\nNeighbor:\t%s\nAnnouncement:\t%s\n" \
                % (self.router, self.neighbor, self.announcement)
        return ann_str
    
def get_field(bytelist, location, length):
    l = bytelist[location:location+length]
    #val = sum([ l[i] << (8*i) for i in range(len(l))]) 
    #print l, hex(val)
    return l

def parse_ktest_string(s):
    s = s.lstrip(' b')
    s = s[1:-1]
    bytelist = []
    while(len(s) > 0):
        if s.startswith(r"\x"):
            bytelist.append(int(s[2:4], 16))
            s = s[4:]
        else:
            bytelist.append(ord(s[0]))
            s = s[1:]
    return bytelist

def read_ktest_output(f):
    objs = []
    a = f.split("\n")
    for line in a:
        temp = line.split(':')
        if(len(temp) >= 3): 
            (obj, field, val) = temp

            obj = obj.lstrip(string.ascii_letters + string.whitespace)
            obj_num = int(obj)

            field = field.strip()

            if field == 'name':
                val = val.lstrip(' b')
                val = val[1:-1]
            elif field == 'data':
                val = parse_ktest_string(val)
            elif field == 'size':
                val = int(val)

            if obj_num >= len(objs):
                objs.append(dict())
            objs[obj_num][field] = val
    return objs

def bytes_to_ip(b):
    return ".".join(str(i) for i in reversed(b))

def bytes_to_int(b):
    return sum( b[i] << 8*i for i in range(4))

def bytes_to_community(b):
    return str((b[3] << 8) + b[2]) + ":"+ str((b[1] << 8) + b[0])

def bytes_to_communities(b):
    communities = []
    for i in range(len(b)/4):
        communities.append( str((b[4*i + 3] << 8) + b[4*i + 2]) + ":"+ str((b[4*i + 1] << 8) + b[4*i]) )
    return communities

def bytes_to_as_path(b):
    return ".".join(hex(i)[2:] for i in reversed(b))
    as_path = []
    for i in range(len(b)/4):
        as_path.append( str(bytes_to_int(b[4*i:4*i+3])) )
    return as_path

def generate_test(objs, router = None, test_map = []):
    communities = []
    as_path = []
    metric = None
    local_pref = None
    community = None
    test_num = None
    for o in objs:
        # Separate Fields
        if o['name'] == 'test_num':
            test_num = bytes_to_int(o['data'])
        if o['name'] == 'pfx':
            prefix = bytes_to_ip(o['data'])
        elif o['name'] == 'mask':
            mask = bytes_to_int(o['data'])
        elif o['name'] == 'comm':
            community = bytes_to_community(o['data'])
        elif o['name'] == 'comm_arr':
            communities = bytes_to_communities(o['data'])
        elif o['name'] == 'comm_len':
            community_len = bytes_to_int(o['data'])
        elif o['name'] == 'as_path':
            as_path = bytes_to_as_path(o['data'])
        elif o['name'] == 'as_path_len':
            as_path_len = bytes_to_int(o['data'])
        elif o['name'] == 'metric':
            metric = bytes_to_int(o['data'])
        elif o['name'] == 'loc_pref':
            local_pref = bytes_to_int(o['data'])

        # Single Field
        if o['name'] == 'ann':
            communities = bytes_to_communities(get_field(o['data'], 0, 64))
            as_path = bytes_to_as_path(get_field(o['data'], 64, 64))
            community_len = bytes_to_int(get_field(o['data'], 128, 4))
            as_path_len = bytes_to_int(get_field(o['data'], 132, 4))
            prefix = bytes_to_ip(get_field(o['data'], 136, 4) )
            mask = bytes_to_int(get_field(o['data'], 140, 4))
            local_pref = bytes_to_int(get_field(o['data'], 144, 4))
            metric = bytes_to_int(get_field(o['data'], 148, 4))

    if test_num is None or test_num >= len(test_map):
        return None
    sender = test_map[test_num][3]
    
    ann_str = "announce route " + prefix + "/" + str(mask) \
            + " next-hop self" 
    if communities and community_len > 0:
        ann_str += " community [" + " ".join(communities[:community_len]) + "]"
    elif community:
        ann_str += " community [" + str(community) + "]"

    if metric:
        ann_str += " metric " + str(metric)
    if as_path and as_path_len > 0:
        ann_str += " as-path " + " ".join(as_path[:as_path_len])
    return Announcement(router, sender, ann_str)

def generate_all_tests(router_name, test_map, directory):
    tests = []
    for filename in os.listdir(directory):
        if filename[-6:] == '.ktest':
            ktest_output = subprocess.check_output(['ktest-tool', directory + '/' + filename])
            objs = read_ktest_output(ktest_output)
            temp = (generate_test(objs, router_name, test_map))
            if temp:
                tests.append(temp)
                print temp.router, temp.neighbor, temp.announcement
    return tests

if __name__ == '__main__':
    args = sys.argv
    map_file = args[1]
    router_name = map_file[:-4].split('/')[-1]
    results = args[2]

    test_map = [ line.split('|') for line in open(map_file) ]
    generate_all_tests(router_name, test_map, results)

   # objs = read_ktest_output(sys.stdin)
   # while(objs):
    #    temp = (generate_test(objs, router_name, test_map))
     #   if temp:
      #      print (temp.router, temp.neighbor, temp.announcement)
       # objs = read_ktest_output(sys.stdin)

