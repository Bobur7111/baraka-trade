import os
import barcode
from barcode.writer import ImageWriter
from django.conf import settings


def generate_barcode_png(code):

    barcode_class = barcode.get_barcode_class('code128')

    output_dir = os.path.join(settings.MEDIA_ROOT, "barcodes")
    os.makedirs(output_dir, exist_ok=True)

    file_path = os.path.join(output_dir, code)

    my_barcode = barcode_class(code, writer=ImageWriter())

    filename = my_barcode.save(file_path)

    return filename