import csv
import random
from datetime import datetime, timedelta

# Config
COUNT = 300
TODAY = datetime(2026, 1, 29)
OUTPUT_FILE = r"D:\InsightPilot\backend\data\customers.csv"

# Targets
# Membership: VIP 36, Standard 174, Basic 90
# Recency: Recent(1-14) 60, Mid(15-90) 120, Old(91-365) 120
# Spend: High(20k+) 30, Mid(5k-20k) 90, Low(<5k) 180

def get_date(category):
    if category == "recent":
        days = random.randint(1, 14)
    elif category == "mid":
        days = random.randint(15, 90)
    else: # old
        days = random.randint(91, 365)
    return (TODAY - timedelta(days=days)).strftime("%Y-%m-%d")

def get_spend_visit(category):
    if category == "high":
        # 20k-80k, visits 20-30
        spent = random.randint(20001, 80000)
        visits = random.randint(20, 30)
    elif category == "mid":
        # 5k-20k, visits 10-20
        spent = random.randint(5001, 20000)
        visits = random.randint(10, 20)
    else: # low
        # 500-5000, visits 1-10
        spent = random.randint(500, 5000)
        visits = random.randint(1, 10)
    
    # Add noise to correlation
    visits += random.choice([-1, 0, 1])
    visits = max(1, min(30, visits))
    return spent, visits

# We build the list of 300 items by carefully allocating buckets to satisfy all constraints
# Strategy: Intersect 3 Dimensions? Too hard.
# Strategy: Assign Membership first, then fill slots for Spend/Recency based on likelihood.

# Initialize slots
# 300 slots.
data = []

# Allocations
# High Spend (30): 30 VIP
# Mid Spend (90): 6 VIP, 80 Std, 4 Basic
# Low Spend (180): 0 VIP, 94 Std, 86 Basic
# -- Checks --
# VIP Total: 30+6+0 = 36 (OK)
# Std Total: 0+80+94 = 174 (OK)
# Basic Total: 0+4+86 = 90 (OK)
# Spend Totals: 30 High, 90 Mid, 180 Low (OK)

groups = []
# Group 1: VIP + High Spend (30 items)
groups.extend([{"m": "VIP", "s": "high"}] * 30)
# Group 2: VIP + Mid Spend (6 items)
groups.extend([{"m": "VIP", "s": "mid"}] * 6)
# Group 3: Std + Mid Spend (80 items)
groups.extend([{"m": "Standard", "s": "mid"}] * 80)
# Group 4: Basic + Mid Spend (4 items)
groups.extend([{"m": "Basic", "s": "mid"}] * 4)
# Group 5: Std + Low Spend (94 items)
groups.extend([{"m": "Standard", "s": "low"}] * 94)
# Group 6: Basic + Low Spend (86 items)
groups.extend([{"m": "Basic", "s": "low"}] * 86)

# Now assign Recency (Recent 60, Mid 120, Old 120) to these 300 items
# Heuristic: VIP/High Spend -> More Recent. Basic/Low -> More Old.

# Available slots
recency_slots = ["recent"] * 60 + ["mid"] * 120 + ["old"] * 120

# We distribute them manually to groups to ensure realism
# Group 1 (30 VIP/High): Take 20 Recent, 10 Mid
g1_r = ["recent"]*20 + ["mid"]*10
# Group 2 (6 VIP/Mid): Take 6 Recent
g2_r = ["recent"]*6
# Group 3 (80 Std/Mid): Take 80 Mid
g3_r = ["mid"]*80
# Group 4 (4 Basic/Mid): Take 4 Mid
g4_r = ["mid"]*4
# Remaining Needs: 
# Total Used: Recent(26/60), Mid(94/120), Old(0/120)
# Remaining Avail: Recent(34), Mid(26), Old(120)
# Group 5 (94 Std/Low)
# Group 6 (86 Basic/Low)
# Assign remaining Recent(34) to Group 5 (Std/Low) -> "Churning soon?" or "New low tier"
# Assign remaining Mid(26) to Group 5
# Remaining 34 of Group 5 get Old.
g5_r = ["recent"]*34 + ["mid"]*26 + ["old"]*34
# Assign 86 Old to Group 6
g6_r = ["old"]*86

# Totals Check for G5/G6:
# G5: 34+26+34 = 94. Correct.
# G6: 86. Correct.
# Overall: 
# Recent: 20+6+34 = 60. OK.
# Mid: 10+0+80+4+26 = 120. OK.
# Old: 34+86 = 120. OK.

# Merge Recency into Groups
# Since groups were extended in order, we can map them back.
# But python lists are just lists.
all_recencies = g1_r + g2_r + g3_r + g4_r + g5_r + g6_r

# Now generate actual data
final_rows = []
for i in range(300):
    g = groups[i]
    r_cat = all_recencies[i]
    
    cid = f"C{i+1:03d}"
    m_type = g["m"]
    
    spent, visits = get_spend_visit(g["s"])
    lvd = get_date(r_cat)
    
    final_rows.append([cid, lvd, spent, visits, m_type])

# Shuffle rows so C001 isn't always VIP
random.shuffle(final_rows)
# Re-assign IDs to be sorted C001-C300 after shuffle?
# "customer_id C001 ~ C300". Usually implies order.
# Let's sort by ID to be neat, or just overwrite ID.
# Overwriting ID is better to mix the types.
final_rows.sort(key=lambda x: x[0]) # Start with C001...
# Actually, if I shuffle, the list is mixed. I should re-label C001..C300
for i in range(300):
    final_rows[i][0] = f"C{i+1:03d}"

# Write CSV
with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["customer_id", "last_visit_date", "total_spent", "visit_count", "membership_type"])
    writer.writerows(final_rows)

print(f"Generated {COUNT} rows to {OUTPUT_FILE}")
