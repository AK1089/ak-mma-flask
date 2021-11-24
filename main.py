# save files
import os
# Flask - python website framework
from flask import Flask, flash, request, redirect, url_for, send_from_directory
from werkzeug.utils import secure_filename
# various functions
import requests
# image uploading API
# Image sequencing library used to get RGB data from input pictures
from PIL import Image
# to post to paste.minr.org
import json

WEB_ADDRESS = "https://ak-mma-flask.herokuapp.com"

# blocks and their respective RGB values on a map
data = '''127 178 56 grass_block
247 233 163 sand
255 252 245 diorite
255 0 0 redstone_block
199 199 199 cobweb
0 124 0 big_dripleaf
160 160 255 packed_ice
167 167 167 block_of_iron
255 255 255 white_concrete
164 168 184 clay
151 109 77 dirt
112 112 112 stone
64 64 225 water
143 119 72 oak_planks
216 127 51 acacia_planks
178 76 216 magenta_wool
102 153 216 light_blue_wool
229 229 51 yellow_wool
127 204 25 lime_wool
242 127 165 pink_wool
153 153 153 light_gray_wool
76 127 153 cyan_wool
51 76 178 blue_wool
102 76 51 dark_oak_planks
102 127 51 green_wool
153 51 51 red_wool
25 25 25 black_wool
250 238 77 block_of_gold
92 219 213 block_of_diamond
74 128 255 lapis_block
0 217 58 block_of_emerald
129 86 49 podzol
112 2 0 netherrack
209 177 161 white_terracotta
159 82 36 orange_terracotta
149 87 108 magenta_terracotta
112 108 138 light_blue_terracotta
186 133 36 yellow_terracotta
103 117 53 lime_terracotta
160 77 78 pink_terracotta
57 41 35 gray_terracotta
135 107 98 light_gray_terracotta
87 92 92 cyan_terracotta
122 73 88 purple_terracotta
76 62 92 blue_terracotta
76 50 35 brown_terracotta
76 82 42 green_terracotta
142 60 46 red_terracotta
37 22 16 black_terracotta
189 48 49 crimson_nylium
22 126 134 warped_nylium
100 100 100 deepslate
216 175 147 raw_iron_block'''

# a place for the colour data to be stored in a dictionary
colours = {}

# converts the raw text in data to a dictionary with namespaced block IDs as keys
for line in data.split('\n'):
    r,g,b, block = line.split(' ')
    colours[block] = (int(r), int(g), int(b))


# a function which gets the squared distance between two points in 3D space
# defined by RGB vectors, as a pretty good proxy for colour similarity
def calculateDistance(rgb1, rgb2):
    return ((rgb1[0] - rgb2[0]) ** 2 + (rgb1[1] - rgb2[1]) ** 2 + (rgb1[2] - rgb2[2]) ** 2)


# for an RGB vector, returns the block ID which most closely matches it
def closestMatch(rgb):

    # currentClosest stores the best match so far and its squared distance
    currentClosest = ('null', 90000)

    # for every colour, evaluate its distance function
    for c in colours:
        dist = calculateDistance(colours[c],rgb)

        # if it is a better match than the current closest, replace current closest
        if dist < currentClosest[1]:
            currentClosest = (c, dist)

    # return final best match having checked all possible colours
    return currentClosest


# takes in the name of a 128x128 PNG file and makes a text file with the commands
# to generate a map displaying the image
def createCommand(filename, baseBlock='white_concrete'):

    # deals with invalid base blocks
    if f' {baseBlock}\n' not in data:
        baseBlock = 'white_concrete'

    # parsing filename - only PNGs allowed!
    filename = filename.lower()
    if '.' in filename and '.png' not in filename:
        return ('Invalid file extension. Please use PNG files only.')
        return

    # strips png extensions from filename if applicable
    elif '.png' in filename:
        filename = filename.replace('.png', '')

    # start commands to reset the canvas and remove the script
    command = f'@fast\n@bypass /fill {startX} {startY-1} {startZ} {startX+127} {startY} {startZ+127} {baseBlock}\n@bypass /s r i -3329 120 -1544 Theta_the_end\n'
    command = command + '@bypass /tellraw {{player}} ["",{"text":"Successfully built map art from ","color":"dark_green"},{"text":"§FILENAMEHERE.png","color":"blue"},{"text":"!","color":"dark_green"}]\n'
    command = command.replace('§FILENAMEHERE', filename[7:])

    # loads RGB data from the image
    try:
        im = Image.open(filename + ".png")
        if im.size != (128, 128):
            im = im.resize((128, 128))
        pix = im.load()
    except FileNotFoundError:
        return (f'Unable to find {filename}.png - this sometimes occurs when your filename has ')


    # iterates through each pixel of the image in natural order (L-R, T-B)
    for zl in range(128):

        # list of commands at this current "line" (one layer on the Z-axis)
        cline = []
        clinetext = ''

        # each x-ordinate within this region
        for xl in range(128):

            # gets the block which most closely matches the pixel's colour
            try:
                match = closestMatch(pix[xl,zl][:3])[0]
            except IndexError:
                return ('Image too small - your image file must be exactly 128x128 pixels in size,')

            # add the block to make the colour right to the list
            cline.append(match)

        # wrote this a little while ago without commenting it and don't
        # know exactly how it works any more, but it gets the job done
        cline.append('null')
        currentStreak = -1
        lastBlock = cline[0]
        originalX = startX

        # handles the distinction between /setblock and /fill
        for block in cline:

            # if the same block appears as before, expand the streak for /fill
            if block == lastBlock:
                currentStreak += 1

            # otherwise, add an additional command
            else:

                # small optimisation: doesn't bother adding superfluous commands
                # to place down white concrete, as the background exists already
                if lastBlock != baseBlock:

                    # /setblock vs /fill
                    if currentStreak == 0:
                        clinetext += f'@bypass /setblock {originalX} {startY} {startZ+zl} {lastBlock}\n'
                    else:
                        clinetext += f'@bypass /fill {originalX} {startY} {startZ+zl} {originalX+currentStreak} {startY} {startZ+zl} {lastBlock}\n'

                # resets for the next streak
                originalX = originalX + currentStreak + 1
                currentStreak = 0
                lastBlock = block

        # adds the last command of the line
        command = command + clinetext

    # posts to paste.minr.org
    try:
        req = requests.post('https://paste.minr.org/documents', data=command)
        key = json.loads(req.content)["key"]

        # opens website and displays success message
        return (f"/s i i -3329 120 -1544 Theta_the_end {key}\n")

    # KeyError: 'key' if script is too long
    except KeyError:
        return ("Script is too long for hastebin to handle. Please try again with a less detailed image.")


# starting coordinates for generating setblock commands
startX = -3392
startY = 140
startZ = -1600

# only allows PNGs, saved to this directory
UPLOAD_FOLDER = '/tmp/'
ALLOWED_EXTENSIONS = {"png"}

# Flask setup
app = Flask(__name__, static_url_path='/tmp/', static_folder='/tmp/')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# checks if a file is a .png
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# returns the actual image itself
@app.route("/view/<filename>")
def view_image(filename):
    print(filename + ".png")
    print(os.getcwd())
    print(app.config['UPLOAD_FOLDER'])
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# generated scripts go here
@app.route("/scripts/<filename>&name=<username>")
def file(filename, username):

    # creates a hastebin script based on the image
    returnstring = createCommand(os.path.join(app.config['UPLOAD_FOLDER'], filename))

    # discord webhook data
    data = {}
    data["username"] = "New Map Script Announcer"
    data["embeds"] = []

    # discord webhook embed data
    embed = {}
    embed["title"] = f"Map Art Request from {username}"
    embed["description"] = returnstring
    embed["url"] = f"https://paste.minr.org/{returnstring.split(' ')[-1]}"

    # discord webhook URL
    url = "https://discord.com/api/webhooks/901857252368072774/Da9nsmOAtOsohg8AJacW7gnJyLKaxjU3aL2aGcADegd69TEo_fPjkt3tIygbBVxy92Gx"

    # if map creation was successful
    if "/s i i" in returnstring:

        # add image to discord embed
        embed["image"] = {"url": f"{WEB_ADDRESS}/view/{filename}"}
        data["embeds"].append(embed)

        # send discord webhook
        result = requests.post(url, json=data, headers={"Content-Type": "application/json"})
        try:
            result.raise_for_status()
        except requests.exceptions.HTTPError as err:
            return err

        # if successful, generate a somewhat detailed page
        returnstring = f"""<!doctype html>
<title>Generated Script</title>
<h1>Successfully generated map script of {filename} for {username}</h1>
<p>Click <a href="https://paste.minr.org/{returnstring.split(" ")[-1]}">here</a> to view your script.</p>
<p>To import your script, use the command <b>{returnstring}</b></p>
<p>This command has been automatically forwarded to the admins.</p>
<img src="{WEB_ADDRESS}/view/{filename}" alt="{filename}">"""
    return returnstring


# how to upload your files - idk how this works but it's Flask
@app.route('/upload', methods=['GET', 'POST'])
def uploadf():
    if request.method == 'POST':

        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        global username
        username = request.form['username']

        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = "abc" + secure_filename(file.filename)
            
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            return redirect(url_for('uploadf',
                                    filename=filename, name=username).replace("upload?filename=", "scripts/"))

    return '''
    <!doctype html>
    <title>AK1089's Mapmaking Tool</title>
    <h1>AK1089's Mapmaking Tool - Upload an image</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
      <br><br>
      <input type=text name=username value=Username>
    </form>
    <p>Images must be in PNG format - works best if size is 128x128</p>
    '''
