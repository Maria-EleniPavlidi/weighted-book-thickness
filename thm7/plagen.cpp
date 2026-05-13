// plagen.cpp

// compute the weighted 2-page book thickness wbt_2 of all planar
// graphs on n vertices, and test if (1) putting a single edge on a
// third page improves the wbt or (2) 7 or more edges are on the
// second page.

//#define OGDF_DEBUG
#include <iostream>
#include <vector>
#include <set>
#include <numeric>
#include <algorithm>
#include <stdexcept>
#include <ogdf/basic/simple_graph_alg.h>
#include <ogdf/basic/extended_graph_alg.h>
#include <ogdf/decomposition/StaticPlanarSPQRTree.h>
#include <ogdf/planarity/BoothLueker.h>

// we use two representations for a graph:
//  (1) explicit as a pair (n,S), where
//      * n denotes #vertices, indexed 0..n-1 and
//      * S is a sequence of pairs (i,j), with 0<=i<j<n, that denotes the edges.
//  (2) implicit as an NT, whose i-th bit corresponds to the i-th entry of the
//      triangular adjacency matrix
//      Note: to work with a 64-bit integer, we want (n choose 2) <= 64, i.e.,
//            n <= 11.

using NT = unsigned long;
using BV = std::vector<bool>;
using IV = std::vector<int>;
using VBV = std::vector<BV>;
using Edge = std::pair<int,int>;
using Edges = std::vector<Edge>;
using MyGraph = std::pair<int, Edges>;

// to make working with the implicit graph representation easier

// where do the edges incident to u start?
IV offset;
// mask all edges incident to u
std::vector<NT> imask;
// identity permutation
IV id;

// to convert between the two representations

MyGraph extract(int n, NT g) {
  MyGraph r;
  r.first = n;
  for (int i = 0; i < n; ++i)
    for (int j = i+1; j < n; ++j) {
      if (g % 2 == 1) r.second.emplace_back(i, j);
      g /= 2;
    }
  return r;
}

// to handle isomorphic graphs
NT encode(const Edges& e, const IV& perm) {
  NT r = 0;
  for (auto i = e.begin(); i != e.end(); ++i) {
    int u = perm[i->first];
    int v = perm[i->second];
    if (u > v) std::swap(u, v);
    r |= (1ul << (offset[u]+v-u-1));
  }
  return r;
}

inline NT encode(const Edges& e) { return encode(e, id); }

void block_isomorphic(const MyGraph& g, BV& done) {
  std::vector<int> perm = id;
  do
    done[encode(g.second, perm)] = true;
  while (std::next_permutation(perm.begin(), perm.end()));
}

std::ostream& operator<<(std::ostream& o, const MyGraph& g) {
  o << g.first << " " << g.second.size();
  int last = -1;
  for (const Edge& e : g.second) {
    if (last != e.first) o << "\n"; else o << " ";
    o << e.first << " " << e.second;
    last = e.first;
  }
  return o;
}

// recursively compute maximum size compatible subset (brute force)
int maxcompatible(int i, int nerm, const VBV& compatible, std::set<int>& s) {
  if (i == nerm) return s.size();
  int dont = maxcompatible(i+1, nerm, compatible, s);
  bool feasible = true;
  for (auto x = s.begin(); x != s.end(); ++x)
    if (!compatible[*x][i]) { feasible = false; break; }
  if (!feasible) return dont;
  s.insert(i);
  int take = maxcompatible(i+1, nerm, compatible, s);
  s.erase(i);
  return std::max(dont, take);    
}

inline int maxcompatible(int nerm, const VBV& compatible) {
  std::set<int> s;
  return maxcompatible(0, nerm, compatible, s);
}

// return.first is min. wbt in a 2-page embedding;
// return.second is min. wbt in a 3-page embedding
// return is (-1,-1) if g is not biconnected planar
std::pair<int,int> test(const MyGraph& g) {
  const int& n = g.first;
  const Edges& E = g.second;
  const int m = E.size();

  // build ogdf graph
  ogdf::Graph og;
  std::vector<ogdf::node> vertex;
  std::vector<ogdf::edge> edges;
  for (int i = 0; i < n; ++i)
    vertex.emplace_back(og.newNode());
  for (int i = 0; i < m; ++i)
    edges.emplace_back(og.newEdge(vertex[E[i].first], vertex[E[i].second]));
  // biconnected planar only
  if (!ogdf::isBiconnected(og) || !ogdf::isPlanar(og))
    return std::make_pair(-1, -1);

  // add new vertex for outerplanarity testing
  ogdf::node nn = og.newNode();
  for (int i = 0; i < n; ++i) og.newEdge(vertex[i], nn);
  
  // determine the best 2-page embedding: remove groups of k edges,
  // for k=0,1,..., until the graph becomes outerplanar. Then test if
  // there is an outerplane drawing such that the remaining edges can
  // fit on the 2nd page. If so, then there is nothing to improve
  // using a 3rd page. If not, then there may be hope.

  // indices (w.r.t. E) of removed edges, sorted increasingly.
  std::vector<int> Erm;
  ogdf::Graph::HiddenEdgeSet hide(og);
  // wbt to beat
  int best = 2*m;
  for (;;) {
    //std::cerr << "\t" << Erm.size() << " forbidden edges" << std::endl;
    
    int nerm = Erm.size();
    if (ogdf::isPlanar(og)) {
      // if at most one edge is on page 2, then this is best possible.
      if (nerm <= 1) return std::make_pair(m+nerm, m+nerm);

      // check for all outerplane drawings if all removed edges are compatible

      // go over all embeddings
      ogdf::StaticPlanarSPQRTree spqr(og);
      spqr.firstEmbedding(og);
      int maxc = 0; // max. #compatible edges found so far
      do {
	// determine which pairs of removed edges are compatible in
	// the current embedding
	
	// adjacent edges are always compatible
	VBV compatible(nerm, BV(nerm, false));
	for (int i = 0; i < nerm; ++i) {
	  int u1 = E[Erm[i]].first;
	  int v1 = E[Erm[i]].second;
	  for (int j = i+1; j < nerm; ++j) {
	    int u2 = E[Erm[j]].first;
	    int v2 = E[Erm[j]].second;
	    if (u1 == u2 || u1 == v2 || v1 == u2 || v1 == v2)
	      compatible[i][j] = compatible[j][i] = true;
	  }
	}

	// walk around the outer cycle and maintain the status of all
	// removed edges; each edge is encountered twice, at its
	// startpoint and at its endpoint
	std::vector<int> count(nerm, 0); // #times we've encountered the edge
	std::vector<int> start(nerm, -1); // step where the edge started
	int step = 0;
	for (ogdf::adjEntry v : nn->adjEntries) {
	  int cur = v->twinNode()->index();
	  for (int i = 0; i < nerm; ++i)
	    if (cur == E[Erm[i]].first || cur == E[Erm[i]].second) {
	      if (++count[i] == 1) start[i] = step;
	      else if (count[i] == 2) {
		// test the remaining edges for compatibility; we
		// decide this when the first of the two edges ends:
		// They are compatible if either the other edge did not
		// even start yet or it started before the current edge
		for (int j = 0; j < nerm; ++j) {
		  if (i == j || compatible[i][j]) continue;
		  if (count[j] == 0 || (count[j] == 1 && start[j] < start[i]))
		    compatible[i][j] = compatible[j][i] = true;
		}
	      }
	    }
	  ++step;
	}
	
	maxc = std::max(maxc, maxcompatible(nerm, compatible));
	// if all removed edges are compatible, this is an optimal
	// 2-page drawing => we cannot improve on what we have seen
	// already (every better drawing must put more edges on page 1
	// => fewer edges removed)
	if (maxc >= nerm) 
	  return std::make_pair(m+nerm, (best < m+nerm ? best : m+nerm));
	
      } while (spqr.nextEmbedding(og));	

      // can Page 3 help? (Recall: We allow at most one edge on Page 3!)
      if (maxc == nerm-1) best = std::min(best, m+nerm+1);
    }
    // remove other edges
    if (nerm == 0) {
      // remove the first edge
      Erm.emplace_back(0);
      hide.hide(edges[0]);
      continue;
    }
    // can we find another set with nerm edges?
    int x = nerm-1;
    int y = m-1;
    while (x >= 0 && Erm[x] >= y) { --x; --y; }
    if (x >= 0) {
      hide.restore(edges[Erm[x]]);
      y = ++Erm[x];
      hide.hide(edges[Erm[x]]);
      for (int i = x+1; i < nerm; ++i) {
	hide.restore(edges[Erm[i]]);
	Erm[i] = ++y;
	hide.hide(edges[Erm[i]]);
      }
      continue;
    }
    // No, so remove one more edge...
    for (int i = 0; i < nerm; ++i) {
      hide.restore(edges[Erm[i]]);
      Erm[i] = i;
      hide.hide(edges[Erm[i]]);
    }
    Erm.emplace_back(nerm);
    hide.hide(edges[nerm]);
  }
}

int main()
{
  int n;
  std::cin >> n;
  if (n < 1 || n > 11) {
    std::cerr << "parameter n out of range (2..10)" << std::endl;
    return 1;
  }
  // #graphs on n vertices
  NT ng = (1ul << n*(n-1)/2);
  std::cout << "considering " << ng << " graphs " << std::flush;
  // initialize id
  for (int i = 0; i < n; ++i) id.push_back(i);
  // compute offsets
  offset.push_back(0);
  for (int i = n-1; i > 1; --i) offset.push_back(offset.back() + i);
  // compute imasks
  for (int i = 0; i < n; ++i) {
    Edges e;
    for (int j = 0; j < n; ++j)
      if (i != j) e.emplace_back(i, j);
    imask.push_back(encode(e));
  }

  // test all graphs on n vertices
  std::vector<bool> done(ng, false);
  int nig = 0;
  for (NT x = 1; x < ng; ++x) {
    if ((x-1) %90000 == 0) std::cerr << "." << std::flush;
    if (done[x]) continue;
    int m = std::popcount(x); // #edges
    // biconnected planar graphs only => n <= m <= 3n-6
    if (m < n || m > 3*n-6) continue;
    // every vertex must have degree >= 2
    bool mindeg = true;
    for (int i = 0; i < n; ++i)
      if (std::popcount(x&imask[i]) < 2) { mindeg = false; break; }
    if (!mindeg) continue;
    MyGraph g = extract(n, x);
    block_isomorphic(g, done);
    auto res = test(g);
    if (res.first >= 1 && (res.first != res.second || res.first - m >= 7)) 
      std::cout << "Graph #" << ++nig << ":\n" << extract(n, x) << "\n";
  }
  std::cerr << "\nFound " << nig << " different graphs on " << n << " vertices." << std::endl;
}
