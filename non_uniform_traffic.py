# non_uniform_traffic.py
import pandas as pd
import numpy as np
import random
import networkx as nx
from topology import build_uniform_topology, build_nonuniform_topology
from topology import config
from routing_strategies import run_ecmp, run_vlb, run_te, simulate_fct

# 固定随机种子，确保可重复性
random.seed(42)

# 获取 Pod ID
def pod_id(node):
    return int(node.split('_')[0][3:])

# 生成非均匀热点流量：Pod0<->Pod1 流量权重 5，其他权重 1
def generate_traffic():
    tors_list = [f"Pod{pod}_Tor{t}" for pod in range(config.NUM_PODS) for t in range(config.TORS_PER_POD)]
    traffic_requests = []
    for src in tors_list:
        for dst in tors_list:
            if src == dst or pod_id(src) == pod_id(dst):
                continue
            weight = 5 if set([pod_id(src), pod_id(dst)]) == {0, 1} else 1 #pod对之间的流量需求除了0-1是5，其他都是1
            traffic_requests.extend([(src, dst)] * weight) #[列表],[(元组)],[(元组)]*2表示把元组复制两份组成一个新的列表，而不是列表复制，不然就成了嵌套列表了
    random.shuffle(traffic_requests) #把流量请求打乱
    return traffic_requests
# 定义策略函数并计算指标
def run_strategy(name):
    G, tors = build_uniform_topology()
    traffic_requests = generate_traffic()
    last_finish = {}  # 每条链路的最近完成时间
    fct_list = []
    hop_list = []
    
    for src, dst in traffic_requests:
        # 路径选择
        if name == "ECMP":
            path = run_ecmp(G, tors, src, dst)
        elif name == "VLB":
            path = run_vlb(G, tors, src, dst)
        else:  # TE
            path = run_te(G, tors, src, dst)
         
        if not path:
            continue  # 跳过无效路径
        # 统计跳数
        hop_list.append(len(path)-1)
        
        # 更新使用量（用于 TE）
        for u, v in zip(path[:-1], path[1:]):
            G[u][v]["usage"] += config.FLOW_UNIT

        # 离散事件模拟
        t = simulate_fct(G, path, last_finish, config.FLOW_UNIT)
        fct_list.append(t)
        
    # 计算指标
    avg_fct = np.mean(fct_list)
    p95_fct = np.percentile(fct_list, 95)
    avg_hops = np.mean(hop_list)
    utils = [G[u][v]["usage"]/G[u][v]["capacity"] for u, v in G.edges()]
    ocs_used = sum(
        1 for n in G.nodes
        if G.nodes[n]["type"] == "ocs" and any(G[n][nbr]["usage"] > 0 for nbr in G.neighbors(n))
    )
    return {
        "Strategy": name,
        "Avg FCT": round(avg_fct, 3),
        "95th % FCT": round(p95_fct, 3),
        "Avg Hop Count": round(avg_hops, 2),
        "Avg Link Utilization": round(np.mean(utils), 3),
        "Max Link Utilization": round(max(utils), 3),
        "Std Dev Util": round(np.std(utils), 3),
        "OCS Links Used": ocs_used
    }

# 对比三种策略
def main():
    results = [run_strategy(s) for s in ["ECMP", "VLB", "TE"]]
    df = pd.DataFrame(results)
    print(df)

if __name__ == "__main__":
    main()


