"""
CLI entry point for the Insurance Data Platform.

Runs the full data pipeline: generate → resolve entities → build graph →
compute graph features → run offline pipeline → validate.

Usage:
  python main.py --generate-data
  python main.py --resolve-entities
  python main.py --reset-graph
  python main.py --build-graph
  python main.py --compute-graph-features
  python main.py --run-offline-pipeline
  python main.py --validate-data
  python main.py --drift-check
"""

import argparse
import json
import os
from pathlib import Path

from dotenv import load_dotenv

from data.synthetic.generator import generate_data
from entities import resolve_vehicles, resolve_persons, resolve_addresses, resolve_phones, resolve_policies
from graph.graph_builder import build_graph_from_claims, clear_graph
from graph.graph_features import compute_graph_features
from data.synthetic.validator import validate_data
from config import CLAIMS_OUTPUT, OFFLINE_FEATURES_DIR, QUOTES_OUTPUT, RISK_MODELS_DIR

load_dotenv()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Insurance Data Platform")
    parser.add_argument("--generate-data", action="store_true",
                        help="Generate synthetic quote and claim datasets")
    parser.add_argument("--resolve-entities", action="store_true",
                        help="Resolve and normalize entity data (vehicles, persons, addresses, phones, policies)")
    parser.add_argument("--reset-graph", action="store_true",
                        help="Delete all graph nodes/relationships and drop all constraints")
    parser.add_argument("--build-graph", action="store_true",
                        help="Build graph from claims data in Neo4j")
    parser.add_argument("--compute-graph-features", action="store_true",
                        help="Compute graph features and update claims data")
    parser.add_argument("--graph-seed-cutoff", metavar="YYYY-MM-DD",
                        help="ISO date: seed BFS hop distances only from fraud claims before this date")
    parser.add_argument("--run-offline-pipeline", action="store_true",
                        help="Build offline feature snapshots from quotes and claims parquet files")
    parser.add_argument("--validate-data", action="store_true",
                        help="Validate generated datasets")
    parser.add_argument("--drift-check", action="store_true",
                        help="Compute PSI drift for quotes and claims; print JSON report to stdout")
    parser.add_argument("--as-of", metavar="YYYY-MM-DD",
                        help="Back-test --drift-check as of a historical date (ISO format)")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.generate_data:
        quotes_df, claims_df = generate_data()
        print(f"Generated {len(quotes_df)} quotes and {len(claims_df)} claims")
        if not (args.resolve_entities or args.reset_graph or args.build_graph
                or args.compute_graph_features or args.run_offline_pipeline or args.validate_data):
            return

    if args.drift_check:
        from monitoring.psi_drift import run_drift_check, report_to_dict
        import pandas as pd
        as_of = pd.Timestamp(args.as_of) if args.as_of else None
        reports = run_drift_check(as_of=as_of)
        payload = {name: report_to_dict(r) for name, r in reports.items()}

        RISK_MODELS_DIR.mkdir(parents=True, exist_ok=True)
        ts = pd.Timestamp.now().strftime("%Y%m%dT%H%M%S")
        out_path = RISK_MODELS_DIR / f"drift_report_{ts}.json"
        out_path.write_text(json.dumps(payload, indent=2))

        print("Drift check summary")
        print("=" * 40)
        for name, rep in reports.items():
            status = "TRIGGERED" if rep.champion_challenger_triggered else "OK"
            top = sorted(rep.feature_results, key=lambda r: r.psi, reverse=True)[:3]
            top_str = ", ".join(f"{r.feature}={r.psi:.3f}" for r in top)
            print(f"  [{name}] cc={status}  top PSI: {top_str}")
        print(f"\nFull report → {out_path}")
        return

    if args.resolve_entities:
        resolve_vehicles()
        resolve_persons()
        resolve_addresses()
        resolve_phones()
        resolve_policies()
        print("Entity resolution complete")
        if not args.validate_data:
            return

    if args.reset_graph:
        clear_graph(os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
        print("Graph cleared")
        if not args.build_graph:
            return

    if args.build_graph:
        build_graph_from_claims(CLAIMS_OUTPUT, os.environ["NEO4J_URI"], os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"])
        print("Graph built successfully")
        if not args.validate_data:
            return

    if args.compute_graph_features:
        import pandas as pd
        seed_cutoff = args.graph_seed_cutoff
        if seed_cutoff is None:
            _dates = pd.to_datetime(pd.read_parquet(CLAIMS_OUTPUT, columns=["loss_event_datetime"])["loss_event_datetime"])
            if _dates.dt.tz is not None:
                _dates = _dates.dt.tz_localize(None)
            seed_cutoff = str(_dates.quantile(0.8).date())
            print(f"Auto-derived graph seed cutoff: {seed_cutoff} (80th-percentile loss date)")
        graph_features_df = compute_graph_features(
            CLAIMS_OUTPUT, os.environ["NEO4J_URI"], os.environ["NEO4J_USER"],
            os.environ["NEO4J_PASSWORD"], seed_cutoff_dt=seed_cutoff
        )

        claims_df = pd.read_parquet(CLAIMS_OUTPUT)
        claims_df = claims_df.drop(columns=['graph_hop_distance', 'attorney_centrality_score', 'shared_attribute_count'], errors='ignore')
        claims_df = claims_df.merge(graph_features_df, on='claim_id', how='left')
        claims_df.to_parquet(CLAIMS_OUTPUT, index=False)
        print("Graph features computed and updated")
        if not args.validate_data:
            return

    if args.run_offline_pipeline:
        from pipeline.offline_pipeline import run_offline_pipeline
        quotes_written, claims_written = run_offline_pipeline(
            quotes_path=QUOTES_OUTPUT,
            claims_path=CLAIMS_OUTPUT,
            output_dir=OFFLINE_FEATURES_DIR,
        )
        print(f"Offline pipeline complete: {quotes_written} quote snapshots, {claims_written} claim snapshots → {OFFLINE_FEATURES_DIR}")
        if not args.validate_data:
            return

    if args.validate_data:
        validate_data()
        return

    parser.print_help()


if __name__ == "__main__":
    main()
