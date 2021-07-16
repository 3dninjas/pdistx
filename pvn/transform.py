import ast
from pathlib import Path
from typing import List


class ImportTransform(ast.NodeTransformer):

    def __init__(self, level, modules):
        self._level = level
        self._modules = modules
        super().__init__()

    def visit_Import(self, node: ast.Import):
        nodes = []
        for name in node.names:
            # Keep "import abc.def" and "import abc.def as xyz" for non included modules
            if name.name.split('.')[0] not in self._modules:
                nodes.append(ast.Import([name]))
                continue

            # Perform an absolute import with "__import__" to ensure nested imports are solved properly
            nodes.append(
                ast.Expr(value=ast.Call(
                    func=ast.Name(id='__import__', ctx=ast.Load()),
                    args=[
                        ast.Call(
                            func=ast.Attribute(value=ast.Constant(value='.'), attr='join', ctx=ast.Load()),
                            args=[
                                ast.BinOp(
                                    left=ast.Subscript(
                                        value=ast.Call(
                                            func=ast.Attribute(
                                                value=ast.Name(id='__package__', ctx=ast.Load()),
                                                attr='split',
                                                ctx=ast.Load(),
                                            ),
                                            args=[ast.Constant(value='.')],
                                            keywords=[],
                                        ),
                                        slice=ast.Slice(upper=ast.UnaryOp(
                                            op=ast.USub(),
                                            operand=ast.Constant(value=self._level),
                                        )),
                                        ctx=ast.Load(),
                                    ),
                                    op=ast.Add(),
                                    right=ast.List(elts=[ast.Constant(value=name.name)], ctx=ast.Load()),
                                )
                            ],
                            keywords=[],
                        ),
                        ast.Call(func=ast.Name(id='globals', ctx=ast.Load()), args=[], keywords=[]),
                        ast.Call(func=ast.Name(id='locals', ctx=ast.Load()), args=[], keywords=[]),
                        ast.List(elts=[], ctx=ast.Load()),
                        ast.Constant(value=0),
                    ],
                    keywords=[],
                )))

            # Rewrite "import abc.def" to "from .. import abc"
            if not name.asname:
                nodes.append(
                    ast.ImportFrom(
                        module=None,
                        names=[ast.alias(
                            name=name.name.split('.')[0],
                            asname=None,
                        )],
                        level=self._level + 1,
                    ))

            # Rewrite "import abc.def as xyz" to "from ..abc import def as xyz"
            else:
                nodes.append(
                    ast.ImportFrom(
                        module='.'.join(name.name.split('.')[:-1]),
                        names=[ast.alias(
                            name=name.name.split('.')[-1],
                            asname=name.asname,
                        )],
                        level=self._level + 1,
                    ))

        return nodes

    def visit_ImportFrom(self, node: ast.ImportFrom):
        # Rewrite "from abc import def (as xyz)" to "from ..abc import def (as xyz)"
        if node.level == 0 and node.module.split('.')[0] in self._modules:
            return ast.ImportFrom(
                module=node.module,
                names=node.names,
                level=self._level + 1,
            )

        return node

    def visit_Call(self, node: ast.Call):
        if isinstance(node.func, ast.Name) and node.func.id == '__import__' and isinstance(node.func.ctx, ast.Load):

            # we do not support *x and **x
            has_starred = len([x for x in node.args if isinstance(x, ast.Starred)]) > 0
            has_kwargs_list = len([x for x in node.keywords if not x.arg]) > 0

            if not has_starred and not has_kwargs_list:

                # extract arguments
                arg_name = node.args[0] if len(node.args) > 0 else ast.Constant(value=None)
                arg_globals = node.args[1] if len(node.args) > 1 else ast.Constant(value=None)
                arg_locals = node.args[2] if len(node.args) > 2 else ast.Constant(value=None)
                arg_fromlist = node.args[3] if len(node.args) > 3 else ast.List(elts=[])
                arg_level = node.args[4] if len(node.args) > 4 else ast.Constant(value=0)

                # extract keyword arguments
                kwargs = {x.arg: x.value for x in node.keywords}
                arg_name = kwargs['name'] if 'name' in kwargs else arg_name
                arg_globals = kwargs['globals'] if 'globals' in kwargs else arg_globals
                arg_locals = kwargs['locals'] if 'locals' in kwargs else arg_locals
                arg_fromlist = kwargs['fromlist'] if 'fromlist' in kwargs else arg_fromlist
                arg_level = kwargs['level'] if 'level' in kwargs else arg_level

                # we support level 0 only
                if isinstance(arg_level, ast.Constant) and arg_level.value == 0:

                    # transform name argument
                    arg_name = ast.Call(
                        func=ast.Attribute(value=ast.Constant(value='.'), attr='join', ctx=ast.Load()),
                        args=[
                            ast.BinOp(
                                left=ast.Subscript(
                                    value=ast.Call(
                                        func=ast.Attribute(
                                            value=ast.Name(id='__package__', ctx=ast.Load()),
                                            attr='split',
                                            ctx=ast.Load(),
                                        ),
                                        args=[ast.Constant(value='.')],
                                        keywords=[],
                                    ),
                                    slice=ast.Slice(upper=ast.UnaryOp(
                                        op=ast.USub(),
                                        operand=ast.Constant(value=self._level),
                                    )),
                                    ctx=ast.Load(),
                                ),
                                op=ast.Add(),
                                right=ast.List(elts=[arg_name], ctx=ast.Load()),
                            )
                        ],
                        keywords=[],
                    )

                    # rewrite __import__ call
                    return ast.Call(
                        func=node.func,
                        args=[arg_name, arg_globals, arg_locals, arg_fromlist, arg_level],
                        keywords=[],
                    )

        return node


def import_transform(source_path: Path, target_path: Path, level: int, modules: List[str]):
    # read file
    with open(source_path, 'r') as sf:
        source = sf.read()

    # transform
    tree = ast.parse(source, filename=str(source_path), type_comments=True)
    tree = ImportTransform(level, modules).visit(tree)
    tree = ast.fix_missing_locations(tree)
    target = ast.unparse(tree)

    # write file
    with open(target_path, 'w') as tf:
        tf.write(target)
