import warnings
import json
import time
import sys
import os
from itertools import product
from multiprocessing import Pool, cpu_count


sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
warnings.filterwarnings("ignore", category=UserWarning)

class Edge:
    def __init__(self, id, source, target, color=None):
        self.id = id
        self.string_id = None
        self.source = source
        self.target = target
        self.color = color

terminal_output = []

def log_print(*args, **kwargs):
    message = " ".join(str(arg) for arg in args)
    print(message, **kwargs)
    terminal_output.append(message)

def json_edges_to_objects(json_edges):
    edges = []
    for idx, edge_data in enumerate(json_edges):
        edge = Edge(
            id=idx,
            source=int(edge_data['source']),
            target=int(edge_data['target']),
            color=edge_data.get('color')
        )
        edge.string_id = edge_data['id']
        edges.append(edge)
    return edges

def get_edge(n1, n2, all_string_ids):
    candidates = [f"{n1}-{n2}", f"{n2}-{n1}"]
    for c in candidates:
        if c in all_string_ids:
            return c
    return None

def load_graph_from_json(filename):
    with open(filename, 'r') as file:
        return json.load(file)

def create_exact_constraints(p1_string_ids, all_edges, string_to_int_id):
    constraints = []
    p1_int_ids = {string_to_int_id[sid] for sid in p1_string_ids if sid in string_to_int_id}
    
    for edge in all_edges:
        # If edge is in our calculated P1 set, assign to P1, else P0
        page = "P1" if edge.id in p1_int_ids else "P0"
        constraints.append({
            "type": "EDGES_ON_PAGES",
            "arguments": [edge.id],
            "modifier": [page]
        })
    return constraints

def test_combination(args):
    (idx, p1_strings, converted_edges, node_strings, entity_id, pages, string_to_int_id) = args
    constraints = create_exact_constraints(p1_strings, converted_edges, string_to_int_id)
    
    try:
        from be.solver import SolverInterface
        solver = SolverInterface()
        result = solver.solve(node_strings, converted_edges, pages, constraints, entity_id)
        is_embeddable = result.satisfiable if hasattr(result, 'satisfiable') else result[0]
        return (idx, is_embeddable, p1_strings)
    except Exception as e:
        return (idx, False, None)

def get_component_configs(m, x, y, edges):
    """
    Generates valid edge combinations for a component based on the 7-removal logic.
    """
    configs = []
    
    #constraint 1 of Lemma 10
    # s1,5-y and s3,5-x must NOT be in P1
    base_removals = {get_edge(m['s1_5'], y, edges), get_edge(m['s3_5'], x, edges)}
    
    # Constraints 2 and 3 of Lemma 10
    # Choice 1: remove s1,5-s1,9 OR s1,9-y
    p2_opts = [[get_edge(m['s1_5'], m['s1_9'], edges)], [get_edge(m['s1_9'], y, edges)]]
    # Choice 2: remove s3,5-s3,9 OR s3,9-x
    p3_opts = [[get_edge(m['s3_5'], m['s3_9'], edges)], [get_edge(m['s3_9'], x, edges)]]
    
    # Constraints 4, 5, and 6 of Lemma 10
    xy = get_edge(x, y, edges)
    hub_choices = []
    
    #  xy is NOT in P1 (constraint  5)
    # constraint 4: remove either s2,5-y or s4,5-x
    # constraint 6a/b: triggers based on constraint 4
    
    #  remove s2,5-y (Triggers 6a)
    opt_a1 = [xy, get_edge(m['s2_5'], y, edges)]
    p6a_opts = [[get_edge(m['s2_5'], m['s2_9'], edges)], [get_edge(m['s2_9'], y, edges)]]
    for p6 in p6a_opts:
        hub_choices.append(opt_a1 + p6)
        
    #  remove s4,5-x (Triggers 6b)
    opt_a2 = [xy, get_edge(m['s4_5'], x, edges)]
    p6b_opts = [[get_edge(m['s4_5'], m['s4_9'], edges)], [get_edge(m['s4_9'], x, edges)]]
    for p6 in p6b_opts:
        hub_choices.append(opt_a2 + p6)

    # xy IS in P1 (constraint 5) 
    # constraint 5: remove BOTH s2,5-y and s4,5-x (Triggers 6a AND 6b)
    opt_b = [get_edge(m['s2_5'], y, edges), get_edge(m['s4_5'], x, edges)]
    for p6a in [[get_edge(m['s2_5'], m['s2_9'], edges)], [get_edge(m['s2_9'], y, edges)]]:
        for p6b in [[get_edge(m['s4_5'], m['s4_9'], edges)], [get_edge(m['s4_9'], x, edges)]]:
            hub_choices.append(opt_b + p6a + p6b)

    # Combine all choices
    for p2 in p2_opts:
        for p3 in p3_opts:
            for hub in hub_choices:
                # A config is the set of edges to REMOVE from the component's full set
                configs.append(set(filter(None, list(base_removals) + p2 + p3 + hub)))
    
    return configs

def main():
    json_filename = '/mnt/c/Users/Admin/Desktop/SATH/server/Graph/complete_colored_graph.json'
    graph_data = load_graph_from_json(json_filename)
    converted_edges = json_edges_to_objects(graph_data['edges'])
    
    string_to_int_id = {e.string_id: e.id for e in converted_edges}
    all_edge_ids = set(string_to_int_id.keys())
    
   
    comp1 = {'s1_5':83, 's1_9':85, 's2_5':84, 's2_9':86, 's3_5':3, 's3_9':2, 's4_5':4, 's4_9':5, 'u':0, 'v':1}
    comp2 = {'s1_5':20, 's1_9':24, 's2_5':19, 's2_9':23, 's3_5':21, 's3_9':37, 's4_5':22, 's4_9':38, 'v':1, 'w':18}
    comp3 = {'s1_5':53, 's1_9':57, 's2_5':54, 's2_9':58, 's3_5':52, 's3_9':56, 's4_5':51, 's4_9':55, 'u':0, 'w':18}

    # Each option is a set of edges to EXCLUDE from P1
    c1_opts = get_component_configs(comp1, 0, 1, all_edge_ids)
    c2_opts = get_component_configs(comp2, 1, 18, all_edge_ids)
    c3_opts = get_component_configs(comp3, 0, 18, all_edge_ids)

    all_combos = list(product(c1_opts, c2_opts, c3_opts))
    log_print(f"Total global combinations to test: {len(all_combos)}")

    args_list = []
    for i, (rem1, rem2, rem3) in enumerate(all_combos):
        all_removals = rem1 | rem2 | rem3
        # P1 is "All Edges" minus "Removals"
        p1_set = all_edge_ids - all_removals
        args_list.append((i, p1_set, converted_edges, [int(n) for n in graph_data['nodes']], 11, 
                         [{'id': "P0", 'type': 'STACK'}, {'id': "P1", 'type': 'STACK'}], string_to_int_id))

    # Multiprocessing execution
    with Pool(processes=min(cpu_count(), 12)) as pool:
        for result in pool.imap_unordered(test_combination, args_list):
            idx, success, _ = result
            if success:
                log_print(f"SUCCESS found at index {idx}")
                pool.terminate()
                break

if __name__ == "__main__":
    main()