# unitus/recommendation/skill_matching.py

"""
Computes how well a set of a candidate's skills satisfies a set of required
skills, as a 0..1 score that gets blended into MatchScoreService's ranking
alongside embedding similarity (see ranker.py).

Why this exists: embedding similarity alone can't reliably enforce "meets
the minimum level". A profile listing "Python (Advanced)" and an ad
requiring "Python (min: Beginner)" read as semantically close either way,
so cosine similarity can't tell "comfortably qualified" apart from
"underqualified but topically similar". This module adds an explicit,
literal check on top of that.

SKILL_LEVEL_ORDER below matches skills/choices.py's MasteryLevel display
labels (Beginner/Intermediate/Advanced/Expert/Master). This assumes
ProjectRoleSkill.min_required_level is drawn from that same MasteryLevel
enum - if it turns out to use a separate choices class with different or
fewer tiers, this dict needs to represent that class's labels instead.
"""

SKILL_LEVEL_ORDER = {
    "Beginner": 1,
    "Intermediate": 2,
    "Advanced": 3,
    "Expert": 4,
    "Master": 5,
}

# Credit given when a candidate has the skill listed but hasn't reached the
# required level, rather than scoring that as a flat zero (they're not a
# non-match, just a partial one - e.g. Beginner Python against a role that
# wants Intermediate is closer to qualifying than not having Python at all).
PARTIAL_CREDIT_BELOW_LEVEL = 0.5


def _level_rank(display_label: str) -> int:
    return SKILL_LEVEL_ORDER.get(display_label, 0)


def score_against_requirements(candidate_skill_levels: dict, required_skills: list) -> float:
    """
    candidate_skill_levels: {skill_id: mastery_level_display_label}
        e.g. {14: "Advanced", 22: "Beginner"} - a user's own skills when
        scoring ads, or a candidate user's skills when scoring for a job ad.

    required_skills: [(skill_id, min_required_level_display_label), ...]
        e.g. [(14, "Intermediate"), (30, "Beginner")] - the role's required
        skills being matched against.

    Returns a 0..1 float: the average, across each required skill, of how
    well it's satisfied - 1.0 if the candidate has it at/above the required
    level, PARTIAL_CREDIT_BELOW_LEVEL if they have it but below level, 0.0
    if they don't have it at all.

    Returns 1.0 (neutral - don't penalize) when there's nothing to check
    against, so a role/profile with no listed skills doesn't tank every
    match purely for lack of data.
    """
    if not required_skills:
        return 1.0

    total = 0.0
    for skill_id, required_label in required_skills:
        candidate_label = candidate_skill_levels.get(skill_id)
        if candidate_label is None:
            total += 0.0
        elif _level_rank(candidate_label) >= _level_rank(required_label):
            total += 1.0
        else:
            total += PARTIAL_CREDIT_BELOW_LEVEL

    return total / len(required_skills)
