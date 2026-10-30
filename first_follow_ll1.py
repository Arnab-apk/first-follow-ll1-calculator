#!/usr/bin/env python3
"""FIRST/FOLLOW calculator and table-driven LL(1) parser.

Grammar format: one production per line, with alternatives separated by |.
Symbols on a right-hand side must be separated by spaces. Use epsilon, eps,
ε, or # for the empty production. The first left-hand side is the start symbol.
Example: E -> T Eprime\nEprime -> + T Eprime | epsilon
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

EPSILON = "ε"
END = "$"


class GrammarError(ValueError):
    """Raised when the grammar or input cannot be interpreted safely."""


def read_grammar(path: str) -> tuple[list[str], dict[str, list[tuple[str, ...]]]]:
    """Read productions, preserving nonterminal and alternative order."""
    productions: dict[str, list[tuple[str, ...]]] = {}
    for line_number, raw in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("//", 1)[0].strip()
        if not line:
            continue
        if "->" not in line:
            raise GrammarError(f"line {line_number}: expected '->'")
        lhs, rhs_text = (part.strip() for part in line.split("->", 1))
        if not lhs or any(ch.isspace() for ch in lhs):
            raise GrammarError(f"line {line_number}: left side must be one symbol")
        alternatives = productions.setdefault(lhs, [])
        for alternative in rhs_text.split("|"):
            words = alternative.split()
            if not words or words in (["ε"], ["eps"], ["epsilon"], ["#"]):
                words = [EPSILON]
            if EPSILON in words and words != [EPSILON]:
                raise GrammarError(f"line {line_number}: epsilon must be the whole alternative")
            alternatives.append(tuple(words))
    if not productions:
        raise GrammarError("grammar file contains no productions")
    nonterminals = list(productions)
    return nonterminals, productions


def compute_first(nonterminals: list[str], productions: dict[str, list[tuple[str, ...]]]) -> dict[str, set[str]]:
    """Compute FIRST sets by fixed-point iteration."""
    first = {nt: set() for nt in nonterminals}

    def first_of_sequence(sequence: tuple[str, ...] | list[str]) -> set[str]:
        if not sequence or sequence == [EPSILON] or sequence == (EPSILON,):
            return {EPSILON}
        result: set[str] = set()
        nullable_prefix = True
        for symbol in sequence:
            if symbol == EPSILON:
                result.add(EPSILON)
                break
            if symbol not in first:
                result.add(symbol)
                nullable_prefix = False
                break
            result.update(first[symbol] - {EPSILON})
            if EPSILON not in first[symbol]:
                nullable_prefix = False
                break
        if nullable_prefix:
            result.add(EPSILON)
        return result

    changed = True
    while changed:
        changed = False
        for lhs, alternatives in productions.items():
            for rhs in alternatives:
                before = len(first[lhs])
                first[lhs].update(first_of_sequence(rhs))
                changed |= len(first[lhs]) != before
    return first


def first_sequence(sequence: tuple[str, ...], first: dict[str, set[str]]) -> set[str]:
    """Return FIRST(sequence), where terminals are symbols absent from first."""
    if not sequence or sequence == (EPSILON,):
        return {EPSILON}
    result: set[str] = set()
    for symbol in sequence:
        if symbol == EPSILON:
            result.add(EPSILON)
            break
        if symbol not in first:
            result.add(symbol)
            break
        result.update(first[symbol] - {EPSILON})
        if EPSILON not in first[symbol]:
            break
    else:
        result.add(EPSILON)
    return result


def compute_follow(nonterminals: list[str], productions: dict[str, list[tuple[str, ...]]],
                   first: dict[str, set[str]]) -> dict[str, set[str]]:
    """Compute FOLLOW sets by fixed-point iteration."""
    follow = {nt: set() for nt in nonterminals}
    follow[nonterminals[0]].add(END)
    changed = True
    while changed:
        changed = False
        for lhs, alternatives in productions.items():
            for rhs in alternatives:
                for index, symbol in enumerate(rhs):
                    if symbol not in follow:
                        continue
                    suffix_first = first_sequence(rhs[index + 1:], first)
                    before = len(follow[symbol])
                    follow[symbol].update(suffix_first - {EPSILON})
                    if EPSILON in suffix_first:
                        follow[symbol].update(follow[lhs])
                    changed |= len(follow[symbol]) != before
    return follow


def build_table(nonterminals: list[str], productions: dict[str, list[tuple[str, ...]]],
                first: dict[str, set[str]], follow: dict[str, set[str]]) -> tuple[dict[tuple[str, str], tuple[str, ...]], list[tuple[str, str, tuple[str, ...], tuple[str, ...]]]]:
    """Build predictive table and return all cells receiving multiple rules."""
    table: dict[tuple[str, str], tuple[str, ...]] = {}
    origins: dict[tuple[str, str], list[tuple[str, ...]]] = defaultdict(list)
    for lhs, alternatives in productions.items():
        for rhs in alternatives:
            lookaheads = first_sequence(rhs, first) - {EPSILON}
            if EPSILON in first_sequence(rhs, first):
                lookaheads |= follow[lhs]
            for terminal in lookaheads:
                origins[(lhs, terminal)].append(rhs)
                table[(lhs, terminal)] = rhs
    conflicts = [(nt, term, tuple(rules)) for (nt, term), rules in origins.items() if len(rules) > 1]
    return table, conflicts


def ordered_terminals(nonterminals: list[str], productions: dict[str, list[tuple[str, ...]]],
                      follow: dict[str, set[str]]) -> list[str]:
    seen: list[str] = []
    for alternatives in productions.values():
        for rhs in alternatives:
            for symbol in rhs:
                if symbol not in nonterminals and symbol != EPSILON and symbol not in seen:
                    seen.append(symbol)
    if END in set().union(*follow.values()) and END not in seen:
        seen.append(END)
    return seen


def parse_input(text: str, nonterminals: list[str], table: dict[tuple[str, str], tuple[str, ...]]) -> tuple[bool, list[tuple[str, str, str]]]:
    """Parse whitespace-separated tokens (or a single-character token string)."""
    stripped = text.strip()
    tokens = stripped.split() if any(ch.isspace() for ch in stripped) else list(stripped)
    if tokens == [""]:
        tokens = []
    tokens.append(END)
    stack = [END, nonterminals[0]]
    trace: list[tuple[str, str, str]] = []
    limit = max(1000, (len(tokens) + 1) * (len(table) + 1) * 20)
    for _ in range(limit):
        top, lookahead = stack[-1], tokens[0]
        stack_text = " ".join(stack)
        input_text = " ".join(tokens)
        if top == END and lookahead == END:
            trace.append((stack_text, input_text, "accept"))
            return True, trace
        if top not in nonterminals:
            if top == lookahead:
                trace.append((stack_text, input_text, f"match {top}"))
                stack.pop()
                tokens.pop(0)
                continue
            trace.append((stack_text, input_text, f"error: expected {top}, found {lookahead}"))
            return False, trace
        rhs = table.get((top, lookahead))
        if rhs is None:
            trace.append((stack_text, input_text, f"error: no rule for ({top}, {lookahead})"))
            return False, trace
        rendered_rhs = " ".join(rhs) if rhs != (EPSILON,) else EPSILON
        trace.append((stack_text, input_text, f"{top} -> {rendered_rhs}"))
        stack.pop()
        if rhs != (EPSILON,):
            stack.extend(reversed(rhs))
    trace.append((" ".join(stack), " ".join(tokens), "error: parsing step limit exceeded"))
    return False, trace


def fmt_set(values: set[str], order: list[str]) -> str:
    return "{" + ", ".join([x for x in order if x in values]) + "}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute FIRST/FOLLOW, build an LL(1) table, and parse a token string.")
    parser.add_argument("grammar", help="path to grammar text file")
    parser.add_argument("--input", help="input token string; separate multi-character tokens with spaces")
    args = parser.parse_args()
    try:
        nonterminals, productions = read_grammar(args.grammar)
        first = compute_first(nonterminals, productions)
        follow = compute_follow(nonterminals, productions, first)
        table, conflicts = build_table(nonterminals, productions, first, follow)
        terminals = ordered_terminals(nonterminals, productions, follow)
        print("FIRST sets:")
        for nt in nonterminals:
            print(f"  FIRST({nt}) = {fmt_set(first[nt], terminals + [EPSILON])}")
        print("\nFOLLOW sets:")
        for nt in nonterminals:
            print(f"  FOLLOW({nt}) = {fmt_set(follow[nt], terminals + [EPSILON])}")
        print("\nPredictive parsing table:")
        print("  Nonterminal | " + " | ".join(terminals))
        print("  " + "-" * (14 + 4 * len(terminals)))
        for nt in nonterminals:
            cells = []
            for terminal in terminals:
                rhs = table.get((nt, terminal))
                cells.append((nt + " -> " + (" ".join(rhs) if rhs != (EPSILON,) else EPSILON)) if rhs else "")
            print(f"  {nt:<11} | " + " | ".join(cells))
        if conflicts:
            print("\nLL(1) check: NO, parsing-table conflicts found:")
            for nt, terminal, rules in conflicts:
                print(f"  M[{nt}, {terminal}]: " + " versus ".join(f"{nt} -> {' '.join(r)}" for r in rules))
        else:
            print("\nLL(1) check: YES, no parsing-table conflicts.")
        if args.input is not None:
            print(f"\nParsing input: {args.input if args.input else '(empty string)'}")
            accepted, trace = parse_input(args.input, nonterminals, table)
            print(f"{'STACK':<24} | {'INPUT':<24} | ACTION")
            print("-" * 76)
            for stack_text, input_text, action in trace:
                print(f"{stack_text:<24} | {input_text:<24} | {action}")
            print("\nResult: " + ("ACCEPTED" if accepted else "REJECTED"))
        return 0
    except (OSError, GrammarError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
