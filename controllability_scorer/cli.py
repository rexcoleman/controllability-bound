#!/usr/bin/env python3
"""CLI for controllability-scorer."""

import argparse
import json
import sys

from controllability_scorer.scorer import SystemSpec, score_system, rank_channels


def main():
    parser = argparse.ArgumentParser(
        description="Score system vulnerability using controllability-observability decomposition"
    )
    sub = parser.add_subparsers(dest="command")

    # Score from JSON
    p_score = sub.add_parser("score", help="Score a system from JSON specification")
    p_score.add_argument("spec_file", help="Path to JSON system spec")
    p_score.add_argument("--model", default="separate", choices=["separate", "product"])
    p_score.add_argument("--domain", help="Domain hint for weight selection")

    # Quick score
    p_quick = sub.add_parser("quick", help="Quick single-channel score")
    p_quick.add_argument("--name", default="channel", help="Channel name")
    p_quick.add_argument("-c", "--controllability", type=float, required=True)
    p_quick.add_argument("-d", "--observability", type=float, required=True)

    # Example
    sub.add_parser("example", help="Print example system spec JSON")

    args = parser.parse_args()

    if args.command == "score":
        with open(args.spec_file) as f:
            data = json.load(f)
        spec = SystemSpec(name=data.get("name", "system"), domain=args.domain or data.get("domain"))
        for ch in data.get("channels", []):
            spec.add_channel(ch["name"], ch["controllability"], ch["observability"],
                             ch.get("description", ""))
        result = score_system(spec, model=args.model)
        print(json.dumps(result, indent=2))

    elif args.command == "quick":
        spec = SystemSpec(name="quick_check")
        spec.add_channel(args.name, args.controllability, args.observability)
        result = score_system(spec)
        ch = result["channels"][0]
        print(f"Channel: {ch['name']}")
        print(f"  C={ch['C']}, D={ch['D']}")
        print(f"  Score: {ch['score']} ({ch['risk_level']})")
        print(f"  {result['recommendation']}")

    elif args.command == "example":
        example = {
            "name": "example-agent-system",
            "domain": "llm_agent",
            "channels": [
                {"name": "user_prompt", "controllability": 1.0, "observability": 1.0,
                 "description": "User input — fully attacker-controlled, fully logged"},
                {"name": "reasoning_chain", "controllability": 0.5, "observability": 0.0,
                 "description": "Agent internal reasoning — indirect control, not observable"},
                {"name": "tool_outputs", "controllability": 0.5, "observability": 0.5,
                 "description": "External tool responses — partial control, partial logging"},
            ]
        }
        print(json.dumps(example, indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
