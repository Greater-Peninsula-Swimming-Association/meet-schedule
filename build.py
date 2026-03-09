#!/usr/bin/env python3
"""
Build script for GPSA Meet Schedule site.
Reads SwimTopia CSV exports from data/, renders HTML schedule pages, outputs to dist/.

Expected files in data/:
  - red.csv, white.csv, blue.csv  (division dual meet schedules)
  - invitationals.csv              (league-wide invitationals)
  - rosters.yaml                   (division roster links)

Run: python build.py
"""

import csv
import shutil
from datetime import datetime
from pathlib import Path

import jinja2
import yaml

# Team abbreviation → display name (from SwimTopia export codes)
TEAM_NAME_MAP = {
    "BLMAR": "Beaconsdale",
    "COL": "Colony",
    "CV": "Coventry",
    "EL": "Elizabeth Lake",
    "GWRA": "George Wythe",
    "GG": "Glendale",
    "HW": "Hidenwood",
    "JRCC": "James River",
    "KCD": "Kiln Creek",
    "MBKMT": "Marlbank",
    "NHM": "Northampton",
    "POQ": "Poquoson",
    "RRST": "Riverdale",
    "RMMR": "Running Man",
    "WW": "Wendwood",
    "WO": "Willow Oaks",
    "WPPIR": "Windy Point",
    "WYCC": "Warwick Yacht",
}

DIVISIONS = ["red", "white", "blue"]


def parse_date(date_str):
    """Parse SwimTopia date format (M/D/YYYY) into a datetime object."""
    return datetime.strptime(date_str.strip(), "%m/%d/%Y")


def format_date_header(dt):
    """Format datetime as 'MONDAY JUNE 16'."""
    return f"{dt.strftime('%A').upper()} {dt.strftime('%B').upper()} {dt.day}"


def team_name(abbr):
    """Resolve team abbreviation to display name."""
    return TEAM_NAME_MAP.get(abbr.strip(), abbr.strip())


def load_division_csv(path):
    """Load a division CSV and return meets grouped by date, sorted chronologically."""
    meets_by_date = {}
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = parse_date(row["MeetDate"])
            meets_by_date.setdefault(dt, []).append({
                "home": team_name(row["HomeTeam"]),
                "visitor": team_name(row["VisitingTeam"]),
            })

    return [
        {"date": format_date_header(dt), "meets": meets}
        for dt, meets in sorted(meets_by_date.items())
    ]


def load_invitationals_csv(path):
    """Load invitationals CSV and return events sorted by date."""
    events = []
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = parse_date(row["MeetDate"])
            events.append({
                "date": format_date_header(dt),
                "name": row["MeetName"].strip(),
                "location": row.get("Location", "").strip(),
                "sort_key": dt,
            })

    events.sort(key=lambda e: e["sort_key"])
    return events


def detect_year(data_dir):
    """Detect season year from the first date found in any CSV."""
    for path in sorted(data_dir.glob("*.csv")):
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                return parse_date(row["MeetDate"]).year
    return datetime.now().year


def build():
    dist = Path("dist")
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir()

    data_dir = Path("data")

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("templates"),
        autoescape=jinja2.select_autoescape(["html"]),
    )

    year = detect_year(data_dir)

    # Build division schedule pages
    schedule_template = env.get_template("schedule.html.j2")
    for division in DIVISIONS:
        csv_path = data_dir / f"{division}.csv"
        if not csv_path.exists():
            print(f"  Skipping {division} (no {csv_path})")
            continue

        date_groups = load_division_csv(csv_path)
        output = schedule_template.render(
            division=division,
            division_title=division.capitalize(),
            date_groups=date_groups,
            year=year,
        )
        out_path = dist / f"schedule-{division}.html"
        out_path.write_text(output)
        print(f"  Built {out_path.name} ({sum(len(g['meets']) for g in date_groups)} meets)")

    # Build invitationals page
    inv_path = data_dir / "invitationals.csv"
    if inv_path.exists():
        inv_template = env.get_template("invitationals.html.j2")
        events = load_invitationals_csv(inv_path)
        output = inv_template.render(events=events, year=year)
        out_path = dist / "invitationals.html"
        out_path.write_text(output)
        print(f"  Built {out_path.name} ({len(events)} events)")
    else:
        print(f"  Skipping invitationals (no {inv_path})")

    # Build divisions (rosters) page
    rosters_path = data_dir / "rosters.yaml"
    if rosters_path.exists():
        with open(rosters_path) as f:
            rosters = yaml.safe_load(f)
        divisions_template = env.get_template("divisions.html.j2")
        output = divisions_template.render(
            divisions=[rosters.get(d, []) for d in DIVISIONS],
            year=year,
        )
        out_path = dist / "divisions.html"
        out_path.write_text(output)
        print(f"  Built {out_path.name}")
    else:
        print(f"  Skipping divisions (no {rosters_path})")

    # Build meet schedules header page
    header_template = env.get_template("header.html.j2")
    output = header_template.render(year=year)
    (dist / "header.html").write_text(output)
    print("  Built header.html")

    # Copy CNAME if present
    if Path("CNAME").exists():
        shutil.copy2("CNAME", dist / "CNAME")

    print(f"\nDone — output in {dist}/")


if __name__ == "__main__":
    build()
