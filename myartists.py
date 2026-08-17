import pylast, json, requests, glob, re
from lastfmcache import LastfmCache
from PIL import Image, UnidentifiedImageError
import os

# Last.fm stopped serving real artist images years ago and returns this gray
# "star" placeholder (or nothing) for every artist. Treat it as "no image".
LASTFM_PLACEHOLDER = "2a96cbd8b46e442fc41c2b86b821562f"

def deezer_image(name):
    """Look up an artist photo on Deezer (free, no auth). Returns a URL or None."""
    try:
        resp = requests.get("https://api.deezer.com/search/artist",
                            params={"q": name, "limit": 1}, timeout=15)
        data = resp.json().get("data", [])
        if data:
            # picture_xl is 1000x1000; fall back to whatever is present.
            return data[0].get("picture_xl") or data[0].get("picture_big") or data[0].get("picture")
    except Exception as e:
        print(f"Deezer lookup failed for {name}: {e}")
    return None

def resolve_image_url(name, lastfm_url):
    """Pick the best available image URL for an artist."""
    if lastfm_url and LASTFM_PLACEHOLDER not in lastfm_url:
        return lastfm_url
    return deezer_image(name)

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "artist"

def crop_center(pil_img, crop_width, crop_height):
    img_width, img_height = pil_img.size
    return pil_img.crop(((img_width - crop_width) // 2,
                         (img_height - crop_height) // 2,
                         (img_width + crop_width) // 2,
                         (img_height + crop_height) // 2))

def crop_max_square(pil_img):
    return crop_center(pil_img, min(pil_img.size), min(pil_img.size))

with open("config.json", "r+") as f:
    config = json.load(f)

network = pylast.LastFMNetwork(api_key=config['apikey'], api_secret=config['secret'], username=config['username'], password_hash=pylast.md5(config['password']))
cache = LastfmCache(config['apikey'], config['secret'])
cache.enable_file_cache()


try:
    artists = network.get_authenticated_user().get_top_artists(limit=6, period=pylast.PERIOD_7DAYS)
except Exception as e:
    print(e)

artist_dict = {}

for a in artists:
    artist = cache.get_artist(a.item.name)
    # Prefer Last.fm's image, but fall back to Deezer when it's missing/placeholder.
    artist_dict[a.item.name] = resolve_image_url(a.item.name, artist.cover_image)

FALLBACK_URL = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"

os.makedirs("artist_images", exist_ok=True)

for k, v in artist_dict.items():
    if not v:
        v = FALLBACK_URL

    resp = requests.get(v, timeout=15)
    # If the image fetch failed or didn't return image data, fall back.
    if resp.status_code != 200 or not resp.headers.get("Content-Type", "").startswith("image/"):
        resp = requests.get(FALLBACK_URL, timeout=15)

    # Name the file after the artist so it's stable and unique (Deezer URLs all
    # share the same generic filename).
    path = os.path.join("artist_images", slugify(k) + ".jpg")
    with open(path, "wb") as f:
        f.write(resp.content)
    artist_dict[k] = path

new_height, new_width = (250, 250)
for a in list(artist_dict.values()):
    try:
        im = Image.open(a)
        im.verify()          # confirm it's a valid image before processing
        im = Image.open(a)   # reopen: verify() leaves the file unusable
    except (UnidentifiedImageError, OSError) as e:
        print(f"Skipping invalid image {a}: {e}")
        continue
    im_thumb = crop_max_square(im).resize((500, 500), Image.LANCZOS)
    im_thumb = im_thumb.convert("RGB")
    im_thumb.save(a)

url_temp = "https://raw.githubusercontent.com/M4cs/M4cs/master/"

template = """\
## Who I've Been Listening To This Week

"""

for image in artist_dict.values():
    template = template + "| <img src=" + url_temp + image.replace('\\', '/') + "> "
template = template + " |\n| :---: | :---: | :---: | :---: | :---: | :---: |\n"
for artist in artist_dict.keys():
    template = template + "| " + "<b>" + artist + "</b> "
template = template + " |\n"


readme = open("READMECOPY.md", "r").read()
with open("README.md", "w") as f:
    f.write(readme.format(template=template))


os.system("git add . && git commit -m \"Update Artists\" && git push")