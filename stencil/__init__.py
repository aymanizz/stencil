import re

from .builder import CodeBuilder

class StencilError(Exception):
    pass

class Template:
    def __init__(self, text, *contexts):
        """Initialize a template with the given `text`.

        `contexts` are dictionaries of values to use for future renderings.
        """
        self.context = {}
        for ctx in contexts:
            self.context.update(ctx)
        self.all_vars = set()
        self.loop_vars = set()
        self._renderer = self._compile_template(text)

    def _expr_code(self, expr):
        """Generate python expression for `expr`.
        """
        if '|' in expr:
            pipes = expr.split('|')
            code = self._expr_code(pipes[0])
            for func in pipes[1:]:
                self._variable(func, self.all_vars)
                code = 'c_{}({})'.format(func, code)
        elif '.' in expr:
            dots = expr.split('.')
            code = self._expr_code(dots[0])
            args = ', '.join(repr(d) for d in dots[1:])
            code = 'do_dots({}, {})'.format(code, args)
        else:
            self._variable(expr, self.all_vars)
            code = 'c_{}'.format(expr)
        return code

    def _error(self, msg: str, where: str):
        raise StencilError("{}: {!r}".format(msg, where))

    def _variable(self, name, vars_set):
        """Add `name` to `vars_set`.

        If `name` is not a valid variable name raises a `StencilError`
        """
        if not re.match(r'[_a-zA-Z][_a-zA-Z0-9]*$', name):
            self._error('invalid variable name', name)
        vars_set.add(name)

    def render(self, ctx=None):
        """Render this template, applying `ctx` to it.

        ctx -- a dictionary of values used for rendering.
        """
        render_ctx = self.context.copy()
        if ctx:
            render_ctx.update(ctx)
        return self._renderer(render_ctx, self._do_dots)

    def _do_dots(self, value, *dots):
        """Evaluate dotted expression at runtime.
        """
        for dot in dots:
            try:
                value = getattr(value, dot)
            except AttributeError:
                value = value[dot]
            if callable(value):
                value = value()
        return value

    def _compile_template(self, text: str):
        code = CodeBuilder()
        code.add_line('def render(ctx, do_dots):')
        code.indent()
        vars_code = code.add_section()
        code.add_line('result = []')
        code.add_line('append = result.append')
        code.add_line('extend = result.extend')
        code.add_line('str = str')

        buffer = []

        def flush_output():
            """Force `buffer` to the code builder.
            """
            if len(buffer) == 1:
                code.add_line('append({})'.format(buffer[0]))
            elif len(buffer) > 1:
                code.add_line('extend([{}])'.format(', '.join(buffer)))
            del buffer[:]

        ops_stack = []
        tokens = re.split(r'(?s) ({{ .*? }} | {% .*? %} | {# .*? #})', text)

        for token in tokens:
            if token.startswith('{#'):
                # comment, ignored.
                continue
            elif token.startswith('{{'):
                # expression
                expr = self._expr_code(token[2:-2].strip())
                buffer.append('str({})'.format(expr))
            elif token.startswith('{%'):
                # tag/control flow
                flush_output()
                words = token[2:-2].strip().split()
                if words[0] == 'if':
                    if len(words) != 2:
                        self._error("invalid syntax: if", token)
                    ops_stack.append('if')
                    expr = self._expr_code(words[1])
                    code.add_line('if {}:'.format(expr))
                    code.indent()
                elif words[0] == 'for':
                    if len(words) != 4 or words[2] != 'in':
                        self._error('invalid syntax: for', token)
                        ops_stack.append('for')
                        self._variable(words[1], self.loop_vars)
                        expr = self._expr_code(words[3])
                        code.add_line('for c_{} in {}:'.format(words[1], expr))
                        code.indent()
                elif words[0].startswith('end'):
                    if len(words) != 1:
                        self._error('invalid syntax: end', token)
                    end = words[0][3:]
                    if not ops_stack:
                        self._error('no opening tag for end', token)
                    start = ops_stack.pop()
                    if start != end:
                        self._error(
                            'mismatched end tag, expected end{}'
                            .format(start), end)
                    code.dedent()
                else:
                    self._error('invalid tag', token)
            else:
                if token:
                    buffer.append(repr(token))

        for var_name in self.all_vars - self.loop_vars:
            vars_code.add_line('c_{0} = context{0!r}'.format(var_name))

        code.add_line("return ''.join(result)")
        code.dedent()
        return code.get_globals()['render']
