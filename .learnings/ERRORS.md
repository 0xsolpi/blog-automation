# ERRORS

Self-improvement log for command failures, exceptions, and integration errors.

---

## 2026-03-06 (KST) — `rg` command unavailable in runtime
- What happened: Tried `rg -n "사장님" ...` and command failed (`rg: command not found`).
- Impact: Minor delay while switching search method.
- Do differently: Use `grep -RIn` as fallback immediately when `rg` is not installed.

