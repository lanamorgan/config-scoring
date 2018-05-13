#!/usr/bin/python
from parse import *
from utils.Write_Code import *
from os.path import isfile, join
import os
from munkres import Munkres
from Levenshtein import distance

def rank(in_path, out_path, routers):
    pair_score = []
    for i in range(len(routers)):
        for j in range(i+1, len(routers)):
            pair = (routers[i], routers[j])
            pair_score.append(find_mapping(in_path, pair, out_path, out_path))
    pair_score = sorted(pair_score, key = lambda p: p.m_score + p.k_score+ p.edit_d)
    router_map = {}
    for pair in pair_score:
        if pair.r1 not in router_map:
            router_map[pair.r1] = pair
        if pair.r2 not in router_map:
            router_map[pair.r2] = pair
    for p1 in router_map:
        p = router_map[p1]
        p2 = p.r2 if p1 == p.r1 else p.r1
        print(p1, p2, p.m_score, p.k_score, p.edit_d)
    return router_map


"""
path:  path to directory containing json files
pair_list: (r1, r2)
directory: directory to write C files to
kdir: directory containing Klee headers; this is where llvm files are placed
"""
def find_mapping(path, pair, directory, kdir):
    (r1, r2) = pair
    r1_file = path + r1 + ".json"
    r2_file = path + r2 + ".json"
    (sld, _, _) = read_file(r1_file)
    (r2_sld, _, _) = read_file(r2_file)
    sld.update(r2_sld)
    if not r1 in sld or not r2 in sld:
        return Pair(r1, r2, 100000, 100000, distance(r1,r2))
    nl = lambda sl: [s.neighbor for s in sl]
    r1_neighbors = nl(sld[r1])
    r2_neighbors = nl(sld[r2])
    (n_map, n_score) = get_neighbor_pair_score(r1_neighbors, r2_neighbors)
    if len(n_map) == 0: 
        return Pair(r1, r2, 100000, 100000,distance(r1,r2))
    score = check_mapping(sld, directory, [((r1, r2), n_map)], kdir)
    return Pair(r1, r2, n_score, score,distance(r1,r2))

def check_mapping(sld, di, mapping, klee_dir):
    write_equivalence_check(sld, di, mapping)
    ((r1, r2), _) = mapping[0]
    file_name = r1 +"_to_" +  r2
    if not os.path.exists(di+ file_name + '.c'):
        return None
    subprocess.call(['clang-3.4', '-Wno-everything', '-I ../../include', '-emit-llvm', '-c', '-g', \
        di + file_name + '.c', '-o', klee_dir + file_name + '.bc'])
    subprocess.call(['clang-3.4', '-Wno-everything', '-I ../../include', '-emit-llvm', '-c', '-g', \
        klee_dir + 'AnnouncementInt.c', '-o', klee_dir + 'AnnouncementInt.bc'])
    subprocess.call(['/usr/bin/llvm-link-3.4', klee_dir + 'AnnouncementInt.bc', \
        klee_dir + file_name + '.bc', '-o', klee_dir+file_name + '_link.bc'])
    subprocess.call(['klee', '--libc=uclibc', '--suppress-external-warnings', '--warnings-only-to-file', '--posix-runtime',  klee_dir+file_name + '_link.bc'])
    results = klee_dir + 'klee-last'
    return len([f for f in os.listdir(results) if isfile(join(results, f)) and f[-10:] == "assert.err"])


def get_neighbor_pair_score(ngh_list1, ngh_list2):

    # make this as good as possible---return a list if at all possible
    # score it by the inverse of the sum of differences
    if (len(ngh_list1)!= len(ngh_list2)):
        return {}, 1000
    ngh_list1_int = [address_to_masked_value(ngh.split('/')[0],'32') for ngh in ngh_list1 ]
    ngh_list2_int = [address_to_masked_value(ngh.split('/')[0],'32') for ngh in ngh_list2 ]
    matrix = []
    for int_ip in ngh_list1_int:
        array = []
        for int2_ip in ngh_list2_int:
            array.append(abs(int2_ip-int_ip))
        matrix.append(array)
    m = Munkres()
    indexes = m.compute(matrix)
    neighbor_map = {}
    score = 0
    for row, column in indexes:
        pair_map = []
        pair_map.append(ngh_list1[row])
        pair_map.append(ngh_list2[column])
        neighbor_map[pair_map[0]] = pair_map[1]
        score = score + matrix[row][column]  
    # x = 0 
    # score = 0 
    # neighbor_map = []
    # for int_ip in ngh_list1_int:
    #     mod_sub = min( (abs(val - int_ip), idx) for (idx,val) in enumerate(ngh_list2_int))
    #     score += mod_sub[0]
    #     pair_map = []
    #     pair_map.append(ngh_list1[x])
    #     pair_map.append(ngh_list2[mod_sub[1]])
    #     if pair_map[1] in [nghs[1] for nghs in neighbor_map]:
    #         print("Multiple Neighbors are getting mapped to Single Neighbor")
    #         return []
    #     neighbor_map.append(pair_map)
    #     x = x + 1
    return neighbor_map, score

class Pair:
    def __init__(self, r1, r2, map_score, klee_score,edit_distance):
        self.r1 = r1
        self.r2 = r2
        self.m_score = map_score
        self.k_score = klee_score
        self.edit_d = edit_distance


def main():
    path = sys.argv[1]
    directory = "utils/bc/"
    routers = [f[:-5] for f in os.listdir(path)]
    rank(path, directory, routers)

if __name__ == "__main__":
    main()
