"""
Generate interactive HTML UA Report - Stickman Survival RPG
Tạo website báo cáo UA với charts tương tác
"""
import pandas as pd
import numpy as np
import json, sys, os, re, warnings
from datetime import datetime, timedelta

sys.stdout.reconfigure(encoding='utf-8')
warnings.filterwarnings('ignore')

DATA_DIR = r"C:\Users\Zitga\.claude\Marketing data"
OUTPUT = r"C:\Users\Zitga\Desktop\UA_Report\index.html"

def safe_num(s):
    try:
        if s == 'N/A' or pd.isna(s): return 0
        return float(s)
    except: return 0

# Load data
print("Đang đọc data...")
partners = pd.read_csv(os.path.join(DATA_DIR, [f for f in os.listdir(DATA_DIR) if 'partners-daily' in f][0]))
country_daily = pd.read_csv(os.path.join(DATA_DIR, [f for f in os.listdir(DATA_DIR) if 'country-daily' in f][0]))
cohort = pd.read_csv(os.path.join(DATA_DIR, [f for f in os.listdir(DATA_DIR) if 'cohort' in f][0]))

for df in [partners, country_daily]:
    df['Date'] = pd.to_datetime(df['Date'])
    for col in df.columns:
        if col not in ['Date','Country','Agency/PMD (af_prt)','Media Source (pid)','Campaign (c)']:
            df[col] = df[col].apply(safe_num)

partners.rename(columns={'Media Source (pid)': 'Source', 'Campaign (c)': 'Campaign'}, inplace=True)
country_daily.rename(columns={'Media Source (pid)': 'Source', 'Campaign (c)': 'Campaign'}, inplace=True)

paid = partners[~partners['Source'].isin(['Organic','organic','restricted'])].copy()
organic = partners[partners['Source'] == 'Organic'].copy()
TODAY = paid['Date'].max()

cohort['Cohort Day'] = pd.to_datetime(cohort['Cohort Day'])
rev_cols_map = {}
for c in cohort.columns:
    m = re.search(r'revenue - sum - day (\d+)', c)
    if m: rev_cols_map[int(m.group(1))] = c
cohort_camp = cohort[cohort['Campaign'].notna() & (cohort['Campaign'] != '')].copy()

last7 = paid[paid['Date'] >= TODAY - timedelta(days=7)]
prev7 = paid[(paid['Date'] >= TODAY - timedelta(days=14)) & (paid['Date'] < TODAY - timedelta(days=7))]
active_list = last7.groupby('Campaign')['Total Cost'].sum()
active_list = active_list[active_list > 0].sort_values(ascending=False).index.tolist()

cd_paid = country_daily[~country_daily['Source'].isin(['Organic','organic','restricted'])]

def src_short(s):
    m = {'googleadwords_int': 'Google', 'Facebook Ads': 'Facebook', 'applovin_int': 'AppLovin',
         'unityads_int': 'Unity', 'mintegral_int': 'Mintegral', 'tiktokglobal_int': 'TikTok'}
    return m.get(s, s[:12])

def get_tier(name):
    if pd.isna(name): return 'Unknown'
    if any(t in name for t in ['Tier 0+1','Tier01','_US_']): return 'Tier 0+1'
    if any(t in name for t in ['Tier 2','Tier 3','Tier 4','Tier 2,3,4','Tier 2, 3, 4','_BR_','_MX_']): return 'Tier 2-4'
    return 'Unknown'

def is_test(name):
    return any(t in name.lower() for t in ['layer 1', 'layer 2', 'creative test', 'test creative'])

month_map = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06',
             'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}
def parse_date(name):
    if pd.isna(name): return None
    for p in name.split('_'):
        m = re.match(r'^(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(\d+)', p)
        if m:
            mon = month_map[m.group(1)]
            day = m.group(2).zfill(2)
            year = '2026' if mon in ['01','02','03'] else '2025'
            try: return pd.Timestamp(f"{year}-{mon}-{day}")
            except: return None
    return None

tier1_countries = ['US','DE','UK','JP','KR','CA','AU']
tier2_countries = ['FR','TW','RU','BR','MX']
def country_tier(c):
    if c in tier1_countries: return 'T1'
    if c in tier2_countries: return 'T2'
    return 'T3-4'

benchmarks = {
    ('Google', 'Tier 0+1'): (1.5, 3.0), ('Google', 'Tier 2-4'): (0.03, 0.15),
    ('Facebook', 'Tier 0+1'): (2.0, 5.0), ('Facebook', 'Tier 2-4'): (0.1, 0.5),
    ('AppLovin', 'Tier 0+1'): (1.5, 4.0), ('Unity', 'Tier 0+1'): (0.5, 2.0),
    ('Mintegral', 'Tier 0+1'): (0.5, 2.0), ('TikTok', 'Tier 0+1'): (2.0, 6.0),
}

avg_arpu = paid['Total Revenue'].sum() / paid['Installs'].sum()
avg_loyal = paid['Loyal Users'].sum() / paid['Installs'].sum() * 100

print("Đang tính toán...")

# ============================================================
# DATA FOR CHARTS
# ============================================================

# 1. Daily trend
daily_paid = paid.groupby('Date').agg({'Total Cost': 'sum', 'Total Revenue': 'sum', 'Installs': 'sum'}).reset_index()
daily_paid['ROAS'] = daily_paid['Total Revenue'] / daily_paid['Total Cost'].replace(0, np.nan) * 100
daily_paid['CPI'] = daily_paid['Total Cost'] / daily_paid['Installs'].replace(0, np.nan)
daily_paid['ARPU'] = daily_paid['Total Revenue'] / daily_paid['Installs'].replace(0, np.nan)
daily_paid['ROAS_7d'] = daily_paid['ROAS'].rolling(7, min_periods=3).mean()
daily_paid['CPI_7d'] = daily_paid['CPI'].rolling(7, min_periods=3).mean()
daily_paid['ARPU_7d'] = daily_paid['ARPU'].rolling(7, min_periods=3).mean()

org_daily = organic.groupby('Date').agg({'Total Revenue': 'sum', 'Installs': 'sum'}).reset_index()
org_daily['ARPU'] = org_daily['Total Revenue'] / org_daily['Installs'].replace(0, np.nan)
org_daily['ARPU_7d'] = org_daily['ARPU'].rolling(7, min_periods=3).mean()

trend_dates = [d.strftime('%Y-%m-%d') for d in daily_paid['Date']]
trend_roas = [round(v, 1) if not pd.isna(v) else None for v in daily_paid['ROAS_7d']]
trend_cpi = [round(v, 4) if not pd.isna(v) else None for v in daily_paid['CPI_7d']]
trend_arpu_paid = [round(v, 4) if not pd.isna(v) else None for v in daily_paid['ARPU_7d']]
org_dates = [d.strftime('%Y-%m-%d') for d in org_daily['Date']]
trend_arpu_org = [round(v, 4) if not pd.isna(v) else None for v in org_daily['ARPU_7d']]

# 2. Source stats
source_stats = paid.groupby('Source').agg({
    'Installs': 'sum', 'Total Cost': 'sum', 'Total Revenue': 'sum', 'Loyal Users': 'sum'
}).reset_index()
source_stats['ROAS'] = source_stats['Total Revenue'] / source_stats['Total Cost'].replace(0, np.nan) * 100
source_stats['Profit'] = source_stats['Total Revenue'] - source_stats['Total Cost']
source_stats['CPI'] = source_stats['Total Cost'] / source_stats['Installs'].replace(0, np.nan)
source_stats['ARPU'] = source_stats['Total Revenue'] / source_stats['Installs'].replace(0, np.nan)
source_stats['Loyal%'] = source_stats['Loyal Users'] / source_stats['Installs'].replace(0, np.nan) * 100
source_stats['Src'] = source_stats['Source'].apply(src_short)
source_stats = source_stats[source_stats['Total Cost'] > 100].sort_values('Total Cost', ascending=False)

src_names = source_stats['Src'].tolist()
src_roas = [round(v, 1) for v in source_stats['ROAS']]
src_profit = [round(v, 0) for v in source_stats['Profit']]
src_spend = [round(v, 0) for v in source_stats['Total Cost']]

# 3. Weekly ROAS D3 by source (from cohort data) — Fri-Thu weeks
top_sources = paid.groupby('Source')['Total Cost'].sum().nlargest(6).index
paid['FriStart'] = paid['Date'].apply(lambda d: d - pd.Timedelta(days=(d.weekday() - 4) % 7))
paid['YW'] = paid['FriStart'].dt.strftime('%Y-%m-%d')
weeks = sorted(paid['YW'].unique())

# Build week labels for overview chart
week_label_map = {}
for wk_key, wk_grp in paid.groupby('YW')['FriStart']:
    fri = wk_grp.iloc[0]
    thu = fri + pd.Timedelta(days=6)
    week_label_map[wk_key] = f"{fri.strftime('%d/%m')}-{thu.strftime('%d/%m')}"

# Map campaign → source from paid data
camp_source_map = paid.drop_duplicates('Campaign').set_index('Campaign')['Source'].to_dict()

# Cohort D3 revenue by campaign × cohort week
cohort_camp_d3 = cohort_camp.copy()
cohort_camp_d3['Source'] = cohort_camp_d3['Campaign'].map(camp_source_map)
cohort_camp_d3['YW'] = cohort_camp_d3['Cohort Day'].apply(lambda d: d - pd.Timedelta(days=(d.weekday() - 4) % 7)).dt.strftime('%Y-%m-%d')
d3_col = rev_cols_map.get(3)

weekly_source_data = {}
if d3_col:
    cohort_camp_d3[d3_col] = pd.to_numeric(cohort_camp_d3[d3_col], errors='coerce').fillna(0)
    # Use cost from paid data per source per week
    paid_src_week_cost = paid.groupby(['Source', 'YW'])['Total Cost'].sum()
    for src in top_sources:
        sname = src_short(src)
        src_cohort = cohort_camp_d3[cohort_camp_d3['Source'] == src]
        cohort_rev = src_cohort.groupby('YW')[d3_col].sum().reindex(weeks).fillna(0)
        roas_vals = []
        for w in weeks:
            rev = cohort_rev.get(w, 0)
            cost = paid_src_week_cost.get((src, w), 0)
            if cost > 0 and rev > 0:
                roas_vals.append(round(rev / cost * 100, 1))
            else:
                roas_vals.append(None)
        weekly_source_data[sname] = roas_vals

week_labels = [week_label_map.get(w, w.split('-')[1]) for w in weeks]

# 4. Cohort ROAS curves
camp_cost_total = paid.groupby('Campaign')['Total Cost'].sum().reset_index()
camp_cost_total.columns = ['Campaign', 'TotalCost']
camp_cohort_agg = cohort_camp.groupby('Campaign').agg(
    {**{'Users': 'sum'}, **{rev_cols_map[d]: 'sum' for d in sorted(rev_cols_map.keys())}}
).reset_index()
camp_cohort_agg = camp_cohort_agg.merge(camp_cost_total, on='Campaign', how='left')
camp_cohort_agg = camp_cohort_agg[camp_cohort_agg['TotalCost'] > 5000].nlargest(10, 'TotalCost')

cohort_days = sorted(rev_cols_map.keys())
cohort_curves = {}
for _, row in camp_cohort_agg.iterrows():
    if row['TotalCost'] <= 0: continue
    cname = row['Campaign'].replace('TSH009a_','').replace('QuanNHLeo_','').replace('Applovin_TSH009a_','APL_')[:40]
    cohort_curves[cname] = [round(row[rev_cols_map[d]] / row['TotalCost'] * 100, 1) for d in cohort_days]

# 5. GEO data
geo = cd_paid.groupby('Country').agg({'Installs': 'sum', 'Total Cost': 'sum', 'Total Revenue': 'sum'}).reset_index()
geo['ROAS'] = geo['Total Revenue'] / geo['Total Cost'].replace(0, np.nan) * 100
geo['CPI'] = geo['Total Cost'] / geo['Installs'].replace(0, np.nan)
geo = geo[(geo['Total Cost'] > 100) & (geo['Installs'] > 20)]
geo['Tier'] = geo['Country'].apply(lambda c: 'Tier 1' if c in tier1_countries else ('Tier 2' if c in tier2_countries else 'Tier 3-4'))
geo_data = []
for _, r in geo.iterrows():
    geo_data.append({'country': r['Country'], 'tier': r['Tier'], 'cost': round(r['Total Cost'], 0),
                     'roas': round(r['ROAS'], 1), 'cpi': round(r['CPI'], 4), 'installs': int(r['Installs'])})

# 6. Campaign details
campaigns_data = []
for camp in active_list:
    test_flag = is_test(camp)
    cd = paid[paid['Campaign'] == camp].sort_values('Date')
    src_raw = cd['Source'].iloc[0]
    src = src_short(src_raw)
    tier = get_tier(camp)
    created = parse_date(camp)
    days_running = (TODAY - created).days if created else None

    t_cost = cd['Total Cost'].sum()
    t_rev = cd['Total Revenue'].sum()
    t_inst = cd['Installs'].sum()
    if t_inst == 0: continue
    t_loyal = cd['Loyal Users'].sum()
    roas = t_rev / t_cost * 100 if t_cost > 0 else 0
    cpi = t_cost / t_inst
    arpu = t_rev / t_inst
    loyal_r = t_loyal / t_inst * 100
    ad_rev = cd['af_ad_revenue (Sales in USD)'].sum()
    iap_rev = cd['af_purchase (Sales in USD)'].sum()
    ad_pct = ad_rev / t_rev * 100 if t_rev > 0 else 0

    l7 = cd[cd['Date'] >= TODAY - timedelta(days=7)]
    p7 = cd[(cd['Date'] >= TODAY - timedelta(days=14)) & (cd['Date'] < TODAY - timedelta(days=7))]
    cost_7d = l7['Total Cost'].sum()
    inst_7d = l7['Installs'].sum()
    rev_7d = l7['Total Revenue'].sum()
    cpi_7d = cost_7d / inst_7d if inst_7d > 0 else 0
    roas_7d = rev_7d / cost_7d * 100 if cost_7d > 0 else 0
    cost_p7 = p7['Total Cost'].sum()
    inst_p7 = p7['Installs'].sum()
    cpi_p7 = cost_p7 / inst_p7 if inst_p7 > 0 else 0
    roas_p7 = rev_p7 = p7['Total Revenue'].sum()
    roas_p7 = rev_p7 / cost_p7 * 100 if cost_p7 > 0 else 0

    cost_change = (cost_7d - cost_p7) / cost_p7 * 100 if cost_p7 > 0 else 0
    inst_change = (inst_7d - inst_p7) / inst_p7 * 100 if inst_p7 > 0 else 0
    cpi_change = (cpi_7d - cpi_p7) / cpi_p7 * 100 if cpi_p7 > 0 else 0
    roas_change = (roas_7d - roas_p7) / roas_p7 * 100 if roas_p7 > 0 else 0

    # Lifecycle
    if days_running and days_running < 7: lifecycle = "Learning"
    elif cost_p7 > 0 and cost_7d < cost_p7 * 0.7: lifecycle = "Decline"
    elif days_running and days_running > 60: lifecycle = "Mature"
    elif days_running and days_running > 21: lifecycle = "Mature"
    else: lifecycle = "Growth"

    # Benchmark
    bm = benchmarks.get((src, tier))
    if bm:
        if cpi < bm[0]: cpi_bm = "low"
        elif cpi <= bm[1]: cpi_bm = "ok"
        else: cpi_bm = "high"
    else: cpi_bm = "na"

    # Saturation
    sat = None
    if len(cd) > 14 and cd['Impressions'].sum() > 0:
        first7 = cd.head(7)
        last7c = cd.tail(7)
        ipi_f = first7['Impressions'].sum() / first7['Installs'].sum() if first7['Installs'].sum() > 0 else 0
        ipi_l = last7c['Impressions'].sum() / last7c['Installs'].sum() if last7c['Installs'].sum() > 0 else 0
        if ipi_f > 0: sat = round((ipi_l - ipi_f) / ipi_f * 100, 0)

    # Cohort (try fuzzy match for Tier naming)
    cr = camp_cohort_agg[camp_cohort_agg['Campaign'] == camp]
    if len(cr) == 0:
        cr = camp_cohort_agg[camp_cohort_agg['Campaign'] == camp.replace('Tier 0 1', 'Tier 0+1')]
    if len(cr) == 0:
        cr = camp_cohort_agg[camp_cohort_agg['Campaign'] == camp.replace('Tier 0+1', 'Tier 0 1')]
    cohort_roas = {}
    if len(cr) > 0:
        cr = cr.iloc[0]
        for d in [0, 3, 7, 14, 30]:
            if d in rev_cols_map and cr['TotalCost'] > 0:
                cohort_roas[f'D{d}'] = round(cr[rev_cols_map[d]] / cr['TotalCost'] * 100, 1)

    # Funnel
    tut = cd['af_complete_tut (Unique users)'].sum() if 'af_complete_tut (Unique users)' in cd.columns else 0
    s3 = cd['af_complete_stage_3 (Unique users)'].sum() if 'af_complete_stage_3 (Unique users)' in cd.columns else 0
    s5 = cd['af_complete_stage_5 (Unique users)'].sum() if 'af_complete_stage_5 (Unique users)' in cd.columns else 0
    purch = cd['af_purchase (Unique users)'].sum() if 'af_purchase (Unique users)' in cd.columns else 0

    # GEO breakdown
    camp_geo = cd_paid[cd_paid['Campaign'] == camp].groupby('Country').agg({
        'Installs': 'sum', 'Total Cost': 'sum', 'Total Revenue': 'sum'
    }).reset_index()
    camp_geo['ROAS'] = camp_geo['Total Revenue'] / camp_geo['Total Cost'].replace(0, np.nan) * 100
    camp_geo['CPI'] = camp_geo['Total Cost'] / camp_geo['Installs'].replace(0, np.nan)
    camp_geo = camp_geo[camp_geo['Total Cost'] > 1].sort_values('Total Cost', ascending=False)
    geos = []
    for _, g in camp_geo.head(10).iterrows():
        geos.append({'country': g['Country'], 'tier': country_tier(g['Country']),
                     'cost': round(g['Total Cost'], 2), 'installs': int(g['Installs']),
                     'cpi': round(g['CPI'], 4), 'roas': round(g['ROAS'], 1)})

    # Daily metrics for mini chart
    daily_camp = cd.groupby('Date').agg({'Total Cost': 'sum', 'Total Revenue': 'sum', 'Installs': 'sum'}).reset_index()
    daily_camp = daily_camp.tail(30)
    daily_roas = daily_camp.apply(lambda r: round(r['Total Revenue']/r['Total Cost']*100, 1) if r['Total Cost'] > 0 else None, axis=1).tolist()
    daily_dates = [d.strftime('%m/%d') for d in daily_camp['Date']]

    # Weekly performance with cohort ROAS D3/D7/D14/D28
    # Week = Friday to Thursday (Thu 5 → Fri 6)
    cd_weekly = cd.copy()
    # Shift so Friday is start of week: Friday.weekday()=4, shift by (day - 4) % 7
    # Week starts on Friday: compute the Friday that starts each week
    cd_weekly['FriStart'] = cd_weekly['Date'].apply(lambda d: d - pd.Timedelta(days=(d.weekday() - 4) % 7))
    cd_weekly['Week'] = cd_weekly['FriStart'].dt.strftime('%Y-%m-%d')
    # Build week label map: YW -> "dd/mm-dd/mm" (actual Fri-Thu range)
    week_date_range = {}
    for wk_key, wk_grp in cd_weekly.groupby('Week')['FriStart']:
        fri = wk_grp.iloc[0]
        thu = fri + pd.Timedelta(days=6)
        week_date_range[wk_key] = f"{fri.strftime('%d/%m')}-{thu.strftime('%d/%m')}"
    weekly_camp = cd_weekly.groupby('Week').agg({'Total Cost': 'sum', 'Total Revenue': 'sum', 'Installs': 'sum', 'Impressions': 'sum', 'Clicks': 'sum'}).reset_index()

    # Cohort ROAS per week — revenue from cohort, cost from paid data
    # Try exact match first, then fuzzy match (partners may have "Tier 0 1" vs cohort "Tier 0+1")
    camp_cohort_wk = cohort_camp[cohort_camp['Campaign'] == camp].copy()
    if len(camp_cohort_wk) == 0:
        camp_cohort_wk = cohort_camp[cohort_camp['Campaign'] == camp.replace('Tier 0 1', 'Tier 0+1')].copy()
    if len(camp_cohort_wk) == 0:
        camp_cohort_wk = cohort_camp[cohort_camp['Campaign'] == camp.replace('Tier 0+1', 'Tier 0 1')].copy()
    cohort_week_roas = {}
    if len(camp_cohort_wk) > 0:
        camp_cohort_wk['YW'] = camp_cohort_wk['Cohort Day'].apply(lambda d: d - pd.Timedelta(days=(d.weekday() - 4) % 7)).dt.strftime('%Y-%m-%d')
        cohort_rev_cols = [rev_cols_map[d] for d in [3,7,14,28] if d in rev_cols_map]
        for nc in cohort_rev_cols:
            if nc in camp_cohort_wk.columns:
                camp_cohort_wk[nc] = pd.to_numeric(camp_cohort_wk[nc], errors='coerce').fillna(0)
        cohort_agg_cols = {c: 'sum' for c in cohort_rev_cols if c in camp_cohort_wk.columns}
        if cohort_agg_cols:
            cwk = camp_cohort_wk.groupby('YW').agg(cohort_agg_cols).reset_index()
            # Get cost from paid data per week (more reliable than cohort Cost which can be 0)
            paid_week_cost = cd_weekly.groupby('Week')['Total Cost'].sum()
            for _, cwr in cwk.iterrows():
                wk_key = cwr['YW']
                wk_cost = paid_week_cost.get(wk_key, 0)
                if wk_cost <= 0: continue
                wk_roas = {}
                for d in [3, 7, 14, 28]:
                    if d in rev_cols_map and rev_cols_map[d] in cwk.columns:
                        rev_val = cwr[rev_cols_map[d]]
                        if rev_val > 0:
                            wk_roas[f'd{d}'] = round(rev_val / wk_cost * 100, 1)
                if wk_roas:
                    cohort_week_roas[wk_key] = wk_roas
            # Also fill weeks that have paid cost but no cohort data yet
            # (cohort export may not cover all weeks)

    weekly_perf = []
    for _, wr in weekly_camp.iterrows():
        w_cost = wr['Total Cost']; w_rev = wr['Total Revenue']; w_inst = wr['Installs']
        w_imp = wr['Impressions']; w_click = wr['Clicks']
        if w_cost <= 0 and w_inst <= 0: continue
        wp = {
            'week': week_date_range.get(wr['Week'], wr['Week'].split('-')[1]),
            'cost': round(w_cost, 2), 'revenue': round(w_rev, 2), 'installs': int(w_inst),
            'cpi': round(w_cost / w_inst, 4) if w_inst > 0 else 0,
            'roas_lt': round(w_rev / w_cost * 100, 1) if w_cost > 0 else 0,
            'ctr': round(w_click / w_imp * 100, 2) if w_imp > 0 else 0,
            'ipm': round(w_inst / w_imp * 1000, 1) if w_imp > 0 else 0,
        }
        # Add cohort ROAS D3/D7/D14/D28
        cr_wk = cohort_week_roas.get(wr['Week'], {})
        for d in [3, 7, 14, 28]:
            wp[f'roas_d{d}'] = cr_wk.get(f'd{d}', None)
        weekly_perf.append(wp)

    # GEO × Weekly ROAS trend (last 8 weeks) — Fri-Thu weeks
    camp_cd_geo = cd_paid[cd_paid['Campaign'] == camp].copy()
    camp_cd_geo['FriStart'] = camp_cd_geo['Date'].apply(lambda d: d - pd.Timedelta(days=(d.weekday() - 4) % 7))
    camp_cd_geo['YW'] = camp_cd_geo['FriStart'].dt.strftime('%Y-%m-%d')
    recent_weeks = sorted(camp_cd_geo['YW'].unique())[-8:]
    geo_week_labels = {}
    for wk_key, wk_grp in camp_cd_geo.groupby('YW')['FriStart']:
        fri = wk_grp.iloc[0]
        thu = fri + pd.Timedelta(days=6)
        geo_week_labels[wk_key] = f"{fri.strftime('%d/%m')}-{thu.strftime('%d/%m')}"
    geo_weekly = []
    top_geos_list = camp_geo.head(5)['Country'].tolist()
    for geo_c in top_geos_list:
        geo_cd = camp_cd_geo[camp_cd_geo['Country'] == geo_c]
        for wk in recent_weeks:
            wk_d = geo_cd[geo_cd['YW'] == wk]
            wk_cost = wk_d['Total Cost'].sum(); wk_rev = wk_d['Total Revenue'].sum(); wk_inst = wk_d['Installs'].sum()
            if wk_cost <= 0 and wk_inst <= 0: continue
            geo_weekly.append({
                'geo': geo_c, 'week': geo_week_labels.get(wk, wk.split('-')[1]),
                'cost': round(wk_cost, 2), 'revenue': round(wk_rev, 2), 'installs': int(wk_inst),
                'cpi': round(wk_cost / wk_inst, 4) if wk_inst > 0 else 0,
                'roas': round(wk_rev / wk_cost * 100, 1) if wk_cost > 0 else 0,
            })

    # Ad-level performance from cohort
    ad_perf = []
    camp_cohort_ads = cohort_camp[cohort_camp['Campaign'] == camp].copy()
    if len(camp_cohort_ads) == 0:
        camp_cohort_ads = cohort_camp[cohort_camp['Campaign'] == camp.replace('Tier 0 1', 'Tier 0+1')].copy()
    if len(camp_cohort_ads) == 0:
        camp_cohort_ads = cohort_camp[cohort_camp['Campaign'] == camp.replace('Tier 0+1', 'Tier 0 1')].copy()
    if len(camp_cohort_ads) > 0 and 'Ad' in camp_cohort_ads.columns:
        num_cols = ['Cost', 'Users'] + [rev_cols_map[d] for d in [0,3,7,14,30] if d in rev_cols_map]
        for nc in num_cols:
            if nc in camp_cohort_ads.columns:
                camp_cohort_ads[nc] = pd.to_numeric(camp_cohort_ads[nc], errors='coerce').fillna(0)
        ad_agg = camp_cohort_ads.groupby('Ad').agg(
            {**{'Users': 'sum', 'Cost': 'sum'}, **{rev_cols_map[d]: 'sum' for d in [0,3,7,14,30] if d in rev_cols_map and rev_cols_map[d] in camp_cohort_ads.columns}}
        ).reset_index()
        ad_agg = ad_agg[ad_agg['Cost'] > 10].sort_values('Cost', ascending=False).head(10)
        for _, ar in ad_agg.iterrows():
            ae = {'ad': str(ar['Ad'])[:60] if pd.notna(ar['Ad']) else 'Unknown',
                  'users': int(ar['Users']), 'cost': round(ar['Cost'], 2)}
            for d in [3, 7, 14, 30]:
                if d in rev_cols_map and rev_cols_map[d] in ad_agg.columns and ar['Cost'] > 0:
                    ae[f'roas_d{d}'] = round(ar[rev_cols_map[d]] / ar['Cost'] * 100, 1)
            ad_perf.append(ae)

    # Decline detection signals
    signals = []
    if roas_7d < roas * 0.7 and cost_7d > 50 and not test_flag:
        signals.append({'type': 'roas', 'sev': 'high', 'msg': f'ROAS 7D ({roas_7d:.1f}%) giảm mạnh so với tổng ({roas:.1f}%)'})
    elif roas_7d < roas * 0.85 and cost_7d > 50 and not test_flag:
        signals.append({'type': 'roas', 'sev': 'med', 'msg': f'ROAS 7D ({roas_7d:.1f}%) đang giảm so với tổng ({roas:.1f}%)'})
    if cpi_change > 30 and cost_7d > 50:
        signals.append({'type': 'cpi', 'sev': 'high', 'msg': f'CPI tăng {cpi_change:.0f}% trong 7 ngày (${cpi_p7:.4f} → ${cpi_7d:.4f})'})
    elif cpi_change > 15 and cost_7d > 50:
        signals.append({'type': 'cpi', 'sev': 'med', 'msg': f'CPI tăng {cpi_change:.0f}% trong 7 ngày'})
    if cost_change < -30 and cost_p7 > 50:
        signals.append({'type': 'spend', 'sev': 'med', 'msg': f'Spend giảm {abs(cost_change):.0f}% — campaign có thể đang bị limited'})
    if inst_change < -50 and inst_p7 > 20:
        signals.append({'type': 'installs', 'sev': 'high', 'msg': f'Installs giảm {abs(inst_change):.0f}% trong 7 ngày'})
    if sat and sat > 100:
        signals.append({'type': 'saturation', 'sev': 'high', 'msg': f'Audience bão hòa nặng (IPI +{sat:.0f}%)'})
    elif sat and sat > 50:
        signals.append({'type': 'saturation', 'sev': 'med', 'msg': f'Audience đang bão hòa (IPI +{sat:.0f}%)'})
    # GEO-specific decline
    for gi in geos[:5]:
        if gi['roas'] < 50 and gi['cost'] > 100:
            signals.append({'type': 'geo', 'sev': 'high', 'msg': f"GEO {gi['country']} ROAS rất thấp ({gi['roas']:.1f}%) với spend ${gi['cost']:.0f}"})

    # Health score
    if bm:
        bm_mid = (bm[0]+bm[1])/2
        cpi_s = 20 if cpi < bm_mid else (15 if cpi <= bm[1] else (10 if cpi <= bm[1]*1.5 else 0))
    else: cpi_s = 10
    roas_s = 25 if roas > 150 else (20 if roas > 120 else (15 if roas > 100 else (5 if roas > 80 else 0)))
    if cpi_p7 > 0 and cpi_p7 < 900:
        ch = (cpi_7d - cpi_p7) / cpi_p7
        trend_s = 20 if ch < -0.1 else (15 if abs(ch) < 0.1 else (5 if ch < 0.3 else 0))
    else: trend_s = 10
    imp = cd['Impressions'].sum()
    ctr = cd['Clicks'].sum()/imp if imp > 0 else 0
    ctr_s = 15 if ctr > 0.015 else (10 if ctr > 0.008 else (5 if ctr > 0.005 else 0))
    qual_s = 20 if (arpu > avg_arpu and loyal_r > avg_loyal) else (10 if (arpu > avg_arpu or loyal_r > avg_loyal) else 0)
    score = cpi_s + roas_s + trend_s + ctr_s + qual_s

    if test_flag: action = "TEST"
    elif score >= 80: action = "SCALE"
    elif score >= 60: action = "KEEP"
    elif score >= 40: action = "OPTIMIZE"
    elif score >= 20: action = "REDUCE"
    else: action = "CUT"

    # Issues
    issues = []
    if roas < 80 and not test_flag: issues.append(f"ROAS rất thấp ({roas:.1f}%)")
    if roas < 100 and roas >= 80 and not test_flag: issues.append(f"ROAS dưới 100% ({roas:.1f}%)")
    if roas_7d < roas * 0.7 and cost_7d > 50: issues.append(f"ROAS 7D ({roas_7d:.1f}%) giảm mạnh vs tổng ({roas:.1f}%)")
    if cpi_change > 30 and cost_7d > 50: issues.append(f"CPI tăng {cpi_change:.0f}% trong 7 ngày")
    if inst_change < -50 and inst_p7 > 20: issues.append(f"Installs giảm {abs(inst_change):.0f}%")
    if cost_change < -30 and cost_p7 > 50: issues.append(f"Underspend: giảm {abs(cost_change):.0f}%")
    if loyal_r < 40 and t_inst > 50: issues.append(f"Loyal thấp ({loyal_r:.1f}%)")
    if bm and cpi > bm[1] * 1.5: issues.append(f"CPI quá cao (${cpi:.2f} vs benchmark ${bm[1]:.2f})")
    if sat and sat > 100: issues.append("Audience bão hòa nặng")
    elif sat and sat > 50: issues.append("Audience đang bão hòa")

    campaigns_data.append({
        'name': camp, 'source': src, 'tier': tier, 'isTest': test_flag,
        'created': created.strftime('%d/%m/%Y') if created else '?',
        'daysRunning': days_running, 'lifecycle': lifecycle,
        'cost': round(t_cost, 2), 'revenue': round(t_rev, 2), 'profit': round(t_rev - t_cost, 2),
        'installs': int(t_inst), 'roas': round(roas, 1), 'cpi': round(cpi, 4), 'arpu': round(arpu, 4),
        'loyal': round(loyal_r, 1), 'adPct': round(ad_pct, 1),
        'cost7d': round(cost_7d, 2), 'inst7d': int(inst_7d), 'roas7d': round(roas_7d, 1),
        'cpi7d': round(cpi_7d, 4), 'costChange': round(cost_change, 0),
        'instChange': round(inst_change, 0), 'cpiChange': round(cpi_change, 0), 'roasChange': round(roas_change, 0),
        'cpiBenchmark': cpi_bm, 'saturation': sat,
        'cohortRoas': cohort_roas,
        'funnel': {'tut': round(tut/t_inst*100, 1), 's3': round(s3/t_inst*100, 1),
                   's5': round(s5/t_inst*100, 1), 'purchase': round(purch/t_inst*100, 2)},
        'geos': geos, 'geoWeekly': geo_weekly, 'adPerf': ad_perf, 'signals': signals,
        'score': score, 'action': action, 'issues': issues,
        'dailyDates': daily_dates, 'dailyRoas': daily_roas, 'weeklyPerf': weekly_perf,
        'scoreBreakdown': {'cpi': cpi_s, 'roas': roas_s, 'trend': trend_s, 'ctr': ctr_s, 'quality': qual_s}
    })

# MoM data
mom_data = []
for month_num, month_name in [(1, 'Tháng 1'), (2, 'Tháng 2'), (3, 'Tháng 3')]:
    p = paid[paid['Date'].dt.month == month_num]
    if len(p) == 0: continue
    c = p['Total Cost'].sum(); r = p['Total Revenue'].sum(); i = p['Installs'].sum()
    mom_data.append({'month': month_name, 'cost': round(c, 0), 'revenue': round(r, 0),
                     'roas': round(r/c*100, 1) if c > 0 else 0, 'installs': int(i),
                     'cpi': round(c/i, 4) if i > 0 else 0, 'arpu': round(r/i, 4) if i > 0 else 0})

# Summary
total_cost = paid['Total Cost'].sum()
total_rev = paid['Total Revenue'].sum()
total_inst = paid['Installs'].sum()
org_inst = organic['Installs'].sum()

summary = {
    'totalCost': round(total_cost, 2), 'totalRevenue': round(total_rev, 2),
    'totalInstalls': int(total_inst), 'organicInstalls': int(org_inst),
    'roas': round(total_rev/total_cost*100, 1), 'roi': round((total_rev-total_cost)/total_cost*100, 1),
    'cpi': round(total_cost/total_inst, 4), 'arpu': round(total_rev/total_inst, 4),
    'loyal': round(paid['Loyal Users'].sum()/total_inst*100, 1),
    'profit': round(total_rev - total_cost, 2),
    'dateRange': f"01/01/2026 - {TODAY.strftime('%d/%m/%Y')}",
    'activeCampaigns': len(active_list)
}

# Problem source weekly
problem_sources = {}
for src_name in ['applovin_int', 'unityads_int']:
    sdata = paid[paid['Source'] == src_name]
    sw = sdata.groupby(sdata['Date'].dt.strftime('%Y-W%U')).agg({'Total Cost': 'sum', 'Total Revenue': 'sum'}).reset_index()
    sw['ROAS'] = sw['Total Revenue'] / sw['Total Cost'].replace(0, np.nan) * 100
    sw = sw.tail(10)
    short = src_short(src_name)
    problem_sources[short] = {
        'weeks': [w.split('-')[1] for w in sw['Date']],
        'roas': [round(v, 1) if not pd.isna(v) else 0 for v in sw['ROAS']],
        'totalLoss': round(sdata['Total Cost'].sum() - sdata['Total Revenue'].sum(), 0)
    }

all_data = {
    'summary': summary, 'mom': mom_data,
    'trendDates': trend_dates, 'trendRoas': trend_roas, 'trendCpi': trend_cpi,
    'trendArpuPaid': trend_arpu_paid, 'orgDates': org_dates, 'trendArpuOrg': trend_arpu_org,
    'srcNames': src_names, 'srcRoas': src_roas, 'srcProfit': src_profit, 'srcSpend': src_spend,
    'weekLabels': week_labels, 'weeklySource': weekly_source_data,
    'cohortDays': cohort_days, 'cohortCurves': cohort_curves,
    'geoData': geo_data, 'campaigns': campaigns_data,
    'problemSources': problem_sources
}

print("Đang tạo HTML...")

html = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>UA Report - Stickman Survival RPG</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>
<style>
:root {
  --bg: #0f1117; --card: #1a1d27; --card2: #252836; --border: #2d3142;
  --text: #e4e4e7; --text2: #9ca3af; --accent: #6366f1;
  --good: #22c55e; --warn: #f59e0b; --bad: #ef4444;
  --google: #4285F4; --fb: #1877F2; --apl: #FF6B35; --unity: #888;
  --mint: #00BFA5; --tt: #FF0050;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.5; }
.container { max-width: 1400px; margin: 0 auto; padding: 20px; }
h1 { font-size: 28px; font-weight: 800; background: linear-gradient(135deg, #6366f1, #a855f7); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
h2 { font-size: 20px; font-weight: 700; margin-bottom: 16px; color: var(--text); }
h3 { font-size: 16px; font-weight: 600; color: var(--text2); margin-bottom: 8px; }

.header { display: flex; justify-content: space-between; align-items: center; padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 24px; }
.header-right { text-align: right; color: var(--text2); font-size: 14px; }

.kpi-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin-bottom: 24px; }
.kpi { background: var(--card); border-radius: 12px; padding: 16px; border: 1px solid var(--border); }
.kpi-label { font-size: 12px; color: var(--text2); text-transform: uppercase; letter-spacing: 0.5px; }
.kpi-value { font-size: 24px; font-weight: 800; margin-top: 4px; }
.kpi-sub { font-size: 12px; color: var(--text2); margin-top: 2px; }
.kpi-good { color: var(--good); } .kpi-bad { color: var(--bad); } .kpi-warn { color: var(--warn); }

.card { background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); margin-bottom: 20px; }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px; }
@media (max-width: 900px) { .chart-row { grid-template-columns: 1fr; } }
.chart-container { position: relative; height: 300px; }
.chart-container-lg { position: relative; height: 400px; }

.alert { background: rgba(239,68,68,0.1); border: 1px solid rgba(239,68,68,0.3); border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.alert-warn { background: rgba(245,158,11,0.1); border-color: rgba(245,158,11,0.3); }
.alert h3 { color: var(--bad); margin-bottom: 8px; }
.alert-warn h3 { color: var(--warn); }
.alert ul { padding-left: 20px; font-size: 14px; }

.mom-table { width: 100%; border-collapse: collapse; font-size: 14px; }
.mom-table th, .mom-table td { padding: 10px 12px; text-align: right; border-bottom: 1px solid var(--border); }
.mom-table th { color: var(--text2); font-weight: 600; text-align: right; font-size: 12px; text-transform: uppercase; }
.mom-table th:first-child, .mom-table td:first-child { text-align: left; }
.roas-good { color: var(--good); font-weight: 700; } .roas-bad { color: var(--bad); font-weight: 700; }

.nav { display: flex; gap: 8px; margin-bottom: 20px; flex-wrap: wrap; }
.nav-btn { background: var(--card2); border: 1px solid var(--border); color: var(--text2); padding: 8px 16px; border-radius: 8px; cursor: pointer; font-size: 13px; transition: all 0.2s; }
.nav-btn:hover, .nav-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

.campaign-card { background: var(--card); border-radius: 12px; border: 1px solid var(--border); margin-bottom: 16px; overflow: hidden; transition: all 0.2s; }
.campaign-card:hover { border-color: var(--accent); }
.campaign-header { padding: 16px 20px; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
.campaign-header:hover { background: var(--card2); }
.camp-name { font-weight: 700; font-size: 14px; flex: 1; }
.camp-badges { display: flex; gap: 8px; align-items: center; }
.badge { padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; }
.badge-scale { background: rgba(34,197,94,0.2); color: var(--good); }
.badge-keep { background: rgba(99,102,241,0.2); color: var(--accent); }
.badge-optimize { background: rgba(245,158,11,0.2); color: var(--warn); }
.badge-reduce { background: rgba(239,68,68,0.2); color: var(--bad); }
.badge-cut { background: rgba(239,68,68,0.4); color: #fff; }
.badge-test { background: rgba(156,163,175,0.2); color: var(--text2); }
.score-circle { width: 36px; height: 36px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-weight: 800; font-size: 13px; }

.campaign-detail { display: none; padding: 0 20px 20px; border-top: 1px solid var(--border); }
.campaign-detail.open { display: block; }
.detail-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin: 12px 0; }
.detail-item { background: var(--card2); border-radius: 8px; padding: 12px; }
.detail-label { font-size: 11px; color: var(--text2); text-transform: uppercase; }
.detail-value { font-size: 16px; font-weight: 700; margin-top: 2px; }
.detail-sub { font-size: 11px; color: var(--text2); }

.trend-row { display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 8px; font-size: 13px; margin: 8px 0; }
.trend-header { color: var(--text2); font-weight: 600; font-size: 11px; text-transform: uppercase; }
.change-pos { color: var(--bad); } .change-neg { color: var(--good); }
.change-pos-good { color: var(--good); } .change-neg-bad { color: var(--bad); }

.geo-table { width: 100%; border-collapse: collapse; font-size: 12px; margin-top: 8px; }
.geo-table th, .geo-table td { padding: 6px 8px; border-bottom: 1px solid var(--border); }
.geo-table th { color: var(--text2); font-size: 11px; text-transform: uppercase; }
.geo-table td:first-child { font-weight: 700; }

.issue-list { list-style: none; padding: 0; }
.issue-list li { padding: 4px 0; font-size: 13px; color: var(--warn); }
.issue-list li::before { content: "⚠ "; }
.issue-list li.critical { color: var(--bad); }
.issue-list li.critical::before { content: "🔴 "; }

.section-title { font-size: 14px; font-weight: 700; color: var(--accent); text-transform: uppercase; letter-spacing: 1px; margin: 16px 0 8px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }

.cohort-inline { display: flex; gap: 6px; align-items: center; margin: 4px 0; font-size: 13px; }
.cohort-day { background: var(--card2); padding: 2px 8px; border-radius: 4px; }
.cohort-arrow { color: var(--text2); }

.score-breakdown { display: flex; gap: 4px; margin-top: 8px; }
.score-bar { height: 6px; border-radius: 3px; }

.filter-group { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; }
.filter-btn { background: transparent; border: 1px solid var(--border); color: var(--text2); padding: 4px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }
.filter-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

.action-plan { background: var(--card); border-radius: 12px; padding: 20px; border: 1px solid var(--border); margin-bottom: 20px; }
.action-section { margin-bottom: 16px; }
.action-title { display: flex; align-items: center; gap: 8px; font-weight: 700; margin-bottom: 8px; }
.action-items { padding-left: 24px; }
.action-items li { padding: 4px 0; font-size: 14px; }
</style>
</head>
<body>
<div class="container">

<div class="header">
  <div>
    <h1>📊 UA Report — Stickman Survival RPG</h1>
    <div style="color:var(--text2);font-size:13px;margin-top:4px">Data: """ + summary['dateRange'] + """ • """ + str(summary['activeCampaigns']) + """ campaigns đang chạy</div>
  </div>
  <div class="header-right">
    <div style="font-size:13px">Generated: """ + datetime.now().strftime('%d/%m/%Y %H:%M') + """</div>
  </div>
</div>

<nav class="nav" id="mainNav">
  <button class="nav-btn active" onclick="showSection('overview')">📊 Tổng quan</button>
  <button class="nav-btn" onclick="showSection('detail')">🔍 Chi tiết Campaign</button>
  <button class="nav-btn" onclick="showSection('action')">🎯 Action Plan</button>
</nav>

<div id="sections"></div>

</div>

<script>
const DATA = """ + json.dumps(all_data, ensure_ascii=False) + """;

const srcColorMap = {Google:'#4285F4',Facebook:'#1877F2',AppLovin:'#FF6B35',Unity:'#888',Mintegral:'#00BFA5',TikTok:'#FF0050'};
const actionBadge = {SCALE:'badge-scale',KEEP:'badge-keep',OPTIMIZE:'badge-optimize',REDUCE:'badge-reduce',CUT:'badge-cut',TEST:'badge-test'};
const actionIcon = {SCALE:'⭐',KEEP:'✅',OPTIMIZE:'⚠️',REDUCE:'🔻',CUT:'❌',TEST:'🧪'};

function fmt$(v) { return '$' + v.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function fmtK(v) { return v >= 1000 ? '$' + (v/1000).toFixed(1) + 'K' : '$' + v.toFixed(0); }
function fmtPct(v) { return v.toFixed(1) + '%'; }
function scoreColor(s) { return s >= 80 ? '#22c55e' : s >= 60 ? '#6366f1' : s >= 40 ? '#f59e0b' : s >= 20 ? '#e65100' : '#ef4444'; }

function showSection(id) {
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  const el = document.getElementById('sections');
  el.innerHTML = '';
  if (id === 'overview') renderFullOverview(el);
  else if (id === 'detail') renderDetailCampaigns(el);
  else if (id === 'action') renderAction(el);
}

function renderFullOverview(el) {
  const s = DATA.summary;
  const roasClass = s.roas >= 100 ? 'kpi-good' : 'kpi-bad';

  // --- KPI + Alert + MoM ---
  let html = `
  <div class="kpi-grid">
    <div class="kpi"><div class="kpi-label">Paid Installs</div><div class="kpi-value">${s.totalInstalls.toLocaleString()}</div><div class="kpi-sub">Organic: ${s.organicInstalls.toLocaleString()}</div></div>
    <div class="kpi"><div class="kpi-label">Total Spend</div><div class="kpi-value">${fmtK(s.totalCost)}</div></div>
    <div class="kpi"><div class="kpi-label">Total Revenue</div><div class="kpi-value">${fmtK(s.totalRevenue)}</div></div>
    <div class="kpi"><div class="kpi-label">ROAS</div><div class="kpi-value ${roasClass}">${fmtPct(s.roas)}</div><div class="kpi-sub">ROI: ${fmtPct(s.roi)}</div></div>
    <div class="kpi"><div class="kpi-label">CPI</div><div class="kpi-value">$${s.cpi.toFixed(4)}</div></div>
    <div class="kpi"><div class="kpi-label">ARPU</div><div class="kpi-value">$${s.arpu.toFixed(4)}</div></div>
    <div class="kpi"><div class="kpi-label">Profit</div><div class="kpi-value ${s.profit >= 0 ? 'kpi-good' : 'kpi-bad'}">${fmtK(s.profit)}</div></div>
    <div class="kpi"><div class="kpi-label">Loyal Rate</div><div class="kpi-value">${fmtPct(s.loyal)}</div></div>
  </div>

  <div class="card"><h2>MoM Performance</h2>
  <table class="mom-table"><thead><tr><th>Tháng</th><th>Spend</th><th>Revenue</th><th>ROAS</th><th>Installs</th><th>CPI</th><th>ARPU</th></tr></thead><tbody>
  ${DATA.mom.map(m => `<tr><td>${m.month}</td><td>${fmtK(m.cost)}</td><td>${fmtK(m.revenue)}</td><td class="${m.roas >= 100 ? 'roas-good' : 'roas-bad'}">${fmtPct(m.roas)}</td><td>${m.installs.toLocaleString()}</td><td>$${m.cpi.toFixed(4)}</td><td>$${m.arpu.toFixed(4)}</td></tr>`).join('')}
  </tbody></table></div>

  <div class="card"><h2>ROAS Trend (7D avg)</h2><div class="chart-container-lg"><canvas id="roasChart"></canvas></div></div>
  <div class="chart-row">
    <div class="card"><h2>ARPU Trend — Paid vs Organic</h2><div class="chart-container"><canvas id="arpuChart"></canvas></div></div>
    <div class="card"><h2>CPI Trend (7D avg)</h2><div class="chart-container"><canvas id="cpiChart"></canvas></div></div>
  </div>

  <!-- Sources -->
  <div class="chart-row">
    <div class="card"><h2>ROAS theo Source</h2><div class="chart-container"><canvas id="srcRoas"></canvas></div></div>
    <div class="card"><h2>Lãi / Lỗ theo Source</h2><div class="chart-container"><canvas id="srcProfit"></canvas></div></div>
  </div>
  <div class="card"><h2>ROAS D3 theo Tuần × Source</h2><div class="chart-container-lg"><canvas id="weeklyRoas"></canvas></div></div>
  <div class="chart-row">
    <div class="card"><h2>Phân bổ Spend</h2><div class="chart-container"><canvas id="spendPie"></canvas></div></div>
    <div class="card"><h2>ROAS Cohort Curves</h2><div class="chart-container"><canvas id="cohortChart"></canvas></div></div>
  </div>

  <!-- GEO -->
  ${(() => {
    const t1 = DATA.geoData.filter(g=>g.tier==='Tier 1').sort((a,b)=>b.cost-a.cost);
    const t2 = DATA.geoData.filter(g=>g.tier==='Tier 2').sort((a,b)=>b.cost-a.cost);
    const t34 = DATA.geoData.filter(g=>g.tier==='Tier 3-4').sort((a,b)=>b.cost-a.cost);
    function gt(d,t) { return '<div class="card"><h2>'+t+'</h2><table class="mom-table"><thead><tr><th style="text-align:left">Country</th><th>Installs</th><th>Spend</th><th>ROAS</th><th>CPI</th></tr></thead><tbody>'+d.slice(0,15).map(g=>'<tr><td style="text-align:left;font-weight:700">'+g.country+'</td><td>'+g.installs.toLocaleString()+'</td><td>'+fmtK(g.cost)+'</td><td class="'+(g.roas>=100?'roas-good':'roas-bad')+'">'+fmtPct(g.roas)+'</td><td>$'+g.cpi.toFixed(4)+'</td></tr>').join('')+'</tbody></table></div>'; }
    return gt(t1,'Tier 1 (US/DE/UK/JP/KR/CA/AU)') + gt(t2,'Tier 2 (FR/TW/RU/BR/MX)') + gt(t34,'Tier 3-4 (Top 15)');
  })()}

  <!-- Cảnh báo suy giảm -->
  ${(() => {
    const declining = DATA.campaigns.filter(c => c.signals && c.signals.length > 0 && !c.isTest).sort((a,b) => b.signals.length - a.signals.length);
    if (declining.length === 0) return '';
    return '<div class="card"><h2>⚠️ Campaigns có dấu hiệu suy giảm (' + declining.length + ')</h2><table class="mom-table"><thead><tr><th style="text-align:left">Campaign</th><th>Source</th><th>ROAS</th><th>7D ROAS</th><th>Score</th><th style="text-align:left">Dấu hiệu</th></tr></thead><tbody>' +
      declining.map(c => '<tr><td style="text-align:left;font-size:12px;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + c.name + '</td><td style="text-align:center">' + c.source + '</td><td class="' + (c.roas>=100?'roas-good':'roas-bad') + '">' + fmtPct(c.roas) + '</td><td class="' + (c.roas7d>=100?'roas-good':'roas-bad') + '">' + fmtPct(c.roas7d) + '</td><td style="text-align:center;color:' + scoreColor(c.score) + ';font-weight:700">' + c.score + '</td><td style="text-align:left;font-size:11px">' + c.signals.map(s => '<span style="color:' + (s.sev==='high'?'var(--bad)':'var(--warn)') + '">' + (s.sev==='high'?'🔴':'⚠️') + ' ' + s.msg + '</span>').join('<br>') + '</td></tr>').join('') +
      '</tbody></table></div>';
  })()}

  <!-- Campaign Health Scoreboard -->
  <div class="card"><h2>Campaign Health Scoreboard</h2>
  <table class="mom-table"><thead><tr><th style="text-align:left">Campaign</th><th>Source</th><th>Score</th><th>ROAS</th><th>CPI</th><th>7D Spend</th><th>Action</th></tr></thead><tbody>
  ${DATA.campaigns.filter(c=>!c.isTest).sort((a,b)=>b.score-a.score).map(c => `<tr>
    <td style="text-align:left;font-size:12px;max-width:250px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.name}</td>
    <td style="text-align:center">${c.source}</td>
    <td style="text-align:center;color:${scoreColor(c.score)};font-weight:700">${c.score}</td>
    <td class="${c.roas>=100?'roas-good':'roas-bad'}">${fmtPct(c.roas)}</td>
    <td>$${c.cpi.toFixed(4)}</td>
    <td>${fmtK(c.cost7d)}</td>
    <td><span class="badge ${actionBadge[c.action]||'badge-test'}">${actionIcon[c.action]||''} ${c.action}</span></td>
  </tr>`).join('')}
  </tbody></table></div>`;

  el.innerHTML = html;

  // Charts
  new Chart('roasChart', {type:'line', data:{labels:DATA.trendDates, datasets:[
    {label:'ROAS 7D avg',data:DATA.trendRoas,borderColor:'#ef4444',backgroundColor:'rgba(239,68,68,0.1)',fill:true,tension:0.3,pointRadius:0},
    {label:'Breakeven',data:DATA.trendDates.map(()=>100),borderColor:'#666',borderDash:[5,5],pointRadius:0}
  ]}, options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9ca3af'}}},scales:{x:{ticks:{color:'#666',maxTicksLimit:12}},y:{ticks:{color:'#666'},min:40,max:180}}}});

  new Chart('arpuChart', {type:'line', data:{labels:DATA.trendDates, datasets:[
    {label:'Paid ARPU',data:DATA.trendArpuPaid,borderColor:'#f59e0b',tension:0.3,pointRadius:0},
    {label:'Organic ARPU',data:DATA.trendArpuOrg,borderColor:'#9ca3af',borderDash:[4,4],tension:0.3,pointRadius:0}
  ]}, options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9ca3af'}}},scales:{x:{ticks:{color:'#666',maxTicksLimit:8}},y:{ticks:{color:'#666'}}}}});

  new Chart('cpiChart', {type:'line', data:{labels:DATA.trendDates, datasets:[
    {label:'CPI 7D avg',data:DATA.trendCpi,borderColor:'#6366f1',tension:0.3,pointRadius:0,fill:true,backgroundColor:'rgba(99,102,241,0.1)'}
  ]}, options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9ca3af'}}},scales:{x:{ticks:{color:'#666',maxTicksLimit:8}},y:{ticks:{color:'#666'}}}}});

  const srcC = DATA.srcNames.map(n => DATA.srcRoas[DATA.srcNames.indexOf(n)] >= 100 ? '#22c55e' : '#ef4444');
  new Chart('srcRoas', {type:'bar', data:{labels:DATA.srcNames, datasets:[{data:DATA.srcRoas,backgroundColor:srcC}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#666'}},y:{ticks:{color:'#ccc'}}}}});

  const profitC = DATA.srcProfit.map(v => v >= 0 ? '#22c55e' : '#ef4444');
  new Chart('srcProfit', {type:'bar', data:{labels:DATA.srcNames, datasets:[{data:DATA.srcProfit,backgroundColor:profitC}]},
    options:{indexAxis:'y',responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}},scales:{x:{ticks:{color:'#666'}},y:{ticks:{color:'#ccc'}}}}});

  const wds = Object.entries(DATA.weeklySource).map(([name, vals]) => ({
    label:name, data:vals, borderColor:srcColorMap[name]||'#999', tension:0.3, pointRadius:2
  }));
  wds.push({label:'Breakeven',data:DATA.weekLabels.map(()=>100),borderColor:'#555',borderDash:[5,5],pointRadius:0});
  new Chart('weeklyRoas', {type:'line', data:{labels:DATA.weekLabels, datasets:wds},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9ca3af'}}},scales:{x:{ticks:{color:'#666'}},y:{ticks:{color:'#666'},min:0,max:220}}}});

  const pieC = DATA.srcNames.map(n => srcColorMap[n]||'#999');
  new Chart('spendPie', {type:'doughnut', data:{labels:DATA.srcNames, datasets:[{data:DATA.srcSpend,backgroundColor:pieC,borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#ccc'}}}}});

  const cColors = ['#6366f1','#ef4444','#22c55e','#f59e0b','#a855f7','#06b6d4','#f97316','#ec4899','#14b8a6','#8b5cf6'];
  const cds = Object.entries(DATA.cohortCurves).map(([name, vals], i) => ({
    label:name, data:vals, borderColor:cColors[i%cColors.length], tension:0.3, pointRadius:2
  }));
  cds.push({label:'Breakeven',data:DATA.cohortDays.map(()=>100),borderColor:'#fff',borderDash:[6,4],pointRadius:0,borderWidth:2});
  new Chart('cohortChart', {type:'line', data:{labels:DATA.cohortDays, datasets:cds},
    options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{labels:{color:'#9ca3af',font:{size:9}}}},scales:{x:{ticks:{color:'#666'}},y:{ticks:{color:'#666'},min:0,max:120}}}});
}

// =============================================
// CHI TIẾT CAMPAIGN
// =============================================
function renderDetailCampaigns(el) {
  let filterHtml = `<div class="filter-group">
    <button class="filter-btn active" onclick="filterCamp('all',this)">Tất cả (${DATA.campaigns.length})</button>
    <button class="filter-btn" onclick="filterCamp('SCALE',this)">⭐ Scale</button>
    <button class="filter-btn" onclick="filterCamp('KEEP',this)">✅ Keep</button>
    <button class="filter-btn" onclick="filterCamp('OPTIMIZE',this)">⚠️ Optimize</button>
    <button class="filter-btn" onclick="filterCamp('REDUCE',this)">🔻 Reduce</button>
    <button class="filter-btn" onclick="filterCamp('declining',this)">📉 Suy giảm</button>
    <button class="filter-btn" onclick="filterCamp('TEST',this)">🧪 Test</button>
  </div><div id="campList"></div>`;
  el.innerHTML = filterHtml;
  renderCampList('all');
}

function filterCamp(filter, btn) {
  document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));
  btn.classList.add('active');
  renderCampList(filter);
}

function renderCampList(filter) {
  let camps = DATA.campaigns;
  if (filter === 'declining') camps = camps.filter(c => c.signals && c.signals.length > 0 && !c.isTest);
  else if (filter !== 'all') camps = camps.filter(c => c.action === filter);

  const listEl = document.getElementById('campList');
  listEl.innerHTML = camps.map((c, i) => {
    const sc = scoreColor(c.score);
    const badgeCls = actionBadge[c.action] || 'badge-test';
    const icon = actionIcon[c.action] || '';
    const hasSignals = c.signals && c.signals.length > 0;

    // Decline signals
    let signalsHtml = '';
    if (hasSignals) {
      signalsHtml = `<div class="section-title">📉 Dấu hiệu suy giảm</div>
        <div style="display:flex;flex-direction:column;gap:6px;margin-bottom:12px">
        ${c.signals.map(s => `<div style="display:flex;align-items:center;gap:8px;padding:8px 12px;border-radius:8px;background:${s.sev==='high'?'rgba(239,68,68,0.15)':'rgba(245,158,11,0.15)'}">
          <span style="font-size:16px">${s.sev==='high'?'🔴':'⚠️'}</span>
          <span style="font-size:13px;color:${s.sev==='high'?'var(--bad)':'var(--warn)'}">${s.msg}</span>
        </div>`).join('')}
        </div>`;
    }

    // Cohort ROAS
    let cohortHtml = '';
    if (Object.keys(c.cohortRoas).length > 0) {
      cohortHtml = `<div class="section-title">ROAS Cohort</div><div class="cohort-inline">
        ${Object.entries(c.cohortRoas).map(([k,v]) => `<span class="cohort-day">${k}: ${v}%</span>`).join('<span class="cohort-arrow">→</span>')}
      </div>`;
    }

    // Weekly performance
    let weeklyHtml = '';
    if (c.weeklyPerf && c.weeklyPerf.length > 0) {
      weeklyHtml = `<div class="section-title">Performance theo Tuần</div>
        <div style="overflow-x:auto"><table class="geo-table"><thead><tr><th>Tuần</th><th>Spend</th><th>Installs</th><th>CPI</th><th>ROAS D3</th><th>ROAS D7</th><th>ROAS D14</th><th>ROAS D28</th><th>ROAS LT</th><th>CTR</th><th>IPM</th></tr></thead><tbody>
        ${c.weeklyPerf.map(w => `<tr>
          <td>${w.week}</td><td style="text-align:right">${fmtK(w.cost)}</td><td style="text-align:right">${w.installs.toLocaleString()}</td>
          <td style="text-align:right">$${w.cpi.toFixed(4)}</td>
          <td style="text-align:right">${w.roas_d3!=null?'<span class="'+(w.roas_d3>=100?'roas-good':'roas-bad')+'">'+fmtPct(w.roas_d3)+'</span>':'—'}</td>
          <td style="text-align:right">${w.roas_d7!=null?'<span class="'+(w.roas_d7>=100?'roas-good':'roas-bad')+'">'+fmtPct(w.roas_d7)+'</span>':'—'}</td>
          <td style="text-align:right">${w.roas_d14!=null?'<span class="'+(w.roas_d14>=100?'roas-good':'roas-bad')+'">'+fmtPct(w.roas_d14)+'</span>':'—'}</td>
          <td style="text-align:right">${w.roas_d28!=null?'<span class="'+(w.roas_d28>=100?'roas-good':'roas-bad')+'">'+fmtPct(w.roas_d28)+'</span>':'—'}</td>
          <td style="text-align:right" class="${w.roas_lt>=100?'roas-good':'roas-bad'}">${fmtPct(w.roas_lt)}</td>
          <td style="text-align:right">${w.ctr.toFixed(2)}%</td><td style="text-align:right">${w.ipm.toFixed(1)}</td>
        </tr>`).join('')}
        </tbody></table></div>`;
    }

    // GEO × Weekly ROAS trend
    let geoWeeklyHtml = '';
    if (c.geoWeekly && c.geoWeekly.length > 0) {
      const geoNames = [...new Set(c.geoWeekly.map(g=>g.geo))];
      const geoWeeks = [...new Set(c.geoWeekly.map(g=>g.week))];
      geoWeeklyHtml = `<div class="section-title">ROAS theo GEO × Tuần</div>
        <table class="geo-table"><thead><tr><th>GEO</th>${geoWeeks.map(w=>'<th>'+w+'</th>').join('')}</tr></thead><tbody>
        ${geoNames.map(geo => {
          const gData = c.geoWeekly.filter(g=>g.geo===geo);
          return '<tr><td style="font-weight:700">'+geo+'</td>' + geoWeeks.map(w => {
            const d = gData.find(g=>g.week===w);
            if (!d) return '<td style="text-align:right;color:var(--text2)">—</td>';
            return '<td style="text-align:right" class="'+(d.roas>=100?'roas-good':'roas-bad')+'">'+fmtPct(d.roas)+'</td>';
          }).join('') + '</tr>';
        }).join('')}
        </tbody></table>`;
    }

    // Ad-level performance
    let adHtml = '';
    if (c.adPerf && c.adPerf.length > 0) {
      adHtml = `<div class="section-title">Performance theo Ad/Creative</div>
        <table class="geo-table"><thead><tr><th>Ad</th><th>Users</th><th>Spend</th>${c.adPerf[0].roas_d3!==undefined?'<th>ROAS D3</th>':''}${c.adPerf[0].roas_d7!==undefined?'<th>ROAS D7</th>':''}${c.adPerf[0].roas_d14!==undefined?'<th>ROAS D14</th>':''}${c.adPerf[0].roas_d30!==undefined?'<th>ROAS D30</th>':''}</tr></thead><tbody>
        ${c.adPerf.map(a => `<tr>
          <td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="${a.ad}">${a.ad}</td>
          <td style="text-align:right">${a.users.toLocaleString()}</td>
          <td style="text-align:right">${fmtK(a.cost)}</td>
          ${a.roas_d3!==undefined?'<td style="text-align:right" class="'+(a.roas_d3>=100?'roas-good':'roas-bad')+'">'+fmtPct(a.roas_d3)+'</td>':''}
          ${a.roas_d7!==undefined?'<td style="text-align:right" class="'+(a.roas_d7>=100?'roas-good':'roas-bad')+'">'+fmtPct(a.roas_d7)+'</td>':''}
          ${a.roas_d14!==undefined?'<td style="text-align:right" class="'+(a.roas_d14>=100?'roas-good':'roas-bad')+'">'+fmtPct(a.roas_d14)+'</td>':''}
          ${a.roas_d30!==undefined?'<td style="text-align:right" class="'+(a.roas_d30>=100?'roas-good':'roas-bad')+'">'+fmtPct(a.roas_d30)+'</td>':''}
        </tr>`).join('')}
        </tbody></table>`;
    }

    // GEO static breakdown
    let geoHtml = '';
    if (c.geos.length > 0) {
      geoHtml = `<div class="section-title">GEO Breakdown (Tổng)</div><table class="geo-table"><thead><tr><th>Country</th><th>Tier</th><th>Spend</th><th>Installs</th><th>CPI</th><th>ROAS</th></tr></thead><tbody>
        ${c.geos.map(g => `<tr><td>${g.country}</td><td>${g.tier}</td><td>${fmt$(g.cost)}</td><td>${g.installs.toLocaleString()}</td><td>$${g.cpi.toFixed(4)}</td><td class="${g.roas>=100?'roas-good':'roas-bad'}">${fmtPct(g.roas)}</td></tr>`).join('')}
      </tbody></table>`;
    }

    return `<div class="campaign-card" data-action="${c.action}">
      <div class="campaign-header" onclick="this.nextElementSibling.classList.toggle('open')">
        <div style="display:flex;align-items:center;gap:12px;flex:1;min-width:0">
          <div class="score-circle" style="background:${sc}20;color:${sc};flex-shrink:0">${c.score}</div>
          <div style="min-width:0"><div class="camp-name" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${c.name}</div>
            <div style="font-size:11px;color:var(--text2)">${c.source} • ${c.tier} • ${c.lifecycle} • ${c.daysRunning||'?'}d${hasSignals?' • <span style="color:var(--bad)">📉 '+c.signals.length+' dấu hiệu</span>':''}</div>
          </div>
        </div>
        <div class="camp-badges">
          <span style="font-size:13px;color:${c.roas>=100?'var(--good)':'var(--bad)'}; font-weight:700">${fmtPct(c.roas)}</span>
          <span style="font-size:12px;color:var(--text2)">${fmtK(c.cost7d)}/7D</span>
          <span class="badge ${badgeCls}">${icon} ${c.action}</span>
        </div>
      </div>
      <div class="campaign-detail">
        ${signalsHtml}
        <div class="detail-grid">
          <div class="detail-item"><div class="detail-label">Total Spend</div><div class="detail-value">${fmtK(c.cost)}</div></div>
          <div class="detail-item"><div class="detail-label">Revenue</div><div class="detail-value">${fmtK(c.revenue)}</div></div>
          <div class="detail-item"><div class="detail-label">Profit</div><div class="detail-value" style="color:${c.profit>=0?'var(--good)':'var(--bad)'}">$${c.profit.toLocaleString()}</div></div>
          <div class="detail-item"><div class="detail-label">ROAS</div><div class="detail-value" style="color:${c.roas>=100?'var(--good)':'var(--bad)'}">${fmtPct(c.roas)}</div><div class="detail-sub">7D: ${fmtPct(c.roas7d)} (${c.roasChange>0?'+':''}${c.roasChange}%)</div></div>
          <div class="detail-item"><div class="detail-label">CPI</div><div class="detail-value">$${c.cpi.toFixed(4)}</div><div class="detail-sub">7D: $${c.cpi7d.toFixed(4)} (${c.cpiChange>0?'+':''}${c.cpiChange}%) • ${c.cpiBenchmark==='low'?'✅ Thấp':c.cpiBenchmark==='ok'?'⚡ OK':c.cpiBenchmark==='high'?'🔴 Cao':'—'}</div></div>
          <div class="detail-item"><div class="detail-label">ARPU</div><div class="detail-value">$${c.arpu.toFixed(4)}</div></div>
          <div class="detail-item"><div class="detail-label">Installs</div><div class="detail-value">${c.installs.toLocaleString()}</div><div class="detail-sub">7D: ${c.inst7d.toLocaleString()} (${c.instChange>0?'+':''}${c.instChange}%)</div></div>
          <div class="detail-item"><div class="detail-label">Loyal Rate</div><div class="detail-value">${fmtPct(c.loyal)}</div></div>
          <div class="detail-item"><div class="detail-label">Revenue Mix</div><div class="detail-value">Ad ${c.adPct.toFixed(0)}% / IAP ${(100-c.adPct).toFixed(0)}%</div></div>
          <div class="detail-item"><div class="detail-label">Saturation</div><div class="detail-value">${c.saturation!==null?(c.saturation>100?'🔴 +'+c.saturation+'%':c.saturation>50?'⚠️ +'+c.saturation+'%':c.saturation>20?'📊 +'+c.saturation+'%':'✅ '+c.saturation+'%'):'—'}</div></div>
          <div class="detail-item"><div class="detail-label">Funnel</div><div class="detail-value" style="font-size:12px">Tut ${c.funnel.tut}% → S3 ${c.funnel.s3}% → S5 ${c.funnel.s5}% → Buy ${c.funnel.purchase}%</div></div>
          <div class="detail-item"><div class="detail-label">Health Score</div><div class="detail-value" style="color:${sc}">${c.score}/100</div>
            <div class="detail-sub">CPI:${c.scoreBreakdown.cpi} ROAS:${c.scoreBreakdown.roas} Trend:${c.scoreBreakdown.trend} CTR:${c.scoreBreakdown.ctr} Qual:${c.scoreBreakdown.quality}</div></div>
        </div>
        ${cohortHtml}
        ${weeklyHtml}
        ${geoWeeklyHtml}
        ${adHtml}
        ${geoHtml}
      </div>
    </div>`;
  }).join('');
}

function renderAction(el) {
  el.innerHTML = `
  <div class="action-plan">
    <div class="action-section">
      <div class="action-title" style="color:var(--bad)">🔴 HÀNH ĐỘNG NGAY (hôm nay)</div>
      <ol class="action-items">
        <li><strong>Giảm budget AppLovin 50-70%</strong> — Pause BLDROASD7_Feb20 (ROAS 72%), giữ ADROASD7 giảm 30%. Tiết kiệm ~$3K/tuần</li>
        <li><strong>Giảm budget Unity 70-80%</strong> — ROAS 76%, ARPU thấp nhất. Tiết kiệm ~$1.5K/tuần</li>
        <li><strong>CUT campaign Mar15_FB_New_nhaps</strong> — $44 chi, 0 install</li>
      </ol>
    </div>
    <div class="action-section">
      <div class="action-title" style="color:var(--warn)">🟡 TUẦN NÀY</div>
      <ol class="action-items">
        <li><strong>Kiểm tra game monetization</strong> — ARPU organic giảm 79% → vấn đề GAME, cần phối hợp team</li>
        <li><strong>Cắt tổng spend 20-25%</strong> — $52K/tuần → $38-41K/tuần, giữ Google + Facebook</li>
        <li><strong>Consolidate campaigns</strong> — Google T0+1: 5→3, Facebook T0+1: 4→2</li>
        <li><strong>Refresh creative</strong> — Mintegral Dec16 (IPI +152%), GG Mar04 (+106%), FB Jul25 (+76%)</li>
      </ol>
    </div>
    <div class="action-section">
      <div class="action-title" style="color:var(--good)">🟢 THÁNG NÀY</div>
      <ol class="action-items">
        <li><strong>Scale Google</strong> (45-50%) — ROAS tốt nhất 131%, diminishing returns OK</li>
        <li><strong>Scale TikTok</strong> (5%→10-12%) — User quality cao nhất, purchase rate 5.24%</li>
        <li><strong>Test GEO mới</strong> — NL, CH, BE (ROAS >150%), scale VN/PH (cohort D30 cao)</li>
        <li><strong>Exclude GEO kém</strong> — RU, HK đang kéo ROAS xuống nhiều campaigns</li>
      </ol>
    </div>
  </div>
  <div class="card"><h2>Phân bổ budget đề xuất</h2>
    <div class="chart-row"><div class="chart-container"><canvas id="budgetCurrent"></canvas></div><div class="chart-container"><canvas id="budgetProposed"></canvas></div></div>
  </div>
  <div class="alert-warn alert"><h3>⚠️ Lưu ý quan trọng</h3><ul>
    <li>ROAS Cohort D30 chỉ 37-65% → campaigns "tốt" cũng chưa payback 30 ngày</li>
    <li>Cần export D60-D90 cohort từ AppsFlyer để đánh giá chính xác</li>
    <li>Nếu ARPU organic tiếp tục giảm → cân nhắc pause toàn bộ UA</li>
    <li>Theo dõi weekly: nếu ROAS < 80% liên tiếp 2 tuần nữa → pause UA</li>
  </ul></div>`;

  const labels = ['Google','Facebook','AppLovin','Mintegral','Unity','TikTok'];
  const colors = [srcColorMap.Google,srcColorMap.Facebook,srcColorMap.AppLovin,srcColorMap.Mintegral,srcColorMap.Unity,srcColorMap.TikTok];
  new Chart('budgetCurrent', {type:'doughnut', data:{labels, datasets:[{data:[25000,11000,8600,4300,1700,1200],backgroundColor:colors,borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{title:{display:true,text:'Hiện tại: $52K/tuần',color:'#ccc'},legend:{labels:{color:'#999'}}}}});
  new Chart('budgetProposed', {type:'doughnut', data:{labels, datasets:[{data:[19000,10500,2500,3500,500,3500],backgroundColor:colors,borderWidth:0}]},
    options:{responsive:true,maintainAspectRatio:false,plugins:{title:{display:true,text:'Đề xuất: $40K/tuần (tiết kiệm $12K)',color:'#ccc'},legend:{labels:{color:'#999'}}}}});
}

// Init
showSection('overview');
</script>
</body></html>"""

with open(OUTPUT, 'w', encoding='utf-8') as f:
    f.write(html)

print(f"✅ Đã tạo website: {OUTPUT}")
print(f"   Mở file index.html trong browser để xem!")
