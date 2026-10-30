# FIRST and FOLLOW Set Calculator with LL(1) Parsing Table

Compiler Design Mini Project 5

**Student:** Arnab Mandal  
**Roll No:** 16900124128  
**Institution:** Academy of Technology

This project computes FIRST and FOLLOW sets for a context-free grammar, builds a predictive LL(1) parsing table, reports table conflicts, and can trace parsing of an input token sequence.

## Requirements

- Python 3.10 or newer
- No third-party packages

## Run

```bash
python3 first_follow_ll1.py grammar_ll1.txt --input "id + id * id"
python3 first_follow_ll1.py grammar_conflict.txt --input "a c"
python3 first_follow_ll1.py grammar_epsilon.txt --input "b"
```

## Grammar and input format

Use one production per line, `->` between the left and right sides, and `|` for alternatives. Separate grammar symbols with spaces. The first left-hand side is the start symbol. Write an empty production as `epsilon`, `eps`, `ε`, or `#`. Separate multi-character input tokens such as `id` with spaces; single-character terminal strings may be supplied without spaces.

## Files

- `first_follow_ll1.py`: FIRST/FOLLOW calculator, LL(1) table builder, and table-driven parser.
- `grammar_ll1.txt`: expression grammar with precedence and repetition.
- `grammar_conflict.txt`: intentionally conflicting grammar for demonstrating a non-LL(1) table.
- `grammar_epsilon.txt`: grammar with an epsilon production.
