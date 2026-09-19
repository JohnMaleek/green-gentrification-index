"""Smoke-test the Streamlit dashboard via AppTest."""
import sys
sys.path.insert(0, r"D:\AI Project\green_gentrification_index")

from streamlit.testing.v1 import AppTest

at = AppTest.from_file("app.py", default_timeout=300)
at.run()

exceptions = at.exception
print(f"Exceptions: {len(exceptions)}")
for e in exceptions:
    print(f"  EXC: {e}")

print(f"Tabs rendered: {len(at.tabs)}")
print(f"Errors: {len(at.error)}")
for err in at.error[:10]:
    print(f"  ERR: {err}")
print(f"Warnings: {len(at.warning)}")

kpi_cards = [m.value for m in at.markdown if "kpi-card" in m.value]
hero_blocks = [m.value for m in at.markdown if "hero-title" in m.value]
sidebar_brand = [m.value for m in at.markdown if "sb-brand" in m.value]
print(f"KPI card grids rendered: {len(kpi_cards)}")
for block in kpi_cards[:4]:
    labels = [line.strip() for line in block.splitlines() if line.strip().startswith('<div class="kpi-label">')]
    print(f"  KPI grid with {len(labels)} card(s): {', '.join(l.split('</div>')[0].replace('<div class=\"kpi-label\">', '') for l in labels)}")

filter_widgets = [w for w in at.sidebar.multiselect if "risk category" in w.label.lower()]
scoreboard_present = any("Risk Scoreboard" in m.value for m in at.markdown) or any(
    s.value == "🏆 Gentrification Risk Scoreboard" for s in at.subheader
)
timeline_present = any("Clean Air Timeline" in m.value for m in at.markdown) or any(
    "Clean Air Timeline" in s.value for s in at.subheader
)
justice_present = any("Environmental Justice" in s.value for s in at.subheader) or any(
    "environmental justice" in m.value.lower() for m in at.markdown
)
justice_scoreboard_present = any("Justice Scoreboard" in s.value for s in at.subheader)
then_now_present = any("Then & Now" in s.value for s in at.subheader) or any(
    "then & now" in m.value.lower() for m in at.markdown
)
watch_table_present = any("Gentrification-watch" in s.value for s in at.subheader) or any(
    "Gentrification-watch" in m.value for m in at.markdown
)
brand_present = any("GreenSense" in m.value for m in at.markdown)
print(f"Sidebar risk-category filters: {len(filter_widgets)}")
print(f"Scoreboard tab content present: {scoreboard_present}")
print(f"Clean-air timeline present: {timeline_present}")
print(f"Environmental justice section present: {justice_present}")
print(f"Justice scoreboard table present: {justice_scoreboard_present}")
print(f"Then & Now tab content present: {then_now_present}")
print(f"Gentrification-watch table present: {watch_table_present}")
print(f"GreenSense brand applied: {brand_present}")
print(f"Hero banner rendered: {len(hero_blocks) > 0}")
print(f"Sidebar brand rendered: {len(sidebar_brand) > 0}")
print(f"Markdown blocks total: {len(at.markdown)}")

if (
    len(exceptions) == 0
    and len(at.tabs) >= 8
    and len(kpi_cards) > 0
    and len(filter_widgets) > 0
    and scoreboard_present
    and timeline_present
    and justice_present
    and then_now_present
    and watch_table_present
    and brand_present
):
    print("SMOKE TEST PASSED")
else:
    print("SMOKE TEST ISSUES DETECTED")