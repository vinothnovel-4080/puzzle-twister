"""Always-on scheduler. GitHub's cron drops runs, so instead one job stays awake and
checks every 5 minutes what is due (times in IST):

  planned reel   07:47 - 12:00   python post_reel.py
  trend slot 1   12:47 - 17:00   python post_trend.py --slot 1
  trend slot 2   17:47 - 20:30   python post_trend.py --slot 2
  trend slot 3   20:47 - 23:59   python post_trend.py --slot 3
  token check    05:47 - 07:30   (once a day)
  planner        00:30 - 05:00   python gen_trends.py, commit, start "Build reels" (once a day)

Each post runs once it succeeds (or is already on Instagram); failures are retried
every 5 minutes until the window closes. Anything missed makes this run fail at the
end, so GitHub emails you. Posts run one at a time, so nothing can be posted twice.
Stdlib only.  Env: RUN_MINUTES (default 340), plus the Instagram secrets.
"""
import datetime, os, subprocess, sys, time

IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
RUN_FOR = float(os.environ.get("RUN_MINUTES", "340")) * 60
CHECK_EVERY = 300

JOBS = [  # (key, start hh:mm, end hh:mm, command)
    ("planned", (7, 47), (12, 0), [sys.executable, "post_reel.py"]),
    ("trend-1", (12, 47), (17, 0), [sys.executable, "post_trend.py", "--slot", "1"]),
    ("trend-2", (17, 47), (20, 30), [sys.executable, "post_trend.py", "--slot", "2"]),
    ("trend-3", (20, 47), (23, 59), [sys.executable, "post_trend.py", "--slot", "3"]),
]
OK_MARKERS = ("Published!", "Already posted", "No post scheduled", "No trend post")

done, missed = set(), []


def now():
    return datetime.datetime.now(IST)


def window(t, start, end):
    a = t.replace(hour=start[0], minute=start[1], second=0, microsecond=0)
    b = t.replace(hour=end[0], minute=end[1], second=59, microsecond=0)
    return a, b


def sh(cmd, **kw):
    print(f"[{now():%H:%M}] $ {' '.join(cmd)}", flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    out = (r.stdout + r.stderr).strip()
    if out:
        print(out, flush=True)
    return r.returncode, out


def post_jobs(t):
    today = t.date().isoformat()
    for key, start, end, cmd in JOBS:
        a, b = window(t, start, end)
        k = (key, today)
        if k in done:
            continue
        if a <= t <= b:
            code, out = sh(cmd)
            if code == 0 and any(m in out for m in OK_MARKERS):
                done.add(k)
            else:
                print(f"::warning::{key} not posted yet; retrying in 5 minutes", flush=True)
        elif t > b and a.date() == t.date() and k not in done and (key, today, "missed") not in done:
            # window closed without success, and this run was alive during it
            if STARTED <= b:
                missed.append(f"{key} on {today}")
                print(f"::error::{key} was not posted on {today}", flush=True)
            done.add((key, today, "missed"))


def token_check(t):
    k = ("token", t.date().isoformat())
    a, b = window(t, (5, 47), (7, 30))
    if k in done or not a <= t <= b:
        return
    code, out = sh([sys.executable, "-c",
                    "import os; from post_reel import graph; "
                    "print('Token OK:', graph('GET', os.environ['IG_USER_ID'].strip(), fields='username'))"])
    done.add(k)
    if code != 0:
        missed.append("token check failed: replace INSTAGRAM_ACCESS_TOKEN")
        print("::error::Instagram token check failed", flush=True)
        return
    # Warn 10 days ahead, so the token is replaced before any post fails.
    code, out = sh([sys.executable, "-c",
                    "from post_reel import token_days_left as d; n = d(); "
                    "print('Token days left:', 'unknown' if n is None else f'{n:.0f}')"])
    left = out.rsplit(":", 1)[-1].strip()
    if left.isdigit() and int(left) <= 10:
        missed.append(f"token expires in {left} days: replace INSTAGRAM_ACCESS_TOKEN")
        print(f"::error::Instagram token expires in {left} days", flush=True)


def planner(t):
    k = ("plan", t.date().isoformat())
    a, b = window(t, (0, 30), (5, 0))
    if k in done or not a <= t <= b:
        return
    done.add(k)
    code, out = sh([sys.executable, "gen_trends.py"])
    if code != 0:
        missed.append("planner failed")
        return
    if subprocess.run(["git", "diff", "--quiet", "trends.json"]).returncode == 0:
        return
    sh(["git", "add", "trends.json"])
    sh(["git", "commit", "-m", f"Plan trend puzzles ({t:%d %b})"])
    code, _ = sh(["git", "push"])
    if code == 0:
        sh(["gh", "workflow", "run", "build-reels.yml", "--ref", "main"])
    else:
        missed.append("planner could not push trends.json")


STARTED = now()


def main():
    print(f"Scheduler started {STARTED:%Y-%m-%d %H:%M} IST, running {RUN_FOR / 60:.0f} minutes", flush=True)
    t0 = time.time()
    while time.time() - t0 < RUN_FOR:
        subprocess.run(["git", "pull", "-q", "--ff-only"])  # pick up new puzzles and code
        t = now()
        token_check(t)
        planner(t)
        post_jobs(t)
        time.sleep(CHECK_EVERY)
    if missed:
        raise SystemExit("Missed: " + "; ".join(missed))
    print("Scheduler finished normally.", flush=True)


if __name__ == "__main__":
    main()
