import urllib.request
import json
import xml.etree.ElementTree as ET
import re
import os
import ssl

RSS_URL = "https://www.khola.blog/feed"
META_PATH = "img/latest_post.json"
THUMBNAIL_PATH = "img/latest_post_thumbnail.jpg"

def get_image_from_content(content):
    match = re.search(r'<img[^>]+src="([^">]+)"', content)
    return match.group(1) if match else None

def main():
    # Set current working directory to script's parent directory (repo root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(script_dir)
    os.chdir(repo_root)

    # Fetch RSS feed
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(RSS_URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req, context=ctx) as response:
            xml_data = response.read()
    except Exception as e:
        print(f"Error fetching RSS: {e}")
        return

    root = ET.fromstring(xml_data)
    channel = root.find('channel')
    if not channel:
        print("No channel found")
        return
        
    first_item = channel.find('item')
    if not first_item:
        print("No items found")
        return
        
    title = first_item.findtext('title')
    link = first_item.findtext('link')
    pubDate = first_item.findtext('pubDate')
    description = first_item.findtext('description')
    
    # Try to extract content encoded for better image extraction
    content_encoded = None
    for child in first_item:
        if child.tag.endswith('encoded') and 'content' in child.tag:
            content_encoded = child.text
            
    # Figure out image URL
    image_url = None
    enclosure = first_item.find('enclosure')
    if enclosure is not None and enclosure.get('url'):
        image_url = enclosure.get('url')
        
    if not image_url and content_encoded:
        image_url = get_image_from_content(content_encoded)
        
    if not image_url and description:
        image_url = get_image_from_content(description)

    # Load existing meta to check if we need to update
    existing_meta = {}
    if os.path.exists(META_PATH):
        try:
            with open(META_PATH, 'r') as f:
                existing_meta = json.load(f)
        except Exception:
            pass

    if existing_meta.get('link') == link and existing_meta.get('pubDate') == pubDate and os.path.exists(THUMBNAIL_PATH):
        print("Latest post is already cached.")
        return

    # Download image
    thumbnail_rel_path = ""
    if image_url:
        try:
            print(f"Downloading image from {image_url}")
            img_req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(img_req, context=ctx) as img_res:
                os.makedirs(os.path.dirname(THUMBNAIL_PATH), exist_ok=True)
                with open(THUMBNAIL_PATH, 'wb') as f:
                    f.write(img_res.read())
            thumbnail_rel_path = THUMBNAIL_PATH
        except Exception as e:
            print(f"Error downloading image: {e}")

    clean_desc = description if description else ""
    clean_desc = re.sub(r'<[^>]+>', '', clean_desc).strip()

    new_meta = {
        "title": title,
        "link": link,
        "description": clean_desc,
        "thumbnail": thumbnail_rel_path,
        "pubDate": pubDate
    }

    os.makedirs(os.path.dirname(META_PATH), exist_ok=True)
    with open(META_PATH, 'w') as f:
        json.dump(new_meta, f, indent=2)

    print(f"Updated cache for latest post: {title}")

if __name__ == "__main__":
    main()
