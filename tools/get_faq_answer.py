"""
get_faq_answer — returns canned answers to common CVC / transfer questions.

The FAQ dict is hardcoded for v0.0. v0.1 hook: swap load_faq() body to
pull from a CMS or DynamoDB table without changing the function signature.
"""

from __future__ import annotations

# Each entry: list of keyword triggers → answer.
# The first trigger in each list is the canonical topic name.
_FAQ: list[dict] = [
    {
        "triggers": ["cvc", "california virtual campus", "what is cvc", "what is this", "what's cvc", "about cvc", "cvc.edu", "virtual campus"],
        "answer": (
            "CVC (California Virtual Campus) is an online marketplace run by the California Community College "
            "Chancellor's Office. It lets students at any California Community College (their 'home college') "
            "enroll in online courses offered by other CCCs (called 'teaching colleges'). "
            "This is useful when your home college doesn't offer a course you need, or a section at another "
            "college fits your schedule better. You pay your home college's fees, not the teaching college's."
        ),
    },
    {
        "triggers": ["enroll", "enrol", "how do i enroll", "how to register", "sign up", "registration", "how to enroll", "how do i sign up", "how to sign up", "register for", "how do i register"],
        "answer": (
            "To enroll in a CVC course: (1) Find a course you want here in the chatbot, then visit cvc.edu "
            "to complete enrollment. (2) You'll log in with your home college credentials (SSO). "
            "(3) You'll see two confirmation screens — read them carefully, they cover add/drop deadlines "
            "for the teaching college. (4) The course appears in your home college's student portal. "
            "Note: I can help you find the right course, but enrollment itself happens on cvc.edu."
        ),
    },
    {
        "triggers": ["transfer credit", "will this count", "does this transfer", "articulation", "assist", "will it count", "can i transfer", "count toward", "count for transfer", "apply to transfer", "tranfer", "transferable", "will this class count", "does it count"],
        "answer": (
            "I can show you which GE areas a course is tagged for (like CSU Breadth B2 or IGETC 5B), "
            "but I can't guarantee it will satisfy a specific requirement at your home college — "
            "articulation agreements vary by college and can change. "
            "To confirm: check assist.org for your specific home college + teaching college combination, "
            "or talk to your counselor before enrolling. Never rely on a chatbot alone for transfer planning."
        ),
    },
    {
        "triggers": ["prerequisite", "prereq", "prerequisites", "do i need", "requirement to take", "pre-req", "prereqs", "pre req", "what do i need to take", "required before", "need before", "needed to take"],
        "answer": (
            "Prerequisites vary by course. I can show you the course notes field, which sometimes lists "
            "prerequisites. For the official prerequisite policy, check the teaching college's catalog "
            "or contact their admissions office — prerequisite enforcement is handled by the teaching college, "
            "not your home college."
        ),
    },
    {
        "triggers": ["seats", "seat count", "how many seats", "is there space", "availability", "full", "waitlist", "is it full", "open seats", "spots left", "spots available", "spaces left", "class full", "still open"],
        "answer": (
            "The seat counts I show come from a recent data snapshot and may not reflect real-time availability. "
            "If a course shows seats available, there's a good chance it still has space — but to confirm, "
            "visit cvc.edu or contact the teaching college directly. "
            "I don't have access to live seat counts (that's a v0.1 feature)."
        ),
    },
    {
        "triggers": ["home college", "my college", "which college am i at", "what is home college"],
        "answer": (
            "Your 'home college' is the California Community College where you're currently enrolled and "
            "paying fees. When you take a course through CVC, you stay enrolled at your home college — "
            "you just take the course online at a 'teaching college.' Your home college handles your "
            "financial aid, fees, and transcript."
        ),
    },
    {
        "triggers": ["teaching college", "host college", "offering college", "what is teaching college"],
        "answer": (
            "The 'teaching college' is the California Community College that offers and runs the online course "
            "you're taking through CVC. They control the syllabus, instructor, grading, and add/drop deadlines. "
            "You pay your home college's fees, not the teaching college's — but you follow the teaching college's "
            "academic policies for that course."
        ),
    },
    {
        "triggers": ["fees", "cost", "tuition", "how much", "price", "how much does it cost", "how much is it", "do i pay", "who do i pay", "payment", "fee", "costs money"],
        "answer": (
            "You pay your home college's enrollment fees for CVC courses — not the teaching college's. "
            "California Community College fees are set by the state (around $46/unit for California residents). "
            "Financial aid you receive at your home college can typically be applied to CVC courses. "
            "Check with your home college's financial aid office to confirm."
        ),
    },
    {
        "triggers": ["async", "asynchronous", "online asynchronous", "no meeting time", "self-paced"],
        "answer": (
            "Asynchronous ('async') courses have no required meeting times — you complete coursework on your "
            "own schedule within weekly or module deadlines. Great for students with variable schedules. "
            "You still have firm deadlines; it's not truly self-paced. "
            "All courses in this chatbot are online; I can filter for async or synchronous if you have a preference."
        ),
    },
    {
        "triggers": ["sync", "synchronous", "online synchronous", "zoom", "live class", "meeting time"],
        "answer": (
            "Synchronous ('sync') courses have scheduled meeting times — usually via Zoom or a similar platform. "
            "You need to attend at the posted days/times. These offer more real-time interaction with instructors "
            "and classmates. Check the course start/end dates and meeting times before enrolling."
        ),
    },
    {
        "triggers": ["drop", "withdraw", "add drop deadline", "drop deadline", "refund", "how do i drop", "can i drop", "withdrawal", "unenroll", "un-enroll", "cancel enrollment", "drop the class", "last day to drop"],
        "answer": (
            "Add/drop deadlines are set by the teaching college, not your home college — and they may differ "
            "from what you're used to. Read the confirmation screens carefully during enrollment on cvc.edu. "
            "If you drop after the refund deadline, you may still owe fees. Contact the teaching college's "
            "admissions office if you have questions about their specific deadlines."
        ),
    },
    {
        "triggers": ["unit", "units", "credit", "credits", "how many units"],
        "answer": (
            "Course units (also called credits) indicate how much work a course involves. "
            "Most transfer GE courses are 3–4 units. I display unit counts for each course I recommend. "
            "Units from CVC courses transfer back to your home college and count toward your unit total."
        ),
    },
    {
        "triggers": ["eligible", "eligibility", "qualify", "can i use cvc", "who can enroll", "am i eligible", "requirements to enroll", "do i qualify", "can i sign up", "eligible for cvc"],
        "answer": (
            "To enroll through CVC Exchange you must: (1) Currently be enrolled at a California community college. "
            "(2) Be at least 18 years old. (3) Have a GPA of 2.0 or higher (or no GPA established yet — first term is fine). "
            "(4) Have no outstanding fees at your home college. (5) Have an in-state address on file. "
            "You're limited to 2 CVC courses per term (winter + spring count as one term). "
            "Note: dual-enrolled high school students and international/F-1 visa students are NOT eligible for CVC Exchange — "
            "they must apply directly via CCCApply. If a course has prerequisites, you'll need to upload a transcript "
            "and allow up to 3 business days for review (your spot is not reserved during this time). "
            "Questions? Email support@cvc.edu."
        ),
    },
    {
        "triggers": ["transcript", "transcripts", "my transcript", "where is my transcript", "get transcript", "grades transfer", "how do grades work", "how does transcript work", "send transcript", "teaching college transcript"],
        "answer": (
            "After the semester ends, the teaching college automatically sends an electronic transcript to your home college — "
            "this typically takes up to 3 weeks. If you need it sooner, request it directly from the teaching college. "
            "If no transcript arrives after 3 weeks, contact support@cvc.edu. "
            "CVC Exchange courses may appear as transfer credit on your home transcript; a counselor evaluation may be required. "
            "If you're transferring to a 4-year university, you must request transcripts directly from the teaching college — "
            "your Teaching College ID (found in your CVC Exchange profile at search.cvc.edu) is required and fees may apply."
        ),
    },
    {
        "triggers": ["financial aid", "fafsa", "pell grant", "aid", "promise grant", "ccpg", "ab540", "dream act", "veterans benefits", "gi bill", "zero textbook", "ztc", "textbook cost"],
        "answer": (
            "Financial aid can apply to CVC courses — here's how: "
            "After enrolling at cvc.edu, select 'Request to use Federal Financial Aid' on the confirmation page. "
            "Your home college evaluates eligibility; you need at least 6 units at your home college. "
            "Requesting aid does NOT guarantee it — you're still responsible for payment during review. "
            "California Promise Grant (CCPG): may cover CVC courses; re-apply through the teaching college via "
            "Exchange Profile > Class Schedule > Pay Now. "
            "AB540/Dream Act students: establish AB540 status at your home college first, then apply to the teaching college via CADAA. "
            "Veterans: your home college sends a Parent School Authorization Letter to the teaching college. "
            "Zero Textbook Cost (ZTC) courses have no required textbook purchases — I can note which courses carry this designation."
        ),
    },
    {
        "triggers": ["cybersecurity", "cyber security", "cyber program", "ict", "comptia", "cisco", "security certificate", "cybersecurity program", "network+", "security+"],
        "answer": (
            "CVC offers a Cybersecurity Certificate Program: 25 units across 8 courses, delivered over 35 weeks "
            "(8-week sequences with 1-week breaks), and students progress as a cohort. "
            "Cost: $46/unit × 25 units; Zero Textbook Cost and financial aid are available. "
            "Three home colleges participate: Cosumnes River College, Fresno City College, and Los Angeles Pierce College — "
            "you must register, get financial aid, and meet with a counselor at one of these. "
            "The certificate is stackable toward advanced ICT credentials and can transfer toward a bachelor's program. "
            "9 industry exams are offered (optional but encouraged): CompTIA A+, Network+, Security+, IT Fundamentals; "
            "Cisco CCENT, CCNA variants. Want help finding a cybersecurity course to get started?"
        ),
    },
    {
        "triggers": ["ineligible", "why can't i enroll", "why cant i enroll", "blocked from enrolling", "account hold", "hold on account", "inactive", "non-credit", "not eligible"],
        "answer": (
            "Common reasons CVC enrollment is blocked: account hold or outstanding fees at your home college, "
            "inactive status at your home college, no CCCApply application on file, non-credit student status, "
            "GPA below 2.0, under 18 years old, or the system can't locate your CCCID or Canvas account. "
            "Dual-enrolled high school students and F-1 visa holders are ineligible for the Exchange entirely. "
            "If none of these apply and you're still blocked, email support@cvc.edu."
        ),
    },
]


def load_faq() -> list[dict]:
    """
    Load FAQ entries. v0.0: returns hardcoded list.
    v0.1 hook: replace body with CMS/DynamoDB fetch; keep return type.
    """
    return _FAQ


def get_faq_answer(topic: str) -> dict:
    """
    Return a plain-language answer to a common transfer/CVC question.

    Args:
        topic: A question or topic string (e.g. "how do I enroll?",
               "what is IGETC?", "will this count for transfer?").

    Returns:
        dict with keys:
          - matched (bool): whether a relevant FAQ entry was found
          - answer (str): the answer text (or a fallback message)
          - topic (str): normalized topic that was matched
    """
    q = topic.strip().lower()
    faq = load_faq()

    for entry in faq:
        if any(trigger in q for trigger in entry["triggers"]):
            return {
                "matched": True,
                "topic": entry["triggers"][0],
                "answer": entry["answer"],
            }

    return {
        "matched": False,
        "topic": topic,
        "answer": (
            f"I don't have a pre-written answer for '{topic}', but I'm happy to help. "
            "I can help you find courses, explain GE area requirements (like IGETC or CSU Breadth), "
            "or answer questions about how CVC works. What would you like to know?"
        ),
    }
