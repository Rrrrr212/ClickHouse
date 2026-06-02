#!/usr/bin/env python3
import yaml
import re
import os
from datetime import datetime

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "community", "config.yaml")
    readme_path = os.path.join(base_dir, "README.md")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    release_info = config.get("next_release", {})
    version = release_info.get("version")
    date_str = release_info.get("date")
    
    if not version or not date_str:
        print("Missing release info in config.yaml")
        return
        
    release_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    today = datetime.today().date()
    
    days_left = (release_date - today).days
    
    if days_left > 0:
        badge_text = f"{days_left} days"
        badge_color = "blue"
    elif days_left == 0:
        badge_text = "Today!"
        badge_color = "success"
    else:
        badge_text = "Released"
        badge_color = "lightgrey"
        
    badge_url = f"https://img.shields.io/badge/Next_Release_v{version}-{badge_text.replace(' ', '%20')}-{badge_color}?style=for-the-badge"
    
    markdown_badge = f"[![Next Release]({badge_url})](https://clickhouse.com/company/events)"
    
    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()
    
    # Replace between markers
    new_readme = re.sub(
        r"(<!-- COUNTDOWN_START -->\n).*?(<!-- COUNTDOWN_END -->)",
        f"\\g<1>{markdown_badge}\n\\g<2>",
        readme,
        flags=re.DOTALL
    )
    
    if new_readme != readme:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_readme)
        print("README.md updated with latest countdown badge.")
    else:
        print("No changes needed in README.md countdown badge.")

if __name__ == "__main__":
    main()
