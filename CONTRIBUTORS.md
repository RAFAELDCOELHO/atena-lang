# Contributors

## Rafael D. Coelho (@RAFAELDCOELHO)
**Language designer & project lead**

All architectural and pedagogical decisions in Atena — the grammar, the teaching philosophy, the error experience, and every design choice made during development:

- Language design: why `repeat N times` instead of `for`, why 1-indexed lists, why `ask` returns string, why floor division, why params-only function scope
- Pedagogical philosophy: the "bridge language" concept, the beginner-first error voice, the concept ladder curriculum
- Architecture: the four-phase transpiler design (Lexer → Parser → Semantic Analyzer → Generator), the collect-all-errors strategy, the `atena run` / `atena build` CLI split
- All 42 v1.0 requirements and the roadmap across 7 phases

## Claude Code (Anthropic)
**Implementation tool**

Used throughout development as the primary coding tool — similar to how engineers use GitHub Copilot or work with a development team. Claude Code wrote the implementation code under Rafael's direction and architectural decisions.

All design decisions, requirement approvals, code reviews, and pedagogical choices were made by Rafael. The `.planning/` directory documents this process in full, including every design discussion and decision rationale.
