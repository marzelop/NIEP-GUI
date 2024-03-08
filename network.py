#!./venv/bin/python
import networkx as nx
import matplotlib.pyplot as plt
import json

def loadTopologyGraph(filepath: str) -> nx.Graph:
	with open(filepath, "r") as fp:
		topo = json.load(fp)

	nodes = topo["MININET"]["HOSTS"]
	edges = topo["CONNECTIONS"]

	G = nx.Graph()

	for i, node in enumerate(nodes):
		G.add_node(node["ID"], attr=node)

	for edge in edges:
		node1 = edge["IN/OUT"]
		node2 = edge["OUT/IN"]
		G.add_edge(node1, node2, attr=edge)
	
	return G


if __name__ == "__main__":
	G = loadTopologyGraph("ServerClient.json")
	options = {
		'node_size': 3000,
		'width': 3,
	}
	nx.draw(G, with_labels=True, **options)

	plt.savefig("plot/graph")
