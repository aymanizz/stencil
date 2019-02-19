from typing import Text, Dict

class CodeBuilder:
    """Build source code conveniently.
    """

    def __init__(self, *, indent: int = 0, indent_step: int = 4):
        """Initialize a new CodeBuilder instance.

        indent -- starting indent level for source code
        indent_step -- number of spaces used for indent
        """
        self._indent = indent
        self._code = []
        self.INDENT_STEP = indent_step

    @property
    def level(self) -> int:
        """Return indentation level.
        """
        return self._indent

    @property
    def source(self) -> str:
        """The source as a string.
        """
        return str(self)

    def add_line(self, line: Text):
        """Add a line of source to the code.

        Proper indentation and a newline are added.
        """
        self._code.extend((' ' * self._indent, line, '\n'))

    def indent(self):
        """Increase indent level for the following lines.
        """
        self._indent += self.INDENT_STEP

    def dedent(self):
        """Decrease indent level for the following lines.
        """
        self._indent -= self.INDENT_STEP

    def add_section(self) -> 'CodeBuilder':
        """Add a section, a sub CodeBuilder.
        """
        section = CodeBuilder(indent=self._indent)
        self._code.append(section)
        return section

    def __str__(self) -> str:
        return "".join(str(block) for block in self._code)

    def get_globals(self) -> Dict[str, object]:
        """Return a dict of globals the code defines.

        Executes the code.
        """
        assert self._indent == 0
        global_ns = {}
        exec(self.source, global_ns)
        return global_ns
