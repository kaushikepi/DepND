DepNegEx
========

Negation detection using dependency parsing.

## How to use:
* Make sure `python 2.7` is installed on your machine. And the program share the the same directory as [GDep parser](http://people.ict.usc.edu/~sagae/parser/gdep/).

* Run the command in terminal: `python DepND.py YOUR_TESTING_DATA_FILEPATH OUTPUT_FILEPATH`.  
> e.g. `python DepND.py ./data/bioscope_abstracts_cleaned.txt ./data/result.txt`

## Basic Workflow ##

* Separate text input into sentences. Filter all sentences not containing negation triggers. For sentences containing negation triggers, parse each of them using a dependency parser.  
> This task is done by `DepNeg` class, using [GDep beta2](http://people.ict.usc.edu/~sagae/parser/gdep/) created by Prof. Kenji Sagae, please see `GDep_README` for more details.  
> Note that all files in folder except `README.md`, `README.html`, and `DepND.py` are parts of `GDep beta2`.

* Use parse tree and rules to determine the scope of negation.  
> This task is done by `DepND` class  

* Extract keywords or entities within these scopes if you like.  
> Such functionality is not implemented in DepNegEx.

## Rules for determining scope

### Default rules:

#### Major rules:

* *gMST*
> maximal spanning tree from its immediate governor;

* *sMST*
> maximal spanning tree from itself;

* *withinPUNC*
> All MST rules *should not cross punctuation marks* during spanning, no matter it spans towards left or right (relatively to the position of trigger word). But some arcs can (such as SUB, OBJ and PRD).

#### Specification

| Trigger_POS | Trigger examples | Rule |
|  --- | --- | --- |
| RB, DT | no, not, hardly, never | *gMST* |
| JJ | absent, negative, unable, unlikely | *gMST* |
| CC | neither, nor | *gMST* |
| VB\*, IN | fail, lack, lacking, excluding, without, except | *sMST* |
| NN | none, lack, absence, failure (to/of)| *sMST* |

### However, default rules above are not panaceas:

#### Exceptions that cannot be coped with default rules:

| trg | trg_pos | trg_dep | gvn | gvn_pos | gvn_dep | rule | comment or alter-rule |
| --- | --- | --- | --- | --- | --- | --- | --- |
| not | RB | DEP | but, and | CC | NMOD | ggMST | *DEP_Elevate*; *SUB&Right* |
| not | RB | PMOD | in | IN | PMOD |gMST| PMOD arc *can* cross punctuation?|
| not | RB | VMOD | does, did, is | VBZ | ROOT | gMST | *SUB&Right* |
| hardly | RB | AMOD | any | DT | NMOD | ggMST | *AMOD_Elevate* |
| never | RB | NMOD | effect | NN | OBJ | gMST | *SUB&Right* |
| rather (than) | RB | PMOD | for | IN | | gMST | *SUB&Right* |
| negative | JJ | NMOD | regulation, factors | NN, NNS | ROOT, PMOD | gMST | only span through of/IN NMOD arc; "factors" has no children |
| absence | NN | PMOD | in | IN | NMOD | gMST | *PMOD_Elevate* |
| none | NN | SUB | had | VBD | ROOT | gMST | *SUB&Right* |
| without | IN | PMOD | with | IN | PMOD | gMST | only span through PMOD towards right |
| lack | VBP | SBAR | | | | sMST | forbid VMOD branching to MD or VB* |
| lacking | VBG | VC | is | VBZ | SUB | gMST | *VC_Elevate* |
| denied | VBN | VC | are | VBP | ROOT | gMST | *VC_Elevate*; *SUB&Right* |
| excluded | VBN | VC | be | VB | VC | ggMST | *VC_Elevate* |

> * P.S. Whether some exceptions (e.g. "negative", "without", "lack" in above table) arose depends on the performance of the dependency parser.
> * *ggMST* (double "g" indicates governor of governor) can be replaced by *$_Elevate*.
> * There're also minor rules to deal with subjunctive moods.

#### So, some minor rules are added:

* *$_Elevate* 
> elevate root node through all possible $ arcs then do a default MST (either sMST or gMST);

* *SUB&Right* 
> only span towards right or span left through SUB arc, span nothing if there's no SUB arc or right part. (notice that this rule only apply to root node)

### Performance of designed rules are vulnerable to:

* Performance of PP attachment in the parser;
> e.g. The prepositional phrase "on sth" in "no effect on sth" is often wrongly attached to other NN rather than "effect".  

* Inconsistency of decision in whether including the left part of parsed tree governed by a SUB arc.
> e.g. In BioScope corpus, human annotator inconsistently include or exclude the subjects of sentences in the negation scope. A safer solution than the *SUB&Right* rule may be discarding SUB arcs and just spanning through towards right, sacrificing false negative for false positive.

## Procedures after determining the scope
* Coping with double/triple negation.
* Coreference and pronoun resolution.
* Output formatting.
