import base64
import io
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import qrcode
import httpx
from PIL import Image
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI()

# Define the request body schema for the endpoint
class InferenceRequest2(BaseModel):
    qr_code_content: str
    # logo_base64: str
    download_link:str
   
# Add CORS middleware with settings to allow all domains
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all domains
    allow_credentials=True,  # Allow cookies to be sent with cross-origin requests
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)   


@app.post("/generate_logo/")
async def generate_image(request: InferenceRequest2):
    try:
        # Ensure QR code content is provided
        if not request.qr_code_content:
            raise HTTPException(status_code=400, detail="QR Code Content is required")

        # Decode base64 logo image and convert to PIL Image
        # logo_image_data = base64.b64decode(request.logo_base64)
        # logo_image = Image.open(io.BytesIO(logo_image_data)).convert("RGBA")

        # Download the logo image from the provided download link
        async with httpx.AsyncClient() as client:
            response = await client.get(request.download_link)
            if response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to download the logo image.")
            logo_image_data = response.content

        # Convert the downloaded image data to a PIL Image
        logo_image = Image.open(io.BytesIO(logo_image_data)).convert("RGBA")

        # Ensure logo_image is in correct format (PIL Image)
        if not isinstance(logo_image, (Image.Image)):
            raise ValueError(f"Input type {type(logo_image)} is not supported. Expected PIL.Image.Image.")

        # # Provide a default prompt if none is provided
        # default_prompt = request.prompt

        # # Configure the pipeline scheduler
        # pipe.scheduler = SAMPLER_MAP[request.sampler](pipe.scheduler.config)
        # generator = torch.manual_seed(request.seed) if request.seed != -1 else torch.Generator()

        # # Run inference using the QR code image as control
        # output = pipe(
        #     prompt=default_prompt,
        #     negative_prompt=request.negative_prompt,
        #     image=logo_image,
        #     control_image=logo_image,
        #     width=768,
        #     height=768,
        #     guidance_scale=request.guidance_scale,
        #     controlnet_conditioning_scale=request.controlnet_conditioning_scale,
        #     generator=generator,
        #     strength=request.strength,
        #     num_inference_steps=50,
        # )

        # # Get the generated image
        # generated_image = output.images[0]
        generated_image = logo_image

        # Generate QR code image
        qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
        qr.add_data(request.qr_code_content)
        qr.make(fit=True)

        qrcode_image = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

        # Ensure the logo fits within the QR code and is square
        qr_width, qr_height = qrcode_image.size
        logo_width, logo_height = logo_image.size

        # Resize logo to make it square, maintaining aspect ratio
        size = min(logo_width, logo_height)  # Take the smaller dimension
        logo_image = logo_image.resize((size, size), Image.Resampling.LANCZOS)

        # Resize logo image to fit within the QR code, maintaining its aspect ratio
        max_logo_size = min(qr_width, qr_height) // 4  # Limit the logo size to 25% of QR code
        if logo_image.width > max_logo_size:
            logo_image = logo_image.resize(
                (max_logo_size, max_logo_size), Image.Resampling.LANCZOS
            )

        # Calculate position to place the logo at the center of the QR code
        logo_x = (qr_width - logo_image.width) // 2
        logo_y = (qr_height - logo_image.height) // 2

        # Paste the logo onto the QR code image
        qrcode_image.paste(logo_image, (logo_x, logo_y), logo_image)

        # Resize generated_image to match the dimensions of the QR code
        generated_image = generated_image.resize((qr_width, qr_height), Image.Resampling.LANCZOS)

        # Now combine the generated image with the QR code if needed (depending on use case)
        final_image = Image.alpha_composite(generated_image.convert("RGBA"), qrcode_image)

        # Return the final image as a PNG
        output_image = io.BytesIO()
        final_image.save(output_image, format="PNG")
        output_image.seek(0)
        return StreamingResponse(output_image, media_type="image/png")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

