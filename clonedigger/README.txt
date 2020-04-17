===================
Clone Digger README
===================

available at http://clonedigger.sourceforge.net

Clone Digger is the tool for finding software clones. 
Currently only Python language is supported, Java support will be added soon.
See the site for details.

Usage
=====

The simplest way of running Clone Digger is::

    clonedigger source_file_1 source_file_2 ...

Or::

    clonedigger --recursive path_to_source_tree

Don't forget to remove automatically generated sources, tests and third party libraries from the source tree.

See http://clonedigger.sourceforge.net/documentation.html for more complex arguments.

The available arguments can be obtained using '--help' also.


[Python ANTLR grammar](https://github.com/RadimBaca/antlr-parse-tree-xml-export)
[ANTLR to XML](https://github.com/antlr/grammars-v4/tree/master/python/python3-without-actions) *allegedly*


Entry point:
	clonedigger.py :
 		1. Deal with CLI arguments
 		2. Parse_files (using Abstract Syntax Tree (AST))
 			According to `options.language`, an AST `supplier` is used to process the file.
 			- Lua, Java, JS : Uses ANTLR (ANother Tool for Language Recognition) to create the AST (AST provides many grammar to analyse many languages)
 			- Python : Uses python**2** builtin `compiler` to create the AST.
 		3. Find duplicate_code (using `clone_detection_algorithm.py`)
 		4. Create a report of duplicate code (using `reports.py`)