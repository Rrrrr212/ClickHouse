#!/usr/bin/env python3
import yaml
import re
import os

def render_community_links(config):
    links = config.get("community_links", [])
    lines = []
    current_line = "* "
    
    for i, link in enumerate(links):
        md_link = f"[{link['name']}]({link['url']})"
        if link.get("inline"):
            current_line += f"{md_link} {link.get('description', '')} "
        else:
            current_line += f"{md_link} {link.get('description', '')}"
            lines.append(current_line.strip())
            current_line = "* "
            
    if current_line != "* ":
        lines.append(current_line.strip())
        
    return "\n".join(lines) + "\n"

def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(base_dir, "community", "config.yaml")
    readme_path = os.path.join(base_dir, "README.md")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    
    with open(readme_path, "r", encoding="utf-8") as f:
        readme = f.read()
    
    rendered_links = render_community_links(config)
    
    # Replace between markers
    new_readme = re.sub(
        r"(<!-- COMMUNITY_LINKS_START -->\n).*?(<!-- COMMUNITY_LINKS_END -->)",
        f"\\g<1>{rendered_links}\\g<2>",
        readme,
        flags=re.DOTALL
    )
    
    if new_readme != readme:
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_readme)
        print("README.md updated with latest community links.")
    else:
        print("No changes needed in README.md.")

if __name__ == "__main__":
    main()
