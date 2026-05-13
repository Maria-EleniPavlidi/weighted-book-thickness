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
        self.id = edge_id  # Changed from id to edge_id to avoid shadowing built-in id()
        self.string_id = None
        self.source = source
        self.target = target

# To store log history for a final summary
terminal_output = []

def log_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    print(message, **kwargs)
    terminal_output.append(message)

def report_success(idx, p1_strings, total_edges):
    """Writes the successful instance to a dedicated file immediately."""
    report = {
        "experiment": "Experiment 1 - Condition B",
        "instance_index": idx,
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "p1_edge_count": len(p1_strings),
        "total_graph_edges": total_edges,
        "p1_edges": list(p1_strings)
    }
    filename = f"SUCCESS_EXP1_B_{idx}.json"
    with open(filename, 'w') as f:
        json.dump(report, f, indent=4)
    log_print(f"\n[!!!] SUCCESS: Valid embedding found at instance {idx}. Saved to {filename}")

def json_edges_to_objects(json_edges):
    edges = []
    for idx, edge_data in enumerate(json_edges):
        # FIX: Changed 'idx' keyword to 'edge_id' and removed 'color'
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

def test_combination(args):
    (idx, p1_strings, converted_edges, node_strings, entity_id, pages, string_to_int_id) = args
    p1_int_ids = {string_to_int_id[sid] for sid in p1_strings if sid in string_to_int_id}
    
    constraints = []
    for edge in converted_edges:
        page = "P1" if edge.id in p1_int_ids else "P0"
        constraints.append({"type": "EDGES_ON_PAGES", "arguments": [edge.id], "modifier": [page]})
    
    try:
        from be.solver import SolverInterface
        solver = SolverInterface()
        result = solver.solve(node_strings, converted_edges, pages, constraints, entity_id)
        is_embeddable = result.satisfiable if hasattr(result, 'satisfiable') else result[0]
        return (idx, is_embeddable, p1_strings)
    except Exception:
        return (idx, False, None)

def get_dense_configs(m, x, y, edges, force_xy_out=False):
    """Generates configurations based on the 'Dense' constraints."""
    configs = []
    base_removals = {get_edge(m['s1_5'], y, edges), get_edge(m['s3_5'], x, edges)}
    
    p2_opts = [[get_edge(m['s1_5'], m['s1_9'], edges)], [get_edge(m['s1_9'], y, edges)]]
    p3_opts = [[get_edge(m['s3_5'], m['s3_9'], edges)], [get_edge(m['s3_9'], x, edges)]]
    
    hub_edge = get_edge(x, y, edges)
    branches = []
    
    # CASE A: Hub edge (xy) is removed
    a1_removals = [hub_edge, get_edge(m['s2_5'], y, edges)]
    for p6 in [[get_edge(m['s2_5'], m['s2_9'], edges)], [get_edge(m['s2_9'], y, edges)]]:
        branches.append(a1_removals + p6)
        
    a2_removals = [hub_edge, get_edge(m['s4_5'], x, edges)]
    for p6 in [[get_edge(m['s4_5'], m['s4_9'], edges)], [get_edge(m['s4_9'], x, edges)]]:
        branches.append(a2_removals + p6)
        
    # CASE B: Hub edge (xy) remains
    if not force_xy_out:
        b_removals = [get_edge(m['s2_5'], y, edges), get_edge(m['s4_5'], x, edges)]
        for p6a in [[get_edge(m['s2_5'], m['s2_9'], edges)], [get_edge(m['s2_9'], y, edges)]]:
            for p6b in [[get_edge(m['s4_5'], m['s4_9'], edges)], [get_edge(m['s4_9'], x, edges)]]:
                branches.append(b_removals + p6a + p6b)

    for p2 in p2_opts:
        for p3 in p3_opts:
            for br in branches:
                configs.append(set(filter(None, list(base_removals) + p2 + p3 + br)))
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
    
    log_print("="*50)
    log_print(f"EXPERIMENT 1 - CONDITION B START: {time.strftime('%H:%M:%S')}")
    log_print(f"Total instances to check: {len(all_combos)}")
    log_print("="*50)

    args_list = []
    for i, (rem1, rem2, rem3) in enumerate(all_combos):
        p1_set = all_edge_ids - (rem1 | rem2 | rem3)
        args_list.append((i, p1_set, converted_edges, [int(n) for n in graph_data['nodes']], 11, 
                          [{'id': "P0", 'type': 'STACK'}, {'id': "P1", 'type': 'STACK'}], string_to_int_id))

    success_count = 0
    successful_indices = []
    start_time = time.time()

    with Pool(processes=min(cpu_count(), 12)) as pool:
        for result in pool.imap_unordered(test_combination, args_list):
            idx, success, p1_strings = result
            if success:
                success_count += 1
                successful_indices.append(idx)
                log_print(f"Instance {idx:04d}: SUCCESS")
                report_success(idx, p1_strings, len(all_edge_ids))
            else:
                if idx % 100 == 0:
                    log_print(f"Instance {idx:04d}: FALSE")

    log_print("\n" + "="*50)
    log_print(f"EXPERIMENT COMPLETE in {time.time() - start_time:.2f}s")
    log_print(f"Total SUCCESSFUL Instances: {success_count}")
    log_print("="*50)

if __name__ == "__main__":
    main()