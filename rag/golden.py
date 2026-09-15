"""Golden questions: the acceptance set for retrieval.

These are the questions the demo is judged on, written down so that "retrieval
still works" is a command rather than an opinion. Each one names the document,
the page it must come back with, and a phrase that must appear in the retrieved
text. The out-of-scope questions exist to prove the corpus does NOT contain an
answer, which is what makes the V1 refusal behaviour honest rather than lucky.

Page numbers refer to the generated sample PDFs in sample_docs/. Regenerating
those documents from changed content can move a page — if it does, fix the
expectation here deliberately rather than loosening the check.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenQuestion:
    question: str
    expect_source: str | None = None
    expect_pages: tuple[int, ...] = ()
    expect_phrases: tuple[str, ...] = ()
    expect_section_prefix: str | None = None
    out_of_scope: bool = False
    note: str = ""


LOGISTICS = "Global_Logistics_Operating_Handbook.pdf"
HR = "Employee_Handbook_2026.pdf"

GOLDEN_QUESTIONS: list[GoldenQuestion] = [
    GoldenQuestion(
        question=(
            "What happens if a freight carrier reports temperature abuse on "
            "perishable cargo over the weekend?"
        ),
        expect_source=LOGISTICS,
        expect_pages=(4,),
        expect_phrases=("within two hours", "CC-12"),
        expect_section_prefix="4.2",
        note="The 60-second demo question. If this one regresses, the demo is dead.",
    ),
    GoldenQuestion(
        question="What is our refund window for international customers?",
        expect_source=LOGISTICS,
        expect_pages=(6,),
        expect_phrases=("thirty calendar days",),
        expect_section_prefix="5.3",
    ),
    GoldenQuestion(
        question="What are the dental insurance co-pay limits?",
        expect_source=HR,
        expect_pages=(4,),
        expect_phrases=("co-pay", "six hundred euro"),
        expect_section_prefix="4.2",
    ),
    GoldenQuestion(
        question="How much notice do I need to give before parental leave?",
        expect_source=HR,
        expect_pages=(5,),
        expect_phrases=("eight weeks",),
        expect_section_prefix="5.3",
    ),
    GoldenQuestion(
        question="When is a carrier suspended from new bookings for poor OTIF?",
        expect_source=LOGISTICS,
        expect_pages=(6,),
        expect_phrases=("88 per cent",),
        expect_section_prefix="5.1",
    ),
    GoldenQuestion(
        question="What is the deadline for submitting an expense claim?",
        expect_source=HR,
        expect_pages=(6,),
        expect_phrases=("thirty days", "receipts"),
        expect_section_prefix="6.3",
    ),
    GoldenQuestion(
        question="Who can authorise the release of temperature-deviated cargo?",
        expect_source=LOGISTICS,
        expect_pages=(2, 4, 5),
        expect_phrases=("quality lead",),
        note="Answer is spread across three pages — any of them is a good hit.",
    ),
    GoldenQuestion(
        question="Who won the 2022 World Cup?",
        out_of_scope=True,
        note="Must produce a clean refusal in V1, never a guess.",
    ),
    GoldenQuestion(
        question="What is the share price forecast for next quarter?",
        out_of_scope=True,
    ),
]

IN_SCOPE = [q for q in GOLDEN_QUESTIONS if not q.out_of_scope]
OUT_OF_SCOPE = [q for q in GOLDEN_QUESTIONS if q.out_of_scope]
