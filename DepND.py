# Copyright 2013 Siyuan Guo

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#  http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


#!/usr/bin/python
# python2.7

import os
import re
import sys
from collections import defaultdict

class DepNeg():

    def __init__(self, test_filepath, result_filepath):
        self.trigger_filepath = "./negTriggers.txt"
        self.test_filepath = test_filepath
        self.result_filepath = result_filepath
        self.trimmed_filepath = "./filtered.tmp"
        self.parsed_filepath = "./parsed.tmp"
        self.read_NegTriggers()

    def read_NegTriggers(self):
        print "Start reading negation triggers ..."
        ## read triggers, one trigger per line
        self.NegTriggers = []
        with open(self.trigger_filepath,'r') as fin:
            for line in fin:
                line = line.strip()
                if line:
                    self.NegTriggers.append(line)
        print "All negation triggers are\n", self.NegTriggers

    def read_TestFile(self):
        print "Start reading test file ..."
        ## read text file for analysis
        ## finding whether a sentence containing negation triggers
        ## aggregate/filter all sentences containing negation into a single text file, one sentence per line
        with open(self.trimmed_filepath,'w') as tfout:
            with open(self.test_filepath,'r') as tfin:
                for line in tfin:
                    line = line.strip()
                    if line:
                        for trigger in self.NegTriggers:
                            ## filter phrases like "no problem/trouble/matter"
                            if trigger == 'no':
                                pattern = re.compile(r'\b'+trigger+r'(?!( problem| trouble| matter| further| one))\b',re.IGNORECASE)
                            elif trigger == 'not':
                                pattern = re.compile(r'\b'+trigger+r'(?!( certain| necessarily| only))\b',re.IGNORECASE)
                            elif trigger == 'without':
                                pattern = re.compile(r'\b'+trigger+r'(?!( difficuly| further| any further))\b',re.IGNORECASE)
                            else:
                                pattern = re.compile(r'\b'+trigger+r'\b',re.IGNORECASE)
                            if pattern.search(line):
                                tfout.write(line+"\n\n")
                                break

    def parse(self):
        ## run gDep to produce denpency trees from plain text sentence
        cmd = "./gdep "+self.trimmed_filepath+" > "+self.parsed_filepath
        print "Start POS tagging, chunking, NER, and parsing ... (this may take several minutes, please wait.)"
        os.system(cmd)
        # if you get "sh: ./gdep permission denied" message, run command "chmod u+rwx ./gdep" first.

    def run_parse(self):
        self.read_TestFile()
        self.parse()

# a wrapper for sentence
class SENT():
    
    def __init__(self):
        self.indices = []
        self.words = []
        self.POS = []
        self.arc_end = [] # another end of the incoming arc, every word has only one incoming arc
        self.dep = []
        self.NegIndice = []

    def add_Row(self, row):
        ## add one row of CoNLL output into the sentence
        row = row.strip()
        cols = row.split('\t')
        self.indices.append(int(cols[0]))
        self.words.append(cols[1])
        self.POS.append(cols[4])
        self.arc_end.append(int(cols[6]))
        self.dep.append(cols[7])

    def add_NegIndex(self, i):
        self.NegIndice.append(i)

    def get_indice(self):
        return self.indices[:]

    def get_words(self):
        return self.words[:]

    def get_POS(self):
        return self.POS[:]

    def get_arc_end(self):
        return self.arc_end[:]

    def get_dep(self):
        return self.dep[:]

    def get_NegIndice(self):
        return self.NegIndice[:]

    def whether_empty(self):
        return self.indices == []
    

class DepND(DepNeg):

    def findNeg(self, sentwrapper):
        core_triggers = self.NegTriggers[:35] #change this index when you changed core negation triggers.
        for i in sentwrapper.get_indice():
            if sentwrapper.get_words()[i-1].lower() in core_triggers:
                sentwrapper.add_NegIndex(i)
            ## deal with phrases
            elif sentwrapper.get_words()[i-1].lower() == 'rather':
                if sentwrapper.get_words()[i].lower() == 'than':
                    sentwrapper.add_NegIndex(i)
            elif any(sentwrapper.get_words()[i-1].lower() == trg for trg in ['rule','rules','ruled','ruling']):
                if sentwrapper.get_words()[i].lower() == 'out':
                    sentwrapper.add_NegIndex(i)
            ## deal with subjunctive mood
            elif any(sentwrapper.get_words()[i-1].lower() == trg for trg in ['would','could']):
                candidates = {}
                for j in sentwrapper.get_indice():
                    if sentwrapper.get_arc_end()[j-1] == i:
                        candidates[j] = [sentwrapper.get_words()[j-1].lower(), sentwrapper.get_POS()[j-1], sentwrapper.get_dep()[j-1]]
                for j in candidates:
                    if candidates[j] == ['if','IN','VMOD']:
                        for k in candidates:
                            if candidates[k][1:] == ['VB','VC']:
                                sentwrapper.add_NegIndex(j)
                                sentwrapper.add_NegIndex(i)
            elif sentwrapper.get_words()[i-1].lower() == 'wish':
                if sentwrapper.get_POS()[i-1] == 'VBP':
                    candidates = {}
                    for j in sentwrapper.get_indice():
                        if sentwrapper.get_arc_end()[j-1] == i:
                            candidates[j] = [sentwrapper.get_words()[j-1].lower(), sentwrapper.get_POS()[j-1], sentwrapper.get_dep()[j-1]]
                    for k in candidates:
                        if candidates[k][1:] == ['VBD','VMOD']:
                            sentwrapper.add_NegIndex(k)

        return sentwrapper.get_NegIndice()
                
    def MST(self, i_root, i_neg, sentwrapper):
        ## maximal spanning tree with SUB&Right and Punc rules
        ## *SUB&Right* = only span towards right or span left through SUB arc, span nothing if there's no SUB arc or right part. (notice that this rule only apply to root node)
        ## *Punc* = All MST rules *should not cross punctuation marks* during spanning, no matter it spans towards left or right (relatively to the position of trigger word). But some arcs can (such as SUB, OBJ and PRD).
        indices = []
        openlist = []
        ## (index, whether_purebred) tuple locates each word
        ## purebred means the node has an SUB, OBJ or PRD ancestor
        ## only purebred nodes can violate Punc-rule (span across punctuations)
        indices.append((i_root,False))
        openlist.append((i_root,False))
        while openlist:
            i_now, whether_purebred = openlist.pop()
            if i_now == i_root:
            ## SUB&Right rule for root node
                for j in sentwrapper.get_indice():
                    if sentwrapper.get_arc_end()[j-1] == i_now:
                        if j >= min(i_root, i_neg):
                            if any(sentwrapper.get_dep()[j-1] == d for d in ['SUB','OBJ','PRD']):
                                whether_purebred = True
                            openlist.append((j,whether_purebred))
                            indices.append((j,whether_purebred))
                        else:
                            if any(sentwrapper.get_dep()[j-1] == d for d in ['SUB','OBJ','PRD']):
                                openlist.append((j,True))
                                indices.append((j,True))
            else:
                for j in sentwrapper.get_indice():
                    if sentwrapper.get_arc_end()[j-1] == i_now:
                        if any(sentwrapper.get_dep()[j-1] == d for d in ['SUB','OBJ','PRD']):
                            whether_purebred = True
                        openlist.append((j,whether_purebred))
                        indices.append((j,whether_purebred))
        ## find all non-purebred punctutations
        i_punc = float("inf")
        for index in indices:
            if sentwrapper.get_dep()[index[0]-1] == 'P' and index[1] == False:
                if index[0] < i_punc:
                    i_punc = index[0]
        ## delete non-purebred punctuation and all non-purebred nodes out of this non-purebred punctuation
        for index in indices:
            if index[0] >= i_punc and index[1] == False:
                indices.remove(index)
        indices = [index[0] for index in indices]
        ## make <SCOPE> tag always enclose <NEG> tag
        if i_neg not in indices:
            indices.append(i_neg)
        indices.sort()
        return indices

    def oldMST(self, i_root, sentwrapper):
        # old maximal spanning tree without any additional rules
        # it's kept in case someone may need it someday
        indice = []
        openlist = []
        indice.append(i_root)
        openlist.append(i_root)
        while openlist:
            i_now = openlist.pop()
            for j in sentwrapper.get_indice():
                if sentwrapper.get_arc_end()[j-1] == i_now:
                    openlist.append(j)
                    indice.append(j)
        indice.sort()
        return indice

    def indice2result(self, indices, i_neg, sentwrapper):
        words = sentwrapper.get_words()
        if any(words[i_neg-1] == trg for trg in ['rather','rule','ruling','rules','ruled']):
            words[i_neg-1] = '<NEG>'+words[i_neg-1]
            words[i_neg] += '</NEG>'
        else:
            words[i_neg-1] = '<NEG>'+words[i_neg-1]+'</NEG>'
        words[indices[0]-1] = '<SCOPE>'+words[indices[0]-1]
        words[indices[-1]-1] += '</SCOPE>'
        return ' '.join(words)

    def elevate(self, i, sentwrapper):
        ## $_Elevate rule
        eDict = defaultdict(list)
        eDict['RB'] = ['DEP', 'AMOD']
        eDict['NN'] = ['PMOD']
        eDict['VBN'] = ['VC']
        eDict['VB'] = ['VC']
        dep_elevate = eDict[sentwrapper.get_POS()[i-1]]
        dep = sentwrapper.get_dep()
        while dep[i-1] in dep_elevate:
            i = sentwrapper.get_arc_end()[i-1]
        return i

    def getNegScope(self, sentwrapper):
        result = ''
        indice_neg = self.findNeg(sentwrapper)
        if indice_neg != []:
            ## map tagset to rules
            tagset_gMST = set(['RB','DT','JJ','CC'])
            tagset_sMST = set(['NN','IN','VB','VBD','VBG','VBN','VBP','VBZ','MD'])
            for i_neg in indice_neg:
                ## sMST rule
                ## maximal spanning tree from itself;
                if sentwrapper.get_POS()[i_neg-1] in tagset_sMST:
                    i_root = self.elevate(i_neg, sentwrapper)
                    result += self.indice2result(self.MST(i_root,i_neg,sentwrapper), i_neg, sentwrapper)+'\n'
                ## gMST rule
                ## maximal spanning tree from its immediate governor;
                if sentwrapper.get_POS()[i_neg-1] in tagset_gMST:
                    i_root = self.elevate(i_neg, sentwrapper)
                    i_root = sentwrapper.get_arc_end()[i_root-1]
                    result += self.indice2result(self.MST(i_root,i_neg,sentwrapper), i_neg, sentwrapper)+'\n'
        return result

    def run_DepND(self):
        # 1. read one sentence, find negation trigger words in the sentence;
        # 2. run corresponding rules to determine scope, return the index-range for the scope.
        print "Start generating scope for negation triggers ..."
        sent_tmp = SENT()
        with open(self.result_filepath,'w') as fout:
            with open(self.parsed_filepath,'r') as fin:
                for line in fin:
                    line = line.strip()
                    if line:
                        sent_tmp.add_Row(line)
                    else:
                        if not sent_tmp.whether_empty():
                            fout.write(self.getNegScope(sent_tmp)+'\n')
                        sent_tmp = SENT()
        print "All done.\nPlease see results at "+self.result_filepath



## run following command to execute this program:
## python DepND.py path/to/test.txt path/to/result.txt
if __name__ == '__main__':
    args = sys.argv
    if len(args) != 3:
        print "Arguments Error: please give 2 arguments - test_filepath, result_filepath."
    else:
        test_filepath = args[1]
        result_filepath = args[2]
        toy = DepND(test_filepath, result_filepath)
        toy.run_parse()
        toy.run_DepND()
