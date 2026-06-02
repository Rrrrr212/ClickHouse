#!/usr/bin/env python3
import os
import re
from datetime import datetime

try:
    import yaml
except ImportError:
    print("PyYAML is not installed. Please install it using 'pip install pyyaml'")
    exit(1)

def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(repo_root, "community", "config.yaml")
    readme_path = os.path.join(repo_root, "README.md")
    
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
        
    release_info = config.get("release_info", {})
    next_date_str = release_info.get("next_release_date")
    next_version = release_info.get("next_release_version", "Next")
    
    if not next_date_str:
        print("No next_release_date found in config.")
        return

    # Calculate days remaining
    try:
        next_date = datetime.strptime(next_date_str, "%Y-%m-%d")
        today = datetime.now()
        delta = next_date - today
        days_remaining = delta.days
        
        if days_remaining > 0:
            time_str = f"in_{days_remaining}_days"
            color = "blue"
        elif days_remaining == 0:
            time_str = "today"
            color = "success"
        else:
            time_str = "released"
            color = "lightgrey"
            
    except ValueError:
        time_str = "unknown"
        color = "inactive"

    badge_url = f"https://img.shields.io/badge/Release_{next_version}-{time_str}-{color}?style=for-the-badge"
    badge_md = f"![Next Release Countdown]({badge_url})"
    
    print(f"Generated Countdown Badge: {badge_md}")
    
    # Inject into README
    if os.path.exists(readme_path):
        with open(readme_path, "r") as f:
            readme_content = f.read()
            
        pattern = r"(<!-- RELEASE_COUNTDOWN_START -->\n)(.*?)(\n<!-- RELEASE_COUNTDOWN_END -->)"
        
        # Check if tags exist
        if re.search(pattern, readme_content, flags=re.DOTALL):
            readme_content = re.sub(pattern, rf"\g<1>{badge_md}\g<3>", readme_content, flags=re.DOTALL)
            with open(readme_path, "w") as f:
                f.write(readme_content)
            print("Successfully injected countdown badge into README.md")
        else:
            print("Could not find RELEASE_COUNTDOWN tags in README.md")

if __name__ == "__main__":
    main()
