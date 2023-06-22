import os
import tempfile
import fitz
import numpy as np
import string
from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont
from keras.models import load_model

# Define system variable
model = load_model(os.getenv("MODEL_PATH"), compile=False)  # Load the model
class_names = open(os.getenv("LABEL_PATH"), "r").readlines()  # Load the labels
chars = list(string.digits + string.ascii_letters)  # Get list possible character
fontsize, dim = 175, 224  # Set dimensions

# Define reusable function
def char_in_font(unicode_char, font):
    if 'cmap' not in font.keys():
        return False

    for cmap in font['cmap'].tables:
        if cmap.isUnicode():
            if ord(unicode_char) in cmap.cmap:
                return True
    return False


def draw_char(char, font_path, font_name):
    # Set canvas size
    W, H = dim, dim
    # Set font
    font = ImageFont.truetype(font_path, fontsize)
    # Make empty image
    image = Image.new('RGB', (W, H), color='white')
    # Draw text to image
    draw = ImageDraw.Draw(image)
    _, _, w, h = font.getbbox(char)
    draw.text(((W-w)/2, ((H-h)/2)-dim/17), char, 0, font=font)

    # turn the image into a numpy array
    image_array = np.asarray(image)

    # Normalize the image
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1

    # Load the image into the array
    return normalized_image_array

def compute_method5(pdf_file):
    # Open file
    pdf = fitz.open(pdf_file)
    data = {
        'fonts': {},
        'pages': [],
    }

    # Get all fonts across document
    fonts = list({el for i in range(pdf.page_count) for el in pdf.get_page_fonts(i)})
    embedded_fonts = []

    # Loop through fonts
    for font in fonts:
        # Extract font
        name, ext, _, content = pdf.extract_font(font[0])
        name = name.split('+')[-1]

        # If font is embedded
        if ext == 'ttf':
            # Write fonts
            f = tempfile.NamedTemporaryFile(suffix=ext, delete=False)  # Open file
            f.write(content)  # Write content
            f.close() # Close temporary file

            # Append to array
            embedded_fonts.append((f.name, name))

    # Setup problematic font map
    hashmap = {}

    # Loop through embedded fonts
    for filename, fontname in embedded_fonts:
        font = TTFont(filename)
        hashmap[fontname] = {}

        # Loop through characters
        for char in chars:
            if not char_in_font(char, font):
                continue

            # Render characters
            input = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
            input[0] = draw_char(char, filename, fontname)
            # Detect characters with OCR
            prediction = model.predict(input, verbose=0)
            index = np.argmax(prediction)
            class_name = class_names[index].strip()

            # If character detected
            if class_name != char:
                hashmap[fontname][char] = True

        if len(hashmap[fontname].keys()) == 0:
            del hashmap[fontname]

    # Set hashmap to data
    data['fonts'] = hashmap

    # Loop through pages
    for page in pdf:
        page_width, page_height = page.mediabox_size  # Get page width and height
        result = page.get_text('rawdict')  # read page text as a dictionary

        items = []
        for block in result['blocks']:  # iterate through the text blocks
            if 'lines' not in block.keys():
                continue

            for line in block['lines']:  # iterate through the text lines
                for span in line['spans']:  # iterate through the text spans
                    for char in span['chars']:  # iterate through text chars
                        if span['font'] in hashmap and char['c'] in hashmap[span['font']]:
                            items.append({
                                'font': span['font'],
                                'char': char['c'],
                                'rect': {
                                    'x1': char['bbox'][0],
                                    'y1': char['bbox'][1],
                                    'x2': char['bbox'][2],
                                    'y2': char['bbox'][3]
                                }
                            })

        if len(items) > 0:
            data['pages'].append({
                'page': page.number,
                'width': page_width,
                'height': page_height,
                'items': items
            })

    # Close resource
    pdf.close()

    # Delete file
    for filename, fontname in embedded_fonts:
        if os.path.exists(filename):
            os.unlink(filename)

    return data