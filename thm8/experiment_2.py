import warnings
import json
import time
import sys
import os
from itertools import product
from multiprocessing import Pool, cpu_count

# Setup environment
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
warnings.filterwarnings("ignore", category=UserWarning)

class Edge:
    def __init__(self, edge_id, source, target):
        self.id = edge_id  # Assigned from the loop index
        self.string_id = None
        self.source = source
        self.target = target

def log_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    print(message, **kwargs)

def report_success(idx, forbidden_edge, p1_strings, total_edges):
    """Writes the successful instance to a JSON report."""
    report = {
        "experiment": "Experiment 2 - 3 Pages",
        "instance_index": idx,
        "moved_to_p2": forbidden_edge,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "p1_edge_count": len(p1_strings),
        "p2_edge_count": 1,
        "p1_edges": list(p1_strings)
    }
    filename = f"SUCCESS_EXP4_{idx}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=4)
    log_print(f"\n[!!!] SUCCESS: Embedding found by moving {forbidden_edge} to P2. Saved to {filename}")

def json_edges_to_objects(json_edges):
    edges = []
    for idx, edge_data in enumerate(json_edges):
        # FIX: Changed keyword from 'idx' to 'edge_id' and removed 'color'
        edge = Edge(edge_id=idx, source=int(edge_data['source']), target=int(edge_data['target']))
        edge.string_id = edge_data['id']
        edges.append(edge)
    return edges

def get_edge(n1, n2, all_string_ids):
    candidates = [f"{n1}-{n2}", f"{n2}-{n1}"]
    for c in candidates:
        if c in all_string_ids: return c
    return None

def load_graph_from_json(filename):
    with open(filename, 'r') as file: return json.load(file)

def test_combination_3page(args):
    (idx, p1_strings, p2_edge, converted_edges, node_strings, entity_id, string_to_int_id) = args
    
    pages = [
        {'id': "P0", 'type': 'STACK'}, 
        {'id': "P1", 'type': 'STACK'},
        {'id': "P2", 'type': 'STACK'}
    ]
    
    p1_int_ids = {string_to_int_id[sid] for sid in p1_strings}
    p2_int_id = string_to_int_id[p2_edge]
    
    constraints = []
    for edge in converted_edges:
        if edge.id == p2_int_id:
            page = "P2"
        elif edge.id in p1_int_ids:
            page = "P1"
        else:
            page = "P0"
        constraints.append({"type": "EDGES_ON_PAGES", "arguments": [edge.id], "modifier": [page]})
    
    try:
        from be.solver import SolverInterface
        solver = SolverInterface()
        result = solver.solve(node_strings, converted_edges, pages, constraints, entity_id)
        is_embeddable = result.satisfiable if hasattr(result, 'satisfiable') else result[0]
        return (idx, is_embeddable, p2_edge, p1_strings)
    except Exception:
        return (idx, False, p2_edge, None)

def get_dense_configs(m, x, y, edges, force_xy_out=False):
    configs = []
    base = {get_edge(m['s1_5'], y, edges), get_edge(m['s3_5'], x, edges)}
    
    p2_opts = [[get_edge(m['s1_5'], m['s1_9'], edges)], [get_edge(m['s1_9'], y, edges)]]
    p3_opts = [[get_edge(m['s3_5'], m['s3_9'], edges)], [get_edge(m['s3_9'], x, edges)]]
    
    hub_edge = get_edge(x, y, edges)
    branches = []
    
    a1 = [hub_edge, get_edge(m['s2_5'], y, edges)]
    for p in [[get_edge(m['s2_5'], m['s2_9'], edges)], [get_edge(m['s2_9'], y, edges)]]: branches.append(a1 + p)
    
    a2 = [hub_edge, get_edge(m['s4_5'], x, edges)]
    for p in [[get_edge(m['s4_5'], m['s4_9'], edges)], [get_edge(m['s4_9'], x, edges)]]: branches.append(a2 + p)
    
    if not force_xy_out:
        b = [get_edge(m['s2_5'], y, edges), get_edge(m['s4_5'], x, edges)]
        for p6a in [[get_edge(m['s2_5'], m['s2_9'], edges)], [get_edge(m['s2_9'], y, edges)]]:
            for p6b in [[get_edge(m['s4_5'], m['s4_9'], edges)], [get_edge(m['s4_9'], x, edges)]]:
                branches.append(b + p6a + p6b)

    for p2 in p2_opts:
        for p3 in p3_opts:
            for br in branches: 
                configs.append(set(filter(None, list(base) + p2 + p3 + br)))
    return configs

def main():
    json_filename = '/mnt/c/Users/Admin/Desktop/SATH/server/Graph/complete_colored_graph.json'
    graph_data = load_graph_from_json(json_filename)
    converted_edges = json_edges_to_objects(graph_data['edges'])
    string_to_int_id = {e.string_id: e.id for e in converted_edges}
    all_edge_ids = set(string_to_int_id.keys())
    
    comp1 = {'s1_5':83, 's1_9':85, 's2_5':84, 's2_9':86, 's3_5':3, 's3_9':2, 's4_5':4, 's4_9':5}
    comp2 = {'s1_5':20, 's1_9':24, 's2_5':19, 's2_9':23, 's3_5':21, 's3_9':37, 's4_5':22, 's4_9':38}
    comp3 = {'s1_5':53, 's1_9':57, 's2_5':54, 's2_9':58, 's3_5':52, 's3_9':56, 's4_5':51, 's4_9':55}

    c1_opts = get_dense_configs(comp1, 0, 1, all_edge_ids, force_xy_out=True)
    c2_opts = get_dense_configs(comp2, 1, 18, all_edge_ids, force_xy_out=True)
    c3_opts = get_dense_configs(comp3, 0, 18, all_edge_ids, force_xy_out=False)

    all_combos = list(product(c1_opts, c2_opts, c3_opts))
    
    args_list = []
    global_idx = 0
    for rem1, rem2, rem3 in all_combos:
        forbidden_set = rem1 | rem2 | rem3
        p1_base = all_edge_ids - forbidden_set
        for edge_to_p2 in forbidden_set:
            args_list.append((global_idx, p1_base, edge_to_p2, converted_edges, 
                              [int(n) for n in graph_data['nodes']], 11, string_to_int_id))
            global_idx += 1

    log_print("="*50)
    log_print(f"EXPERIMENT 4 START: {time.strftime('%H:%M:%S')}")
    log_print(f"Total sub-instances to check: {len(args_list)}")
    log_print("="*50)

    success_count = 0
    successful_indices = []
    start_time = time.time()

    with Pool(processes=min(cpu_count(), 12)) as pool:
        for result in pool.imap_unordered(test_combination_3page, args_list):
            idx, success, p2_edge, p1_strings = result
            if success:
                success_count += 1
                successful_indices.append(idx)
                log_print(f"Instance {idx:05d}: TRUE (Edge {p2_edge} on P2)")
                report_success(idx, p2_edge, p1_strings, len(all_edge_ids))
            elif idx % 1000 == 0:
                log_print(f"Progress: {idx}/{len(args_list)} checked...")

    end_time = time.time()
    log_print("\n" + "="*50)
    log_print("FINAL RESULTS SUMMARY")
    log_print(f"Total Successful Embeddings: {success_count}")
    log_print(f"Total Execution Time: {end_time - start_time:.2f} seconds")
    log_print("="*50)

if __name__ == "__main__":
    main()