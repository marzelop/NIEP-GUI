import json
import networkx as nx

def get_filename_no_extension(filepath: str):
	return filepath.split("/")[-1].split(".")[0]

# Topology JSON generator/loader

def get_VMs(G: nx.Graph):
	return []

def get_VNFs(G: nx.Graph):
	return []

def get_SFCs(G: nx.Graph):
	return []

def get_hosts(G: nx.Graph):
	hosts = []
	for node in G.nodes:
		hosts.append({"ID": node, "INTERFACES": G.nodes[node]["info"]["INTERFACES"]})
	return hosts

def get_switches(G: nx.Graph):
	return []

def get_controllers(G: nx.Graph):
	return []

def get_OVswitches(G: nx.Graph):
	return []

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
		u, v = e
		ifaces = G.edges[e]['info']['INTERFACES']
		edgeobj = G.edges[e]['obj']
		connection = {
			"IN/OUT": u,
			"IN/OUTIFACE": edgeobj.nodes[0].nodeInfo["INTERFACES"][ifaces[0]]["MAC"],
			"OUT/IN": v,
			"OUT/INIFACE": edgeobj.nodes[1].nodeInfo["INTERFACES"][ifaces[1]]["MAC"]
		}
		connections.append(connection)
	return connections

def generate_topo_dict(G: nx.Graph, filepath: str):
	topo = dict()
	# Only to guarantee a valid topology, resulting file should never get this ID unless the user wants to
	topo["ID"] = get_filename_no_extension(filepath)
	topo["VMS"] = get_VMs(G)
	topo["VNFS"] = get_VNFs(G)
	topo["SFCS"] = get_SFCs(G)
	topo["MININET"] = get_mininet(G)
	topo["CONNECTIONS"] = get_connections(G)

	return topo

def generate_topo_file(G: nx.Graph, filepath: str):
	topo = generate_topo_dict(G, filepath)
	with open(filepath, "w") as fp: 
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

# NPGI file exporter
		
def generate_NPGI_file(G: nx.graph, filepath: str):
	npgi = dict()
	npgi["VERSION"] = "1.0"
	npgi["TOPO"] = generate_topo_dict(G, filepath)
	npgi["POSITIONS"] = generate_position_dict(G)

	with open(filepath, "w") as fp:
		json.dump(npgi, fp, indent=4)

def load_NPGI_file(filepath: str):
	npgi: dict
	with open(filepath, "r") as fp:
		npgi = json.load(fp)
	return npgi
