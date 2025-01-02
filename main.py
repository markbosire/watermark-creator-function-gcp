import os
from google.cloud import storage
from PIL import Image

# Initialize Google Cloud Storage client
storage_client = storage.Client()

# Path to the watermark file
WATERMARK_FILE = "watermark.png"

def add_watermark(input_path, output_path):
    """Adds a translucent, centered watermark to an image."""
    # Check if the watermark file exists
    if not os.path.exists(WATERMARK_FILE):
        print(f"Error: Watermark file '{WATERMARK_FILE}' not found.")
        return

    with Image.open(input_path) as img:
        watermark = Image.open(WATERMARK_FILE)

        # Ensure watermark is in RGBA mode
        watermark = watermark.convert("RGBA")
        
        # Resize watermark if it's too large (optional)
        watermark = watermark.resize((img.width // 4, img.height // 4))  # Adjust size as needed
        
        # Create a new watermark with adjusted transparency
        translucent_watermark = Image.new("RGBA", watermark.size)
        watermark_pixels = watermark.load()
        translucent_pixels = translucent_watermark.load()

        for x in range(watermark.width):
            for y in range(watermark.height):
                r, g, b, a = watermark_pixels[x, y]
                # Preserve fully transparent pixels
                if a == 0:
                    translucent_pixels[x, y] = (0, 0, 0, 0)
                else:
                    # Adjust alpha for translucency
                    translucent_pixels[x, y] = (r, g, b, int(a * 0.5))  # 50% transparency

        # Calculate position to center watermark
        watermark_width, watermark_height = watermark.size
        position = ((img.width - watermark_width) // 2, (img.height - watermark_height) // 2)
        
        # Paste the translucent watermark
        img.paste(translucent_watermark, position, translucent_watermark)
        img.save(output_path)

def watermark_image(event, context):
    """Background Cloud Function triggered by Cloud Storage."""
    bucket_name = event['bucket']
    file_name = event['name']

    if not file_name.lower().endswith(('.png', '.jpg', '.jpeg')):
        print(f"Skipping non-image file: {file_name}")
        return

    # Paths for temporary storage
    temp_local_file = f"/tmp/{file_name}"
    temp_local_output = f"/tmp/watermarked-{file_name}"

    # Download the image from GCS
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)
    blob.download_to_filename(temp_local_file)
    print(f"Downloaded {file_name} to {temp_local_file}")

    # Add the watermark
    add_watermark(temp_local_file, temp_local_output)
    print(f"Watermark added to {temp_local_output}")

    # Upload the watermarked image to GCS
    output_blob = bucket.blob(f"watermarked/{file_name}")
    output_blob.upload_from_filename(temp_local_output)
    print(f"Uploaded watermarked image to watermarked/{file_name}")
