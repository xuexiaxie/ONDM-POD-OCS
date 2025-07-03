import random
from itertools import combinations, cycle
import matplotlib
matplotlib.use('Agg')  # 无头环境
import matplotlib.pyplot as plt
import networkx as nx
from dataclasses import dataclass

# 固定随机种子
random.seed(42)


@dataclass
class TopoConfig:
    NUM_PODS: int = 4
    TORS_PER_POD: int = 2
    AGGRS_PER_POD: int = 2
    LINK_CAPACITY: float = 10.0
    OCS_PORT_LIMIT: int = 4
    OCS_LINKS_PER_POD_PAIR: int = 2
    FLOW_UNIT: int = 1
config = TopoConfig()

def node_name(pod, role, idx):
    return f"Pod{pod}_{role}{idx}"

def build_uniform_topology():
    G = nx.Graph()
    tors = []
    ocs_counter = 0
    # 添加 ToR 与 Aggr 节点
    for pod in range(config.NUM_PODS):
        for t in range(config.TORS_PER_POD):
            tor = node_name(pod, "Tor", t)
            G.add_node(tor, type="tor", pod=pod)
            tors.append(tor)
        for a in range(config.AGGRS_PER_POD):
            aggr = node_name(pod, "Aggr", a)
            G.add_node(aggr, type="aggr", pod=pod)

    # ToR–Aggr 连接：双重循环每个tor和每个aggr相连
    for pod in range(config.NUM_PODS):
        for t in range(config.TORS_PER_POD):
            tor = node_name(pod, "Tor", t)
            for a in range(config.AGGRS_PER_POD):
                aggr = node_name(pod, "Aggr", a)
                G.add_edge(tor, aggr, capacity=config.LINK_CAPACITY, usage=0.0)

    # Aggr–Aggr (OCS) 连接，每个aggr不超过4，每对pod之间不超过2，用哪个aggr连具有一定随机性，但大体是均匀的
    for p1, p2 in combinations(range(config.NUM_PODS), 2): #建立任意pod对
        connected = 0
        cands1 = [f"Pod{p1}_Aggr{i}" for i in range(config.AGGRS_PER_POD)] #pod对下所有的aggr
        cands2 = [f"Pod{p2}_Aggr{i}" for i in range(config.AGGRS_PER_POD)]
        tried = set() #建立集合表示已经尝试过的组合
        # 每对pod的连接数上限是config.OCS_LINKS_PER_POD_PAIR
        while connected < config.OCS_LINKS_PER_POD_PAIR and len(tried) < len(cands1)*len(cands2):
            a1 = random.choice(cands1) #pod下随机选一个aggr
            a2 = random.choice(cands2)
            if (a1, a2) in tried:
                continue
            tried.add((a1, a2))
            # a1这个aggr的度一部分是和tor连，一部分是和ocs连
            if G.degree(a1) < config.TORS_PER_POD + config.OCS_PORT_LIMIT and G.degree(a2) < config.TORS_PER_POD + config.OCS_PORT_LIMIT:
                ocs_node = f"OCS_{ocs_counter}"
                G.add_node(ocs_node, type="ocs", pod=None)
                G.add_edge(a1, ocs_node, capacity=config.LINK_CAPACITY, usage=0.0)
                G.add_edge(ocs_node, a2, capacity=config.LINK_CAPACITY, usage=0.0)
                connected += 1
                ocs_counter += 1

    return G, tors

def build_nonuniform_topology():
    # 不均匀的光路配置：每对 Pod 之间的 OCS 链路数
    ocs_links_config = {
        (0, 1): 1,
        (0, 2): 3,
        (0, 3): 2,
        (1, 2): 2,
        (1, 3): 1,
        (2, 3): 3,
    }
    G = nx.Graph()
    tors = []
    ocs_counter = 0
    # 创建节点
    for pod in range(config.NUM_PODS):
        for t in range(config.TORS_PER_POD):
            tor = node_name(pod, "Tor", t)
            G.add_node(tor, type="tor", pod=pod)
            tors.append(tor)
        for a in range(config.AGGRS_PER_POD):
            aggr = node_name(pod, "Aggr", a)
            G.add_node(aggr, type="aggr", pod=pod)
    # ToR-Aggr 本地链路
    for pod in range(config.NUM_PODS):
        for t in range(config.TORS_PER_POD):
            tor = node_name(pod, "Tor", t)
            for a in range(config.AGGRS_PER_POD):
                G.add_edge(tor, node_name(pod, "Aggr", a), capacity=config.LINK_CAPACITY, usage=0)
    # Pod-Pod OCS 链路（不均匀）
    for (p1, p2), k in ocs_links_config.items():
        connected = 0
        candidates1 = [node_name(p1, "Aggr", i) for i in range(config.AGGRS_PER_POD)]
        candidates2 = [node_name(p2, "Aggr", i) for i in range(config.AGGRS_PER_POD)]
        tried = set()
        while connected < k and len(tried) < len(candidates1)*len(candidates2):
            a1 = random.choice(candidates1)
            a2 = random.choice(candidates2)
            if (a1, a2) in tried:
                continue
            tried.add((a1, a2))
            if G.degree(a1) < config.TORS_PER_POD + config.OCS_PORT_LIMIT and G.degree(a2) < config.TORS_PER_POD + config.OCS_PORT_LIMIT:
                ocs_node = f"OCS_{ocs_counter}"
                G.add_node(ocs_node, type="ocs", pod=None)
                G.add_edge(a1, ocs_node, capacity=config.LINK_CAPACITY, usage=0.0)
                G.add_edge(ocs_node, a2, capacity=config.LINK_CAPACITY, usage=0.0)
                connected += 1
                ocs_counter += 1
    return G, tors

def build_aggr_uniform_topology():
    G = nx.Graph()
    tors = []
    ocs_counter = 0

    # 添加 ToR 和 Aggr 节点
    for pod in range(config.NUM_PODS):
        for t in range(config.TORS_PER_POD):
            tor = node_name(pod, "Tor", t)
            G.add_node(tor, type="tor", pod=pod)
            tors.append(tor)
        for a in range(config.AGGRS_PER_POD):
            aggr = node_name(pod, "Aggr", a)
            G.add_node(aggr, type="aggr", pod=pod)

    # ToR – Aggr 连接
    for pod in range(config.NUM_PODS):
        for t in range(config.TORS_PER_POD):
            tor = node_name(pod, "Tor", t)
            for a in range(config.AGGRS_PER_POD):
                aggr = node_name(pod, "Aggr", a)
                G.add_edge(tor, aggr, capacity=config.LINK_CAPACITY, usage=0.0)

    # 跨 Pod Aggr – Aggr (OCS) 连接（轮转均匀分配）
    aggr_iters = {
        pod: cycle([f"Pod{pod}_Aggr{i}" for i in range(config.AGGRS_PER_POD)])
        for pod in range(config.NUM_PODS)
    }

    for p1, p2 in combinations(range(config.NUM_PODS), 2):
        connected = 0
        attempts = 0
        max_attempts = 10 * config.OCS_LINKS_PER_POD_PAIR
        while connected < config.OCS_LINKS_PER_POD_PAIR and attempts < max_attempts:
            a1 = next(aggr_iters[p1])
            a2 = next(aggr_iters[p2])
            attempts += 1

            if G.degree(a1) >= config.TORS_PER_POD + config.OCS_PORT_LIMIT:
                continue
            if G.degree(a2) >= config.TORS_PER_POD + config.OCS_PORT_LIMIT:
                continue

            if G.has_edge(a1, a2) or any(G.nodes[n]["type"] == "ocs" and a1 in G[n] and a2 in G[n] for n in G.nodes):
                continue

            ocs_node = f"OCS_{ocs_counter}"
            G.add_node(ocs_node, type="ocs", pod=None)
            G.add_edge(a1, ocs_node, capacity=config.LINK_CAPACITY, usage=0.0)
            G.add_edge(ocs_node, a2, capacity=config.LINK_CAPACITY, usage=0.0)
            connected += 1
            ocs_counter += 1

    return G, tors

def custom_layout(G):
    pos = {}
    x_spacing = 2.0
    aggr_layer_y = 2.0
    tor_layer_y = 0.0
    ocs_layer_y = 4.0
    pod_offsets = {}
    ocs_x = 0

    for node in G.nodes:
        node_type = G.nodes[node].get('type')

        if node_type == 'tor':
            pod = G.nodes[node]['pod']
            if pod not in pod_offsets:
                pod_offsets[pod] = pod * x_spacing * 4
            index = int(node.split('Tor')[-1])
            x = pod_offsets[pod] + index * x_spacing
            pos[node] = (x, tor_layer_y)

        elif node_type == 'aggr':
            pod = G.nodes[node]['pod']
            if pod not in pod_offsets:
                pod_offsets[pod] = pod * x_spacing * 4
            index = int(node.split('Aggr')[-1])
            x = pod_offsets[pod] + index * x_spacing
            pos[node] = (x, aggr_layer_y)

        elif node_type == 'ocs':
            pos[node] = (ocs_x, ocs_layer_y)
            ocs_x += x_spacing

    return pos

if __name__ == "__main__":
    G, tors = build_aggr_uniform_topology()
    # G, tors = build_uniform_topology()
    # G, tors = build_nonuniform_topology()
    pos = custom_layout(G)

    # 为不同类型的节点上色
    node_colors = []
    for n in G.nodes:
        t = G.nodes[n].get('type')
        if t == 'tor':
            node_colors.append('skyblue')
        elif t == 'aggr':
            node_colors.append('orange')
        elif t == 'ocs':
            node_colors.append('lightgreen')

    fig = plt.figure(figsize=(12, 6))
    nx.draw(
        G, pos,
        with_labels=True,
        node_size=500,
        font_size=8,
        node_color=node_colors,
        edge_color='gray'
    )
    fig.savefig('./pictures/aggr_uniform_topology.png', dpi=300, bbox_inches='tight')
    # fig.savefig('./pictures/uniform_topology.png', dpi=300, bbox_inches='tight')
    # fig.savefig('./pictures/nonuniform_topology.png', dpi=300, bbox_inches='tight')
    plt.close(fig)