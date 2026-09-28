"""Answer the analysis questions using the Applicant SQLAlchemy model."""
from sqlalchemy import func, or_, select

from src.models import Applicant, create_session_factory

A = Applicant


def original_four_universities():
    return or_(
        A.program.ilike("%Georgetown University%"),
        A.program.ilike("%Massachusetts Institute of Technology%"),
        A.program.ilike("%, MIT%"),
        A.program.ilike("%Stanford University%"),
        A.program.ilike("%Carnegie Mellon University%"),
    )


def llm_four_universities():
    return or_(
        A.llm_generated_university.ilike("%Georgetown University%"),
        A.llm_generated_university.ilike("%Massachusetts Institute of Technology%"),
        A.llm_generated_university.ilike("MIT"),
        A.llm_generated_university.ilike("%Stanford University%"),
        A.llm_generated_university.ilike("%Carnegie Mellon University%"),
    )


def run_analyses(session):
    """Calculate Q1 through Q11 from the existing applicants table."""
    result = {}


    result["q1"] = session.scalar(
        select(func.count())
        .select_from(A)
        .where(A.term.ilike("Fall 2026"))
    )


    result["q2"] = session.scalar(
        select(
            100.0
            * func.count().filter(
                A.us_or_international.ilike("International")
            )
            / func.nullif(func.count(), 0)
        ).where(
            A.us_or_international.is_not(None),
            func.trim(A.us_or_international) != "",
        )
    )


    result["q3"] = session.execute(
        select(
            func.avg(A.gpa),
            func.avg(A.gre),
            func.avg(A.gre_v),
            func.avg(A.gre_aw),
        )
    ).one()


    result["q4"] = session.scalar(
        select(func.avg(A.gpa)).where(
            A.term.ilike("Fall 2026"),
            A.us_or_international.ilike("American"),
        )
    )


    result["q5"] = session.scalar(
        select(
            100.0
            * func.count().filter(A.status.ilike("Accepted%"))
            / func.nullif(func.count(), 0)
        ).where(A.term.ilike("Fall 2025"))
    )


    result["q6"] = session.scalar(
        select(func.avg(A.gpa)).where(
            A.term.ilike("Fall 2026"),
            A.status.ilike("Accepted%"),
        )
    )


    result["q7"] = session.scalar(
        select(func.count())
        .select_from(A)
        .where(
            or_(
                A.program.ilike("%Johns Hopkins%"),
                A.program.ilike("%JHU%"),
            ),
            A.program.ilike("%Computer Science%"),
            A.degree.ilike("Masters"),
        )
    )


    common = (
        A.degree.ilike("PhD"),
        A.term.ilike("Fall 2026"),
        A.status.ilike("Accepted%"),
    )


    result["q8"] = session.scalar(
        select(func.count())
        .select_from(A)
        .where(
            original_four_universities(),
            A.program.ilike("%Computer Science%"),
            *common,
        )
    )


    result["q9"] = session.scalar(
        select(func.count())
        .select_from(A)
        .where(
            llm_four_universities(),
            A.llm_generated_program.ilike("%Computer Science%"),
            *common,
        )
    )


    masters_count, phd_count, total = session.execute(
        select(
            func.count().filter(A.degree.ilike("Masters")),
            func.count().filter(A.degree.ilike("PhD")),
            func.count(),
        ).where(
            A.term.ilike("Fall 2026"),
            A.program.ilike("%Computer Science%"),
        )
    ).one()

    result["q10_total"] = total
    result["q10"] = []

    if total:
        result["q10"] = [
            ("Masters", masters_count, 100.0 * masters_count / total),
            ("PhD", phd_count, 100.0 * phd_count / total),
        ]


    result["q11"] = session.execute(
        select(
            func.count(A.gpa).filter(A.status.ilike("Accepted%")),
            func.avg(A.gpa).filter(A.status.ilike("Accepted%")),
            func.count(A.gpa).filter(A.status.ilike("Rejected%")),
            func.avg(A.gpa).filter(A.status.ilike("Rejected%")),
        ).where(
            A.term.ilike("Fall 2026"),
            A.program.ilike("%Computer Science%"),
            A.degree.ilike("Masters"),
        )
    ).one()

    return result


def display(result):
    """Print the analysis answers to the console."""
    def average(number):
        return f"{number:.2f}" if number is not None else "no reported values"


    def percent(number):
        return f"{number:.2f}%" if number is not None else "no reported values"

    print(f"Fall 2026 applicant count: {result['q1']}")
    print(f"Percent international: {percent(result['q2'])}")

    labels = (
        "Average GPA",
        "Average GRE Quantitative",
        "Average GRE Verbal",
        "Average GRE Analytical Writing",
    )
    for label, number in zip(labels, result["q3"]):
        print(f"{label}: {average(number)}")

    print(f"Average GPA of Americans for Fall 2026: {average(result['q4'])}")
    print(f"Fall 2025 acceptance percentage: {percent(result['q5'])}")
    print(f"Average GPA of accepted applicants in Fall 2026: {average(result['q6'])}")
    print(f"Johns Hopkins Computer Science master's entries: {result['q7']}")
    print(
        "Accepted Fall 2026 Computer Science PhD entries "
        f"at four universities: {result['q8']}"
    )
    print(f"Original-field count: {result['q8']}")
    print(f"LLM-field count: {result['q9']}")
    print(f"Difference: {result['q9'] - result['q8']:+d}")

    for degree, count, percentage in result["q10"]:
        print(
            f"{degree}: {count} entries "
            f"({percentage:.2f}% of Fall 2026 CS entries)"
        )

    accepted_count, accepted_avg, rejected_count, rejected_avg = result["q11"]
    print(
        f"Accepted: {accepted_count} reported GPAs, "
        f"average {average(accepted_avg)}"
    )
    print(
        f"Rejected: {rejected_count} reported GPAs, "
        f"average {average(rejected_avg)}"
    )

    if accepted_avg is not None and rejected_avg is not None:
        print(f"Average GPA difference: {accepted_avg - rejected_avg:+.2f}")
    else:
        print("Average GPA difference: unavailable")


if __name__ == "__main__":
    Session = create_session_factory()

    with Session() as session:
        display(run_analyses(session))
