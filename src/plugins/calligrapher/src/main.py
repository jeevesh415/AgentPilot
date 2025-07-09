
import os
import json
import numpy as np
from datetime import datetime
import torch
from PIL import Image

from plugins.calligrapher.src.pipeline_calligrapher import CalligrapherPipeline
from plugins.calligrapher.src.models.calligrapher import Calligrapher
from plugins.calligrapher.src.models.transformer_flux_inpainting import FluxTransformer2DModel
from plugins.calligrapher.src.utils import get_bbox_from_mask, crop_image_from_bb, \
    resize_img_and_pad, generate_context_reference_image
from huggingface_hub import snapshot_download

# Download the base model FLUX.1-Fill-dev (granted access needed)
snapshot_download("black-forest-labs/FLUX.1-Fill-dev", token="")
# Download SigLIP image encoder (this model can also be automatically downloaded when running the code)
snapshot_download("google/siglip-so400m-patch14-384")
# Download Calligrapher model and test data
snapshot_download("Calligrapher2025/Calligrapher")

# Global settings.
with open(os.path.join(os.path.dirname(__file__), 'path_dict.json'), 'r') as f:
    path_dict = json.load(f)
SAVE_DIR = path_dict.get('save_dir', path_dict.get('gradio_save_dir', '/tmp/calligrapher'))


# Function of loading pre-trained models.
def load_models():
    base_model_path = path_dict['base_model_path']
    image_encoder_path = path_dict['image_encoder_path']
    calligrapher_path = path_dict['calligrapher_path']
    transformer = FluxTransformer2DModel.from_pretrained(base_model_path, subfolder="transformer",
                                                         torch_dtype=torch.bfloat16)
    pipe = CalligrapherPipeline.from_pretrained(base_model_path, transformer=transformer,
                                                torch_dtype=torch.bfloat16).to("cuda")
    model = Calligrapher(pipe, image_encoder_path, calligrapher_path, device="cuda", num_tokens=128)
    return model


# Init models.
model = load_models()
print('Model loaded!')


def process_and_generate(source_image, mask_image, reference_image, prompt, height, width,
                         scale, steps=50, seed=42, use_context=True, num_images=1):
    print('Begin processing!')
    # Job directory.
    job_name = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    job_dir = os.path.join(SAVE_DIR, job_name)
    os.makedirs(job_dir, exist_ok=True)

    # Save input images.
    source_image.save(os.path.join(job_dir, 'source_image.png'))
    mask_image.save(os.path.join(job_dir, 'mask_image.png'))

    # Resize source and mask.
    source_image = source_image.resize((width, height))
    mask_image = mask_image.resize((width, height), Image.NEAREST)
    mask_np = np.array(mask_image)
    mask_np[mask_np > 0] = 255
    mask_image = Image.fromarray(mask_np.astype(np.uint8))

    if reference_image is None:
        # If self-inpaint (no input ref): (1) get bounding box from the mask and (2) perform cropping to get the ref image.
        tl, br = get_bbox_from_mask(mask_image)
        # Convert irregularly shaped masks into rectangles.
        reference_image = crop_image_from_bb(source_image, tl, br)
    # Raw reference image before resizing.
    reference_image.save(os.path.join(job_dir, 'reference_image_raw.png'))
    reference_image_to_encoder = resize_img_and_pad(reference_image, target_size=(512, 512))
    reference_image_to_encoder.save(os.path.join(job_dir, 'reference_to_encoder.png'))
    reference_context = generate_context_reference_image(reference_image, width)

    if use_context:
        # Concat the context on the top of the input masked image in the pixel space.
        source_with_context = Image.new(source_image.mode, (width, reference_context.size[1] + height))
        source_with_context.paste(reference_context, (0, 0))
        source_with_context.paste(source_image, (0, reference_context.size[1]))
        # Concat the zero mask on the top of the mask image.
        mask_with_context = Image.new(mask_image.mode,
                                      (mask_image.size[0], reference_context.size[1] + mask_image.size[0]), color=0)
        mask_with_context.paste(mask_image, (0, reference_context.size[1]))

        source_image = source_with_context
        mask_image = mask_with_context

    all_generated_images = []
    for i in range(num_images):
        res = model.generate(
            image=source_image,
            mask_image=mask_image,
            ref_image=reference_image_to_encoder,
            prompt=prompt,
            scale=scale,
            num_inference_steps=steps,
            width=source_image.size[0],
            height=source_image.size[1],
            seed=seed + i,
        )[0]
        if use_context:
            res_vis = res.crop((0, reference_context.size[1], res.width, res.height))  # remove context
            mask_vis = mask_image.crop(
                (0, reference_context.size[1], mask_image.width, mask_image.height))  # remove context mask
        else:
            res_vis = res
            mask_vis = mask_image
        res_vis.save(os.path.join(job_dir, f'result_{i}.png'))
        all_generated_images.append((res_vis, f"Generating {i + 1} (Seed: {seed + i})"))

    return mask_vis, reference_image_to_encoder, all_generated_images


def test_calligrapher():
    # Create test images
    source_image = Image.new('RGB', (512, 512), color='white')
    mask_image = Image.new('L', (512, 512), color='black')
    # Add a white rectangle to the mask
    import numpy as np
    mask_array = np.array(mask_image)
    mask_array[100:200, 100:200] = 255
    mask_image = Image.fromarray(mask_array)
    
    reference_image = Image.new('RGB', (256, 256), color='blue')
    
    # Test the function
    print("Testing process_and_generate function...")
    try:
        result = process_and_generate(
            source_image=source_image,
            mask_image=mask_image,
            reference_image=reference_image,
            prompt="The text is 'Test'",
            height=512,
            width=512,
            scale=1.0,
            steps=10,  # Lower steps for faster testing
            seed=42,
            use_context=True,
            num_images=1
        )
        
        mask_vis, reference_demo, generated_images = result
        print(f"✓ Function executed successfully!")
        print(f"✓ Generated {len(generated_images)} images")
        print(f"✓ Mask visualization: {mask_vis.size}")
        print(f"✓ Reference demo: {reference_demo.size}")
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()