"""Sheet matrices: classical T-accounts + process-style Sơ đồ chữ T."""

from __future__ import annotations

from typing import Any

from app.services.t_accounts import PROCESS_CYCLE_ACCOUNTS


def _account_lookup(build: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {a["account"]: a for a in build.get("accounts") or []}


def _turnover(acct: dict[str, Any]) -> float:
    return float(acct.get("debitTotal") or 0) + float(acct.get("creditTotal") or 0)


def classical_t_account_rows(build: dict[str, Any], *, max_lines_per_side: int = 40) -> list[list[Any]]:
    """Rows for tab T-accounts: Nợ | TK | Có blocks."""
    rows: list[list[Any]] = [
        [f"T-accounts ({build.get('circular') or 'TT200'})"],
        [
            f"Entries={build.get('entryCount')}",
            f"Accounts={build.get('accountCount')}",
            f"Total Debit={build.get('totalDebit')}",
            f"Total Credit={build.get('totalCredit')}",
            "Balanced" if build.get("balanced") else "UNBALANCED",
        ],
        [],
        ["Nợ (Debit)", "Diễn giải Nợ", "Tài khoản", "Diễn giải Có", "Có (Credit)"],
    ]
    for acct in build.get("accounts") or []:
        code = acct["account"]
        rows.append([])
        rows.append([f"TK {code}", "", f"TK {code}", "", f"TK {code}"])
        rows.append(
            [
                acct.get("debitTotal"),
                "Tổng Nợ",
                f"Net={acct.get('net')}",
                "Tổng Có",
                acct.get("creditTotal"),
            ]
        )
        debits = list(acct.get("debits") or [])[:max_lines_per_side]
        credits = list(acct.get("credits") or [])[:max_lines_per_side]
        n = max(len(debits), len(credits))
        for i in range(n):
            d = debits[i] if i < len(debits) else {}
            c = credits[i] if i < len(credits) else {}
            rows.append(
                [
                    d.get("amount") if d else "",
                    (d.get("description") or d.get("counterAccount") or "") if d else "",
                    "",
                    (c.get("description") or c.get("counterAccount") or "") if c else "",
                    c.get("amount") if c else "",
                ]
            )
        if len(acct.get("debits") or []) > max_lines_per_side or len(acct.get("credits") or []) > max_lines_per_side:
            rows.append(["…", "truncated", "", "truncated", "…"])
    return rows


def _flow_amount(flows: list[dict[str, Any]], debit: str, credit: str) -> float:
    for f in flows:
        if str(f.get("debit")) == debit and str(f.get("credit")) == credit:
            return float(f.get("amount") or 0)
    # prefix match (156 vs 1561)
    total = 0.0
    for f in flows:
        d, c = str(f.get("debit") or ""), str(f.get("credit") or "")
        if (d == debit or d.startswith(debit)) and (c == credit or c.startswith(credit)):
            total += float(f.get("amount") or 0)
    return total


def process_diagram_rows(build: dict[str, Any]) -> list[list[Any]]:
    """
    Template-inspired Sơ đồ chữ T for inventory/COGS cycle.
    Amounts come only from posted aggregates — never invented.
    """
    lookup = _account_lookup(build)
    flows = build.get("topFlows") or []
    # Expand flows from full account pairs if topFlows truncated — rebuild from accounts
    if not flows:
        flows = []

    year_hint = ""
    rows: list[list[Any]] = [
        [year_hint or f"Sơ đồ chữ T — {build.get('circular')}"],
        ["Amounts from nhật ký chung postings (deterministic). Narrative labels are template."],
        [],
    ]

    # Pick cycle accounts present with material turnover
    present = []
    for code in PROCESS_CYCLE_ACCOUNTS:
        matches = [a for a in (build.get("accounts") or []) if str(a["account"]).startswith(code)]
        if not matches:
            continue
        best = max(matches, key=_turnover)
        if _turnover(best) > 0:
            present.append(best["account"])

    rows.append(["Tài khoản trong chu kỳ vật tư / giá vốn:"] + present)
    rows.append([])

    # Layout blocks similar to India Gate (columns A–R style compact grid)
    def amt(d: str, c: str) -> Any:
        v = _flow_amount(flows, d, c)
        # also try any account starting with prefixes
        if v:
            return v
        for a in build.get("accounts") or []:
            pass
        # scan all pair from rebuild
        return v if v else ""

    # Rebuild pair map from accounts for better coverage
    pair_map: dict[tuple[str, str], float] = {}
    for a in build.get("accounts") or []:
        for line in a.get("debits") or []:
            counter = str(line.get("counterAccount") or "")
            key = (a["account"], counter)
            # wait: debit side of account a means counter is credit account
            key = (a["account"], counter)
            pair_map[key] = pair_map.get(key, 0.0) + float(line.get("amount") or 0)

    def flow(debit_prefix: str, credit_prefix: str) -> float:
        total = 0.0
        for (d, c), v in pair_map.items():
            if d.startswith(debit_prefix) and c.startswith(credit_prefix):
                total += v
        return round(total, 2) if total else 0.0

    # Movement catalog (template narrative)
    movements = [
        ("(1)", "Mua hàng hóa / NVL nhập kho", "156|152", "331", True),
        ("(2)", "Mua nguyên vật liệu", "152", "331", True),
        ("(3)", "Xuất / bán hàng (giá vốn)", "632", "156", True),
        ("(4)", "Nghiệm thu NVL vào sản xuất", "154|611", "152", True),
        ("(5)", "Kết chuyển NVL sử dụng", "154|611", "152", False),
        ("(6)", "Kiểm kê tồn NVL", "152", "154|611", False),
        ("(7)", "Xuất kho đầu kỳ", "154|611", "152", False),
        ("(8)", "Vật dụng nhỏ dùng ngay", "642|641|632", "152|153", False),
        ("(9)", "Vật dụng lớn / CCDC", "242", "152|153|331", False),
        ("(10)", "Phân bổ CCDC", "642|641", "242", False),
        ("(11)", "Kết chuyển giá vốn", "911", "632", True),
    ]

    rows.append(["STT", "Diễn giải bút toán", "Nợ", "Có", "Giá trị (từ sổ)"])
    for stt, label, debit_spec, credit_spec, _required in movements:
        best = 0.0
        best_d, best_c = "", ""
        for d_part in debit_spec.split("|"):
            for c_part in credit_spec.split("|"):
                v = flow(d_part, c_part)
                if v > best:
                    best, best_d, best_c = v, d_part, c_part
        rows.append([stt, label, best_d or debit_spec, best_c or credit_spec, best if best else ""])

    rows.append([])
    rows.append(["Số dư / phát sinh theo TK (chu kỳ)"])
    rows.append(["TK", "Tổng Nợ", "Tổng Có", "Net"])
    for code in present:
        a = lookup.get(code) or next(
            (x for x in (build.get("accounts") or []) if str(x["account"]).startswith(code[:3])),
            None,
        )
        if not a:
            continue
        rows.append([a["account"], a.get("debitTotal"), a.get("creditTotal"), a.get("net")])

    rows.append([])
    rows.append(
        [
            "Ghi chú",
            "Layout inspired by sample Sơ đồ chữ T; not a pixel clone. "
            "Empty Giá trị means no matching nhật ký flow for that narrative.",
        ]
    )
    return rows


def workbook_matrices(build: dict[str, Any]) -> dict[str, list[list[Any]]]:
    return {
        "T-accounts": classical_t_account_rows(build),
        "Sơ đồ chữ T": process_diagram_rows(build),
    }
