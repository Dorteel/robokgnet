import nltk

nltk.download("wordnet")
nltk.download("framenet_v17")
nltk.download("verbnet")
nltk.download("propbank")

from nltk.corpus import wordnet as wn
from nltk.corpus import framenet as fn
from nltk.corpus import verbnet as vn
from nltk.corpus import propbank as pb

def create_wordnet_kg():
    pass

def create_framenet_kg():
    pass

def create_verbnet_kg():
    pass

def create_propbank_kg():
    pass

def create_mappings():
    pass

print(wn.synsets("run", pos=wn.VERB))
print(fn.frames("Motion")[:3])
print(vn.classids("run"))
print(pb.roleset("run.01"))