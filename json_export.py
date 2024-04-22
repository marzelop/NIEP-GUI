import json
import networkx as nx

def get_VMs(G: nx.Graph):
	return []

def get_VNFs(G: nx.Graph):
	return []

def get_SFCs(G: nx.Graph):
	return []

def get_hosts(G: nx.Graph):
	hosts = []
	for node in G.nodes:
		print(G.nodes[node])
		print(node)
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

def netgraph_to_json(G: nx.Graph, filepath: str):
	topo = dict()
	topo["ID"] = filepath.split("/")[-1].split(".")[0]
	topo["VMS"] = get_VMs(G)
	topo["VNFS"] = get_VNFs(G)
	topo["SFCS"] = get_SFCs(G)
	topo["MININET"] = get_mininet(G)
	topo["CONNECTIONS"] = get_connections(G)
	with open(filepath, "w") as fp: 
		json.dump(topo, fp, indent=4)
