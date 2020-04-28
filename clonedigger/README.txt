===================
Clone Digger README
===================

This forks major changes:
- Fixed extra spaces and other esthetic things
- Refactored (simplified) the way `arguments.py` and CLI options work together
- All SourceFle using ANTLR inherits from new object `ANTLRSourceFile`
- Moved out subfunctions
- Added some documentation (+ sphinx documentation)

available at http://clonedigger.sourceforge.net

Clone Digger is the tool for finding software clones. 
Currently only Python language is supported, Java support will be added soon.
See the site for details.
It implements the following paper [Duplicate code detection using anti-unification](http://clonedigger.sourceforge.net/duplicate_code_detection_bulychev_minea.pdf).

Usage
=====

The simplest way of running Clone Digger is::

    clonedigger source_file_1 source_file_2 ...

Or::

    clonedigger --recursive path_to_source_tree

Don't forget to remove automatically generated sources, tests and third party libraries from the source tree.

See http://clonedigger.sourceforge.net/documentation.html for more complex arguments.

The available arguments can be obtained using '--help' also.


Overview of the program:
1. Deal with CLI arguments
2. Parse_files (using SourceFile to return AbstractSyntaxTree (AST))
	According to `options.language`, an AST `supplier` is used to process the file.
	- Lua, Java, JS : Uses ANTLR (ANother Tool for Language Recognition) to create the AST (ANTLR provides many grammar to analyse many languages)
	- Python : Uses python**2** builtin `compiler` module to create the AST.
3. Find duplicate_code (using `clone_detection_algorithm.py`)
4. Create a report of duplicate code (using `reports.py`)

ANTLR resources:
- [ANTLR to XML](https://github.com/RadimBaca/antlr-parse-tree-xml-export)
- [Python ANTLR grammar](https://github.com/antlr/grammars-v4/tree/master/python/python3-without-actions)


![img](../doc/uml/clonedigger_classes_manual.png)