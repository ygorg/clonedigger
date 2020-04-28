# Doc readme

## Documentation

### Generate template files

This creates `.rst` files according to python modules.

```bash
sphinx-apidoc --ext-autodoc --ext-todo --ext-coverage -o api ../clonedigger ../clonedigger/logilab

```

### Generate html doc

This creates `_build/html/*` by reading the documentation in python files. According to `.rst` files.

`make html`


## Class diagram

Please note that `uml/clonedigger_classes_manual.uml` was created by hand because (to my knowledge) no tool uses type annotation to create class diagram. AbstractSyntaxTree and Reports are not finished. It is possible that it does not reflect the actual state of the documentation or the code !

### Pyreverse

Generates `classes.dot`

```bash
pyreverse clonedigger/ -f ALL --ignore=logilab
dot classes.dot -Tsvg > classes.svg
```

### [PlantUML](https://plantuml.com)

Generates `clonedigger_classes.uml` and `clonedigger_packages.uml`.

```bash
/Users/ygorgallina/Library/Python/2.7/bin/pyplantuml  --ignore=logilab -f ALL clonedigger
java -jar plantuml.jar uml/clonedigger_classes.uml
java -jar plantuml.jar uml/clonedigger_packages.uml
java -jar plantuml.jar uml/clonedigger_classes_manual.uml
```