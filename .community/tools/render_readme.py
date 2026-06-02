#!/usr/bin/env python3
import json
import os


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def render_useful_links(config):
    links = [
        f"* [Official website]({config['content']['website']}) has a quick high-level overview of ClickHouse on the main page.",
        f"* [ClickHouse Cloud]({config['content']['cloud']}) ClickHouse as a service, built by the creators and maintainers.",
        f"* [Tutorial]({config['content']['tutorial']}) shows how to set up and query a small ClickHouse cluster.",
        f"* [Documentation]({config['content']['docs']}) provides more in-depth information.",
        f"* [YouTube channel]({config['content']['youtube']}) has a lot of content about ClickHouse in video format.",
        f"* [ClickHouse Theater]({config['content']['theater']}) contains presentations and videos about ClickHouse.",
        f"* [Slack]({config['channels']['slack']}) and [Telegram]({config['channels']['telegram']}) allow chatting with ClickHouse users in real-time.",
        f"* [Blog]({config['content']['blog']}) contains various ClickHouse-related articles, as well as announcements and reports about events.",
        f"* [Bluesky]({config['channels']['bluesky']}) and [X]({config['channels']['twitter']}) for short news.",
        f"* [Code Browser (github.dev)]({config['content']['code_browser']}) with syntax highlighting, powered by github.dev.",
        f"* [Contacts]({config['content']['contacts']}) can help to get your questions answered if there are any."
    ]
    return "\n".join(links)


def render_release_section(config):
    release = config["release"]
    return f"""## Monthly Release & Community Call

Join us for the [ClickHouse **{release['current']}** Release Call]({release['call_url']}) on {release['call_date']}.

Watch all release presentations and videos at [ClickHouse Theater]({release['theater_playlist']}) and [YouTube Playlist]({release['youtube_playlist']})."""


def update_readme():
    config = load_config()
    
    # This is a demo - in real usage you would read the existing README and update sections
    print("Community config loaded successfully")
    print(f"Current release: {config['release']['current']}")
    print(f"Slack channel: {config['channels']['slack']}")
    print("\nUseful links:")
    print(render_useful_links(config))


if __name__ == "__main__":
    update_readme()
