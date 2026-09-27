"""Small viewer smoke test: bounded neighborhoods and HTTP routes."""
from pathlib import Path
import json
import threading
import unittest
from urllib.request import urlopen
from http.server import ThreadingHTTPServer

from rdflib import Graph, Literal, RDF, RDFS, URIRef
from tools.view_robokgnet import Viewer, handler_for, WN, CN, AT_LOCATION, MAPPING


class ViewerTests(unittest.TestCase):
    def test_real_conceptnet_semantic_projection_and_filters(self):
        graph = Graph()
        # Legacy reification remains viewable; the canonical graph now has histograms.
        book_uri = URIRef('http://api.conceptnet.io/c/en/book')
        graph.add((book_uri, RDF.type, URIRef(CN + 'ConceptNetConcept')))
        for name in ('bed', 'floor', 'row', 'stack'):
            obj = URIRef('http://api.conceptnet.io/c/en/' + name)
            assertion = URIRef('urn:assertion:' + name)
            graph.add((obj, RDF.type, URIRef(CN + 'ConceptNetConcept')))
            for predicate, value in [(RDF.type, URIRef(CN + 'AtLocationAssertion')), (RDF.subject, book_uri), (RDF.predicate, AT_LOCATION), (RDF.object, obj)]:
                graph.add((assertion, predicate, value))
        for target in ('100000001-n', '100000002-n'):
            graph.add((book_uri, MAPPING, URIRef('http://wordnet-rdf.princeton.edu/wn31/' + target)))
        before = set(graph)
        viewer = Viewer(graph, 'conceptnet')
        book = 'http://api.conceptnet.io/c/en/book'
        self.assertEqual(viewer.nodes[book]['label'], 'book')
        self.assertEqual(viewer.search('book')['nodes'][0]['id'], book)
        semantic = viewer.neighborhood(book)
        targets = {e['target'] for e in semantic['edges'] if e['source'] == book}
        self.assertEqual(targets, {'http://api.conceptnet.io/c/en/' + name for name in ('bed', 'floor', 'row', 'stack')})
        self.assertTrue(all(e['predicate'] == str(AT_LOCATION) for e in semantic['edges']))
        self.assertTrue(all(n['kind'] != 'assertion' for n in semantic['nodes']))
        self.assertTrue(all(e['assertions'] for e in semantic['edges']))
        raw = viewer.neighborhood(book, view='raw')
        self.assertTrue(any(n['kind'] == 'assertion' for n in raw['nodes']))
        self.assertTrue(any(e['predicate'] == str(RDF.subject) for e in raw['edges']))
        mappings = viewer.neighborhood(book, relation='mappings')
        self.assertEqual(len(mappings['edges']), 2)
        self.assertTrue(all(e['predicate'] == str(MAPPING) for e in mappings['edges']))
        both = viewer.neighborhood(book, mappings=True)
        self.assertEqual(len(both['edges']), len(semantic['edges']) + 2)
        only_locations = viewer.neighborhood(book, relation='atlocation', mappings=True)
        self.assertEqual(only_locations['edges'], semantic['edges'])
        self.assertEqual(viewer.neighborhood(book, relation='hierarchy')['total'], 0)
        assertion = next(n['id'] for n in raw['nodes'] if n['kind'] == 'assertion'
                         and graph.value(URIRef(n['id']), RDF.subject) == URIRef(book))
        self.assertEqual(viewer.neighborhood(assertion)['focus'], book)
        self.assertEqual(set(graph), before)

    def test_neighborhood_search_inspector_and_http(self):
        graph = Graph()
        center = URIRef('urn:test:object')
        graph.add((center, RDFS.label, Literal('<mug>')))
        graph.add((center, URIRef(WN + 'partOfSpeech'), Literal('noun')))
        graph.add((center, RDF.type, RDFS.Class))
        for i in range(55):
            graph.add((URIRef(f'urn:test:child{i:02}'), RDFS.subClassOf, center))
        viewer = Viewer(graph, 'wordnet')
        self.assertEqual(viewer.search('mug')['nodes'][0]['id'], str(center))
        self.assertEqual(viewer.inspect(str(center))['kind'], 'noun')
        first, second = viewer.neighborhood(str(center)), viewer.neighborhood(str(center), 40)
        self.assertEqual(first['total'], 55)
        self.assertEqual(len(first['edges']), 40)
        self.assertEqual(len(second['edges']), 15)
        self.assertTrue(all(e['predicate'] != str(RDF.type) for e in first['edges']))
        with ThreadingHTTPServer(('127.0.0.1', 0), handler_for(viewer)) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f'http://127.0.0.1:{server.server_port}'
            try:
                with urlopen(base + '/') as response:
                    html = response.read().decode()
                    self.assertIn('graph explorer', html)
                    self.assertNotIn('<script src=', html)  # no CDN dependency
                with urlopen(base + '/api/graph?uri=urn:test:object') as response:
                    self.assertEqual(json.load(response)['total'], 55)
                with urlopen(base + '/api/node?uri=urn:test:object') as response:
                    self.assertEqual(json.load(response)['label'], '<mug>')
            finally:
                server.shutdown()
                thread.join()


if __name__ == '__main__':
    unittest.main()
