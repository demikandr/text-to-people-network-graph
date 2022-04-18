# !conda install -c conda-forge -y ipymarkup slovnet natasha
# !wget https://storage.yandexcloud.net/natasha-slovnet/packs/slovnet_ner_news_v1.tar
# !wget https://storage.yandexcloud.net/natasha-navec/packs/navec_news_v1_1B_250K_300d_100q.tar
# The best quality NER that doesn't require GPU is chosen from the benchmark https://github.com/natasha/naeval

from collections import defaultdict, namedtuple
import json
import logging
from typing import Iterable
from natasha import (
    Segmenter,
    MorphVocab,
    NewsEmbedding,
    NewsSyntaxParser,
    NewsNERTagger,
    PER,
    NamesExtractor,
    NewsMorphTagger,
    Doc,
)
import numpy as np

IndexedSpan = namedtuple('IndexedSpan', ['span', 'index'])
Person = namedtuple('Person', ['description', 'last_name', 'spans', 'count'])

def is_person_in_list(doc: Doc, indexed_span: IndexedSpan):
    index = indexed_span.index
    span = indexed_span.span
    previous_span = doc.spans[index-1]
    if previous_span.type=='PER' and span.start - previous_span.stop < 10:
        return True
    next_span = doc.spans[index+1]
    if next_span.type=='PER' and  next_span.start - span.stop < 10:
        return True
    
# TODO: return several descriptions
def generate_descriptions(doc: Doc, spans: Iterable[IndexedSpan]):
    for indexed_span in spans:
        index = indexed_span.index
        span = indexed_span.span
        if not is_person_in_list(doc, indexed_span):
            return doc.text[span.start-150:span.stop+150]

def is_cooccurance(first_span, second_span):
    MAX_COOCCURANCE_DISTANCE_CHARS = 100
    if first_span.start > second_span.start:
        first_span, second_span = second_span, first_span
    return (second_span.start - first_span.stop) < MAX_COOCCURANCE_DISTANCE_CHARS

def count_cooccurances(first_person_spans, second_person_spans):
    first_span_index = 0
    second_span_index = 0
    cooccurances_number = 0
    while first_span_index < len(first_person_spans) and second_span_index < len(second_person_spans):
        first_person_span = first_person_spans[first_span_index].span
        second_person_span = second_person_spans[second_span_index].span
        if is_cooccurance(first_person_span, second_person_span):
            cooccurances_number += 1
        if first_person_span.start < second_person_span.start:
            first_span_index += 1
        else:
            second_span_index += 1
    return cooccurances_number

def exportGraphToWeb(cooccurances_matrix, people: Iterable[Person], min_cooccurances: int):
    getStringId = lambda id: f'{people[id].last_name}id'
    graph = {'nodes':\
                 [{'id': getStringId(i), 'group':i} for i in range(min(20, len(people)))],\
             'links': []\
            }
    for first_person_id, line in enumerate(cooccurances_matrix[:20,:20]):
        for second_person_id, cooccurances in enumerate(line[:first_person_id]):
            if cooccurances >= min_cooccurances:
                graph['links'].append({'source':getStringId(first_person_id),\
                                       'target': getStringId(second_person_id),\
                                       'value': cooccurances})
    return graph

def get_graph_from_text(text: str):
    # Step 1: init stuff
    segmenter = Segmenter()
    emb = NewsEmbedding()
    morph_vocab = MorphVocab()
    syntax_parser = NewsSyntaxParser(emb)
    ner_tagger = NewsNERTagger(emb)
    names_extractor = NamesExtractor(morph_vocab)

    doc = Doc(text) 

    doc.segment(segmenter) # There's an unnecessary dependency of tag_ner method on Doc being segmentedw

    morph_tagger = NewsMorphTagger(emb)
    doc.tag_morph(morph_tagger)
    doc.parse_syntax(syntax_parser)

    doc.tag_ner(ner_tagger)

    for span in doc.spans:
        span.normalize(morph_vocab)
        
    for span in doc.spans:
        if span.type == PER:
            span.extract_fact(names_extractor)
    
    # Step 2: aggregate name spans for the same people
    last_name_to_span = defaultdict(list)
    for indexed_span in [IndexedSpan(index=i, span=_) for i,_ in enumerate(doc.spans) if _.fact]:
        span = indexed_span.span
        if 'last' in span.fact.as_dict:
            last_name_to_span[span.fact.as_dict['last']].append(indexed_span)
        else:
            last_name_to_span[''].append(indexed_span)

    # Step 3: extract people and annotate them with descriptions
    people = [Person(last_name=k, spans=v, description=generate_descriptions(doc, v), count=len(v)) for k,v in sorted(last_name_to_span.items())]
    people = list(sorted(people, key=lambda x: x.count))[::-1]

    # Step 4: extract people connections
    cooccurances_matrix = [[count_cooccurances(first_person.spans, second_person.spans) for second_person in people] for first_person in people]
    cooccurances_matrix = np.array(cooccurances_matrix) * (1-np.identity(len(people)))

    # Step 5: return exported graph 
    # PARAM: min_cooccurances
    logging.warning(f'Number of parsed people: {len(people)}')
    json_graph = exportGraphToWeb(cooccurances_matrix, people, min_cooccurances=1)
    return json_graph


def load_rockets_and_people():
    with open('Rockets and people.txt', encoding='cp1251') as text:
        return ''.join(text.readlines())
