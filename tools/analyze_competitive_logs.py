import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re


ACTION_RE = re.compile(
    r"Competitive action: kind=(?P<kind>\w+) \| move=(?P<move>.*?) "
    r"\| switch=(?P<switch>.*?) \| value=(?P<value>-?(?:inf|\d+(?:\.\d+)?)) "
    r"\| reason=(?P<reason>.*)"
)
RANK_RE = re.compile(
    r"\s+(?P<kind>\w+): target=(?P<target>.*?) \| "
    r"value=(?P<value>-?(?:inf|\d+(?:\.\d+)?)) \| reason=(?P<reason>.*)"
)
RESULT_RE = re.compile(r"Player (?P<bot>SmartBot|CompetitiveBot) victories: (?P<wins>\d+)")
PLAN_RE = re.compile(
    r"Competitive plan: .*phase=(?P<phase>\w+) .*matchup=(?P<matchup>-?\d+(?:\.\d+)?) "
    r"\| threat=(?P<threat>-?\d+(?:\.\d+)?) .*best_attack_damage=(?P<damage>-?\d+(?:\.\d+)?) "
    r"\| opponent_hp=(?P<hp>-?\d+(?:\.\d+)?) .*expected_switch=(?P<expected>\w+) "
    r"\| expected_switch_reason=(?P<expected_reason>.*?)(?: \| active_first_turn=(?P<active_first_turn>\w+))?$"
)

FIRST_TURN_ONLY_MOVES = {"fakeout", "firstimpression"}


def parse_value(raw: str) -> float:
    if raw == "-inf":
        return float("-inf")
    if raw == "inf":
        return float("inf")
    return float(raw)


@dataclass
class ActionBlock:
    line_no: int
    kind: str
    target: str
    value: float
    reason: str
    plan: dict
    ranking: list


def normalize_target(raw: str) -> str:
    if raw in {"None", ""}:
        return raw
    return raw.split(" ", 1)[0]


def parse_log(path: Path) -> tuple[list[ActionBlock], dict[str, int]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    results = {}
    blocks = []
    current_plan = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if plan_match := PLAN_RE.match(line):
            current_plan = plan_match.groupdict()
        elif action_match := ACTION_RE.match(line):
            action = action_match.groupdict()
            target = action["move"] if action["move"] != "None" else action["switch"]
            ranking = []
            j = i + 1
            while j < len(lines):
                if lines[j].startswith("Competitive action ranking: no legal actions"):
                    break
                rank_match = RANK_RE.match(lines[j])
                if rank_match:
                    item = rank_match.groupdict()
                    item["value"] = parse_value(item["value"])
                    ranking.append(item)
                elif lines[j].startswith("Competitive action ranking:"):
                    pass
                else:
                    if ranking:
                        break
                j += 1
            blocks.append(
                ActionBlock(
                    line_no=i + 1,
                    kind=action["kind"],
                    target=normalize_target(target),
                    value=parse_value(action["value"]),
                    reason=action["reason"],
                    plan=current_plan.copy(),
                    ranking=ranking,
                )
            )
            i = j - 1
        elif result_match := RESULT_RE.match(line):
            results[result_match.group("bot")] = int(result_match.group("wins"))
        i += 1
    return blocks, results


def analyze(blocks: list[ActionBlock], results: dict[str, int]) -> str:
    selected_moves = Counter()
    selected_reasons = Counter()
    large_gaps = []
    selected_not_top = []
    negative_selected_positive_top = []
    emergency_attacks = []
    expected_switch_attacks = []
    low_value_actions = []
    illegal_first_turn_actions = []
    illegal_first_turn_ranks = []

    for block in blocks:
        selected_moves[(block.kind, block.target)] += 1
        selected_reasons[block.reason] += 1
        target_id = block.target.lower()

        if block.ranking:
            top = block.ranking[0]
            gap = top["value"] - block.value
            if gap > 0.01:
                selected_not_top.append((gap, block, top))
            if gap > 18.5 and "override_floor" not in block.reason:
                large_gaps.append((gap, block, top))
            if block.value < 0 and top["value"] > 0:
                negative_selected_positive_top.append((gap, block, top))
            if block.plan.get("active_first_turn") == "False":
                for item in block.ranking:
                    ranked_target = normalize_target(item["target"]).lower()
                    if ranked_target in FIRST_TURN_ONLY_MOVES and item["value"] != float("-inf"):
                        illegal_first_turn_ranks.append((block, item))

        if block.reason.startswith("emergency") and block.kind == "attack":
            emergency_attacks.append(block)
        if (
            block.kind == "attack"
            and target_id in FIRST_TURN_ONLY_MOVES
            and block.plan.get("active_first_turn") == "False"
        ):
            illegal_first_turn_actions.append(block)
        if (
            block.kind == "attack"
            and block.plan.get("expected") == "True"
            and block.plan.get("expected_reason") not in {"near_ko_pressure", "low_hp_and_attack_pressure"}
        ):
            expected_switch_attacks.append(block)
        if block.value < 10:
            low_value_actions.append(block)

    lines = []
    if results:
        smart = results.get("SmartBot", 0)
        competitive = results.get("CompetitiveBot", 0)
        total = smart + competitive
        lines.append(f"Results: SmartBot={smart}, CompetitiveBot={competitive}, total={total}")
    lines.append(f"Competitive actions parsed: {len(blocks)}")
    lines.append("")
    lines.append("Top selected actions:")
    for (kind, target), count in selected_moves.most_common(12):
        lines.append(f"  {count:>4}  {kind:<12} {target}")
    lines.append("")
    lines.append("Top reasons:")
    for reason, count in selected_reasons.most_common(12):
        lines.append(f"  {count:>4}  {reason}")
    lines.append("")
    lines.append(f"Large selected-vs-top gaps (>18.5): {len(large_gaps)}")
    for gap, block, top in sorted(large_gaps, reverse=True, key=lambda item: item[0])[:12]:
        lines.append(
            f"  line {block.line_no}: selected {block.kind}/{block.target}={block.value:.2f} "
            f"vs top {top['kind']}/{normalize_target(top['target'])}={top['value']:.2f} "
            f"gap={gap:.2f} reason={block.reason}"
        )
    lines.append("")
    lines.append(f"Selected was not top-ranked: {len(selected_not_top)}")
    for gap, block, top in sorted(selected_not_top, reverse=True, key=lambda item: item[0])[:12]:
        lines.append(
            f"  line {block.line_no}: selected {block.kind}/{block.target}={block.value:.2f} "
            f"vs top {top['kind']}/{normalize_target(top['target'])}={top['value']:.2f} "
            f"gap={gap:.2f} reason={block.reason}"
        )
    lines.append("")
    lines.append(
        f"Negative selected while top-ranked action was positive: {len(negative_selected_positive_top)}"
    )
    for gap, block, top in sorted(
        negative_selected_positive_top,
        reverse=True,
        key=lambda item: item[0],
    )[:12]:
        lines.append(
            f"  line {block.line_no}: selected {block.kind}/{block.target}={block.value:.2f} "
            f"vs top {top['kind']}/{normalize_target(top['target'])}={top['value']:.2f} "
            f"gap={gap:.2f} reason={block.reason}"
        )
    lines.append("")
    lines.append(f"Emergency attacks: {len(emergency_attacks)}")
    for block in emergency_attacks[:12]:
        lines.append(
            f"  line {block.line_no}: {block.target} value={block.value:.2f} "
            f"threat={block.plan.get('threat')} hp={block.plan.get('hp')} reason={block.reason}"
        )
    lines.append("")
    lines.append(f"Attacks into expected bad-matchup switches: {len(expected_switch_attacks)}")
    for block in expected_switch_attacks[:12]:
        lines.append(
            f"  line {block.line_no}: {block.target} value={block.value:.2f} "
            f"expected={block.plan.get('expected_reason')} reason={block.reason}"
        )
    lines.append("")
    lines.append(f"Very low-value selected actions (<10): {len(low_value_actions)}")
    for block in low_value_actions[:12]:
        lines.append(
            f"  line {block.line_no}: {block.kind}/{block.target}={block.value:.2f} "
            f"reason={block.reason}"
        )
    lines.append("")
    lines.append(
        f"First-turn-only moves selected after first active turn: {len(illegal_first_turn_actions)}"
    )
    for block in illegal_first_turn_actions[:12]:
        lines.append(
            f"  line {block.line_no}: {block.target} value={block.value:.2f} "
            f"reason={block.reason}"
        )
    lines.append(
        f"First-turn-only moves ranked finite after first active turn: {len(illegal_first_turn_ranks)}"
    )
    for block, item in illegal_first_turn_ranks[:12]:
        lines.append(
            f"  line {block.line_no}: ranked {normalize_target(item['target'])}="
            f"{item['value']:.2f} during selected {block.kind}/{block.target}"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("log", type=Path)
    args = parser.parse_args()
    blocks, results = parse_log(args.log)
    print(analyze(blocks, results))


if __name__ == "__main__":
    main()
