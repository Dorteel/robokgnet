import nltk

nltk.download("wordnet")
nltk.download("framenet_v17")
nltk.download("verbnet")
nltk.download("propbank")

from nltk.corpus import wordnet as wn
from nltk.corpus import framenet as fn
from nltk.corpus import verbnet as vn
from nltk.corpus import propbank as pb


from utils.conceptnet_utils import filter_conceptnet, analyze_filtered_conceptnet

def create_wordnet_kg():
    pass

def create_framenet_kg():
    pass

def create_verbnet_kg():
    pass

def create_propbank_kg():
    pass

def create_conceptnet_kg():
    predicates_of_interest = [
        'AtLocation',
        'UsedFor',
        'IsA'
    ]
    conceptnet_source_path = 'sources/conceptnet/assertions.csv'
    n = filter_conceptnet(predicates=predicates_of_interest, language='en', require_wordnet_linked_endpoints=True)
    print(f"Wrote {n} rows.")


def create_mappings():
    pass



# print(wn.synsets("run", pos=wn.VERB))
# print(fn.frames("Motion")[:3])
# print(vn.classids("run"))
# print(pb.roleset("run.01"))

if __name__ == '__main__':
    create_conceptnet_kg()