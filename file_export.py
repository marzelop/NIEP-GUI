import json
import networkx as nx
import copy

def add_default_extension(filepath: str, extension: str):
	if len(filepath.split("/")[-1].split(".")) == 1:
		return f"{filepath}{'.' if filepath[-1] != '.' else ''}{extension}"
	return filepath

def get_filename_no_extension(filepath: str):
	return filepath.split("/")[-1].split(".")[0]

def has_iface(node):
	if (node.type == "Host"):
		return True
	return False

# Topology JSON generator/loader

'''def get_VMs(G: nx.Graph):
	vms = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "VM", G.nodes):
		if G.nodes[node]["info"]["VNF"]:
			vms.append(f"./VMS/{node}@VNF.json")
		else:	
			vms.append(f"./VMS/{node}.json")
	return vms

def get_VNFs(G: nx.Graph):
	vnfs = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "VM" and G.nodes[n]["info"]["VNF"], G.nodes):
		vnfs.append(f"./VNFS/{node}.json")
	return vnfs'''

def get_VMs_and_VNFs(G: nx.Graph):
	vms = []
	vnfs = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "VM", G.nodes):
		if G.nodes[node]["info"]["VNF"]:
			vnfs.append(f"./VNFS/{node}.json")
		else:	
			vms.append(f"./VMS/{node}.json")
	return vms, vnfs

def get_SFCs(G: nx.Graph):
	return []

def get_hosts(G: nx.Graph):
	hosts = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "Host", G.nodes):
		hosts.append({"ID": node, "INTERFACES": G.nodes[node]["info"]["INTERFACES"]})
	return hosts

def get_switches(G: nx.Graph):
	switches = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "Switch", G.nodes):
		switches.append(node)
	return switches

def get_controllers(G: nx.Graph):
	controllers = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "Controller", G.nodes):
		obj = G.nodes[node]["obj"]
		controllers.append({"ID": node, "IP": obj.nodeInfo["IP"], "PORT": obj.nodeInfo["PORT"]})

	return controllers

def get_OVswitches(G: nx.Graph):
	ovswitches = []
	for node in filter(lambda n: G.nodes[n]["obj"].type == "OVSwitch", G.nodes):
		controller = G.nodes[node]["obj"].nodeInfo["CONTROLLER"]
		if controller is not None:
			controller = controller.getName()
		ovs = {
			"ID": node,
			"CONTROLLER": controller
		}
		ovswitches.append(ovs)
	return ovswitches

def get_mininet(G: nx.Graph):
	mini = dict()
	mini["HOSTS"] = get_hosts(G)
	mini["SWITCHES"] = get_switches(G)
	mini["CONTROLLERS"] = get_controllers(G)
	mini["OVSWITCHES"] = get_OVswitches(G)
	return mini

def get_connections(G: nx.Graph):
	connections = []
	for e in G.edges:
		edgeobj = G.edges[e]['obj']
		u, v = e
		ui, vi = 1, 0
		if u == edgeobj.nodes[0].getName():
			uobj, vobj = edgeobj.nodes
			ui, vi = 0, 1
		else: vobj, uobj = edgeobj.nodes
		if uobj.type == "Controller" or vobj.type == "Controller":
			continue
		ifaces = G.edges[e]['info']['INTERFACES']

		connection = dict()
		connection["IN/OUT"] = u
		print(u)
		print(uobj.getName())
		print(v)
		print(vobj.getName())
		print(ifaces)
		print()
		if uobj.hasInterface():
			connection["IN/OUTIFACE"] = uobj.nodeInfo["INTERFACES"][ifaces[ui]]["MAC"]
		connection["OUT/IN"] = v
		if vobj.hasInterface():
			connection["OUT/INIFACE"] = vobj.nodeInfo["INTERFACES"][ifaces[vi]]["MAC"]

		connections.append(connection)
	return connections

def generate_topo_dict(G: nx.Graph, filepath: str):
	topo = dict()
	# Only to guarantee a valid topology, resulting file should never get this ID unless the user wants to
	topo["ID"] = get_filename_no_extension(filepath)
	topo["VMS"], topo["VNFS"] = get_VMs_and_VNFs(G)
	topo["SFCS"] = get_SFCs(G)
	topo["MININET"] = get_mininet(G)
	topo["CONNECTIONS"] = get_connections(G)

	return topo

def generate_topo_file(G: nx.Graph, filepath: str):
	topo = generate_topo_dict(G, filepath)
	with open(add_default_extension(filepath, "json"), "w") as fp: 
		json.dump(topo, fp, indent=4)

# Node position JSON generator

def generate_position_dict(G: nx.Graph):
	positions = dict()
	for n in G.nodes:
		nodeobj = G.nodes[n]['obj']
		nodepos = nodeobj.pos()
		nodepos = [nodepos.x(), nodepos.y()]
		positions[n] = nodepos
	
	return positions

def generate_position_file(G: nx.Graph, filepath: str):
	pos = generate_position_dict(G)
	with open(filepath, "w") as fp:
		json.dump(pos, fp, indent=4)

# JSON Definitions

def generate_VM_definitions(G: nx.Graph):
	vms = []
	for node in G.nodes:
		nodeobj = G.nodes[node]['obj']
		if nodeobj.type != "VM":
			continue
		vminfo = copy.deepcopy(nodeobj.nodeInfo)
		for iface in vminfo["INTERFACES"]:
			if iface["LINK_MAC"] == "":
				iface.pop("LINK_MAC")
		if vminfo["VNF"]:
			vm = {"ID": f"{node}@VNF"}
		else: vm = {"ID": f"{node}"}
		vminfo.pop("VNF")
		vm.update(vminfo)
		vms.append(vm)
	return vms

def generate_VNF_definitions(topo: dict):
	vnfs = []
	for vnf in topo["VNFS"]:
		id = get_filename_no_extension(vnf)
		vm = f"./VMS/{id}@VNF.json"
		vnfs.append({
			"ID": id,
			"VM": vm
		})

	return vnfs

# NPGI file exporter

def generate_NPGI_file(G: nx.graph, filepath: str):
	npgi = dict()
	npgi["VERSION"] = "1.0"
	npgi["TOPO"] = generate_topo_dict(G, filepath)
	npgi["VMS"] = generate_VM_definitions(G)
	npgi["POSITIONS"] = generate_position_dict(G)

	with open(add_default_extension(filepath, "npgi"), "w") as fp:
		json.dump(npgi, fp, indent=4)

def load_NPGI_file(filepath: str):
	npgi: dict
	with open(filepath, "r") as fp:
		npgi = json.load(fp)
	return npgi
