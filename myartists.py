import pylast, json, requests, glob
from lastfmcache import LastfmCache
from PIL import Image
import os

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
    artist_dict.update({ a.item.name : artist.cover_image })

for k, v in artist_dict.items():
    if not v:
        v = "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_960_720.png"
    res = requests.get(v).content
    with open("artist_images\\" + v.split('/')[-1], "wb") as f:
        f.write(res)
    artist_dict[k] = "artist_images\\" + v.split('/')[-1]

new_height, new_width = (250, 250)
for a in glob.glob("artist_images\\*.jpg"):
    im = Image.open(a)
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