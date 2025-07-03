# ocs_topo_compar
import pandas as pd
import numpy as np
import random
from topology import build_uniform_topology, build_nonuniform_topology
from topology import config
from routing_strategies import run_ecmp, run_vlb, run_te, simulate_fct

# 获取 Pod ID
def pod_id(node):
    return int(node.split('_')[0][3:])

# 生成all-to-all均匀流量
def generate_traffic():
    tors_list = [f"Pod{pod}_Tor{t}" for pod in range(config.NUM_PODS) for t in range(config.TORS_PER_POD)]
    traffic_requests = []
    for src in tors_list:
        for dst in tors_list:
            if src != dst and src.split('_')[0] != dst.split('_')[0]:  # 跨Pod
                traffic_requests.append((src,dst))
    return traffic_requests

def run_strategy(name):
    G, tors_list = build_uniform_topology()
    traffic_requests = generate_traffic()
    last_finish = {}  # 每条链路的最近完成时间
    fct_list = []
    hop_list = []
    
    for src, dst in traffic_requests:
        # 路径选择
        if name == "ECMP":
            path = run_ecmp(G, tors_list, src, dst)
        elif name == "VLB":
            path = run_vlb(G, tors_list, src, dst)
        else:  # TE
            path = run_te(G, tors_list, src, dst)
         
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
