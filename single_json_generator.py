import os
import json

with open("allnodes.json",'r') as batfish_output:
        count = 0   
        raw_data = batfish_output.readlines()   
        for line in raw_data:
                count+= 1
                if "}" in line:
                        break

open("allnodes.json",'w').writelines(raw_data[count:-1])

with open("allnodes.json", 'r') as data_file: 
        data = json.load(data_file)

target_loc  = "BatfishJSONs/"

for names in data["nodes"]:
    router_data = data["nodes"][names]
    first_level = {}
    second_level = {}
    second_level[names] = router_data
    first_level["nodes"] = second_level
    with open(target_loc + names+ '.json', 'w') as outfile:         
            json.dump(first_level, outfile, indent=4)
