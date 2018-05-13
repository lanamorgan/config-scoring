class Router:
    def __init__(self, name):
        self.name = name
        self.static = False # Bool redistribute static routes
        self.connected = False # Bool redistribute connected routes
        self.static_rm = None
        self.connected_rm = None
        self.networks = [] # Advertised subnets
        self.static_routes = [] # Static routes

    def __str__(self):
        router_str = "Router Name:\t" + self.name + "\n" \
                + "Redistribute Connected:\t" + str(self.connected) + "\n" \
                + "Redistribute Static:\t" + str(self.static)
        if self.connected_rm:
            router_str += "\nConnected RM:\t" + self.connected_rm
        if self.static_rm:
            router_str += "\nStatic RM:\t" + self.static_rm
        router_str += "\nAdvertised Networks:\n"
        for network in self.networks:
            router_str += "\t%s\n" % (network)
        for route in self.static_routes:
            router_str += "\t%s\n" % (route)
        return router_str

    def set_static(self, rm):
        self.static = True
        self.static_rm = rm

    def set_connected(self, rm):
        self.connected = True
        self.connected_rm = rm

    def add_network(self, network):
        self.networks.append(network)

    def add_static_route(self, route):
        self.static_routes.append(route)

class Route:
    def __init__(self, network, next_hop, cost):
        self.network = network
        self.next_hop = next_hop
        self.cost = cost

    def __str__(self):
        route_str = "Network:\t\t" + self.network + "\n" \
                + "Next Hop IP:\t\t" + str(self.next_hop) + "\n" \
                + "Administrative Cost:\t" + str(self.cost) + "\n"
        return route_str

class Session:
    def __init__(self, router_name, neighbor_ip, as_number, import_policy, export_policy):
        self.router_name = router_name
        self.neighbor = neighbor_ip
        self.neighbor_name = None
        self.as_number = as_number
        self.import_policy = None
        self.import_policy_name = import_policy
        self.export_policy = None
        self.export_policy_name = export_policy
        self.interface = None

    def __str__(self):
        session_str = "Router Name:\t" + self.router_name + "\n" \
                + "Neighbor:\t" + self.neighbor + "\n" \
                + "AS Number:\t" + str(self.as_number) + "\n" \
                + "Import Policy Name:\t" + self.import_policy_name + "\n" \
                + "Export Policy Name:\t" + self.export_policy_name
        if self.neighbor_name:
            session_str += "\nNeighbor Name:\t" + self.neighbor_name
        if self.interface:
            session_str += "\nInterface:\t" + self.interface + "\n"
        if self.import_policy:
            session_str += "\nImport Policy:\n"
            for policy in self.import_policy:
                session_str += str(policy) + "\n"
        if self.export_policy:
            session_str += "\nExport Policy:\n"
            for policy in self.export_policy:
                session_str += str(policy) + "\n"
        return session_str

class Community_List:
    def __init__(self, name, permit, regex):
        self.name = name
        self.permit = permit
        self.regex = regex

    def __str__(self):
        cl_str = "Name:\t" + self.name + "\n" \
                + "Permit:\t" + str(self.permit) + "\n" \
                + "Regex:\t" + str(self.regex)
        return cl_str

class Route_Filter_List:
    def __init__(self, name, permit, prefix, mask_lower, mask_upper, seq):
        self.name = name
        self.permit = permit
        self.prefix = prefix
        self.mask_lower = mask_lower
        self.mask_upper = mask_upper
        self.seq = seq

    def __str__(self):
        rfl_str = "Name:\t" + self.name + "\n" \
                + "Permit:\t" + str(self.permit) + "\n" \
                + "Prefix:\t" + str(self.prefix) + "\n" \
                + "Range:\t" + str(self.mask_lower) + "-" + str(self.mask_upper) + "\n" \
                + "Seq:\t" + str(self.seq)
        return rfl_str

class AS_Path_List:
    def __init__(self, name, permit, regex):
        self.name = name
        self.permit = permit
        self.regex = regex

    def __str__(self):
        aspl_str = "Name:\t" + self.name + "\n" \
                + "Permit:\t" + str(self.permit) + "\n" \
                + "Regex:\t" + str(self.regex)
        return aspl_str

class Route_Map_Clause:
    class Action:
        def __init__(self, field=None, value=None, additive=False):
            self.field = field
            self.value = value
            self.additive = additive # Boolean for community tags

        def __str__(self):
            action_str = "Field:\t" + self.field + "\n" \
                    + "Value:\t" + str(self.value) + "\n" \
                    + "Add:\t" + str(self.additive) + "\n"
            return action_str

    def __init__(self, name, seq="", permit=True, cl=[], rfl=[], aspl=[]):
        self.name = name # name
        self.seq = seq # empty string "" as placeholder
        self.permit = permit # bool: True for permit, False for deny
        self.community_list = cl
        self.route_filter_list = rfl
        self.as_path_list = aspl
        self.actions = [] # List of possible Actions

    def __str__(self):
        rmc_str = "Name:\t" + self.name + "\n" \
                + "Seq:\t" + self.seq + "\n" \
                + "Permit:\t" + str(self.permit) + "\n"
        if self.community_list:
            rmc_str += "Community List:\n"
            for cl in self.community_list:
                rmc_str += str(cl) + "\n"
        if self.route_filter_list:
            rmc_str += "Route Filter List:\n"
            for rfl in self.route_filter_list:
                rmc_str += str(rfl) + "\n"
        if self.as_path_list:
            rmc_str += "AS Path List:\n"
            for aspl in self.as_path_list:
                rmc_str += str(aspl) + "\n"
        rmc_str += "\nActions:\n"

        for action in self.actions:
            rmc_str += str(action)
        return rmc_str

    def update_permit(self, permit):
        self.permit = permit

    def update_community_list(self, cl=None):
        self.community_list = cl

    def update_route_filter_list(self, rfl=None):
        self.route_filter_list = rfl

    def update_as_path_list(self, aspl=None):
        self.as_path_list = aspl

    def update_action(self, field, value, additive=False):
        self.actions.append(self.Action(field, value, additive))
