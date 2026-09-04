# Python Code
- every thing (classes, functions, variables) in the code should be typed
- always import the library and use the variables/classes/functions in the format: library.something, never import a name directly from inside the library. Meaning, never do: from library import x. Also, if you have more than one module, always import the name of the last module, for example: "from x.y import z", where "z" is a library name, such that the user must be doing: "print(z.something)"
- never do relative imports, always use absolute imports
- always include docstrings in modules, files, functions, classes. As we are including the types of the variables in type hints the docstring should not contain type information
- this program should not raise unhandled errors. it is preferred to return boolean to indicate if something works or not, but try to avoid raise errors.