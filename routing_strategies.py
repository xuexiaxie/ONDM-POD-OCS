import random
import networkx as nx
from topology import config

def run_ecmp(G, tors, src, dst):
    if src == dst or G.nodes[src]["pod"] == G.nodes[dst]["pod"]:
        return None
    spaths = list(nx.all_shortest_paths(G, src, dst)) #nx自带的最短路径算法，根据跳数
    if not spaths:
        return None
    return random.choice(spaths) #随机选一条

def run_vlb(G, tors, src, dst):
    if src == dst or G.nodes[src]["pod"] == G.nodes[dst]["pod"]:
         return None
    interm = random.choice([t for t in tors if t not in (src, dst)])
    p1 = nx.shortest_path(G, src, interm)
    p2 = nx.shortest_path(G, interm, dst)
    return p1 + p2[1:] #第二段路径跳过第一个节点，以免路径重复

def run_te(G, tors, src, dst, alpha=1.0, beta=1.0):
    if src == dst or G.nodes[src]["pod"] == G.nodes[dst]["pod"]:
        return None
    
    def cost(path):
        hops = len(path) - 1
        util = sum(G[u][v]["usage"] / G[u][v]["capacity"] for u, v in zip(path[:-1], path[1:]))
        return alpha * hops + beta * util #返回cost

            
    candidates = list(nx.all_simple_paths(G, src, dst, cutoff=6)) #找出6跳以内路径
    if not candidates:
        return None
    
    costs = [(p, cost(p)) for p in candidates] #为这些候选路径计算cost
    min_cost = min(c for p, c in costs)
    eq = [p for p, c in costs if abs(c - min_cost) < 1e-1] #找到cost相等的等效路径
    
    def ocs_ports(path):
        ags = [n for n in path if G.nodes[n]["type"] == "aggr"] #从路径中找出aggr类型
        return max((G.degree(a) - config.TORS_PER_POD) for a in ags) if ags else 0 # 找到aggr上连接ocs数最多的那条路径
    
    return max(eq, key=ocs_ports)

# 定义fct计算方法
def simulate_fct(G, path, last_finish, flow_unit):
    t = 0.0
    for u, v in zip(path[:-1], path[1:]):
        link = tuple(sorted([u, v]))
        free_time = last_finish.get(link, 0.0)# 链路空闲开始时间
        t = max(t, free_time)# 等待到链路空闲
        t += flow_unit / G[u][v]["capacity"] # 传输时间 = 流量 / 容量
        last_finish[link] = t # 更新链路完成时间
    return t
       