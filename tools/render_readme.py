#!/usr/bin/env python3
import os
import re

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
    
    links = config.get("community_links", {})
    
    community_md = []
    if "youtube" in links:
        community_md.append(f"* [YouTube channel]({links['youtube']}) has a lot of content about ClickHouse in video format.")
    if "slack" in links and "telegram" in links:
        community_md.append(f"* [Slack]({links['slack']}) and [Telegram]({links['telegram']}) allow chatting with ClickHouse users in real-time.")
    elif "slack" in links:
        community_md.append(f"* [Slack]({links['slack']}) allows chatting with ClickHouse users in real-time.")
    elif "telegram" in links:
        community_md.append(f"* [Telegram]({links['telegram']}) allows chatting with ClickHouse users in real-time.")
        
    if "blog" in links:
        community_md.append(f"* [Blog]({links['blog']}) contains various ClickHouse-related articles, as well as announcements and reports about events.")
        
    if "bluesky" in links and "x" in links:
        community_md.append(f"* [Bluesky]({links['bluesky']}) and [X]({links['x']}) for short news.")
    
    community_text = "\n".join(community_md)
    
    with open(readme_path, "r") as f:
        readme_content = f.read()
        
    # Replace community links
    pattern = r"(<!-- COMMUNITY_LINKS_START -->\n)(.*?)(\n<!-- COMMUNITY_LINKS_END -->)"
    readme_content = re.sub(pattern, rf"\g<1>{community_text}\g<3>", readme_content, flags=re.DOTALL)
    
    with open(readme_path, "w") as f:
        f.write(readme_content)
        
    print("README.md updated with community links successfully.")

if __name__ == "__main__":
    main()
