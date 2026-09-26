"""Deterministic double-entry posting to classical T-accounts."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional


class PostError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


# Material inventory / COGS cycle accounts for process diagram (TT 200 style)
PROCESS_CYCLE_ACCOUNTS = ("152", "154", "156", "242", "331", "611", "632", "511", "1331", "33311")


def build_t_accounts(
    entries: list[dict[str, Any]],
    *,
    circular: str = "TT200",
    account_filter: Optional[list[str]] = None,
) -> dict[str, Any]:
    if not entries:
        raise PostError("NO_ENTRIES", "entries list is empty")
    circ = (circular or "TT200").strip().upper().replace(" ", "")
    if circ not in ("TT200", "TT133", "200", "133"):
        raise PostError("INVALID_CIRCULAR", "circular must be TT200 or TT133")
    if circ in ("200", "133"):
        circ = f"TT{circ}"

    filt = None
    if account_filter:
        filt = {str(a).strip() for a in account_filter if str(a).strip()}

    accounts: dict[str, dict[str, Any]] = {}
    total_debit = 0.0
    total_credit = 0.0
    posted_lines = 0
    skipped = 0
    pair_flows: dict[tuple[str, str], float] = defaultdict(float)

    for e in entries:
        debit = str(e.get("debit_account") or "").strip()
        credit = str(e.get("credit_account") or "").strip()
        # Optional one-sided / asymmetric amounts for fail-closed audit paths
        debit_amt_raw = e.get("debit_amount", e.get("amount"))
        credit_amt_raw = e.get("credit_amount", e.get("amount"))
        try:
            debit_amt = float(debit_amt_raw or 0)
            credit_amt = float(credit_amt_raw or 0)
        except (TypeError, ValueError):
            skipped += 1
            continue
        if (not debit and not credit) or (debit_amt <= 0 and credit_amt <= 0):
            skipped += 1
            continue
        if filt:
            if debit and debit not in filt and credit and credit not in filt:
                skipped += 1
                continue
            if debit and debit not in filt and not credit:
                skipped += 1
                continue
            if credit and credit not in filt and not debit:
                skipped += 1
                continue

        # Classical pair: both sides present with shared amount
        if debit and credit and debit_amt > 0 and credit_amt > 0:
            amount = debit_amt if abs(debit_amt - credit_amt) < 0.01 else None
            if amount is None:
                # Asymmetric amounts on a pair line → books imbalance
                total_debit += debit_amt
                total_credit += credit_amt
                posted_lines += 1
                continue
            total_debit += amount
            total_credit += amount
            pair_flows[(debit, credit)] += amount
            posted_lines += 1
            for side, acct, amt in (("debit", debit, amount), ("credit", credit, amount)):
                bucket = accounts.setdefault(
                    acct,
                    {
                        "account": acct,
                        "debits": [],
                        "credits": [],
                        "debitTotal": 0.0,
                        "creditTotal": 0.0,
                        "net": 0.0,
                    },
                )
                line = {
                    "line": e.get("line"),
                    "date": e.get("date"),
                    "amount": amt,
                    "description": e.get("description") or "",
                    "voucher": e.get("voucher") or "",
                    "counterAccount": credit if side == "debit" else debit,
                }
                if side == "debit":
                    bucket["debits"].append(line)
                    bucket["debitTotal"] += amt
                else:
                    bucket["credits"].append(line)
                    bucket["creditTotal"] += amt
            continue

        # One-sided line (malformed journal) — count toward imbalance
        if debit and debit_amt > 0:
            total_debit += debit_amt
            posted_lines += 1
            bucket = accounts.setdefault(
                debit,
                {
                    "account": debit,
                    "debits": [],
                    "credits": [],
                    "debitTotal": 0.0,
                    "creditTotal": 0.0,
                    "net": 0.0,
                },
            )
            bucket["debits"].append(
                {
                    "line": e.get("line"),
                    "date": e.get("date"),
                    "amount": debit_amt,
                    "description": e.get("description") or "",
                    "voucher": e.get("voucher") or "",
                    "counterAccount": credit,
                }
            )
            bucket["debitTotal"] += debit_amt
        elif credit and credit_amt > 0:
            total_credit += credit_amt
            posted_lines += 1
            bucket = accounts.setdefault(
                credit,
                {
                    "account": credit,
                    "debits": [],
                    "credits": [],
                    "debitTotal": 0.0,
                    "creditTotal": 0.0,
                    "net": 0.0,
                },
            )
            bucket["credits"].append(
                {
                    "line": e.get("line"),
                    "date": e.get("date"),
                    "amount": credit_amt,
                    "description": e.get("description") or "",
                    "voucher": e.get("voucher") or "",
                    "counterAccount": debit,
                }
            )
            bucket["creditTotal"] += credit_amt
        else:
            skipped += 1

    if posted_lines == 0:
        raise PostError(
            "NO_POSTED_ENTRIES",
            f"No valid journal lines posted (skipped={skipped}, input={len(entries)})",
        )

    for b in accounts.values():
        b["net"] = round(b["debitTotal"] - b["creditTotal"], 2)
        b["debitTotal"] = round(b["debitTotal"], 2)
        b["creditTotal"] = round(b["creditTotal"], 2)

    imbalance = abs(total_debit - total_credit)
    if imbalance > 0.01:
        raise PostError(
            "BOOKS_UNBALANCED",
            f"Journal does not balance: debit={total_debit:.2f} credit={total_credit:.2f}",
        )

    ordered = sorted(accounts.values(), key=lambda a: a["account"])
    top_pairs = sorted(
        (
            {"debit": d, "credit": c, "amount": round(v, 2)}
            for (d, c), v in pair_flows.items()
        ),
        key=lambda x: -x["amount"],
    )[:40]

    return {
        "circular": circ,
        "entryCount": len(entries),
        "postedCount": posted_lines,
        "skippedCount": skipped,
        "accountCount": len(ordered),
        "totalDebit": round(total_debit, 2),
        "totalCredit": round(total_credit, 2),
        "balanced": True,
        "accounts": ordered,
        "topFlows": top_pairs,
    }
