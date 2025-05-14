import os
import json
import re

AST_ROOT = os.path.join(os.getcwd(), 'ast-output')
SRC_DIR = os.path.join(AST_ROOT, 'src')
TESTS_DIR = os.path.join(AST_ROOT, 'tests')

SUPERGLOBALS = ['_GET', '_POST', '_REQUEST', '_COOKIE', '_FILES']

def load_ast(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def is_from_superglobal(node):
    return (
        node.get('kind') == 'offsetlookup'
        and node.get('what', {}).get('kind') == 'variable'
        and node['what'].get('name') in SUPERGLOBALS
    )

def extract_functions(ast, namespace=None, class_name=None):
    functions = []

    for node in ast:
        node_type = node.get("nodeType")
        if node_type == "Stmt_Namespace":
            ns_name = node["name"]["name"] if node.get("name") else None
            # Rekursif ke dalam namespace
            inner = extract_functions(node.get("stmts", []), namespace=ns_name)
            functions.extend(inner)

        elif node_type == "Stmt_Class":
            cls_name = node["name"]["name"]
            # Rekursif ke dalam class
            inner = extract_functions(node.get("stmts", []), namespace=namespace, class_name=cls_name)
            functions.extend(inner)

        elif node_type == "Stmt_ClassMethod":
            func_name = node["name"]["name"]
            func_start_line = node["attributes"].get("startLine")
            full_name = "::".join(filter(None, [namespace, class_name, func_name]))
            functions.append({
                "function": func_name,
                "fq_name": full_name,
                "line": func_start_line,
            })

        elif node_type == "Stmt_Function":
            func_name = node["name"]["name"]
            func_start_line = node["attributes"].get("startLine")
            full_name = "::".join(filter(None, [namespace, func_name]))
            functions.append({
                "function": func_name,
                "fq_name": full_name,
                "line": func_start_line,
            })

        elif "stmts" in node:  # Tangani node lain yang mengandung `stmts`
            inner = extract_functions(node["stmts"], namespace=namespace, class_name=class_name)
            functions.extend(inner)

    return functions


def extract_func_calls(ast, current_class=None, current_function=None):
    calls = []

    def visit(node, current_class=None, current_function=None):
        if isinstance(node, dict):
            node_type = node.get("nodeType")
            
            # Update context: masuk ke dalam class atau method
            if node_type == "Stmt_Class":
                current_class = node.get("name", {}).get("name")
            elif node_type == "Stmt_ClassMethod":
                current_function = node.get("name", {}).get("name")

            # Tangkap pemanggilan method
            if node_type == "Expr_MethodCall":
                method_name = node.get("name", {}).get("name")
                if method_name:
                    calls.append({
                        "name": method_name,
                        "line": node.get("attributes", {}).get("startLine"),
                        "test_function": current_function,
                        "class": current_class
                    })

            # Rekursi ke semua child (baik dict maupun list)
            for key, child in node.items():
                visit(child, current_class, current_function)

        elif isinstance(node, list):
            for item in node:
                visit(item, current_class, current_function)

    visit(ast)
    return calls

def detect_vulnerabilities(ast_node):
    vulnerabilities = []

    inclusion_kinds = {"Expr_Include"}
    file_funcs = {"file_get_contents", "readfile", "fopen", "file", "fpassthru"}
    path_funcs = {"realpath", "is_readable", "is_file"}
    header_func_name = "header"
    redirect_keywords = {
        "checkout_url", "continue", "dest", "destination", "go", "image_url", "next",
        "redir", "redirect", "redirect_uri", "redirect_url", "return_path", "return_to",
        "return", "returnTo", "rurl", "target", "url", "view"
    }

    tainted_vars = set()
    inside_function = False

    def is_user_input(expr):
        if expr.get("nodeType") == "Expr_ArrayDimFetch":
            var_name = expr.get("var", {}).get("name")
            return var_name in SUPERGLOBALS
        elif expr.get("nodeType") == "Expr_Variable":
            return expr.get("name") in tainted_vars or expr.get("name") in SUPERGLOBALS
        return False

    def recursive_check(node):
        nonlocal inside_function
        if isinstance(node, dict):
            node_type = node.get("nodeType")

            if node_type in ["Stmt_Function", "Stmt_ClassMethod"]:
                prev = inside_function
                inside_function = True
                for k in node.values():
                    recursive_check(k)
                inside_function = prev
                return

            if node_type == "Expr_Assign":
                var = node.get("var")
                expr = node.get("expr")
                if var and var.get("nodeType") == "Expr_Variable" and is_user_input(expr):
                    tainted_vars.add(var.get("name"))

            if inside_function and node_type in inclusion_kinds:
                print({
                    "type": "File Inclusion",
                    "detail": f"Unsanitized input passed to `{node_type}`",
                    "lineno": node.get("attributes", {}).get("startLine")
                })
                vulnerabilities.append({
                    "type": "File Inclusion",
                    "detail": f"Unsanitized input passed to `{node_type}`",
                    "lineno": node.get("attributes", {}).get("startLine")
                })

            if node_type == "Expr_FuncCall":
                name_node = node.get("name")
                func_name = name_node.get("parts", [None])[0] if name_node and name_node.get("nodeType") == "Name" else None

                args = node.get("args", [])
                if func_name == header_func_name:
                    if args:
                        arg_val = args[0].get("value", {})
                        if arg_val.get("nodeType") == "Scalar_String" and "Location:" in arg_val.get("value", ""):
                            vulnerabilities.append({
                                "type": "Open Redirect",
                                "detail": "Hardcoded Location header used",
                                "lineno": node.get("attributes", {}).get("startLine")
                            })
                        elif is_user_input(arg_val):
                            vulnerabilities.append({
                                "type": "Open Redirect",
                                "detail": "User input used in Location header",
                                "lineno": node.get("attributes", {}).get("startLine")
                            })

                if inside_function and func_name in file_funcs | path_funcs:
                    for arg in args:
                        val = arg.get("value")
                        print(val)
                        if val and is_user_input(val):
                            vulnerabilities.append({
                                "type": "File Inclusion",
                                "detail": f"User input passed to `{func_name}()`",
                                "lineno": node.get("attributes", {}).get("startLine")
                            })

            if node_type == "Expr_ArrayDimFetch":
                dim = node.get("dim")
                if dim and dim.get("nodeType") == "Scalar_String" and dim.get("value", "").lower() in redirect_keywords:
                    vulnerabilities.append({
                        "type": "Open Redirect (Param Hint)",
                        "detail": f"Suspicious param `{dim['value']}` may allow redirect injection",
                        "lineno": node.get("attributes", {}).get("startLine")
                    })

            for v in node.values():
                recursive_check(v)

        elif isinstance(node, list):
            for item in node:
                recursive_check(item)

    recursive_check(ast_node)
    if vulnerabilities:
        print(vulnerabilities)
    return vulnerabilities

def main():
    report = {
        'functions': []
    }

    # Load all source functions
    function_map = []
    for filename in os.listdir(SRC_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(SRC_DIR, filename)
        ast = load_ast(filepath)
        functions = extract_functions(ast)
        vulns = detect_vulnerabilities(ast)
        if vulns:
            print(functions)

        for func in functions:
            if vulns:
                print(func['line'])
            function_map.append({
                'name': func['fq_name'],  # gunakan fq_name
                'file': f"src/{filename.replace('.json', '')}",
                'line': func['line'],
                'covered_by': [],
                'vulnerabilities': [v for v in vulns if v['lineno'] == func['line']]
            })

    # Load test cases and map them to functions
    test_calls = {}
    for filename in os.listdir(TESTS_DIR):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(TESTS_DIR, filename)
        ast = load_ast(filepath)
        calls = extract_func_calls(ast)
        test_calls[filename] = calls

    # Map test case calls to functions
    for func in function_map:
        func_name = func['name'].split('::')[-1]  # hanya nama fungsi tanpa namespace/class
        for test_file, calls in test_calls.items():
            for call in calls:
                call_name = call['name']
                if call_name == func_name or func_name.lower() in call_name.lower():
                    test_func_name = call.get('test_function') or test_file.replace('.json', '')
                    if test_func_name not in func['covered_by']:
                        func['covered_by'].append(test_func_name)

    report['functions'] = function_map

    with open('analysis_report.json', 'w') as out:
        json.dump(report, out, indent=2)

    print("✅ Analysis complete. Output written to analysis_report.json")

if __name__ == '__main__':
    main()
