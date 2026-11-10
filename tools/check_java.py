#!/usr/bin/env python3
"""Static consistency check for the Java sources, runnable without a JDK.

No JDK and no Maven Central access exist in the environment where this repository was
prepared, so ``javac`` cannot be run here (see ``docs/testing.md``). This tool does the part
of that work which does not need a compiler:

* every ``import io.github.goshadows.pythonforminecraft.*`` resolves to a declared type;
* the top-level type of a file matches the file name;
* braces, parentheses and square brackets balance in every file;
* ``Type.member(...)`` and ``variable.member(...)`` call sites that point at a type declared
  in this repository refer to a member that type, or one of its supertypes in this
  repository, actually declares.

The last check is a poor-man's type check. It knows nothing about JDK, Truffle, Fabric or
NeoForge types, so those call sites are skipped; a type that extends something outside this
repository gets its misses reported as warnings instead of errors, because ``getMessage()``
and friends legitimately come from the unknown supertype. What it does catch is the class of
mistake a rename leaves behind, which is what a 34-file Java tree that has never been
compiled is exposed to.

Run it with::

    python3 tools/check_java.py
"""

from __future__ import annotations

import os
import re
from typing import Dict, List, Optional, Set, Tuple

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JAVA_ROOTS = ["core", "loader-adapters"]
OWN_PREFIX = "io.github.goshadows.pythonforminecraft"
KEYWORDS = {"if", "for", "while", "switch", "catch", "return", "new", "else", "do",
            "synchronized", "try", "assert", "throw", "instanceof", "super", "this",
            "yield", "case"}
MODIFIERS = {"public", "protected", "private", "static", "final", "synchronized",
             "abstract", "default", "native", "strictfp", "sealed", "non-sealed",
             "transient", "volatile"}

TYPE_DECL = re.compile(
    r"(?:^|[;{}])\s*"
    r"(?:@\w+(?:\s*\([^()]*\))?\s*)*"
    r"((?:(?:public|protected|private|static|final|abstract|sealed|non-sealed|strictfp)\s+)*)"
    r"(class|interface|enum|record|@interface)\s+([A-Za-z_$][A-Za-z0-9_$]*)")
RECORD_PARAMS = re.compile(r"record\s+[A-Za-z_$][A-Za-z0-9_$]*\s*(?:<[^>]*>)?\s*\(([^)]*)\)")
PAREN = re.compile(r"([A-Za-z_$][A-Za-z0-9_$]*)\s*\(")
ANNOTATION = re.compile(r"@\w+(?:\s*\([^()]*(?:\([^()]*\)[^()]*)*\))?\s*")


def strip_noise(text: str) -> str:
    """Removes comments and literals, keeping newlines so line numbers stay meaningful."""
    out = []
    i = 0
    n = len(text)
    while i < n:
        char = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if char == "/" and nxt == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif char == "/" and nxt == "*":
            depth = 1
            i += 2
            while i < n and depth:
                if text[i:i + 2] == "/*":
                    depth += 1
                    i += 2
                elif text[i:i + 2] == "*/":
                    depth -= 1
                    i += 2
                else:
                    if text[i] == "\n":
                        out.append("\n")
                    i += 1
        elif text.startswith('"""', i):
            i += 3
            while i < n and not text.startswith('"""', i):
                if text[i] == "\n":
                    out.append("\n")
                i += 1
            i += 3
            out.append('""')
        elif char in ('"', "'"):
            quote = char
            i += 1
            while i < n and text[i] != quote:
                if text[i] == "\\":
                    i += 2
                else:
                    if text[i] == "\n":
                        out.append("\n")
                    i += 1
            i += 1
            out.append('""' if quote == '"' else "'x'")
        else:
            out.append(char)
            i += 1
    return "".join(out)


class Report:
    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.checked = 0

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)

    def ok(self) -> None:
        self.checked += 1


class JavaType:
    def __init__(self, path: str, package: str, name: str, kind: str) -> None:
        self.path = path
        self.package = package
        self.name = name
        self.kind = kind
        self.fqcn = "%s.%s" % (package, name)
        self.supers: List[str] = []
        self.super_class: Optional[str] = None
        self.interfaces: List[str] = []
        self.members: Set[str] = set()
        self.imports: Dict[str, str] = {}
        self.local_types: Dict[str, str] = {}
        self.calls: List[Tuple[int, str, str]] = []


def java_files() -> List[str]:
    result = []
    for root in JAVA_ROOTS:
        for dirpath, dirs, files in os.walk(os.path.join(REPO, root)):
            dirs[:] = [d for d in dirs if d not in {"build", ".gradle"}]
            for name in files:
                if name.endswith(".java"):
                    result.append(os.path.join(dirpath, name))
    return sorted(result)


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def parse(path: str, report: Report) -> Optional[JavaType]:
    rel = os.path.relpath(path, REPO)
    with open(path, encoding="utf-8") as handle:
        raw = handle.read()
    text = strip_noise(raw)
    if os.path.basename(path) == "package-info.java":
        if "package " in text:
            report.ok()
            return None
        report.error("%s: no package declaration" % rel)
        return None

    package = ""
    match = re.search(r"\bpackage\s+([\w.]+)\s*;", text)
    if match:
        package = match.group(1)
    else:
        report.error("%s: no package declaration" % rel)

    imports: Dict[str, str] = {}
    for target in re.findall(r"\bimport\s+(?:static\s+)?([\w.]+(?:\.\*)?)\s*;", text):
        if target.endswith(".*"):
            continue
        imports[target] = target.rsplit(".", 1)[-1]

    # Structural balance.
    pairs = {"}": "{", ")": "(", "]": "["}
    stack: List[Tuple[str, int]] = []
    for index, char in enumerate(text):
        if char in "{([":
            stack.append((char, line_of(text, index)))
        elif char in "})]":
            if not stack or stack[-1][0] != pairs[char]:
                report.error("%s:%d: unbalanced %r" % (rel, line_of(text, index), char))
                stack = []
                break
            stack.pop()
    if stack:
        report.error("%s: %d unclosed bracket(s), first opened on line %d"
                     % (rel, len(stack), stack[0][1]))

    decl = TYPE_DECL.search(text)
    if decl is None:
        report.error("%s: no top-level type declaration found" % rel)
        return None
    kind, name = decl.group(2), decl.group(3)
    expected = os.path.splitext(os.path.basename(path))[0]
    if name != expected:
        report.error("%s: top-level type %r does not match the file name %r"
                     % (rel, name, expected))
    java_type = JavaType(path, package, name, kind)
    java_type.imports = imports

    # Supertypes: everything between the class name and the opening brace.
    brace = text.find("{", decl.end())
    header = text[decl.end():brace] if brace > 0 else ""
    extends = re.search(r"\bextends\s+(.*?)(?:\bimplements\b|$)", header, re.S)
    implements = re.search(r"\bimplements\s+(.*)$", header, re.S)
    for chunk in (extends.group(1) if extends else "",
                  implements.group(1) if implements else ""):
        for part in re.sub(r"<[^<>]*>", "", chunk).split(","):
            cleaned = part.strip().rstrip("{").strip()
            if cleaned and cleaned not in KEYWORDS:
                java_type.supers.append(cleaned)
    if extends:
        first = re.sub(r"<[^<>]*>", "", extends.group(1)).split(",")[0].strip()
        if first:
            java_type.super_class = first
    java_type.interfaces = [item for item in java_type.supers
                            if item != java_type.super_class]

    # Members: declarations are `name(` not preceded by a dot, preceded by a type.
    record = RECORD_PARAMS.search(text)
    if record:
        for component in re.sub(r"<[^<>]*>", "", record.group(1)).split(","):
            tokens = component.strip().split()
            if tokens:
                java_type.members.add(tokens[-1])
    for match in PAREN.finditer(text):
        callee = match.group(1)
        if callee in KEYWORDS:
            continue
        before = match.start() - 1
        while before >= 0 and text[before].isspace():
            before -= 1
        if before >= 0 and text[before] == ".":
            continue
        delimiter = max(text.rfind(";", 0, match.start()),
                        text.rfind("{", 0, match.start()),
                        text.rfind("}", 0, match.start()))
        prefix = ANNOTATION.sub(" ", text[delimiter + 1:match.start()])
        tokens = prefix.split()
        if not tokens or "=" in prefix:
            continue
        if tokens[0] not in MODIFIERS and len(tokens) < 2:
            continue
        if any(token in MODIFIERS or token.startswith("<") or re.match(r"^[\w$.<>,\[\]?]+$", token)
               for token in tokens[:-1]):
            java_type.members.add(callee)

    # Fields.
    for match in re.finditer(
            r"(?:public|protected|private)\s+(?:static\s+)?(?:final\s+)?(?:volatile\s+)?"
            r"[A-Za-z_$][\w$.<>,\[\]\s?]*?\s+([A-Za-z_$][A-Za-z0-9_$]*)\s*[=;]", text):
        java_type.members.add(match.group(1))

    # Declared types of local variables and parameters, for receiver resolution.
    for match in re.finditer(r"\b([A-Z][A-Za-z0-9_$]*)\s+(?:final\s+)?([a-z][A-Za-z0-9_$]*)\b",
                             text):
        if match.group(1) in ("String", "Integer", "Boolean", "Object", "Long", "Double"):
            continue
        java_type.local_types.setdefault(match.group(2), match.group(1))

    # Call sites, skipping `a.b.c(` chains (the receiver of the outer call is unknown to us).
    for match in re.finditer(r"(?<![\w$.])([A-Za-z_$][A-Za-z0-9_$]*)\s*\.\s*"
                             r"([A-Za-z_$][A-Za-z0-9_$]*)\s*\(", text):
        java_type.calls.append((line_of(text, match.start()), match.group(1),
                                match.group(2)))
    return java_type


def resolve(type_name: str, importer: JavaType, index: Dict[str, JavaType]) -> Optional[JavaType]:
    for fqcn, simple in importer.imports.items():
        if simple == type_name:
            return index.get(fqcn)
    return index.get("%s.%s" % (importer.package, type_name))


def collect_members(type_name: str, index: Dict[str, JavaType], importer: JavaType,
                    seen: Optional[Set[str]] = None) -> Tuple[Set[str], bool]:
    """Members of *type_name* plus whether any supertype lives outside this repository."""
    seen = seen or set()
    resolved = resolve(type_name, importer, index) or index.get(type_name)
    if resolved is None or resolved.fqcn in seen:
        return set(), False
    seen.add(resolved.fqcn)
    members = set(resolved.members)
    # Only an external *class* can hand down an arbitrary inherited member; an external
    # interface only explains members the type is known to implement, so those stay errors.
    external = (resolved.super_class is not None
                and resolve(resolved.super_class.rsplit(".", 1)[-1], resolved, index) is None)
    for supertype in resolved.supers:
        if resolve(supertype.rsplit(".", 1)[-1], resolved, index) is None:
            continue
        more, ext = collect_members(supertype.rsplit(".", 1)[-1], index, resolved, seen)
        members |= more
        external = external or ext
    return members, external


def check_comment_terminators(report: "Report") -> None:
    """Flags a block comment that terminates in the middle of a line.

    `* into the log through *out*/*err*` closes the comment at `*out*/`, and javac then
    reads the rest of the sentence as code. Nothing else in this checker sees it, because
    the rest of the file still parses as plausible Java.
    """
    for path in java_files():
        rel = os.path.relpath(path, REPO)
        in_block = False
        for line_no, raw in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            text = raw.strip()
            if in_block:
                at = text.find("*/")
                if at >= 0:
                    if text[at + 2:].strip():
                        report.error("%s:%d block comment ends mid-line, so javac reads "
                                     "the rest as code: %s" % (rel, line_no, text))
                    in_block = False
            elif text.startswith("/*"):
                at = text.find("*/", 2)
                if at < 0:
                    in_block = True
                elif text[at + 2:].strip():
                    report.error("%s:%d block comment ends mid-line: %s" % (rel, line_no, text))


def main() -> int:
    report = Report()
    index: Dict[str, JavaType] = {}
    types: List[JavaType] = []
    paths = java_files()
    for path in paths:
        parsed = parse(path, report)
        if parsed is not None:
            index[parsed.fqcn] = parsed
            types.append(parsed)
    print("java files: %d, declared types: %d" % (len(paths), len(index)))
    check_comment_terminators(report)

    for java_type in types:
        rel = os.path.relpath(java_type.path, REPO)
        for fqcn in java_type.imports:
            if not fqcn.startswith(OWN_PREFIX):
                continue
            if fqcn in index:
                report.ok()
            else:
                report.error("%s: imports %s, which no file declares" % (rel, fqcn))

        for line_no, receiver, member in java_type.calls:
            target = java_type if receiver == java_type.name else resolve(receiver, java_type, index)
            if target is None:
                declared = java_type.local_types.get(receiver)
                if declared is None:
                    continue
                target = resolve(declared, java_type, index)
                if target is None:
                    continue
            known, external = collect_members(target.name, index, java_type)
            if member in known:
                report.ok()
            elif external:
                report.warn("%s:%d %s.%s() not declared here; assuming it comes from an "
                            "external supertype" % (rel, line_no, target.name, member))
            else:
                report.error("%s:%d calls %s.%s(), but %s declares no such member (%s)"
                             % (rel, line_no, target.name, member, target.name,
                                ", ".join(sorted(known))))

    print("checks passed: %d" % report.checked)
    if report.warnings:
        print("warnings: %d" % len(report.warnings))
        for warning in sorted(set(report.warnings)):
            print("  ~ " + warning)
    if report.errors:
        print("FAILED: %d problem(s)" % len(report.errors))
        for error in sorted(set(report.errors)):
            print("  - " + error)
        return 1
    print("PASSED: no problems in %d files / %d types" % (len(paths), len(index)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
